import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import VirtualLobby, VirtualLobbyParticipant

logger = logging.getLogger(__name__)
User = get_user_model()


class VirtualLobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.lobby_id = self.scope["url_route"]["kwargs"].get("lobby_id", "main")
        self.room_group_name = f"lobby_{self.lobby_id}"
        self.user = self.scope["user"]

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        try:
            # Get or create the main lobby
            lobby = await self.get_or_create_lobby()
            if not lobby:
                await self.close()
                return

            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            await self.accept()

            # Add user to active participants
            participant = await self.add_participant(lobby)
            if participant:
                # Broadcast to others that user has joined
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "participant_joined",
                        "user": {
                            "username": self.user.username,
                            "full_name": self.user.get_full_name() or self.user.username,
                            "position_x": participant.position_x,
                            "position_y": participant.position_y,
                        },
                    },
                )

                # Send current participants list to everyone
                await self.send_participants_list()

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "user") and self.user.is_authenticated:
                # Remove user from active participants
                await self.remove_participant()

                # Broadcast to others that user has left
                if hasattr(self, "room_group_name"):
                    try:
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "participant_left",
                                "user": {
                                    "username": self.user.username,
                                    "full_name": self.user.get_full_name() or self.user.username,
                                },
                            },
                        )
                    except Exception as e:
                        logger.error(f"Error sending participant_left message: {str(e)}")

                # Leave room group
                if hasattr(self, "room_group_name") and hasattr(self, "channel_name"):
                    try:
                        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                    except Exception as e:
                        logger.error(f"Error discarding from group: {str(e)}")

        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")
        finally:
            # Ensure connection is closed
            try:
                await self.close()
            except Exception:
                pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "update_position":
                position_x = data.get("position_x")
                position_y = data.get("position_y")

                # Update participant's position
                participant = await self.update_participant_position(position_x, position_y)
                if participant:
                    # Broadcast position update to all users
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "position_updated",
                            "user": {
                                "username": self.user.username,
                                "full_name": self.user.get_full_name() or self.user.username,
                            },
                            "position_x": position_x,
                            "position_y": position_y,
                        },
                    )

            elif message_type == "chat_message":
                message = data.get("message", "")
                if message.strip():
                    # Broadcast chat message to all users
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat_message",
                            "user": {
                                "username": self.user.username,
                                "full_name": self.user.get_full_name() or self.user.username,
                            },
                            "message": message,
                            "timestamp": timezone.now().isoformat(),
                        },
                    )

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")

    async def participant_joined(self, event):
        """Handle when a new participant joins"""
        await self.send(text_data=json.dumps(event))

    async def participant_left(self, event):
        """Handle when a participant leaves"""
        await self.send(text_data=json.dumps(event))

    async def position_updated(self, event):
        """Handle when a participant's position is updated"""
        await self.send(text_data=json.dumps(event))

    async def chat_message(self, event):
        """Handle chat messages"""
        await self.send(text_data=json.dumps(event))

    async def participants_list(self, event):
        """Send the current list of participants"""
        await self.send(text_data=json.dumps({"type": "participants_list", "participants": event["participants"]}))

    @database_sync_to_async
    def get_or_create_lobby(self):
        """Get or create the main lobby"""
        try:
            if self.lobby_id == "main":
                lobby, created = VirtualLobby.objects.get_or_create(
                    name="Main Lobby",
                    defaults={"description": "Welcome to the main lobby! Connect with other learners."},
                )
                return lobby
            else:
                return VirtualLobby.objects.get(id=self.lobby_id, is_active=True)
        except VirtualLobby.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting/creating lobby: {str(e)}")
            return None

    @database_sync_to_async
    def add_participant(self, lobby):
        """Add user to active participants"""
        try:
            participant, _ = VirtualLobbyParticipant.objects.get_or_create(lobby=lobby, user=self.user)
            return participant
        except Exception as e:
            logger.error(f"Error adding participant: {str(e)}")
            return None

    @database_sync_to_async
    def remove_participant(self):
        """Remove user from active participants"""
        try:
            VirtualLobbyParticipant.objects.filter(user=self.user).delete()
        except Exception as e:
            logger.error(f"Error removing participant: {str(e)}")

    @database_sync_to_async
    def update_participant_position(self, position_x, position_y):
        """Update participant's position in the lobby"""
        try:
            participant = VirtualLobbyParticipant.objects.filter(user=self.user).first()
            if participant:
                participant.position_x = position_x
                participant.position_y = position_y
                participant.save()  # This will update last_active due to auto_now=True
                return participant
        except Exception as e:
            logger.error(f"Error updating participant position: {str(e)}")
        return None

    @database_sync_to_async
    def get_participants_list(self):
        """Get list of current participants with their positions"""
        try:
            # Get participants who were active in the last 5 minutes
            five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
            participants = VirtualLobbyParticipant.objects.filter(last_active__gte=five_minutes_ago).select_related(
                "user"
            )

            return [
                {
                    "username": p.user.username,
                    "full_name": p.user.get_full_name() or p.user.username,
                    "position_x": p.position_x,
                    "position_y": p.position_y,
                    "joined_at": p.joined_at.isoformat(),
                    "last_active": p.last_active.isoformat(),
                }
                for p in participants
            ]
        except Exception as e:
            logger.error(f"Error getting participants list: {str(e)}")
            return []

    async def send_participants_list(self):
        """Send current participants list to the group"""
        try:
            participants = await self.get_participants_list()
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "participants_list", "participants": participants}
            )
        except Exception as e:
            logger.error(f"Error sending participants list: {str(e)}")
