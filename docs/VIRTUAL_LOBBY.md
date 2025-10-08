# Virtual Lobby Feature

## Overview

The Virtual Lobby is a real-time collaborative space where all users on the website can join, see each other, chat, and interact in a visual environment. It's similar to the virtual classroom feature but designed for casual social interaction and networking among learners.

## Features

### 1. Real-time User Presence
- See all active users in the lobby in real-time
- Users are represented as avatars on a canvas
- Active status tracking (users active within the last 5 minutes)

### 2. Visual Interaction
- Interactive canvas-based lobby space
- Click and drag to move your avatar around
- See other users' positions update in real-time
- Visual grid background for orientation

### 3. Chat System
- Real-time chat with all lobby participants
- System messages for join/leave events
- Message history during session
- Message counter

### 4. Lobby Management
- Maximum participant capacity control
- Active/inactive lobby states
- Admin interface for lobby configuration

## Technical Architecture

### Models

#### VirtualLobby
- **name**: Lobby name (default: "Main Lobby")
- **description**: Description of the lobby
- **is_active**: Whether the lobby is active
- **max_participants**: Maximum capacity (default: 100)
- **created_at/updated_at**: Timestamps

#### VirtualLobbyParticipant
- **user**: Foreign key to User
- **lobby**: Foreign key to VirtualLobby
- **joined_at/last_active**: Timestamps
- **position_x/position_y**: Avatar position coordinates
- **Unique constraint**: (lobby, user) - prevents duplicate entries

### WebSocket Communication

The lobby uses Django Channels for WebSocket communication:

**WebSocket URL**: `ws://[host]/ws/lobby/[lobby_id]/`

**Message Types**:

1. **participant_joined**: Broadcast when a user joins
2. **participant_left**: Broadcast when a user leaves
3. **position_updated**: Broadcast when a user moves
4. **chat_message**: Broadcast chat messages
5. **participants_list**: Initial list of active participants

## Usage

### Accessing the Lobby

1. Navigate to `/lobby/` (requires authentication)
2. The main lobby is automatically created if it doesn't exist
3. Your WebSocket connection is established automatically

### Moving Around

1. Click and hold on the canvas
2. Drag to move your avatar
3. Release to update your position
4. Other users will see your movement in real-time

### Chatting

1. Type your message in the chat input
2. Press Enter or click Send
3. Message is broadcast to all participants
4. System messages show join/leave events

## API Endpoints

### POST `/lobby/<lobby_id>/join/`
Join a lobby (creates VirtualLobbyParticipant)

### POST `/lobby/leave/`
Leave the lobby (removes VirtualLobbyParticipant)

## Testing

Run the test suite:

```bash
python manage.py test tests.test_virtual_lobby
```

## Dependencies

- Django Channels (WebSocket support)
- Channels Redis (Channel layer backend)
- Django authentication system
- Canvas API (frontend)
