/* Global variables */
let signalingChannel = null;
let peerConnection = null;

/* Asynchronously capture the teacher's screen stream */
async function startScreenCapture() {
    try {
        // Request screen media
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        // Attach the stream to the preview video element
        const preview = document.getElementById('screen-preview');
        if (preview) {
            preview.srcObject = stream;
            preview.play();
        }
        return stream;
    } catch (error) {
        console.error('Error capturing screen:', error);
        return null;
    }
}

/* Asynchronously capture the teacher's camera stream */
async function startCameraCapture() {
    try {
        // Request camera media
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        // Attach the stream to the preview video element
        const preview = document.getElementById('camera-preview');
        if (preview) {
            preview.srcObject = stream;
            preview.play();
        }
        return stream;
    } catch (error) {
        console.error('Error capturing camera:', error);
        return null;
    }
}

/* Initialize signaling via WebSocket and set up event listeners */
function initSignaling() {
    const signalingUrl = "wss://your-signaling-server.example.com"; // Replace with your real signaling server URL
    const ws = new WebSocket(signalingUrl);

    ws.addEventListener('open', () = > {
        console.log('Signaling connection opened.');
    });

    ws.addEventListener('message', (event) => {
        console.log('Received signaling message:', event.data);
        let message;
        try {
            message = JSON.parse(event.data);
        } catch (error) {
            console.error("Error parsing signaling message:", error);
            return;
        }
        if (message.type === 'answer') {
            // Set the remote description with the answer SDP
            if (peerConnection) {
                peerConnection.setRemoteDescription(new RTCSessionDescription(message))
                    .catch(e => console.error("Error setting remote description:", e));
            }
        } else if (message.type === 'candidate') {
            // Add received ICE candidate to the peer connection
            if (peerConnection) {
                peerConnection.addIceCandidate(new RTCIceCandidate(message.candidate))
                    .catch(e => console.error("Error adding ICE candidate:", e));
            }
        }
    });

    ws.addEventListener('error', (error) => {
        console.error('Signaling error:', error);
    });

    ws.addEventListener('close', () => {
        console.log('Signaling connection closed.');
    });

    return ws;
}

/* Set up the RTCPeerConnection, add media tracks, and handle ICE candidates */
function setupPeerConnection(screenStream, cameraStream) {
    const configuration = {
        iceServers: [
            { urls: "stun:stun.l.google.com:19302" }
        ]
    };
    const pc = new RTCPeerConnection(configuration);

    // Add tracks from the screen stream to the connection
    if (screenStream) {
        screenStream.getTracks().forEach(track => {
            pc.addTrack(track, screenStream);
        });
    }

    // Add tracks from the camera stream to the connection
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => {
            pc.addTrack(track, cameraStream);
        });
    }

    // Handle ICE candidate events and send them to the signaling server
    pc.onicecandidate = (event) => {
        if (event.candidate && signalingChannel) {
            console.log("Sending ICE candidate:", event.candidate);
            signalingChannel.send(JSON.stringify({
                type: 'candidate',
                candidate: event.candidate
            }));
        }
    };

    return pc;
}

/* Generate an SDP offer, set it as the local description, and send it via the signaling channel */
async function negotiateConnection(pc) {
    try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        console.log('Sending SDP offer:', offer);
        signalingChannel.send(JSON.stringify(offer));
    } catch (error) {
        console.error('Error negotiating connection:', error);
    }
}

/* Orchestrate media capture and initiate the signaling process */
async function startTeacherStream() {
    try {
        // Capture both screen and camera streams concurrently
        const [screenStream, cameraStream] = await Promise.all([
            startScreenCapture(),
            startCameraCapture()
        ]);

        if (!screenStream || !cameraStream) {
            console.error('Failed to capture one or both media streams.');
            return;
        }

        // Initialize the signaling channel
        signalingChannel = initSignaling();

        // Once the signaling channel is open, set up the peer connection and negotiate the connection
        signalingChannel.addEventListener('open', () => {
            peerConnection = setupPeerConnection(screenStream, cameraStream);
            negotiateConnection(peerConnection);
        });
    } catch (error) {
        console.error('Error starting teacher stream:', error);
    }
}

/* Add an event listener to the "start-stream" button to initiate the teacher stream */
document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('start-stream');
    if (startButton) {
        startButton.addEventListener('click', startTeacherStream);
    } else {
        console.error("Start stream button not found.");
    }
});