import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import VirtualClassroom, VirtualClassroomParticipant
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class VirtualClassroomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.classroom_id = self.scope['url_route']['kwargs']['classroom_id']
        self.room_group_name = f'classroom_{self.classroom_id}'
        self.user = self.scope['user']

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        try:
            # Verify user has access to this classroom
            if not await self.verify_classroom_access():
                await self.close()
                return

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

            # Add user to active participants
            participant = await self.add_participant()
            if participant:
                # Broadcast to others that user has joined
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'participant_joined',
                        'user': {
                            'username': self.user.username,
                            'full_name': self.user.get_full_name() or self.user.username,
                        },
                        'seat_id': participant.seat_id
                    }
                )

                # Send current participants list to everyone
                await self.send_participants_list()
        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and self.user.is_authenticated:
            try:
                # Remove user from active participants
                await self.remove_participant()

                # Broadcast to others that user has left
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'participant_left',
                        'user': {
                            'username': self.user.username,
                            'full_name': self.user.get_full_name() or self.user.username,
                        }
                    }
                )

                # Leave room group
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception as e:
                logger.error(f"Error in disconnect: {str(e)}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'update_seat':
                seat_id = data.get('seat_id')
                if seat_id:
                    await self.update_participant_seat(seat_id)
                    # Broadcast updated participants list
                    await self.send_participants_list()
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")

    async def participant_joined(self, event):
        """Handle when a new participant joins"""
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'user': event['user'],
            'seat_id': event.get('seat_id')
        }))

    async def participant_left(self, event):
        """Handle when a participant leaves"""
        await self.send(text_data=json.dumps({
            'type': 'participant_left',
            'user': event['user']
        }))

    async def participants_list(self, event):
        """Send the current list of participants"""
        await self.send(text_data=json.dumps({
            'type': 'participants_list',
            'participants': event['participants']
        }))

    @database_sync_to_async
    def verify_classroom_access(self):
        """Verify user has access to this classroom"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            is_teacher = self.user == classroom.teacher
            is_enrolled = False
            if classroom.course:
                is_enrolled = classroom.course.enrollments.filter(
                    student=self.user, 
                    status="approved"
                ).exists()
            return is_teacher or is_enrolled
        except VirtualClassroom.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error verifying classroom access: {str(e)}")
            return False

    @database_sync_to_async
    def add_participant(self):
        """Add user to active participants"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            participant, _ = VirtualClassroomParticipant.objects.get_or_create(
                classroom=classroom,
                user=self.user
            )
            return participant
        except Exception as e:
            logger.error(f"Error adding participant: {str(e)}")
            return None

    @database_sync_to_async
    def remove_participant(self):
        """Remove user from active participants"""
        try:
            VirtualClassroomParticipant.objects.filter(
                classroom_id=self.classroom_id,
                user=self.user
            ).delete()
        except Exception as e:
            logger.error(f"Error removing participant: {str(e)}")

    @database_sync_to_async
    def update_participant_seat(self, seat_id):
        """Update participant's seat"""
        try:
            VirtualClassroomParticipant.objects.filter(
                classroom_id=self.classroom_id,
                user=self.user
            ).update(seat_id=seat_id)
        except Exception as e:
            logger.error(f"Error updating participant seat: {str(e)}")

    @database_sync_to_async
    def get_participants_list(self):
        """Get list of current participants"""
        try:
            participants = VirtualClassroomParticipant.objects.filter(
                classroom_id=self.classroom_id
            ).select_related('user')
            
            return [{
                'username': p.user.username,
                'full_name': p.user.get_full_name() or p.user.username,
                'seat_id': p.seat_id,
                'joined_at': p.joined_at.isoformat()
            } for p in participants]
        except Exception as e:
            logger.error(f"Error getting participants list: {str(e)}")
            return []

    async def send_participants_list(self):
        """Send current participants list to the group"""
        try:
            participants = await self.get_participants_list()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'participants_list',
                    'participants': participants
                }
            )
        except Exception as e:
            logger.error(f"Error sending participants list: {str(e)}") 