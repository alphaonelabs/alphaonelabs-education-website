"""Tests for Voice Chat functionality."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from web.models import VoiceChatParticipant, VoiceChatRoom


class VoiceChatModelTests(TestCase):
    """Test VoiceChat models."""

    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username="testuser1", password="testpass123")
        self.user2 = User.objects.create_user(username="testuser2", password="testpass123")

    def test_voice_chat_room_creation(self):
        """Test that a voice chat room can be created."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user1)
        self.assertEqual(room.name, "Test Room")
        self.assertEqual(room.created_by, self.user1)
        self.assertTrue(room.is_active)
        self.assertIsNotNone(room.id)

    def test_voice_chat_room_str(self):
        """Test the string representation of a VoiceChatRoom."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user1)
        self.assertEqual(str(room), "Test Room")

    def test_voice_chat_participant_creation(self):
        """Test that a participant can be added to a room."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user1)
        participant = VoiceChatParticipant.objects.create(user=self.user2, room=room)
        self.assertEqual(participant.user, self.user2)
        self.assertEqual(participant.room, room)
        self.assertFalse(participant.is_speaking)
        self.assertFalse(participant.is_muted)

    def test_voice_chat_participant_str(self):
        """Test the string representation of a VoiceChatParticipant."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user1)
        participant = VoiceChatParticipant.objects.create(user=self.user2, room=room)
        self.assertEqual(str(participant), "testuser2 in Test Room")

    def test_voice_chat_participant_unique_constraint(self):
        """Test that a user can only join a room once."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user1)
        VoiceChatParticipant.objects.create(user=self.user2, room=room)

        # Try to create a duplicate participant
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            VoiceChatParticipant.objects.create(user=self.user2, room=room)

    def test_voice_chat_room_participants_many_to_many(self):
        """Test the many-to-many relationship between rooms and users."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user1)
        room.participants.add(self.user1, self.user2)

        self.assertEqual(room.participants.count(), 2)
        self.assertIn(self.user1, room.participants.all())
        self.assertIn(self.user2, room.participants.all())


class VoiceChatViewTests(TestCase):
    """Test VoiceChat views."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

    def test_list_voice_chat_rooms_view(self):
        """Test that the voice chat list view is accessible."""
        response = self.client.get(reverse("voice_chat_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/voice_chat/list.html")

    def test_create_voice_chat_room_view_get(self):
        """Test that the create room view shows the form."""
        response = self.client.get(reverse("voice_chat_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/voice_chat/create.html")

    def test_create_voice_chat_room_view_post(self):
        """Test that a room can be created via POST."""
        response = self.client.post(reverse("voice_chat_create"), {"name": "New Room"})
        self.assertEqual(response.status_code, 302)  # Redirect after creation

        # Check that the room was created
        room = VoiceChatRoom.objects.filter(name="New Room").first()
        self.assertIsNotNone(room)
        self.assertEqual(room.created_by, self.user)

    def test_voice_chat_room_view(self):
        """Test that a room detail view is accessible."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user)
        response = self.client.get(reverse("voice_chat_room", kwargs={"room_id": room.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/voice_chat/room.html")

    def test_delete_voice_chat_room_view_get(self):
        """Test that the delete confirmation page is shown."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user)
        response = self.client.get(reverse("delete_voice_chat_room", kwargs={"room_id": room.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/voice_chat/delete_confirm.html")

    def test_delete_voice_chat_room_view_post(self):
        """Test that a room can be deleted by its creator."""
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=self.user)
        response = self.client.post(reverse("delete_voice_chat_room", kwargs={"room_id": room.id}))
        self.assertEqual(response.status_code, 302)  # Redirect after deletion

        # Check that the room was deleted
        self.assertFalse(VoiceChatRoom.objects.filter(id=room.id).exists())

    def test_delete_voice_chat_room_permission(self):
        """Test that only the creator can delete a room."""
        other_user = User.objects.create_user(username="otheruser", password="testpass123")
        room = VoiceChatRoom.objects.create(name="Test Room", created_by=other_user)

        response = self.client.post(reverse("delete_voice_chat_room", kwargs={"room_id": room.id}))
        self.assertEqual(response.status_code, 302)  # Redirect

        # Check that the room was NOT deleted
        self.assertTrue(VoiceChatRoom.objects.filter(id=room.id).exists())

    def test_voice_chat_requires_authentication(self):
        """Test that voice chat views require authentication."""
        self.client.logout()

        # Test list view
        response = self.client.get(reverse("voice_chat_list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Test create view
        response = self.client.get(reverse("voice_chat_create"))
        self.assertEqual(response.status_code, 302)  # Redirect to login
