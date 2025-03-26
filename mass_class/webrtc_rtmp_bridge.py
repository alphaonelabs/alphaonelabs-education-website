import argparse
import asyncio
import json
import logging

from aiohttp import web

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webrtc_rtmp_bridge")

# Global set to manage active peer connections
pcs = set()

async def offer(request):
    # Parse the incoming JSON to extract SDP offer details
    params = await request.json()
    sdp = params.get("sdp")
    offer_type = params.get("type")
    if sdp is None or offer_type is None:
        return web.Response(status=400, text="Invalid SDP offer")

    # Create a new RTCPeerConnection and add it to the global set
    pc = RTCPeerConnection()
    pcs.add(pc)
    logger.info("Created PeerConnection %s", pc)

    # Register event handler for connection state changes
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state changed: %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # Register event handler for new media tracks
    @pc.on("track")
    async def on_track(track):
        logger.info("Track received: %s", track.kind)
        # Retrieve the RTMP URL from the application configuration
        rtmp_url = request.app.get("RTMP_URL")
        if not rtmp_url:
            logger.error("RTMP URL not configured.")
            return

        # Instantiate and start the MediaRecorder using the RTMP URL
        recorder = MediaRecorder(rtmp_url)
        await recorder.start()

        # When the track ends, stop the recorder
        @track.on("ended")
        async def on_ended():
            logger.info("Track %s ended", track.kind)
            await recorder.stop()

    # Set remote description using the received SDP offer
    offer_desc = RTCSessionDescription(sdp=sdp, type=offer_type)
    await pc.setRemoteDescription(offer_desc)

    # Create and set the local answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Optionally wait for ICE gathering to complete
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.1)

    # Return the SDP answer as JSON
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })

async def on_shutdown(app):
    # Cleanly close all active peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

def main():
    parser = argparse.ArgumentParser(description="WebRTC to RTMP Bridge Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--rtmp-url", required=True, help="RTMP URL for recording streams")
    args = parser.parse_args()

    app = web.Application()
    # Register the /offer route
    app.router.add_post("/offer", offer)
    # Set the shutdown callback
    app.on_shutdown.append(on_shutdown)
    # Store the RTMP URL in the application configuration
    app["RTMP_URL"] = args.rtmp_url

    web.run_app(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()