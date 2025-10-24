"""WebSocket consumers for real-time virtual classroom functionality."""

import json
from datetime import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from django.utils import timezone

from .models import ClassroomSeat, RaisedHand, UpdateRound, VirtualClassroom


class VirtualClassroomConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time virtual classroom interactions."""

    async def connect(self):
        """Accept WebSocket connection and add to classroom group."""
        self.classroom_id = self.scope["url_route"]["kwargs"]["classroom_id"]
        self.classroom_group_name = f"classroom_{self.classroom_id}"
        self.user = self.scope["user"]

        # Join classroom group
        await self.channel_layer.group_add(self.classroom_group_name, self.channel_name)
        await self.accept()

        # Send current classroom state to the newly connected user
        classroom_state = await self.get_classroom_state()
        await self.send(text_data=json.dumps({"type": "classroom_state", "data": classroom_state}))

    async def disconnect(self, close_code):
        """Leave classroom group."""
        await self.channel_layer.group_discard(self.classroom_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "select_seat":
            await self.handle_seat_selection(data)
        elif message_type == "raise_hand":
            await self.handle_raise_hand(data)
        elif message_type == "lower_hand":
            await self.handle_lower_hand(data)
        elif message_type == "select_speaker":
            await self.handle_select_speaker(data)
        elif message_type == "start_update_round":
            await self.handle_start_update_round(data)
        elif message_type == "next_speaker":
            await self.handle_next_speaker(data)
        elif message_type == "complete_speaking":
            await self.handle_complete_speaking(data)

    async def handle_seat_selection(self, data):
        """Handle student selecting a seat."""
        row = data.get("row")
        column = data.get("column")

        result = await self.select_seat(self.user, row, column)

        if result["success"]:
            # Broadcast seat update to all users in the classroom
            await self.channel_layer.group_send(
                self.classroom_group_name,
                {
                    "type": "seat_update",
                    "row": row,
                    "column": column,
                    "student": self.user.username,
                    "student_id": self.user.id,
                    "is_occupied": True,
                },
            )
        else:
            # Send error only to the user who tried to select the seat
            await self.send(text_data=json.dumps({"type": "error", "message": result["message"]}))

    async def handle_raise_hand(self, data):
        """Handle student raising hand."""
        result = await self.raise_hand(self.user)

        if result["success"]:
            # Broadcast hand raise to all users
            await self.channel_layer.group_send(
                self.classroom_group_name,
                {
                    "type": "hand_raised",
                    "student": self.user.username,
                    "student_id": self.user.id,
                    "seat_id": result["seat_id"],
                    "timestamp": result["timestamp"],
                },
            )

    async def handle_lower_hand(self, data):
        """Handle student lowering hand."""
        result = await self.lower_hand(self.user)

        if result["success"]:
            # Broadcast hand lower to all users
            await self.channel_layer.group_send(
                self.classroom_group_name, {"type": "hand_lowered", "student": self.user.username, "student_id": self.user.id}
            )

    async def handle_select_speaker(self, data):
        """Handle teacher selecting a student to speak."""
        student_id = data.get("student_id")
        result = await self.select_speaker(student_id)

        if result["success"]:
            # Broadcast speaker selection to all users
            await self.channel_layer.group_send(
                self.classroom_group_name,
                {"type": "speaker_selected", "student_id": student_id, "student": result["student_username"]},
            )

    async def handle_start_update_round(self, data):
        """Handle teacher starting an update round."""
        duration = data.get("duration", 120)
        result = await self.start_update_round(duration)

        if result["success"]:
            # Broadcast update round start to all users
            await self.channel_layer.group_send(
                self.classroom_group_name,
                {
                    "type": "update_round_started",
                    "round_id": result["round_id"],
                    "duration": duration,
                    "current_speaker_id": result["current_speaker_id"],
                    "current_speaker": result["current_speaker"],
                },
            )

    async def handle_next_speaker(self, data):
        """Handle moving to the next speaker in update round."""
        round_id = data.get("round_id")
        result = await self.next_speaker(round_id)

        if result["success"]:
            # Broadcast next speaker to all users
            await self.channel_layer.group_send(
                self.classroom_group_name,
                {
                    "type": "next_speaker_update",
                    "round_id": round_id,
                    "current_speaker_id": result["current_speaker_id"],
                    "current_speaker": result["current_speaker"],
                    "is_complete": result.get("is_complete", False),
                },
            )

    async def handle_complete_speaking(self, data):
        """Handle student completing their speaking turn."""
        round_id = data.get("round_id")
        await self.handle_next_speaker({"round_id": round_id})

    # WebSocket event handlers (called by channel layer)
    async def seat_update(self, event):
        """Send seat update to WebSocket."""
        await self.send(text_data=json.dumps({"type": "seat_update", "data": event}))

    async def hand_raised(self, event):
        """Send hand raised notification to WebSocket."""
        await self.send(text_data=json.dumps({"type": "hand_raised", "data": event}))

    async def hand_lowered(self, event):
        """Send hand lowered notification to WebSocket."""
        await self.send(text_data=json.dumps({"type": "hand_lowered", "data": event}))

    async def speaker_selected(self, event):
        """Send speaker selection to WebSocket."""
        await self.send(text_data=json.dumps({"type": "speaker_selected", "data": event}))

    async def update_round_started(self, event):
        """Send update round start to WebSocket."""
        await self.send(text_data=json.dumps({"type": "update_round_started", "data": event}))

    async def next_speaker_update(self, event):
        """Send next speaker update to WebSocket."""
        await self.send(text_data=json.dumps({"type": "next_speaker_update", "data": event}))

    # Database operations
    @database_sync_to_async
    def get_classroom_state(self):
        """Get current state of the classroom."""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            seats = list(
                classroom.seats.all().values(
                    "id", "row", "column", "is_occupied", "is_speaking", "student__username", "student__id"
                )
            )
            raised_hands = list(
                classroom.raised_hands.filter(is_active=True).values(
                    "student__username", "student__id", "seat__id", "created_at"
                )
            )
            active_round = classroom.update_rounds.filter(is_active=True).first()

            return {
                "classroom_id": classroom.id,
                "title": classroom.title,
                "seats": seats,
                "raised_hands": raised_hands,
                "active_round": {
                    "id": active_round.id,
                    "duration": active_round.duration_seconds,
                    "current_speaker_id": active_round.current_speaker_id,
                    "current_speaker": active_round.current_speaker.username if active_round.current_speaker else None,
                }
                if active_round
                else None,
            }
        except VirtualClassroom.DoesNotExist:
            return {"error": "Classroom not found"}

    @database_sync_to_async
    def select_seat(self, user, row, column):
        """Select a seat for a student."""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            seat = ClassroomSeat.objects.get(classroom=classroom, row=row, column=column)

            if seat.is_occupied:
                return {"success": False, "message": "Seat is already occupied"}

            # Release any previously occupied seat by this user
            ClassroomSeat.objects.filter(classroom=classroom, student=user).update(
                student=None, is_occupied=False
            )

            # Assign the new seat
            seat.student = user
            seat.is_occupied = True
            seat.save()

            return {"success": True}
        except (VirtualClassroom.DoesNotExist, ClassroomSeat.DoesNotExist):
            return {"success": False, "message": "Invalid classroom or seat"}

    @database_sync_to_async
    def raise_hand(self, user):
        """Raise hand for a student."""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            seat = ClassroomSeat.objects.get(classroom=classroom, student=user)

            # Check if hand is already raised
            if RaisedHand.objects.filter(classroom=classroom, student=user, is_active=True).exists():
                return {"success": False, "message": "Hand is already raised"}

            # Create raised hand
            raised_hand = RaisedHand.objects.create(classroom=classroom, student=user, seat=seat)

            return {
                "success": True,
                "seat_id": seat.id,
                "timestamp": raised_hand.created_at.isoformat(),
            }
        except (VirtualClassroom.DoesNotExist, ClassroomSeat.DoesNotExist):
            return {"success": False, "message": "Must select a seat first"}

    @database_sync_to_async
    def lower_hand(self, user):
        """Lower hand for a student."""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            RaisedHand.objects.filter(classroom=classroom, student=user, is_active=True).update(is_active=False)
            return {"success": True}
        except VirtualClassroom.DoesNotExist:
            return {"success": False, "message": "Classroom not found"}

    @database_sync_to_async
    def select_speaker(self, student_id):
        """Select a student to speak (teacher action)."""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            student = User.objects.get(id=student_id)
            seat = ClassroomSeat.objects.get(classroom=classroom, student=student)

            # Clear all other speaking seats
            ClassroomSeat.objects.filter(classroom=classroom).update(is_speaking=False)

            # Set this seat as speaking
            seat.is_speaking = True
            seat.save()

            # Mark the raised hand as selected
            RaisedHand.objects.filter(classroom=classroom, student=student, is_active=True).update(
                is_active=False, selected_at=timezone.now()
            )

            return {"success": True, "student_username": student.username}
        except (VirtualClassroom.DoesNotExist, User.DoesNotExist, ClassroomSeat.DoesNotExist):
            return {"success": False, "message": "Invalid classroom or student"}

    @database_sync_to_async
    def start_update_round(self, duration):
        """Start an update round."""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)

            # Deactivate any existing active rounds
            UpdateRound.objects.filter(classroom=classroom, is_active=True).update(
                is_active=False, completed_at=timezone.now()
            )

            # Create new update round
            update_round = UpdateRound.objects.create(
                classroom=classroom, duration_seconds=duration, is_active=True, started_at=timezone.now()
            )

            # Add all seated students as participants
            seated_students = ClassroomSeat.objects.filter(classroom=classroom, is_occupied=True).select_related(
                "student"
            )

            from random import shuffle

            participants_list = list(seated_students)
            shuffle(participants_list)

            from .models import UpdateRoundParticipant

            for idx, seat in enumerate(participants_list):
                UpdateRoundParticipant.objects.create(
                    update_round=update_round, student=seat.student, order=idx
                )

            # Set first speaker
            if participants_list:
                first_speaker = participants_list[0].student
                update_round.current_speaker = first_speaker
                update_round.save()

                # Mark seat as speaking
                ClassroomSeat.objects.filter(classroom=classroom).update(is_speaking=False)
                participants_list[0].is_speaking = True
                participants_list[0].save()

                return {
                    "success": True,
                    "round_id": update_round.id,
                    "current_speaker_id": first_speaker.id,
                    "current_speaker": first_speaker.username,
                }
            else:
                return {"success": False, "message": "No students in classroom"}

        except VirtualClassroom.DoesNotExist:
            return {"success": False, "message": "Classroom not found"}

    @database_sync_to_async
    def next_speaker(self, round_id):
        """Move to the next speaker in update round."""
        try:
            from .models import UpdateRoundParticipant

            update_round = UpdateRound.objects.get(id=round_id)

            if not update_round.is_active:
                return {"success": False, "message": "Round is not active"}

            # Get current speaker participant
            current_participant = UpdateRoundParticipant.objects.filter(
                update_round=update_round, student=update_round.current_speaker
            ).first()

            if current_participant:
                current_participant.has_spoken = True
                current_participant.spoken_at = timezone.now()
                current_participant.save()

            # Get next participant who hasn't spoken
            next_participant = (
                UpdateRoundParticipant.objects.filter(update_round=update_round, has_spoken=False)
                .order_by("order")
                .first()
            )

            if next_participant:
                # Set next speaker
                update_round.current_speaker = next_participant.student
                update_round.save()

                # Update seat speaking status
                ClassroomSeat.objects.filter(classroom=update_round.classroom).update(is_speaking=False)
                ClassroomSeat.objects.filter(
                    classroom=update_round.classroom, student=next_participant.student
                ).update(is_speaking=True)

                return {
                    "success": True,
                    "current_speaker_id": next_participant.student.id,
                    "current_speaker": next_participant.student.username,
                    "is_complete": False,
                }
            else:
                # No more speakers, complete the round
                update_round.is_active = False
                update_round.completed_at = timezone.now()
                update_round.current_speaker = None
                update_round.save()

                ClassroomSeat.objects.filter(classroom=update_round.classroom).update(is_speaking=False)

                return {
                    "success": True,
                    "current_speaker_id": None,
                    "current_speaker": None,
                    "is_complete": True,
                }

        except UpdateRound.DoesNotExist:
            return {"success": False, "message": "Update round not found"}
