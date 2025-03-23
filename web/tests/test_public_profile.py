from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from web.models import Course, Subject


class PublicProfileViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a subject needed for courses.
        cls.subject = Subject.objects.create(name="Mathematics", slug="mathematics")

        # Create a teacher user with a public profile.
        cls.teacher = User.objects.create_user(username="teacheruser", password="password", email="teacher@example.com")
        cls.teacher.profile.is_teacher = True
        cls.teacher.profile.is_profile_public = True
        cls.teacher.profile.bio = "Teacher bio"
        cls.teacher.profile.expertise = "Mathematics, Physics"
        cls.teacher.profile.save()

        # Create a student user with a public profile.
        cls.student = User.objects.create_user(username="studentuser", password="password", email="student@example.com")
        cls.student.profile.is_teacher = False
        cls.student.profile.is_profile_public = True
        cls.student.profile.bio = "Student bio"
        cls.student.profile.expertise = "Physics"
        cls.student.profile.save()

        # Create a private user.
        cls.private_user = User.objects.create_user(
            username="privateuser", password="password", email="private@example.com"
        )
        cls.private_user.profile.is_teacher = False
        cls.private_user.profile.is_profile_public = False
        cls.private_user.profile.bio = "Private bio"
        cls.private_user.profile.expertise = "Chemistry"
        cls.private_user.profile.save()

        # Create a sample course for the teacher.
        cls.course = Course.objects.create(
            title="Sample Course",
            slug="sample-course",
            teacher=cls.teacher,
            description="A sample course",
            learning_objectives="Learn testing",
            prerequisites="None",
            price=10,
            max_students=30,
            subject=cls.subject,
            level="beginner",
        )
        cls.client = Client()

    def setUp(self):
        # Add this instead:
        self.slack_patcher = patch("web.views.send_slack_message", return_value=None)
        self.mock_slack = self.slack_patcher.start()
        self.addCleanup(self.slack_patcher.stop)  # This handles cleanup automatically

    def test_public_teacher_profile(self):
        url = reverse("public_profile", kwargs={"username": self.teacher.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Teacher profiles should include teacher_stats.
        self.assertIn("teacher_stats", response.context)
        self.assertEqual(response.context["teacher_stats"]["total_courses"], 1)
        self.assertEqual(response.context["teacher_stats"]["total_students"], 0)
        self.assertTemplateUsed(response, "public_profile_detail.html")

    def test_public_student_profile(self):
        url = reverse("public_profile", kwargs={"username": self.student.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_courses", response.context)
        self.assertIn("total_completed", response.context)
        self.assertIn("avg_progress", response.context)
        self.assertTemplateUsed(response, "public_profile_detail.html")

    def test_private_profile(self):
        # For a private profile, the view calls custom_404, so the response should have status 404.
        url = reverse("public_profile", kwargs={"username": self.private_user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_profile_update_radio_remains_selected(self):
        # Log in as teacher.
        self.client.login(username="teacheruser", password="password")
        post_data = {
            "username": self.teacher.username,
            "first_name": self.teacher.first_name,
            "last_name": self.teacher.last_name,
            "email": self.teacher.email,
            "bio": "Updated teacher bio",
            "expertise": "Updated expertise",
            "is_profile_public": "True",  # Radio value for Public.
        }
        response = self.client.post(reverse("profile"), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.profile.is_profile_public)

        # GET the profile update page and check that the radio input with value "True" is rendered as checked.
        response = self.client.get(reverse("profile"))
        content = response.content.decode()
        # Regex that does not assume attribute order.
        pattern = r'<input[^>]+name="is_profile_public"[^>]+value="True"[^>]+checked'
        self.assertRegex(content, pattern)
