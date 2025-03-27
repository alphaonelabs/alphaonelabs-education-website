from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import ScheduledPost

User = get_user_model()


class SocialMediaDashboardTests(TestCase):
    def setUp(self):
        # Create and log in a test user because views are decorated with @login_required.
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client = Client()
        self.client.login(username="testuser", password="testpass")

    def test_create_scheduled_post_success(self):
        """
        Test that a valid post is created successfully and appears on the dashboard.
        """
        url = reverse("create_scheduled_post")
        data = {"content": "Test post content"}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        # Success message should be added
        self.assertTrue(any("Post created successfully!" in m.message for m in messages))
        self.assertEqual(ScheduledPost.objects.count(), 1)
        post = ScheduledPost.objects.first()
        self.assertEqual(post.content, "Test post content")
        # Verify the post appears on the dashboard.
        dashboard_response = self.client.get(reverse("social_media_dashboard"))
        self.assertContains(dashboard_response, "Test post content")

    def test_create_scheduled_post_empty_content(self):
        """
        Test that submitting empty content returns an error message.
        """
        url = reverse("create_scheduled_post")
        data = {"content": ""}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Post content cannot be empty." in m.message for m in messages))
        self.assertEqual(ScheduledPost.objects.count(), 0)

    def test_dashboard_view(self):
        """
        Test that the dashboard view displays the header and any posts.
        """
        ScheduledPost.objects.create(content="Dashboard test post", scheduled_time=timezone.now())
        url = reverse("social_media_dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Social Media Dashboard")
        self.assertContains(response, "Dashboard test post")

    @patch("web.views.get_twitter_client")
    def test_post_to_twitter_success(self, mock_get_twitter_client):
        """
        Test the "Post Now" view. Patches Tweepy so no real API call is made.
        """
        post = ScheduledPost.objects.create(content="Test post to twitter", scheduled_time=timezone.now())
        mock_api = mock_get_twitter_client.return_value
        mock_api.update_status.return_value = None

        url = reverse("post_to_twitter", args=[post.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        # Check that the post is marked as posted.
        post.refresh_from_db()
        self.assertTrue(post.posted)

    @patch("web.views.get_twitter_client")
    def test_post_to_twitter_exceeds_limit(self, mock_get_twitter_client):
        """
        Test that attempting to post a tweet with content over 280 characters returns an error.
        """
        post = ScheduledPost.objects.create(content="x" * 281, scheduled_time=timezone.now())
        url = reverse("post_to_twitter", args=[post.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Tweet content exceeds the 280 character limit." in m.message for m in messages),
            "Expected error message for tweet exceeding character limit was not found.",
        )
        post.refresh_from_db()
        self.assertFalse(post.posted)

    def test_delete_post(self):
        """
        Test that a post can be deleted.
        """
        post = ScheduledPost.objects.create(content="Test post to delete", scheduled_time=timezone.now())
        url = reverse("delete_post", args=[post.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Post deleted successfully!" in m.message for m in messages))
        self.assertEqual(ScheduledPost.objects.count(), 0)
