/**
 * EncryptedVoiceChat - Implements end-to-end encrypted group voice chat
 * using WebRTC, WebSockets, and the Web Crypto API.
 */
class EncryptedVoiceChat {
    constructor(roomId, userId) {
        this.roomId = roomId;
        this.userId = userId;
        this.peers = {};
        this.localStream = null;
        this.encryptionKeys = {};
        this.socket = null;
        this.audioContext = null;
        this.analyser = null;
        this.speaking = false;
        this.muted = false;

        // Initialize WebSocket connection
        this.initializeWebSocket();
    }

    async initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const maxRetries = 5;
        let retries = 0;

        const connect = () => {
            console.log(`Attempting WebSocket connection (attempt ${retries + 1}/${maxRetries})...`);
            this.socket = new WebSocket(`${protocol}://${window.location.host}/ws/voice-chat/${this.roomId}/`);

            this.socket.onopen = () => {
                console.log('WebSocket connection established');
                retries = 0; // Reset retry counter on successful connection
                this.joinRoom();
            };

            this.socket.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    // Log all incoming messages for debugging
                    console.log(`[RECV] ${data.type} from ${data.from || 'server'} to ${data.target || 'all'}`);
                    await this.handleSignaling(data);
                } catch (error) {
                    console.error('Error handling WebSocket message:', error);
                }
            };

            this.socket.onclose = (event) => {
                console.log(`WebSocket connection closed: ${event.code} - ${event.reason}`);

                // Clear all peer connections and UI elements for existing participants
                // This ensures we don't show stale participants when the connection is lost
                if (event.code !== 1000 && event.code !== 1001) {
                    this.cleanupAllParticipants();
                }

                // Attempt to reconnect unless this was a normal closure
                if (event.code !== 1000 && event.code !== 1001 && retries < maxRetries) {
                    retries++;
                    const delay = Math.min(1000 * Math.pow(2, retries), 10000); // Exponential backoff up to 10 seconds
                    console.log(`Retrying connection in ${delay}ms...`);
                    setTimeout(connect, delay);
                } else if (retries >= maxRetries) {
                    console.error('Max WebSocket reconnection attempts reached.');
                    alert('Unable to connect to voice chat. Please refresh the page to try again.');
                }
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        };

        // Initial connection attempt
        connect();
    }

    async joinRoom() {
        try {
            // Get audio stream
            this.localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });

            // Generate encryption key
            const encryptionKey = await this.generateEncryptionKey();

            // Get username from document if available
            const username = document.querySelector('meta[name="username"]')?.getAttribute('content') || null;

            // Notify server about joining
            this.socket.send(JSON.stringify({
                type: 'join',
                userId: this.userId,
                roomId: this.roomId,
                username: username
            }));

            // Add current user to UI
            const isCurrentUser = true;
            this.addParticipantToUI(this.userId, username, isCurrentUser);

            // Set up audio visualization
            this.setupAudioVisualization();

            // Setup UI controls
            this.setupUIControls();

            // Start periodic sync to ensure UI remains accurate
            this.startPeriodicSync();

        } catch (error) {
            console.error('Error joining room:', error);
            alert('Could not access microphone. Please check your permissions and try again.');
        }
    }

    async generateEncryptionKey() {
        // Generate a new AES-GCM encryption key
        const key = await window.crypto.subtle.generateKey(
            {
                name: "AES-GCM",
                length: 256
            },
            true,
            ["encrypt", "decrypt"]
        );

        this.encryptionKeys[this.userId] = key;
        return key;
    }

    async exportPublicKeyData(key) {
        // Export key in a format that can be shared with peers
        return await window.crypto.subtle.exportKey("jwk", key);
    }

    async importPublicKeyData(keyData) {
        // Import a key from another peer
        return await window.crypto.subtle.importKey(
            "jwk",
            keyData,
            {
                name: "AES-GCM",
                length: 256
            },
            true,
            ["encrypt", "decrypt"]
        );
    }

    async encrypt(data, key) {
        // Generate a random IV for encryption
        const iv = window.crypto.getRandomValues(new Uint8Array(12));

        // Encrypt the data
        const encryptedData = await window.crypto.subtle.encrypt(
            {
                name: "AES-GCM",
                iv: iv
            },
            key,
            data
        );

        // Combine IV and encrypted data for transmission
        const result = new Uint8Array(iv.length + encryptedData.byteLength);
        result.set(iv, 0);
        result.set(new Uint8Array(encryptedData), iv.length);

        return result;
    }

    async decrypt(encryptedData, key) {
        // Extract IV from the combined data
        const iv = encryptedData.slice(0, 12);
        const data = encryptedData.slice(12);

        // Decrypt the data
        const decryptedData = await window.crypto.subtle.decrypt(
            {
                name: "AES-GCM",
                iv: iv
            },
            key,
            data
        );

        return decryptedData;
    }

    async createPeerConnection(peerId) {
        console.log(`Creating peer connection for ${peerId}`);
        const peerConnection = new RTCPeerConnection({
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        });

        // Add tracking flags for signaling
        peerConnection.hasPendingOffer = false;
        peerConnection.hasAnsweredOffer = false;

        // Add local stream to peer connection if it exists
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                peerConnection.addTrack(track, this.localStream);
            });
        } else {
            console.warn(`Local stream not available yet for peer ${peerId}, tracks will be added later`);

            // Attempt to get media stream if not already available
            try {
                this.localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });

                // Now add tracks since we have a stream
                this.localStream.getTracks().forEach(track => {
                    peerConnection.addTrack(track, this.localStream);
                });

                // If this is the first time getting the stream, setup audio visualization
                if (!this.audioContext) {
                    this.setupAudioVisualization();
                    this.setupUIControls();
                }
            } catch (error) {
                console.error('Error accessing microphone:', error);
                // Continue creating the connection without local tracks
                // The user will be able to hear others but not send audio
            }
        }

        // Handle ICE candidates
        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendSignalingMessage({
                    type: 'ice-candidate',
                    candidate: event.candidate,
                    target: peerId,
                    from: this.userId
                });
            }
        };

        // Log connection state changes
        peerConnection.oniceconnectionstatechange = () => {
            console.log(`ICE connection state with ${peerId} changed to: ${peerConnection.iceConnectionState}`);
        };

        peerConnection.onsignalingstatechange = () => {
            console.log(`Signaling state with ${peerId} changed to: ${peerConnection.signalingState}`);
        };

        peerConnection.onconnectionstatechange = () => {
            console.log(`Connection state with ${peerId} changed to: ${peerConnection.connectionState}`);
        };

        // Handle incoming tracks
        peerConnection.ontrack = (event) => {
            console.log(`Received track from ${peerId}`);
            this.handleRemoteTrack(peerId, event.streams[0]);
        };

        this.peers[peerId] = peerConnection;
        return peerConnection;
    }

    async handleSignaling(data) {
        const { type, from, target } = data;

        // Ignore messages not intended for this user
        if (target && target !== this.userId) return;

        try {
            console.log(`Processing signaling message: ${type}`, data);

            switch (type) {
                case 'participants_list':
                    this.updateParticipantsList(data.participants);
                    break;
                case 'user_joined':
                    await this.handleUserJoined(from, data.username);
                    break;
                case 'offer':
                    await this.handleOffer(data);
                    break;
                case 'answer':
                    await this.handleAnswer(data);
                    break;
                case 'ice-candidate':
                    await this.handleIceCandidate(data);
                    break;
                case 'user_left':
                    console.log(`User left event received for userId: ${from}`);
                    this.handleUserLeft(from);
                    break;
                case 'encryption-key':
                    await this.handleEncryptionKey(data);
                    break;
                case 'speaking_status_changed':
                    this.handleSpeakingStatusChange(data);
                    break;
                case 'mute_status_changed':
                    this.handleMuteStatusChange(data);
                    break;
                default:
                    console.warn(`Unknown message type: ${type}`);
            }
        } catch (error) {
            console.error(`Error handling signaling message of type ${type}:`, error);
        }
    }

    updateParticipantsList(participants) {
        console.log('Updating participants list:', participants);

        // Track current participants to detect stale ones
        const currentParticipantIds = new Set();
        participants.forEach(participant => {
            currentParticipantIds.add(participant.id.toString());
        });

        // First remove any participants that are no longer in the list
        this.removeStaleParticipants(currentParticipantIds);

        // Then create connections to all existing participants
        participants.forEach(async (participant) => {
            if (participant.id !== this.userId) {
                await this.handleUserJoined(participant.id, participant.username);

                // Update UI for existing participants
                const speakingIndicator = document.getElementById(`speaking-indicator-${participant.id}`);
                if (speakingIndicator) {
                    speakingIndicator.style.display = participant.is_speaking ? 'block' : 'none';
                }

                const mutedIndicator = document.getElementById(`muted-indicator-${participant.id}`);
                if (mutedIndicator) {
                    mutedIndicator.style.display = participant.is_muted ? 'block' : 'none';
                }

                // Update visualization if needed
                const visualizer = document.getElementById(`visualizer-${participant.id}`);
                if (visualizer && participant.is_muted) {
                    // This will be updated in the next visualization frame
                    const container = document.getElementById(`visualizer-container-${participant.id}`);
                    if (container) {
                        container.classList.add('opacity-75');
                    }
                }
            }
        });
    }

    removeStaleParticipants(currentParticipantIds) {
        // Get all participant elements in the UI
        const participantsContainer = document.getElementById('participants-container');
        if (!participantsContainer) return;

        // Create a new array from the children to avoid live collection issues during removal
        Array.from(participantsContainer.children).forEach(element => {
            // Extract the userId from the element ID (format: participant-{userId})
            const match = element.id.match(/participant-(.+)/);
            if (match) {
                const userId = match[1];

                // Skip the current user's element
                if (userId === this.userId) return;

                // If this participant is not in the current list, remove it
                if (!currentParticipantIds.has(userId)) {
                    console.log(`Removing stale participant: ${userId}`);
                    this.handleUserLeft(userId);
                }
            }
        });
    }

    async handleUserJoined(userId, username) {
        console.log(`User joined: ${userId}`);

        // Add the user to the participants list with username if provided
        this.addParticipantToUI(userId, username);

        // Create peer connection for new user
        await this.createPeerConnection(userId);

        // Make sure we have an encryption key
        if (!this.encryptionKeys[this.userId]) {
            try {
                console.log("Generating encryption key before sharing with peer");
                await this.generateEncryptionKey();
            } catch (error) {
                console.error("Error generating encryption key:", error);
            }
        }

        // Share encryption key with the new user if we have one
        if (this.encryptionKeys[this.userId]) {
            try {
                const keyData = await this.exportPublicKeyData(this.encryptionKeys[this.userId]);
                this.sendSignalingMessage({
                    type: 'encryption-key',
                    keyData: keyData,
                    target: userId,
                    from: this.userId
                });
            } catch (error) {
                console.error(`Error sharing encryption key with ${userId}:`, error);
            }
        } else {
            console.warn(`Could not share encryption key with ${userId} as it is not available`);
        }

        // Create and send offer
        try {
            console.log(`Creating offer for ${userId}...`);
            // Track pending offers to avoid duplicate signaling
            this.peers[userId].hasPendingOffer = true;

            const offer = await this.peers[userId].createOffer();
            await this.peers[userId].setLocalDescription(offer);

            this.sendSignalingMessage({
                type: 'offer',
                offer: offer,
                target: userId,
                from: this.userId
            });
        } catch (error) {
            console.error(`Error creating offer for ${userId}:`, error);
            // Reset the pending flag on error
            if (this.peers[userId]) {
                this.peers[userId].hasPendingOffer = false;
            }
        }
    }

    async handleOffer(data) {
        const { from, offer } = data;

        try {
            console.log(`Received offer from ${from}, state: ${this.peers[from]?.signalingState || 'no connection'}`);

            // Create peer connection if it doesn't exist
            if (!this.peers[from]) {
                await this.createPeerConnection(from);
            }

            const pc = this.peers[from];
            const signalingState = pc.signalingState;

            // Make sure we're in a state where we can set a remote offer
            if (signalingState !== 'stable') {
                console.warn(`Cannot set remote offer in state: ${signalingState}, rolling back`);
                await pc.setLocalDescription({type: "rollback"});
            }

            // Set remote description
            await pc.setRemoteDescription(new RTCSessionDescription(offer));
            console.log(`Set remote offer from ${from}, new state: ${pc.signalingState}`);

            // Create and send answer
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            console.log(`Created answer for ${from}, state: ${pc.signalingState}`);

            // Mark that we're expecting this connection to be established
            pc.hasAnsweredOffer = true;

            this.sendSignalingMessage({
                type: 'answer',
                answer: answer,
                target: from,
                from: this.userId
            });
        } catch (error) {
            console.error('Error handling offer:', error);
        }
    }

    async handleAnswer(data) {
        const { from, answer } = data;

        if (!this.peers[from]) {
            console.warn(`Received answer from unknown peer: ${from}`);
            return;
        }

        try {
            const pc = this.peers[from];
            const signalingState = pc.signalingState;
            console.log(`Received answer from ${from}, current state: ${signalingState}, hasPendingOffer: ${pc.hasPendingOffer}`);

            // Only process the answer if we sent an offer
            if (!pc.hasPendingOffer) {
                console.warn(`Received answer from ${from} but we didn't send an offer`);
                return;
            }

            // Only apply the answer if we're in the have-local-offer state
            if (signalingState === 'have-local-offer') {
                await pc.setRemoteDescription(new RTCSessionDescription(answer));
                console.log(`Successfully set remote answer from ${from}, new state: ${pc.signalingState}`);
                // Clear the pending offer flag
                pc.hasPendingOffer = false;
            } else if (signalingState === 'stable') {
                console.log(`Connection with ${from} already established, ignoring redundant answer`);
                pc.hasPendingOffer = false;
            } else {
                console.warn(`Cannot set remote description in state: ${signalingState}`);
            }
        } catch (error) {
            console.error(`Error setting remote description for ${from}:`, error);
            // Clear the pending flag on error
            if (this.peers[from]) {
                this.peers[from].hasPendingOffer = false;
            }
        }
    }

    async handleIceCandidate(data) {
        const { from, candidate } = data;

        if (!this.peers[from]) {
            console.warn(`Received ICE candidate for unknown peer: ${from}`);
            return;
        }

        try {
            const pc = this.peers[from];
            console.log(`Adding ICE candidate from ${from}, state: ${pc.signalingState}`);
            await pc.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (error) {
            // It's normal for this to throw errors if the remote description isn't set yet
            console.warn(`Failed to add ICE candidate from ${from}: ${error.message}`);
        }
    }

    handleUserLeft(userId) {
        console.log(`User left: ${userId}`);

        // Close peer connection if it exists
        if (this.peers[userId]) {
            this.peers[userId].close();
            delete this.peers[userId];
        }

        // Remove user's audio element
        const audioElement = document.getElementById(`audio-${userId}`);
        if (audioElement) {
            audioElement.remove();
        }

        // Remove user's participant card
        this.removeParticipantFromUI(userId);

        // Remove user's visualizer canvas
        const visualizer = document.getElementById(`visualizer-${userId}`);
        if (visualizer) {
            visualizer.remove();
        }

        // Remove user's visualizer container
        const visualizerContainer = document.getElementById(`visualizer-container-${userId}`);
        if (visualizerContainer) {
            visualizerContainer.remove();
        }

        // Remove encryption key for this user
        if (this.encryptionKeys[userId]) {
            delete this.encryptionKeys[userId];
        }
    }

    async handleEncryptionKey(data) {
        const { from, keyData } = data;

        // Import the encryption key from the peer
        const key = await this.importPublicKeyData(keyData);
        this.encryptionKeys[from] = key;
        console.log(`Received encryption key from ${from}`);
    }

    handleSpeakingStatusChange(data) {
        const { from, speaking } = data;
        const speakingIndicator = document.getElementById(`speaking-indicator-${from}`);
        if (speakingIndicator) {
            speakingIndicator.style.display = speaking ? 'block' : 'none';
        }
    }

    handleMuteStatusChange(data) {
        const { from, muted } = data;
        const mutedIndicator = document.getElementById(`muted-indicator-${from}`);
        if (mutedIndicator) {
            mutedIndicator.style.display = muted ? 'block' : 'none';
        }
    }

    addParticipantToUI(userId, username, isCurrentUser = false) {
        // Check if the participant already exists in the UI
        if (document.getElementById(`participant-${userId}`)) {
            return;
        }

        // Create participant element
        const participantElement = document.createElement('div');
        participantElement.id = `participant-${userId}`;

        const baseClasses = 'bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 w-28 flex flex-col items-center';
        participantElement.className = isCurrentUser ?
            `${baseClasses} ring-2 ring-teal-500 dark:ring-teal-400` : baseClasses;

        // Extract first letter of username for the avatar
        const displayName = username || `User ${String(userId).substring(0, 5)}`;
        const firstLetter = displayName.charAt(0).toUpperCase();

        participantElement.innerHTML = `
            <div class="relative">
                <div class="w-16 h-16 bg-teal-300 dark:bg-teal-500 rounded-full flex items-center justify-center mb-2 text-white text-xl">
                    ${firstLetter}
                </div>
                <div id="speaking-indicator-${userId}" class="absolute inset-0 border-2 border-green-600 dark:border-green-500 rounded-full hidden"></div>
                <div id="muted-indicator-${userId}" class="absolute bottom-0 right-0 bg-red-600 dark:bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hidden">
                    <i class="fas fa-microphone-slash"></i>
                </div>
                ${isCurrentUser ? `
                <div class="absolute -top-2 -right-2 bg-teal-500 dark:bg-teal-400 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">
                    <i class="fas fa-user"></i>
                </div>` : ''}
            </div>
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                ${displayName}${isCurrentUser ? ' (You)' : ''}
            </span>
        `;

        // Add to participants container
        document.getElementById('participants-container').appendChild(participantElement);

        // Update participant count
        this.updateParticipantsCount();

        // Create visualizer for this user
        this.createRemoteVisualization(userId, displayName);

        // Don't show speaking/muted indicators by default
        // (They will be controlled by the corresponding events)
    }

    removeParticipantFromUI(userId) {
        console.log(`Removing participant from UI: ${userId}`);

        // Remove the participant element
        const participantElement = document.getElementById(`participant-${userId}`);
        if (participantElement) {
            participantElement.remove();
            console.log(`Participant element removed for ${userId}`);
        } else {
            console.warn(`Participant element not found for ${userId}`);
        }

        // Remove from visualizer container
        const visualizerContainer = document.getElementById(`visualizer-container-${userId}`);
        if (visualizerContainer) {
            visualizerContainer.remove();
            console.log(`Visualizer container removed for ${userId}`);
        }

        // Remove the audio element
        const audioElement = document.getElementById(`audio-${userId}`);
        if (audioElement) {
            audioElement.remove();
            console.log(`Audio element removed for ${userId}`);
        }

        // Update participant count
        this.updateParticipantsCount();
    }

    updateParticipantsCount() {
        // Get count of participants in the container
        const count = document.querySelectorAll('#participants-container > div').length;

        // Update the count in the UI
        const countElements = document.querySelectorAll('.participants-count');
        countElements.forEach(element => {
            element.textContent = count;
        });
    }

    handleRemoteTrack(userId, stream) {
        // Create audio element for remote stream
        let audioElement = document.getElementById(`audio-${userId}`);

        if (!audioElement) {
            audioElement = document.createElement('audio');
            audioElement.id = `audio-${userId}`;
            audioElement.autoplay = true;
            document.getElementById('remote-audio-container').appendChild(audioElement);

            // Create visualization for this user
            this.createAudioVisualization(userId, stream);
        }

        audioElement.srcObject = stream;
    }

    setupAudioVisualization() {
        // Create audio context and analyzer for local stream
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;

        // Connect local stream to analyzer
        const source = this.audioContext.createMediaStreamSource(this.localStream);
        source.connect(this.analyser);

        // Create canvas for visualization
        const canvas = document.getElementById('local-visualizer');
        const canvasContext = canvas.getContext('2d');

        // Modern voice activity detection using AudioWorklet (if supported)
        // or fallback to deprecated ScriptProcessor
        let speechDetection;

        // Voice activity detection setup
        if (this.audioContext.audioWorklet) {
            // Use AudioWorklet for modern browsers
            const detectVoiceActivity = (rms) => {
                const threshold = 0.01; // Adjust based on testing
                const isSpeaking = rms > threshold;

                // Only update if status changed
                if (isSpeaking !== this.speaking && !this.muted) {
                    this.speaking = isSpeaking;

                    // Update the speaking indicator
                    const speakingIndicator = document.getElementById(`speaking-indicator-${this.userId}`);
                    if (speakingIndicator) {
                        speakingIndicator.style.display = this.speaking ? 'block' : 'none';
                    }

                    // Send speaking status to other participants
                    this.socket.send(JSON.stringify({
                        type: 'speaking_status',
                        speaking: this.speaking
                    }));
                }
            };

            // Set up RMS analyzer
            const rmsAnalyzer = this.audioContext.createAnalyser();
            rmsAnalyzer.fftSize = 256;
            source.connect(rmsAnalyzer);

            // Use regular interval instead of processor to avoid deprecation
            const analyzeVolume = () => {
                if (!this.localStream) return;

                const bufferLength = rmsAnalyzer.frequencyBinCount;
                const dataArray = new Float32Array(bufferLength);
                rmsAnalyzer.getFloatTimeDomainData(dataArray);

                let sum = 0;
                for (let i = 0; i < bufferLength; i++) {
                    sum += dataArray[i] * dataArray[i];
                }

                const rms = Math.sqrt(sum / bufferLength);
                detectVoiceActivity(rms);
            };

            // Analyze volume every 100ms
            this.volumeInterval = setInterval(analyzeVolume, 100);
        } else {
            // Fallback to ScriptProcessor (deprecated but still works)
            console.warn("Using deprecated ScriptProcessorNode. Consider upgrading your browser.");
            speechDetection = this.audioContext.createScriptProcessor(4096, 1, 1);
            source.connect(speechDetection);
            speechDetection.connect(this.audioContext.destination);

            speechDetection.onaudioprocess = (event) => {
                const input = event.inputBuffer.getChannelData(0);
                let sum = 0;

                // Calculate RMS (root mean square) as volume indicator
                for (let i = 0; i < input.length; i++) {
                    sum += input[i] * input[i];
                }

                const rms = Math.sqrt(sum / input.length);
                const threshold = 0.01; // Adjust based on testing
                const isSpeaking = rms > threshold;

                // Only update if status changed
                if (isSpeaking !== this.speaking && !this.muted) {
                    this.speaking = isSpeaking;

                    // Update the speaking indicator
                    const speakingIndicator = document.getElementById(`speaking-indicator-${this.userId}`);
                    if (speakingIndicator) {
                        speakingIndicator.style.display = this.speaking ? 'block' : 'none';
                    }

                    // Send speaking status to other participants
                    this.socket.send(JSON.stringify({
                        type: 'speaking_status',
                        speaking: this.speaking
                    }));
                }
            };
        }

        // Visualization loop
        const visualize = () => {
            requestAnimationFrame(visualize);

            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            this.analyser.getByteFrequencyData(dataArray);

            canvasContext.clearRect(0, 0, canvas.width, canvas.height);
            canvasContext.fillStyle = 'rgb(31, 41, 55)'; // dark:bg-gray-800
            canvasContext.fillRect(0, 0, canvas.width, canvas.height);

            const barWidth = (canvas.width / bufferLength) * 2.5;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = dataArray[i] / 2;

                if (this.muted) {
                    canvasContext.fillStyle = 'rgb(156, 163, 175)'; // gray-400
                } else {
                    // Use teal color palette for non-muted audio visualization
                    const intensity = Math.min(255, barHeight * 2);
                    canvasContext.fillStyle = `rgb(45, ${intensity}, 211)`; // teal color with dynamic intensity
                }

                canvasContext.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

                x += barWidth + 1;
            }
        };

        visualize();
    }

    createRemoteVisualization(userId, displayName) {
        const container = document.getElementById('remote-visualizers');

        // Create visualization container
        const visualizerContainer = document.createElement('div');
        visualizerContainer.id = `visualizer-container-${userId}`;
        visualizerContainer.className = 'bg-gray-100 dark:bg-gray-700 p-3 rounded-lg mb-3';

        // Convert userId to string to ensure substring works
        const userIdStr = String(userId);

        visualizerContainer.innerHTML = `
            <p class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">${displayName}</p>
            <canvas id="visualizer-${userId}" class="w-full h-24 bg-gray-900 dark:bg-gray-800 rounded"></canvas>
        `;

        container.appendChild(visualizerContainer);
    }

    createAudioVisualization(userId, stream) {
        // Create audio context and analyzer for remote stream
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;

        // Connect remote stream to analyzer
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        // Get canvas for visualization
        const canvas = document.getElementById(`visualizer-${userId}`);
        if (!canvas) return;

        const canvasContext = canvas.getContext('2d');

        // Visualization loop
        const visualize = () => {
            // Check if the visualizer still exists
            if (!document.getElementById(`visualizer-${userId}`)) {
                return;
            }

            requestAnimationFrame(visualize);

            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            analyser.getByteFrequencyData(dataArray);

            canvasContext.clearRect(0, 0, canvas.width, canvas.height);
            canvasContext.fillStyle = 'rgb(31, 41, 55)'; // dark:bg-gray-800
            canvasContext.fillRect(0, 0, canvas.width, canvas.height);

            const barWidth = (canvas.width / bufferLength) * 2.5;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = dataArray[i] / 2;

                // Check if the user is muted
                const mutedIndicator = document.getElementById(`muted-indicator-${userId}`);
                const isMuted = mutedIndicator && mutedIndicator.style.display === 'block';

                if (isMuted) {
                    canvasContext.fillStyle = 'rgb(156, 163, 175)'; // gray-400
                } else {
                    // Use teal color palette for non-muted audio visualization
                    const intensity = Math.min(255, barHeight * 2);
                    canvasContext.fillStyle = `rgb(45, ${intensity}, 211)`; // teal color with dynamic intensity
                }

                canvasContext.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

                x += barWidth + 1;
            }
        };

        visualize();
    }

    setupUIControls() {
        // Mute button
        const muteButton = document.getElementById('mute-button');
        muteButton.addEventListener('click', () => {
            this.toggleMute();
        });

        // Leave room button
        const leaveButton = document.getElementById('leave-button');
        leaveButton.addEventListener('click', () => {
            this.leaveRoom();
        });

        // Refresh participants button
        const refreshButton = document.getElementById('refresh-participants');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => {
                // Visual feedback for button click
                refreshButton.classList.add('animate-spin');
                setTimeout(() => {
                    refreshButton.classList.remove('animate-spin');
                }, 1000);

                // Request fresh participants list
                this.requestParticipantsList();
            });
        }
    }

    toggleMute() {
        this.muted = !this.muted;

        // Toggle audio tracks
        this.localStream.getAudioTracks().forEach(track => {
            track.enabled = !this.muted;
        });

        // Update mute button text
        const muteButton = document.getElementById('mute-button');
        muteButton.innerHTML = this.muted ?
            `<i class="fas fa-microphone-slash mr-2"></i> Unmute` :
            `<i class="fas fa-microphone mr-2"></i> Mute`;

        muteButton.className = this.muted ?
            'flex items-center justify-center px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition duration-200' :
            'flex items-center justify-center px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition duration-200';

        // Update muted indicator
        const mutedIndicator = document.getElementById(`muted-indicator-${this.userId}`);
        if (mutedIndicator) {
            mutedIndicator.style.display = this.muted ? 'block' : 'none';
        }

        // Send mute status to other participants
        this.socket.send(JSON.stringify({
            type: 'mute_status',
            muted: this.muted
        }));
    }

    leaveRoom(redirect = true) {
        // Stop all tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                track.stop();
            });
        }

        // Clear intervals
        if (this.volumeInterval) {
            clearInterval(this.volumeInterval);
        }

        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }

        // Close all peer connections
        Object.values(this.peers).forEach(peer => {
            peer.close();
        });

        // Close WebSocket connection
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.close();
        }

        // Redirect to room list if specified
        if (redirect) {
            window.location.href = '/voice-chat/';
        }
    }

    // Add a method for sending messages with logging
    sendSignalingMessage(message) {
        // Check if socket exists and is open
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.warn(`Cannot send message of type ${message.type}: WebSocket not open`);
            return;
        }

        // Log all outgoing messages for debugging
        console.log(`[SEND] ${message.type} to ${message.target || 'all'} from ${this.userId}`);
        this.socket.send(JSON.stringify(message));
    }

    cleanupAllParticipants() {
        console.log('Cleaning up all participants due to connection loss');

        // Get IDs of all peers
        const peerIds = Object.keys(this.peers);

        // Close all peer connections
        peerIds.forEach(peerId => {
            if (peerId !== this.userId) {
                this.handleUserLeft(peerId);
            }
        });

        // Clear participants container except for current user
        const participantsContainer = document.getElementById('participants-container');
        const currentUserElement = document.getElementById(`participant-${this.userId}`);

        if (participantsContainer) {
            // Create a new array from the children to avoid live collection issues during removal
            Array.from(participantsContainer.children).forEach(element => {
                if (element.id !== `participant-${this.userId}`) {
                    element.remove();
                }
            });
        }

        // Update participant count
        this.updateParticipantsCount();
    }

    startPeriodicSync() {
        // Request participants list every 10 seconds to ensure UI stays in sync
        this.syncInterval = setInterval(() => {
            this.requestParticipantsList();
        }, 10000);
    }

    requestParticipantsList() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('Requesting current participants list from server');
            this.socket.send(JSON.stringify({
                type: 'get_participants',
                roomId: this.roomId
            }));
        }
    }

    getCsrfToken() {
        // Get CSRF token from cookie
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        return cookieValue || '';
    }
}

// Initialize voice chat when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const roomIdInput = document.getElementById('room-id');
    const userIdInput = document.getElementById('user-id');

    if (roomIdInput && userIdInput) {
        const roomId = roomIdInput.value;
        const userId = userIdInput.value;

        if (roomId && userId) {
            window.voiceChat = new EncryptedVoiceChat(roomId, userId);
        }
    }
});
