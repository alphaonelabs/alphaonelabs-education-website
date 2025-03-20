from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from web.models import AdminQuiz, AdminQuizQuestion, AdminQuizOption

User = get_user_model()


class QuizAdminTests(TestCase):
    def setUp(self):
        # Create superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.client = Client()
        self.client.login(username="admin", password="adminpass123")

        self.captured_queries = CaptureQueriesContext(connection)
        self.quiz = AdminQuiz.objects.create(
            title="Test Admin Quiz",
            description="Test quiz description for admin",
            start_date=timezone.now().date(),
            start_time=timezone.now().time(),
            end_date=(timezone.now() + timedelta(days=7)).date(),
            end_time=timezone.now().time(),
            duration_minutes=60,
        )

    def test_quiz_admin_list(self):
        """Test that quizzes appear in admin list view"""
        admin_url = reverse("admin:web_adminquiz_changelist")
        response = self.client.get(admin_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Admin Quiz")

        # Additional assertions
        self.assertContains(response, self.quiz.description[:30])  # Check description appears
        self.assertContains(response, str(self.quiz.duration_minutes))  # Check duration appears

    def test_quiz_admin_add(self):
        """Test adding a quiz through admin"""
        admin_url = reverse("admin:web_adminquiz_add")

        # Use more complete form data
        quiz_data = {
            "title": "New Admin Quiz",
            "description": "Quiz added through admin",
            "start_date": timezone.now().date().strftime("%Y-%m-%d"),
            "start_time": "10:00:00",
            "end_date": (timezone.now() + timedelta(days=7)).date().strftime("%Y-%m-%d"),
            "end_time": "11:00:00",
            "duration_minutes": 30,
            "_save": "Save",
        }

        with self.captured_queries:
            response = self.client.post(admin_url, quiz_data)

        if response.status_code != 302:
            self.fail(f"Expected redirect, got {response.status_code}: {response.content.decode()[:500]}")

        # Check for 302 redirect on success
        self.assertEqual(response.status_code, 302)

    def test_quiz_question_admin_add_with_form(self):
        """Test adding a quiz question through Django admin"""
        # Get the form to retrieve necessary fields (like CSRF token)
        response = self.client.get(reverse("admin:web_adminquizquestion_add"))
        self.assertEqual(response.status_code, 200)
        # Prepare form data
        form_data = {
            "quiz": self.quiz.id,  # Assuming self.quiz is defined in setUp()
            "question_text": "Test question?",
            "order": 1,
            "points":10,
            "_save": "Save",
            "csrfmiddlewaretoken": response.context["csrf_token"],
        }
        # Submit the form
        response = self.client.post(
            reverse("admin:web_adminquizquestion_add"), data=form_data, follow=True  # Follow redirects
        )

        
        # Assert that the quiz question was successfully created
        self.assertTrue(AdminQuizQuestion.objects.filter(question_text="Test question?").exists())

    def test_quiz_option_admin_add(self):
        """Test adding a quiz option through Django admin"""
        # First, get the form to see all required fields
        response = self.client.get(reverse("admin:web_adminquizoption_add"))
        self.assertEqual(response.status_code, 200)

        # Create a question first if needed
        question = AdminQuizQuestion.objects.create(quiz=self.quiz, question_text="Test question", order=1)

        # Now collect all form data from the actual form
        form_data = {
            "question": question.id,
            "option_text": "Test option",
            "is_correct": True,
            "order": 1,
            "_save": "Save",
            "csrfmiddlewaretoken": response.context["csrf_token"],
        }

        # Submit the form
        response = self.client.post(
            reverse("admin:web_adminquizoption_add"), data=form_data, follow=True  # Follow redirects
        )

        if not AdminQuizOption.objects.filter(option_text="Test option").exists():
            self.fail(
                f"Quiz option not created. Status: {response.status_code}, Response: {response.content.decode()[:500]}"
            )

        # Check for object creation instead of status code
        self.assertTrue(AdminQuizOption.objects.filter(option_text="Test option").exists())

    def test_quiz_edit(self):
        """Test editing a quiz through admin interface"""
        # Get the edit URL for the quiz
        edit_url = reverse("admin:web_adminquiz_change", args=[self.quiz.id])

        # Prepare updated data
        updated_data = {
            "title": "Updated Quiz Title",
            "description": "Updated description",
            "start_date": timezone.now().date().strftime("%Y-%m-%d"),
            "start_time": "10:00:00",
            "end_date": (timezone.now() + timedelta(days=14)).date().strftime("%Y-%m-%d"),
            "end_time": "11:00:00",
            "duration_minutes": 45,
            "_save": "Save",
        }

        # Submit the form
        response = self.client.post(edit_url, updated_data)

        # Check for redirect on success
        self.assertEqual(response.status_code, 302)

        # Verify the quiz was updated
        updated_quiz = AdminQuiz.objects.get(id=self.quiz.id)
        self.assertEqual(updated_quiz.title, "Updated Quiz Title")
        self.assertEqual(updated_quiz.duration_minutes, 45)
