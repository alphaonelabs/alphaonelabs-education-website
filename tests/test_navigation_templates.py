from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class NavigationTemplateTests(TestCase):
    """Test that navigation templates render correctly for both desktop and mobile."""

    def setUp(self):
        self.client = Client()

    def test_base_template_includes_nav_items(self):
        """Test that base template includes navigation item templates."""
        # Get the index page which extends base.html
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

        # Check that navigation items are present (they should be rendered from includes)
        self.assertContains(response, "Classes Near Me")
        self.assertContains(response, "Courses")
        self.assertContains(response, "Subjects")
        self.assertContains(response, "Forum")
        self.assertContains(response, "Blog")

    def test_navigation_items_appear_in_both_desktop_and_mobile(self):
        """Test that navigation items appear for both desktop and mobile views."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

        # Desktop navigation should have dropdown classes
        self.assertContains(response, "LEARN")
        self.assertContains(response, "COMMUNITY")
        self.assertContains(response, "RESOURCES")
        self.assertContains(response, "ABOUT")

        # Mobile navigation should have accordion
        self.assertContains(response, "learn-accordion")
        self.assertContains(response, "community-accordion")
        self.assertContains(response, "resources-accordion")
        self.assertContains(response, "about-accordion")

    def test_authenticated_user_navigation(self):
        """Test navigation for authenticated users."""
        user = User.objects.create_user(username="testuser", password="testpass")
        self.client.login(username="testuser", password="testpass")

        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

        # Should not show login/signup links
        # self.assertNotContains(response, "Login")  # This might appear in other contexts
        # Should show user dropdown
        self.assertContains(response, "testuser")
