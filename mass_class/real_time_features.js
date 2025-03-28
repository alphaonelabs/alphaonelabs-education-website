// File: mass_class/real_time_features.js

class RealTimeFeatures {
    /**
     * Initializes the RealTimeFeatures instance with the provided options.
     * @param {Object} options - Configuration options.
     * @param {string} options.serverUrl - The WebSocket server URL.
     * @param {string} options.chatRoom - The chat room to join.
     */
    constructor(options) {
        this.serverUrl = options.serverUrl;
        this.chatRoom = options.chatRoom;
        this.ws = null;
    }

    /**
     * Establishes a WebSocket connection and sets up event listeners.
     */
    init() {
        this.ws = new WebSocket(this.serverUrl);

        this.ws.addEventListener('open', () = > {
            console.log('WebSocket connection opened');
            this.joinRoom(this.chatRoom);
        });

        this.ws.addEventListener('message', (event) => {
            this.handleIncomingData(event.data);
        });

        this.ws.addEventListener('close', () => {
            console.log('WebSocket connection closed');
        });

        this.ws.addEventListener('error', (error) => {
            console.error('WebSocket error:', error);
        });
    }

    /**
     * Sends a JSON message to join a specific chat room.
     * @param {string} room - The name of the chat room to join.
     */
    joinRoom(room) {
        const message = { type: 'joinRoom', room: room };
        this.send(message);
    }

    /**
     * Sends JSON-stringified data if the WebSocket is open.
     * @param {Object} data - The data to send.
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(data));
            } catch (error) {
                console.error('Error sending message:', error);
            }
        } else {
            console.warn('WebSocket is not open. Unable to send message:', data);
        }
    }

    /**
     * Parses incoming JSON messages and dispatches them based on the "type" field.
     * @param {string} data - The incoming message data.
     */
    handleIncomingData(data) {
        let parsed;
        try {
            parsed = typeof data === 'string' ? JSON.parse(data) : data;
        } catch (error) {
            console.error('Failed to parse incoming data:', error);
            return;
        }

        switch (parsed.type) {
            case 'chatMessage':
                this.displayChatMessage(parsed);
                break;
            case 'pollUpdate':
                this.updatePollResults(parsed);
                break;
            case 'notification':
                console.log('Notification:', parsed);
                break;
            default:
                console.warn('Unhandled message type:', parsed.type);
        }
    }

    /**
     * Appends incoming chat messages to the DOM element with id "chat-container" or logs them if absent.
     * @param {Object} data - The chat message data.
     */
    displayChatMessage(data) {
        const container = document.getElementById('chat-container');
        if (container) {
            const messageElement = document.createElement('div');
            messageElement.textContent = data.sender ? `${data.sender}: ${data.message}` : data.message;
            container.appendChild(messageElement);
        } else {
            console.log('Chat Message:', data);
        }
    }

    /**
     * Updates the DOM element with id "poll-container" to display current poll options and vote counts.
     * @param {Object} data - The poll update data.
     */
    updatePollResults(data) {
        const container = document.getElementById('poll-container');
        if (container) {
            container.innerHTML = '';
            if (data.options && typeof data.options === 'object') {
                for (const [option, votes] of Object.entries(data.options)) {
                    const optionElement = document.createElement('div');
                    optionElement.textContent = `${option}: ${votes} vote(s)`;
                    container.appendChild(optionElement);
                }
            } else {
                container.textContent = 'No poll data available.';
            }
        } else {
            console.log('Poll Update:', data);
        }
    }

    /**
     * Convenience method to send a chat message via the WebSocket.
     * @param {string} sender - The sender’s name.
     * @param {string} message - The chat message.
     */
    sendChatMessage(sender, message) {
        const data = {
            type: 'chatMessage',
            sender: sender,
            message: message
        };
        this.send(data);
    }

    /**
     * Convenience method to send a poll vote via the WebSocket.
     * @param {string|number} pollId - The poll identifier.
     * @param {string} option - The selected poll option.
     */
    sendPollVote(pollId, option) {
        const data = {
            type: 'pollVote',
            pollId: pollId,
            option: option
        };
        this.send(data);
    }
}

// Global helper function to initialize RealTimeFeatures and attach it to the window for global access.
function initRealTimeFeatures(options) {
    const realTimeFeatures = new RealTimeFeatures(options);
    realTimeFeatures.init();
    window.realTimeFeatures = realTimeFeatures;
    return realTimeFeatures;
}

// Attach the helper function to window for global accessibility.
window.initRealTimeFeatures = initRealTimeFeatures;