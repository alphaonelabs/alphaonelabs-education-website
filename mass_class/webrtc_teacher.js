// URL of the signaling server. Adjust this to your server's address.
const SIGNALING_SERVER_URL = "wss://example-signaling-server.com";

// Global variables to hold the signaling channel, peer connection, and media streams.
let signaling;
let pc;
let screenStream;
let cameraStream;

/**
 * Asynchronously captures the teacher's screen using getDisplayMedia.
 * Attaches the captured stream to the 'screen-preview' video element.
 */
async function startScreenCapture() {
    try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        const preview = document.getElementById('screen-preview');
        if (preview) {
            preview.srcObject = stream;
        }
        return stream;
    } catch (error) {
        console.error("Error capturing screen:", error);
    }
}

/**
 * Asynchronously captures the teacher's camera using getUserMedia.
 * Attaches the captured stream to the 'camera-preview' video element.
 */
async function startCameraCapture() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        const preview = document.getElementById('camera-preview');
        if (preview) {
            preview.srcObject = stream;
        }
        return stream;
    } catch (error) {
        console.error("Error capturing camera:", error);
    }
}

/**
 * Initializes the signaling channel by opening a WebSocket connection to the signaling server.
 * Sets up listeners for open, message, error, and close events.
 */
function initSignaling() {
    signaling = new WebSocket(SIGNALING_SERVER_URL);

    signaling.onopen = () = > {
        console.log("WebSocket connection opened.");
    };

    signaling.onmessage = (message) => {
        const data = JSON.parse(message.data);
        if (data.type === "answer") {
            console.log("Received SDP answer:", data);
            pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
        } else if (data.type === "ice-candidate") {
            console.log("Received ICE candidate:", data);
            pc.addIceCandidate(new RTCIceCandidate(data.candidate))
              .catch(e => console.error("Error adding ICE candidate:", e));
        }
    };

    signaling.onerror = (error) => {
        console.error("WebSocket error:", error);
    };

    signaling.onclose = () => {
        console.warn("WebSocket connection closed.");
    };
}

/**
 * Configures the RTCPeerConnection, adds media tracks from both the screen and camera streams,
 * and handles ICE candidate events by sending them to the signaling server.
 */
function setupPeerConnection() {
    const config = {
        iceServers: [
            { urls: "stun:stun.l.google.com:19302" }
        ]
    };

    pc = new RTCPeerConnection(config);

    // Add all tracks from the screen stream.
    if (screenStream) {
        screenStream.getTracks().forEach((track) => {
            pc.addTrack(track, screenStream);
        });
    }

    // Add all tracks from the camera stream.
    if (cameraStream) {
        cameraStream.getTracks().forEach((track) => {
            pc.addTrack(track, cameraStream);
        });
    }

    // When an ICE candidate is gathered, send it to the signaling server.
    pc.onicecandidate = (event) => {
        if (event.candidate) {
            console.log("Sending ICE candidate:", event.candidate);
            signaling.send(JSON.stringify({
                type: "ice-candidate",
                candidate: event.candidate
            }));
        }
    };

    pc.onconnectionstatechange = () => {
        console.log("Peer connection state:", pc.connectionState);
    };
}

/**
 * Negotiates the connection by creating an SDP offer, setting it as the local description,
 * and transmitting it via the signaling channel.
 */
async function negotiateConnection() {
    try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        console.log("Sending SDP offer:", offer);
        signaling.send(JSON.stringify({
            type: "offer",
            sdp: pc.localDescription
        }));
    } catch (error) {
        console.error("Error during negotiation:", error);
    }
}

/**
 * Orchestrates the teacher's stream:
 * - Captures the screen and camera media.
 * - Initializes the signaling process.
 * - Sets up the RTCPeerConnection.
 * - Initiates SDP negotiation.
 */
async function startTeacherStream() {
    // Capture both screen and camera simultaneously.
    [screenStream, cameraStream] = await Promise.all([
        startScreenCapture(),
        startCameraCapture()
    ]);

    if (!screenStream && !cameraStream) {
        console.error("No media streams available for streaming.");
        return;
    }

    // Establish a signaling connection.
    initSignaling();

    // Setup the peer connection with the captured streams.
    setupPeerConnection();

    // If the signaling channel is already open, initiate negotiation immediately.
    if (signaling.readyState === WebSocket.OPEN) {
        await negotiateConnection();
    } else {
        // Otherwise, wait for the signaling channel to open.
        signaling.addEventListener('open', async () => {
            await negotiateConnection();
        });
    }
}

// Add an event listener to the 'start-stream' button to initiate the teacher's stream.
document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('start-stream');
    if (startButton) {
        startButton.addEventListener('click', startTeacherStream);
    }
});