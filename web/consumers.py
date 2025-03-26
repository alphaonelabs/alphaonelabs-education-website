import json
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import VoiceChatParticipant, VoiceChatRoom

User = get_user_model()


class VoiceChatConsumer(AsyncWebsocketConsumer):
    """Implements WebSocket communication for voice chat rooms."""

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
            print(f"WebSocket connection attempt for room_id: {self.room_id}, type: {type(self.room_id)}")

            # Debug information
            print(f"User authentication: {self.scope.get('user', 'No user')}")
            print(f"Headers: {dict(self.scope.get('headers', []))}")
            print(f"Query string: {self.scope.get('query_string', b'').decode()}")

            self.room_group_name = f"voice_chat_{self.room_id}"
            self.user = self.scope["user"]

            # Check if user is authenticated
            if not self.user.is_authenticated:
                print("User is not authenticated, closing connection")
                await self.close(code=4003)
                return

            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            # Accept the connection
            await self.accept()
            print(f"WebSocket connection accepted for room {self.room_id} and user {self.user.username}")

            # Get room participants and notify about new user
            participants = await self.get_room_participants()
            print(f"Participants in room {self.room_id}: {participants}")

            # Notify the new user about existing participants
            await self.send(text_data=json.dumps({"type": "participants_list", "participants": participants}))

            # Notify others about the new user
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "user_joined", "from": self.user.id, "username": self.user.username}
            )

            # Update participant status in database
            await self.update_participant_joined()
        except Exception as e:
            print(f"Error in connect: {e}")
            # Try to close connection gracefully
            try:
                await self.close(code=4500)
            except Exception as close_error:
                print(f"Error while closing connection: {close_error}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Notify others about user leaving
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "user_left", "from": self.user.id, "username": self.user.username}
        )

        # Update participant status in database
        await self.update_participant_left()

    async def receive(self, text_data):
        """Handle messages received from WebSocket."""
        data = json.loads(text_data)
        message_type = data.get("type")

        # Route message based on type
        if message_type == "join":
            # No need to do anything, already handled in connect
            pass
        elif message_type == "offer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "signaling_offer",
                    "offer": data.get("offer"),
                    "from": self.user.id,
                    "target": data.get("target"),
                },
            )
        elif message_type == "answer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "signaling_answer",
                    "answer": data.get("answer"),
                    "from": self.user.id,
                    "target": data.get("target"),
                },
            )
        elif message_type == "ice-candidate":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "signaling_ice_candidate",
                    "candidate": data.get("candidate"),
                    "from": self.user.id,
                    "target": data.get("target"),
                },
            )
        elif message_type == "encryption-key":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "encryption_key",
                    "keyData": data.get("keyData"),
                    "from": self.user.id,
                    "target": data.get("target"),
                },
            )
        elif message_type == "speaking_status":
            await self.update_speaking_status(data.get("speaking", False))
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "speaking_status_changed", "from": self.user.id, "speaking": data.get("speaking", False)},
            )
        elif message_type == "mute_status":
            await self.update_mute_status(data.get("muted", False))
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "mute_status_changed", "from": self.user.id, "muted": data.get("muted", False)},
            )

    # Event handlers sent to the client
    async def user_joined(self, event):
        """Send notification about a user joining the room."""
        # Only send to others, not back to the sender
        if event["from"] != self.user.id:
            await self.send(
                text_data=json.dumps({"type": "user_joined", "from": event["from"], "username": event["username"]})
            )

    async def user_left(self, event):
        """Send notification about a user leaving the room."""
        await self.send(
            text_data=json.dumps({"type": "user_left", "from": event["from"], "username": event["username"]})
        )

    async def signaling_offer(self, event):
        """Forward WebRTC offer to the target client."""
        # Only send to the target user
        if event["target"] == self.user.id:
            await self.send(text_data=json.dumps({"type": "offer", "offer": event["offer"], "from": event["from"]}))

    async def signaling_answer(self, event):
        """Forward WebRTC answer to the target client."""
        # Only send to the target user
        if event["target"] == self.user.id:
            await self.send(text_data=json.dumps({"type": "answer", "answer": event["answer"], "from": event["from"]}))

    async def signaling_ice_candidate(self, event):
        """Forward ICE candidate to the target client."""
        # Only send to the target user
        if event["target"] == self.user.id:
            await self.send(
                text_data=json.dumps({"type": "ice-candidate", "candidate": event["candidate"], "from": event["from"]})
            )

    async def encryption_key(self, event):
        """Forward encryption key to the target client."""
        # Only send to the target user
        if event["target"] == self.user.id:
            await self.send(
                text_data=json.dumps({"type": "encryption-key", "keyData": event["keyData"], "from": event["from"]})
            )

    async def speaking_status_changed(self, event):
        """Broadcast speaking status change to all clients."""
        await self.send(
            text_data=json.dumps(
                {"type": "speaking_status_changed", "from": event["from"], "speaking": event["speaking"]}
            )
        )

    async def mute_status_changed(self, event):
        """Broadcast mute status change to all clients."""
        await self.send(
            text_data=json.dumps({"type": "mute_status_changed", "from": event["from"], "muted": event["muted"]})
        )

    # Database operations (async)
    @database_sync_to_async
    def get_room_participants(self):
        """Get all participants in the room."""
        try:
            # Try to parse the room_id as a UUID if it's a string
            room_uuid = self.room_id
            if isinstance(room_uuid, str):
                room_uuid = uuid.UUID(room_uuid)

            room = VoiceChatRoom.objects.get(id=room_uuid)
            participants = []

            for user in room.participants.all():
                try:
                    participant = VoiceChatParticipant.objects.get(user=user, room=room)
                    is_speaking = participant.is_speaking
                    is_muted = participant.is_muted
                except VoiceChatParticipant.DoesNotExist:
                    is_speaking = False
                    is_muted = False

                participants.append(
                    {"id": user.id, "username": user.username, "is_speaking": is_speaking, "is_muted": is_muted}
                )

            return participants
        except Exception as e:
            print(f"Error getting room participants: {e}")
            return []

    @database_sync_to_async
    def update_participant_joined(self):
        """Mark user as joined in the database."""
        try:
            room_uuid = self.room_id
            if isinstance(room_uuid, str):
                room_uuid = uuid.UUID(room_uuid)

            room = VoiceChatRoom.objects.get(id=room_uuid)
            room.participants.add(self.user)
            VoiceChatParticipant.objects.get_or_create(
                user=self.user, room=room, defaults={"is_speaking": False, "is_muted": False}
            )
        except Exception as e:
            print(f"Error updating participant joined: {e}")

    @database_sync_to_async
    def update_participant_left(self):
        """Mark user as left in the database."""
        try:
            room_uuid = self.room_id
            if isinstance(room_uuid, str):
                room_uuid = uuid.UUID(room_uuid)

            room = VoiceChatRoom.objects.get(id=room_uuid)
            participant = VoiceChatParticipant.objects.filter(user=self.user, room=room).first()
            if participant:
                participant.delete()
        except Exception as e:
            print(f"Error updating participant left: {e}")

    @database_sync_to_async
    def update_speaking_status(self, is_speaking):
        """Update the speaking status of a participant."""
        try:
            room_uuid = self.room_id
            if isinstance(room_uuid, str):
                room_uuid = uuid.UUID(room_uuid)

            room = VoiceChatRoom.objects.get(id=room_uuid)
            participant = VoiceChatParticipant.objects.filter(user=self.user, room=room).first()
            if participant:
                participant.is_speaking = is_speaking
                participant.save()
        except Exception as e:
            print(f"Error updating speaking status: {e}")

    @database_sync_to_async
    def update_mute_status(self, is_muted):
        """Update the mute status of a participant."""
        try:
            room_uuid = self.room_id
            if isinstance(room_uuid, str):
                room_uuid = uuid.UUID(room_uuid)

            room = VoiceChatRoom.objects.get(id=room_uuid)
            participant = VoiceChatParticipant.objects.filter(user=self.user, room=room).first()
            if participant:
                participant.is_muted = is_muted
                participant.save()
        except Exception as e:
            print(f"Error updating mute status: {e}")
