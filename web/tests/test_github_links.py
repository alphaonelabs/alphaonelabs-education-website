from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from web.models import ForumCategory, ForumTopic

User = get_user_model()


class ForumTopicGithubTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client.login(username="testuser", password="password")
        self.category = ForumCategory.objects.create(name="Test Category", slug="test-category")

    def test_create_topic_with_valid_github_links(self):
        url = reverse("create_topic", kwargs={"category_slug": self.category.slug})
        form_data = {
            "title": "Valid Github Links",
            "content": "This is a test topic with valid GitHub links.",
            "github_issue_url": "https://github.com/example/repo/issues/123",
            "github_milestone_url": "https://github.com/example/repo/milestone/1",
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(ForumTopic.objects.count(), 1)
        topic = ForumTopic.objects.first()
        self.assertEqual(topic.title, form_data["title"])
        self.assertEqual(topic.github_issue_url, form_data["github_issue_url"])
        self.assertEqual(topic.github_milestone_url, form_data["github_milestone_url"])
        expected_redirect = reverse("forum_topic", kwargs={"category_slug": self.category.slug, "topic_id": topic.id})
        self.assertRedirects(response, expected_redirect)

    def test_create_topic_with_invalid_github_issue_url(self):
        url = reverse("create_topic", kwargs={"category_slug": self.category.slug})
        form_data = {
            "title": "Invalid Github Issue URL",
            "content": "Topic with invalid GitHub issue URL.",
            "github_issue_url": "https://notgithub.com/example/repo/issues/123",  # Invalid URL
            "github_milestone_url": "https://github.com/example/repo/milestone/1",
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(ForumTopic.objects.count(), 0)
        self.assertContains(response, "Please enter a valid GitHub issue URL")

    def test_create_topic_with_invalid_github_milestone_url(self):
        url = reverse("create_topic", kwargs={"category_slug": self.category.slug})
        form_data = {
            "title": "Invalid Github Milestone URL",
            "content": "Topic with invalid GitHub milestone URL.",
            "github_issue_url": "https://github.com/example/repo/issues/123",
            "github_milestone_url": "https://notgithub.com/example/repo/milestone/1",  # Invalid URL
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(ForumTopic.objects.count(), 0)
        self.assertContains(response, "Please enter a valid GitHub milestone URL")

    def test_topic_detail_displays_github_links(self):
        topic = ForumTopic.objects.create(
            category=self.category,
            author=self.user,
            title="Topic with GitHub Links",
            content="Content for testing GitHub links in the detail view.",
            github_issue_url="https://github.com/example/repo/issues/123",
            github_milestone_url="https://github.com/example/repo/milestone/1",
        )
        url = reverse("forum_topic", kwargs={"category_slug": self.category.slug, "topic_id": topic.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GitHub Issue")
        self.assertContains(response, "GitHub Milestone")
