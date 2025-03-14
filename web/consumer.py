# web/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import QuizSubmission  # Assuming you have a QuizSubmission model

class QuizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.quiz_id = self.scope['url_route']['kwargs']['quiz_id']
        self.room_group_name = f'quiz_{self.quiz_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']

        if message_type == 'submit_quiz':
            user_id = text_data_json['user_id']
            score = text_data_json['score']
            await self.update_leaderboard(user_id, score)

    # Send message to room group
    async def update_leaderboard(self, user_id, score):
        # Save quiz submission
        await sync_to_async(QuizSubmission.objects.create)(
            user_id=user_id,
            quiz_id=self.quiz_id,
            score=score
        )

        # Fetch updated leaderboard
        leaderboard = await sync_to_async(self.get_leaderboard)()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'leaderboard_update',
                'leaderboard': leaderboard
            }
        )

    async def leaderboard_update(self, event):
        # Send leaderboard update to WebSocket
        leaderboard = event['leaderboard']
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'leaderboard': leaderboard
        }))

    def get_leaderboard(self):
        # Fetch top 10 scores for the quiz
        submissions = QuizSubmission.objects.filter(
            quiz_id=self.quiz_id
        ).order_by('-score')[:10]
        return [
            {
                'user_id': sub.user_id,
                'score': sub.score
            }
            for sub in submissions
        ]