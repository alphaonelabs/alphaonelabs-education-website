import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import VirtualClassroom, VirtualClassroomParticipant
from django.contrib.auth import get_user_model

User = get_user_model()

class VirtualClassroomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.classroom_id = self.scope['url_route']['kwargs']['classroom_id']
        self.room_group_name = f'classroom_{self.classroom_id}'
        self.user = self.scope['user']

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Add user to active participants
        await self.add_participant()

        # Send current participants list to the new user
        await self.send_participants_list()

    async def disconnect(self, close_code):
        # Remove user from active participants
        await self.remove_participant()

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'update_seat':
            await self.update_participant_seat(data.get('seat_id'))

    async def participant_joined(self, event):
        """Handle when a new participant joins"""
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'user': event['user'],
            'seat_id': event['seat_id']
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
    def add_participant(self):
        """Add user to active participants"""
        classroom = VirtualClassroom.objects.get(id=self.classroom_id)
        VirtualClassroomParticipant.objects.get_or_create(
            classroom=classroom,
            user=self.user
        )

    @database_sync_to_async
    def remove_participant(self):
        """Remove user from active participants"""
        VirtualClassroomParticipant.objects.filter(
            classroom_id=self.classroom_id,
            user=self.user
        ).delete()

    @database_sync_to_async
    def update_participant_seat(self, seat_id):
        """Update participant's seat"""
        VirtualClassroomParticipant.objects.filter(
            classroom_id=self.classroom_id,
            user=self.user
        ).update(seat_id=seat_id)

    @database_sync_to_async
    def get_participants_list(self):
        """Get list of current participants"""
        participants = VirtualClassroomParticipant.objects.filter(
            classroom_id=self.classroom_id
        ).select_related('user')
        
        return [{
            'username': p.user.username,
            'full_name': p.user.get_full_name() or p.user.username,
            'seat_id': p.seat_id,
            'joined_at': p.joined_at.isoformat()
        } for p in participants]

    async def send_participants_list(self):
        """Send current participants list to the group"""
        participants = await self.get_participants_list()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'participants_list',
                'participants': participants
            }
        ) 