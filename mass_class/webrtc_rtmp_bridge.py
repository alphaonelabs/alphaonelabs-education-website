import argparse
import asyncio
import json
import logging

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder

logging.basicConfig(level=logging.INFO)

# Global set to hold active peer connections.
pcs = set()

async def offer(request):
    """
    HTTP POST handler for /offer.
    Expects a JSON body with an SDP offer.
    """
    params = await request.json()
    logging.info("Received offer: %s", params)

    # Create a new RTCPeerConnection and add it to the global set.
    pc = RTCPeerConnection()
    pcs.add(pc)
    logging.info("Created RTCPeerConnection: %s", pc)

    # Register an event handler to monitor connection state changes.
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info("Connection state changed: %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # Register an event handler for when new media tracks are received.
    @pc.on("track")
    async def on_track(track):
        logging.info("Track '%s' received", track.kind)
        # Initialize MediaRecorder with the RTMP URL from app configuration.
        recorder = MediaRecorder(request.app["rtmp_url"])
        await recorder.start()

        # When the track ends, stop the recorder.
        @track.on("ended")
        async def on_ended():
            logging.info("Track '%s' ended", track.kind)
            await recorder.stop()

    # Set the remote description from the received SDP offer.
    offer_desc = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer_desc)

    # Create and set the local answer.
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Return the SDP answer as JSON.
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })

async def on_shutdown(app):
    """
    Shutdown handler to cleanly close all active RTCPeerConnections.
    """
    logging.info("Shutting down: closing all RTCPeerConnections")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

def main():
    parser = argparse.ArgumentParser(description="WebRTC to RTMP Bridge")
    parser.add_argument("--host", default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--rtmp-url", required=True, help="RTMP URL for MediaRecorder")
    args = parser.parse_args()

    app = web.Application()
    # Store the RTMP URL in the application configuration.
    app["rtmp_url"] = args.rtmp_url
    app.router.add_post("/offer", offer)
    app.on_shutdown.append(on_shutdown)

    logging.info("Starting server on %s:%s", args.host, args.port)
    web.run_app(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()