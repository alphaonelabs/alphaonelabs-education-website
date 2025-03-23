from django.contrib.auth.models import User
from django.test import Client, SimpleTestCase
from django.urls import reverse

from web.models import ProgressTracker


class ProgressTrackerTests(SimpleTestCase): 
    @classmethod
    def setUpTestData(cls):
        # Create user once for the whole test class
        cls.user = User.objects.create_user(username="testuser", password="testpassword")
        # Create tracker once for the whole test class
        cls.tracker = ProgressTracker.objects.create(
            user=cls.user,
            title="Test Tracker",
            description="Testing progress",
            current_value=25,
            target_value=100,
            color="blue-600",
            public=True,
        )

    def setUp(self):
        # Set up a fresh client and login for each test
        self.client = Client()
        self.client.login(username="testuser", password="testpassword")

    def test_tracker_list(self):
        response = self.client.get(reverse("tracker_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Tracker")

    def test_create_tracker(self):
        response = self.client.post(reverse('create_tracker'), {
            'title': 'New Tracker',
            'description': 'New description',
            'current_value': 10,
            'target_value': 50,
            'color': 'green-600',
            'public': True
        })
        # Check for redirect after successful form submission
        self.assertEqual(response.status_code, 302)  # Should redirect after creation
        # Now there should be 2 trackers (the one from setUpTestData + the new one)
        self.assertEqual(ProgressTracker.objects.count(), 2)
        new_tracker = ProgressTracker.objects.get(title="New Tracker")
        self.assertEqual(new_tracker.current_value, 10)
        self.assertEqual(new_tracker.percentage, 20)

    def test_update_progress(self):
        response = self.client.post(
            reverse("update_progress", args=[self.tracker.id]),
            {"current_value": 50},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.tracker.refresh_from_db()
        self.assertEqual(self.tracker.current_value, 50)
        self.assertEqual(self.tracker.percentage, 50)

    def test_embed_tracker(self):
        response = self.client.get(reverse("embed_tracker", args=[self.tracker.embed_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Tracker")
        self.assertContains(response, "25%")