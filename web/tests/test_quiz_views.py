# web/tests/test_quiz_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

from web.models import Quiz, QuizQuestion, QuizOption, QuizSubmission

User = get_user_model()


class QuizViewTests(TestCase):
    def setUp(self):
        # Create client
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123"
        )
        
        # Create an active quiz
        self.start_date = timezone.now().date()
        self.end_date = (timezone.now() + timedelta(days=7)).date()
        self.quiz = Quiz.objects.create(
            title="Test Quiz",
            description="Test quiz description",
            start_date=self.start_date,
            start_time=timezone.now().time(),
            end_date=self.end_date,
            end_time=timezone.now().time(),
            duration_minutes=60
        )
        
        # Create a question for the quiz
        self.question = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="What is the capital of France?"
        )
        
        # Create options for the question
        self.correct_option = QuizOption.objects.create(
            question=self.question,
            option_text="Paris",
            is_correct=True
        )
        
        self.incorrect_option = QuizOption.objects.create(
            question=self.question,
            option_text="London",
            is_correct=False
        )
        
    def test_current_live_quiz_view_not_logged_in(self):
        """Test current_live_quiz view for unauthenticated users"""
        url = reverse('current_live_quiz', args=[self.quiz.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Quiz")
        self.assertContains(response, "What is the capital of France?")
        self.assertContains(response, "Paris")
        self.assertContains(response, "London")
        
    def test_current_live_quiz_view_logged_in(self):
        """Test current_live_quiz view for authenticated users"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse('current_live_quiz', args=[self.quiz.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Quiz")
        
    def test_current_live_quiz_view_already_submitted(self):
        """Test current_live_quiz view when user has already submitted"""
        self.client.login(username="testuser", password="testpass123")
        
        # Create a submission for the user
        QuizSubmission.objects.create(
            user=self.user,
            quiz=self.quiz,
            score=80
        )
        
        url = reverse('current_live_quiz', args=[self.quiz.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You have already submitted this quiz.")
        
    def test_current_live_quiz_view_invalid_quiz_id(self):
        """Test current_live_quiz view with an invalid quiz ID"""
        url = reverse('current_live_quiz', args=[999])  # Non-existent quiz ID
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)  # Should redirect
        self.assertRedirects(response, reverse('index'))
        
    def test_submit_quiz_without_login(self):
        """Test submit_quiz view without login should redirect to login page"""
        url = reverse('submit_quiz', args=[self.quiz.id])
        response = self.client.post(url, {
            f'question_{self.question.id}': self.correct_option.id
        })
        
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        
    def test_submit_quiz_with_correct_answer(self):
        """Test submit_quiz view with correct answer"""
        self.client.login(username="testuser", password="testpass123")
        
        url = reverse('submit_quiz', args=[self.quiz.id])
        response = self.client.post(url, {
            f'question_{self.question.id}': self.correct_option.id
        })
        
        # Should redirect to leaderboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('leaderboard', args=[self.quiz.id]))
        
        # Check that submission was created with correct score
        submission = QuizSubmission.objects.get(user=self.user, quiz=self.quiz)
        self.assertEqual(submission.score, 10)  # 10 points for correct answer
        
    def test_submit_quiz_with_incorrect_answer(self):
        """Test submit_quiz view with incorrect answer"""
        self.client.login(username="testuser", password="testpass123")
        
        url = reverse('submit_quiz', args=[self.quiz.id])
        response = self.client.post(url, {
            f'question_{self.question.id}': self.incorrect_option.id
        })
        
        # Should redirect to leaderboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('leaderboard', args=[self.quiz.id]))
        
        # Check that submission was created with score of 0
        submission = QuizSubmission.objects.get(user=self.user, quiz=self.quiz)
        self.assertEqual(submission.score, 0)  # 0 points for incorrect answer
        
    def test_submit_quiz_twice(self):
        """Test attempting to submit a quiz twice"""
        self.client.login(username="testuser", password="testpass123")
        
        # Create initial submission
        QuizSubmission.objects.create(
            user=self.user,
            quiz=self.quiz,
            score=80
        )
        
        url = reverse('submit_quiz', args=[self.quiz.id])
        response = self.client.post(url, {
            f'question_{self.question.id}': self.correct_option.id
        })
        
        # Should redirect to leaderboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('leaderboard', args=[self.quiz.id]))
        
        # Score should remain unchanged
        submission = QuizSubmission.objects.get(user=self.user, quiz=self.quiz)
        self.assertEqual(submission.score, 80)
        
    def test_submit_quiz_missing_answer(self):
        """Test submit_quiz view with missing answer"""
        self.client.login(username="testuser", password="testpass123")
        
        url = reverse('submit_quiz', args=[self.quiz.id])
        response = self.client.post(url, {})  # No answers submitted
        
        # Should redirect to leaderboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('leaderboard', args=[self.quiz.id]))
        
        # Check that submission was created with score of 0
        submission = QuizSubmission.objects.get(user=self.user, quiz=self.quiz)
        self.assertEqual(submission.score, 0)
        
    def test_leaderboard_view(self):
        """Test leaderboard view"""
        url = reverse('leaderboard', args=[self.quiz.id])
        
        # Create some submissions with different scores
        user1 = User.objects.create_user(username="user1", password="pass123")
        user2 = User.objects.create_user(username="user2", password="pass123")
        user3 = User.objects.create_user(username="user3", password="pass123")
        
        QuizSubmission.objects.create(user=user1, quiz=self.quiz, score=90)
        QuizSubmission.objects.create(user=user2, quiz=self.quiz, score=80)
        QuizSubmission.objects.create(user=user3, quiz=self.quiz, score=100)
        
        # Login and access leaderboard
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Quiz")
        
        # Check that submissions are ordered by score (highest first)
        submissions = list(response.context['submissions'])
        self.assertEqual(submissions[0].score, 100)
        self.assertEqual(submissions[1].score, 90)
        self.assertEqual(submissions[2].score, 80)
        
    def test_leaderboard_quiz_ended_flag(self):
        """Test quiz_ended flag in leaderboard view"""
        # Create a quiz that has already ended
        past_quiz = Quiz.objects.create(
            title="Past Quiz",
            description="Quiz that already ended",
            start_date=(timezone.now() - timedelta(days=14)).date(),
            start_time=timezone.now().time(),
            end_date=(timezone.now() - timedelta(days=7)).date(),
            end_time=timezone.now().time(),
            duration_minutes=60
        )
        
        url = reverse('leaderboard', args=[past_quiz.id])
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['quiz_ended'])
        
        # Test with ongoing quiz
        url = reverse('leaderboard', args=[self.quiz.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['quiz_ended'])