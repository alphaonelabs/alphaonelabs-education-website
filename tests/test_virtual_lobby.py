from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from web.models import VirtualLobby, VirtualLobbyParticipant


class VirtualLobbyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.client.login(username="testuser", password="testpassword")
        self.lobby = VirtualLobby.objects.create(
            name="Test Lobby", description="A test lobby", is_active=True, max_participants=50
        )

    def test_lobby_creation(self):
        """Test that a lobby can be created successfully."""
        self.assertEqual(self.lobby.name, "Test Lobby")
        self.assertEqual(self.lobby.max_participants, 50)
        self.assertTrue(self.lobby.is_active)

    def test_lobby_str(self):
        """Test the string representation of a lobby."""
        self.assertEqual(str(self.lobby), "Test Lobby")

    def test_lobby_access_requires_login(self):
        """Test that accessing the lobby requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("virtual_lobby"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_lobby_view_authenticated(self):
        """Test that authenticated users can access the lobby."""
        response = self.client.get(reverse("virtual_lobby"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Virtual Lobby")

    def test_participant_creation(self):
        """Test that participants can be added to a lobby."""
        participant = VirtualLobbyParticipant.objects.create(
            user=self.user, lobby=self.lobby, position_x=200.0, position_y=150.0
        )
        self.assertEqual(participant.user, self.user)
        self.assertEqual(participant.lobby, self.lobby)
        self.assertEqual(participant.position_x, 200.0)
        self.assertEqual(participant.position_y, 150.0)

    def test_participant_str(self):
        """Test the string representation of a participant."""
        participant = VirtualLobbyParticipant.objects.create(user=self.user, lobby=self.lobby)
        self.assertEqual(str(participant), f"{self.user.username} in {self.lobby.name}")

    def test_participant_unique_constraint(self):
        """Test that a user can only participate once in a lobby."""
        VirtualLobbyParticipant.objects.create(user=self.user, lobby=self.lobby)
        # Attempting to create another participant with same user and lobby should fail
        with self.assertRaises(Exception):
            VirtualLobbyParticipant.objects.create(user=self.user, lobby=self.lobby)

    def test_get_active_participants_count(self):
        """Test counting active participants."""
        # Create some participants
        user2 = User.objects.create_user(username="testuser2", password="testpassword")
        user3 = User.objects.create_user(username="testuser3", password="testpassword")

        VirtualLobbyParticipant.objects.create(user=self.user, lobby=self.lobby)
        VirtualLobbyParticipant.objects.create(user=user2, lobby=self.lobby)
        VirtualLobbyParticipant.objects.create(user=user3, lobby=self.lobby)

        # All participants should be active (created now)
        count = self.lobby.get_active_participants_count()
        self.assertEqual(count, 3)

    def test_participant_to_dict(self):
        """Test participant data serialization."""
        participant = VirtualLobbyParticipant.objects.create(
            user=self.user, lobby=self.lobby, position_x=100.0, position_y=200.0
        )
        data = participant.to_dict()

        self.assertEqual(data["username"], self.user.username)
        self.assertEqual(data["position_x"], 100.0)
        self.assertEqual(data["position_y"], 200.0)
        self.assertIn("joined_at", data)
        self.assertIn("last_active", data)

    def test_join_lobby_api(self):
        """Test joining a lobby via API."""
        response = self.client.post(reverse("join_virtual_lobby", args=[self.lobby.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["participant"]["username"], self.user.username)

        # Verify participant was created
        participant = VirtualLobbyParticipant.objects.get(user=self.user, lobby=self.lobby)
        self.assertIsNotNone(participant)

    def test_leave_lobby_api(self):
        """Test leaving a lobby via API."""
        # First join the lobby
        VirtualLobbyParticipant.objects.create(user=self.user, lobby=self.lobby)

        # Then leave
        response = self.client.post(reverse("leave_virtual_lobby"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify participant was removed
        self.assertEqual(VirtualLobbyParticipant.objects.filter(user=self.user, lobby=self.lobby).count(), 0)

    def test_lobby_full_capacity(self):
        """Test that a lobby cannot exceed max participants."""
        # Create a lobby with max 2 participants
        small_lobby = VirtualLobby.objects.create(name="Small Lobby", max_participants=2)

        # Add 2 participants
        user2 = User.objects.create_user(username="user2", password="pass")
        VirtualLobbyParticipant.objects.create(user=self.user, lobby=small_lobby)
        VirtualLobbyParticipant.objects.create(user=user2, lobby=small_lobby)

        # Try to add a third participant via API
        User.objects.create_user(username="user3", password="pass")
        self.client.logout()
        self.client.login(username="user3", password="pass")

        response = self.client.post(reverse("join_virtual_lobby", args=[small_lobby.id]))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Lobby is full")
