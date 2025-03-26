class RealTimeFeatures {
    constructor(options) {
        this.serverUrl = options.serverUrl;
        this.chatRoom = options.chatRoom;
        this.ws = null;
    }

    init() {
        this.ws = new WebSocket(this.serverUrl);
        this.ws.addEventListener('open', () = > {
            console.log('WebSocket connection opened.');
            // Join the specified chat room once the connection is open
            this.joinRoom(this.chatRoom);
        });
        this.ws.addEventListener('message', (event) => {
            this.handleIncomingData(event.data);
        });
        this.ws.addEventListener('close', () => {
            console.log('WebSocket connection closed.');
        });
        this.ws.addEventListener('error', (error) => {
            console.error('WebSocket encountered an error:', error);
        });
    }

    joinRoom(room) {
        const message = {
            action: 'join',
            room: room
        };
        this.send(message);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket is not open. Unable to send data:', data);
        }
    }

    handleIncomingData(data) {
        let parsedData;
        try {
            parsedData = JSON.parse(data);
        } catch (error) {
            console.error('Failed to parse incoming data:', error);
            return;
        }

        if (!parsedData.type) {
            console.warn('Received data without a type field:', parsedData);
            return;
        }

        switch (parsedData.type) {
            case 'chatMessage':
                this.displayChatMessage(parsedData);
                break;
            case 'pollUpdate':
                this.updatePollResults(parsedData);
                break;
            case 'notification':
                console.log('Notification:', parsedData);
                break;
            default:
                console.warn('Unhandled message type:', parsedData.type);
        }
    }

    displayChatMessage(data) {
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            const messageElement = document.createElement('div');
            messageElement.textContent = `${data.sender}: ${data.message}`;
            chatContainer.appendChild(messageElement);
        } else {
            console.log('Chat container not found. Chat message:', data);
        }
    }

    updatePollResults(data) {
        const pollContainer = document.getElementById('poll-container');
        if (pollContainer) {
            // Clear previous poll content
            pollContainer.innerHTML = '';
            if (data.options && Array.isArray(data.options)) {
                data.options.forEach(option => {
                    const optionElement = document.createElement('div');
                    optionElement.textContent = `${option.text}: ${option.votes}`;
                    pollContainer.appendChild(optionElement);
                });
            } else {
                pollContainer.textContent = 'No poll options available.';
            }
        } else {
            console.log('Poll container not found. Poll update:', data);
        }
    }

    sendChatMessage(sender, message) {
        const data = {
            type: 'chatMessage',
            sender: sender,
            message: message
        };
        this.send(data);
    }

    sendPollVote(pollId, option) {
        const data = {
            type: 'pollVote',
            pollId: pollId,
            vote: option
        };
        this.send(data);
    }
}

// Global helper function to initialize RealTimeFeatures
function initRealTimeFeatures(options) {
    const realTimeFeatures = new RealTimeFeatures(options);
    realTimeFeatures.init();
    window.realTimeFeatures = realTimeFeatures;
}

// If using a module system, you can export the class and helper function:
// export { RealTimeFeatures, initRealTimeFeatures };