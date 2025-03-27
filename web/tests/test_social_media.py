from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import ScheduledPost


class SocialMediaDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_scheduled_post(self):
        """
        Test that the create view adds a new ScheduledPost.
        """
        url = reverse("create_scheduled_post")
        data = {"content": "Test post content"}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ScheduledPost.objects.count(), 1)
        post = ScheduledPost.objects.first()
        self.assertEqual(post.content, "Test post content")
        # Verify the post appears on the dashboard
        self.assertContains(response, "Test post content")

    def test_dashboard_view(self):
        """
        Test that the dashboard view displays the page header and post content.
        """
        ScheduledPost.objects.create(content="Dashboard test post", scheduled_time=timezone.now())
        url = reverse("social_media_dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Social Media Dashboard")
        self.assertContains(response, "Dashboard test post")

    @patch("web.views.get_twitter_client")
    def test_post_to_twitter(self, mock_get_twitter_client):
        """
        Test the "Post Now" functionality. Patches Tweepy so no real API call is made.
        """
        post = ScheduledPost.objects.create(content="Test post to twitter", scheduled_time=timezone.now())
        mock_api = mock_get_twitter_client.return_value
        mock_api.update_status.return_value = None

        url = reverse("post_to_twitter", args=[post.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)

        post.refresh_from_db()
        self.assertTrue(post.posted)

    def test_delete_post(self):
        """
        Test that a post can be deleted.
        """
        post = ScheduledPost.objects.create(content="Test post to delete", scheduled_time=timezone.now())
        url = reverse("delete_post", args=[post.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ScheduledPost.objects.count(), 0)
