import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import VirtualLobby, LobbyParticipant

logger = logging.getLogger(__name__)


class LobbyConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for virtual lobby real-time communication."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.lobby_id = self.scope['url_route']['kwargs']['lobby_id']
        self.lobby_group_name = f'lobby_{self.lobby_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if lobby exists and user can join
        lobby = await self.get_lobby()
        if not lobby:
            await self.close(code=4004)  # Lobby not found
            return
        
        can_join, message = await self.can_user_join_lobby()
        if not can_join:
            await self.close(code=4000)  # Cannot join lobby
            return
        
        # Join lobby group
        await self.channel_layer.group_add(
            self.lobby_group_name,
            self.channel_name
        )
        
        # Create or update participant
        participant = await self.get_or_create_participant()
        if participant:
            participant.mark_online()
            
            # Accept connection
            await self.accept()
            
            # Send current lobby state to user
            await self.send_lobby_state()
            
            # Notify others that user joined
            await self.channel_layer.group_send(
                self.lobby_group_name,
                {
                    'type': 'user_joined',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'display_name': participant.get_display_name(),
                    'position_x': participant.position_x,
                    'position_y': participant.position_y,
                    'avatar_color': participant.avatar_color,
                    'timestamp': timezone.now().isoformat()
                }
            )
        else:
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'lobby_group_name'):
            # Mark participant as offline
            participant = await self.get_participant()
            if participant:
                participant.mark_offline()
            
            # Leave lobby group
            await self.channel_layer.group_discard(
                self.lobby_group_name,
                self.channel_name
            )
            
            # Notify others that user left
            await self.channel_layer.group_send(
                self.lobby_group_name,
                {
                    'type': 'user_left',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def receive(self, text_data):
        """Handle received WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'user_movement':
                await self.handle_user_movement(data)
            elif message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'user_action':
                await self.handle_user_action(data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_user_movement(self, data):
        """Handle user movement in the virtual space."""
        x = data.get('x', 0)
        y = data.get('y', 0)
        
        # Update participant position
        participant = await self.get_participant()
        if participant:
            participant.update_position(x, y)
            
            # Broadcast movement to other users
            await self.channel_layer.group_send(
                self.lobby_group_name,
                {
                    'type': 'user_moved',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'x': x,
                    'y': y,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def handle_chat_message(self, data):
        """Handle chat messages."""
        message = data.get('message', '').strip()
        if not message:
            return
        
        participant = await self.get_participant()
        if not participant or participant.is_muted:
            return
        
        # Broadcast message to lobby
        await self.channel_layer.group_send(
            self.lobby_group_name,
            {
                'type': 'chat_message',
                'user_id': self.user.id,
                'username': self.user.username,
                'display_name': participant.get_display_name(),
                'avatar_color': participant.avatar_color,
                'message': message,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def handle_user_action(self, data):
        """Handle user actions (wave, emoji, etc.)."""
        action = data.get('action')
        if not action:
            return
        
        participant = await self.get_participant()
        if participant:
            await self.channel_layer.group_send(
                self.lobby_group_name,
                {
                    'type': 'user_action',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'display_name': participant.get_display_name(),
                    'action': action,
                    'timestamp': timezone.now().isoformat()
                }
            )
    
    async def handle_ping(self):
        """Handle ping to keep connection alive."""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def send_lobby_state(self):
        """Send current lobby state to the connected user."""
        lobby = await self.get_lobby()
        if not lobby:
            return
        participants = await self.get_online_participants()
        
        state = {
            'type': 'lobby_state',
            'lobby': {
                'id': lobby.id,
                'name': lobby.name,
                'description': lobby.description,
                'online_count': len(participants),
                'max_users': lobby.max_users
            },
            'participants': [
                {
                    'user_id': p.user.id,
                    'username': p.user.username,
                    'display_name': p.get_display_name(),
                    'position_x': p.position_x,
                    'position_y': p.position_y,
                    'avatar_color': p.avatar_color,
                    'is_online': p.is_online
                }
                for p in participants
            ],
            'timestamp': timezone.now().isoformat()
        }
        }
        
        await self.send(text_data=json.dumps(state))
    
    # Event handlers for group messages
    async def user_joined(self, event):
        """Handle user joined event."""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event['user_id'],
            'username': event['username'],
            'display_name': event['display_name'],
            'position_x': event['position_x'],
            'position_y': event['position_y'],
            'avatar_color': event['avatar_color'],
            'timestamp': event['timestamp']
        }))
    
    async def user_left(self, event):
        """Handle user left event."""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))
    
    async def user_moved(self, event):
        """Handle user movement event."""
        # Don't send movement updates to the user who moved
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_moved',
                'user_id': event['user_id'],
                'username': event['username'],
                'x': event['x'],
                'y': event['y'],
                'timestamp': event['timestamp']
            }))
    
    async def chat_message(self, event):
        """Handle chat message event."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'user_id': event['user_id'],
            'username': event['username'],
            'display_name': event['display_name'],
            'avatar_color': event['avatar_color'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))
    
    async def user_action(self, event):
        """Handle user action event."""
        await self.send(text_data=json.dumps({
            'type': 'user_action',
            'user_id': event['user_id'],
            'username': event['username'],
            'display_name': event['display_name'],
            'action': event['action'],
            'timestamp': event['timestamp']
        }))
    
    # Database helper methods
    @database_sync_to_async
    def get_lobby(self):
        """Get lobby by ID."""
        try:
            return VirtualLobby.objects.get(id=self.lobby_id, is_active=True)
        except VirtualLobby.DoesNotExist:
            return None
    
    
    async def can_user_join_lobby(self):
        """Check if user can join the lobby."""
        lobby = await self.get_lobby()
        if not lobby:
            return False, "Lobby not found"
        return lobby.can_user_join(self.user)
    
    @database_sync_to_async
    def get_or_create_participant(self):
        """Get or create lobby participant."""
        try:
            lobby = VirtualLobby.objects.get(id=self.lobby_id)
            participant, created = LobbyParticipant.objects.get_or_create(
                user=self.user,
                lobby=lobby,
                defaults={
                    'position_x': 100.0,  # Default starting position
                    'position_y': 100.0,
                    'display_name': self.user.username,
                    'is_online': True
                }
            )
            return participant
        except VirtualLobby.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_participant(self):
        """Get lobby participant for current user."""
        try:
            return LobbyParticipant.objects.get(
                user=self.user,
                lobby_id=self.lobby_id
            )
        except LobbyParticipant.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_online_participants(self):
        """Get all online participants in the lobby."""
        lobby = VirtualLobby.objects.get(id=self.lobby_id)
        return list(lobby.get_online_participants())
