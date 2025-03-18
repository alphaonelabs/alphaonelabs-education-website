from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from web.models import Quiz, QuizQuestion, QuizOption

User = get_user_model()


class QuizAdminTests(TestCase):
    def setUp(self):
        # Create superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        self.client = Client()
        self.client.login(username="admin", password="adminpass123")

        # Create quiz data
        self.quiz = Quiz.objects.create(
            title="Test Admin Quiz",
            description="Test quiz description for admin",
            start_date=timezone.now().date(),
            start_time=timezone.now().time(),
            end_date=(timezone.now() + timedelta(days=7)).date(),
            end_time=timezone.now().time(),
            duration_minutes=60
        )

    def test_quiz_admin_list(self):
        """Test that quizzes appear in admin list view"""
        admin_url = "/admin/web/quiz/"
        response = self.client.get(admin_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Admin Quiz")

    def test_quiz_admin_add(self):
        """Test adding a quiz through admin"""
        admin_url = "/admin/web/quiz/add/"

        quiz_data = {
            "title": "New Admin Quiz",
            "description": "Quiz added through admin",
            "start_date_0": timezone.now().date().strftime("%Y-%m-%d"),
            "start_time_0": "10:00:00",
            "end_date_0": (timezone.now() + timedelta(days=7)).date().strftime("%Y-%m-%d"),
            "end_time_0": "11:00:00",
            "duration_minutes": 30,
        }

        response = self.client.post(admin_url, quiz_data)

        # Redirects on success
        self.assertEqual(response.status_code, 302)

        # Check that quiz was created
        self.assertTrue(Quiz.objects.filter(title="New Admin Quiz").exists())

    def test_quiz_question_admin_add(self):
        """Test adding a quiz question through admin"""
        admin_url = "/admin/web/quizquestion/add/"

        question_data = {
            "quiz": self.quiz.title,
            "question_text": "What is the meaning of life?",
        }

        response = self.client.post(admin_url, question_data)

        # Redirects on success
        self.assertEqual(response.status_code, 302)

        # Check that question was created
        self.assertTrue(QuizQuestion.objects.filter(question_text="What is the meaning of life?").exists())

    def test_quiz_option_admin_add(self):
        """Test adding quiz options through admin"""
        # First create a question
        question = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="What is the capital of France?"
        )

        admin_url = "/admin/web/quizoption/add/"

        option_data = {
            "question": question.id,
            "option_text": "Paris",
            "is_correct": True,
        }

        response = self.client.post(admin_url, option_data)

        # Redirects on success
        self.assertEqual(response.status_code, 302)

        # Check that option was created
        self.assertTrue(QuizOption.objects.filter(option_text="Paris").exists())
