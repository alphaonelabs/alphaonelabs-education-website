# web/tests/test_quiz_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.utils import IntegrityError
from datetime import datetime, timedelta

from web.models import Quiz, QuizQuestion, QuizOption, QuizSubmission

User = get_user_model()


class QuizModelTests(TestCase):
    def setUp(self):
        # Create a quiz for testing
        self.quiz = Quiz.objects.create(
            title="Test Quiz",
            description="Test quiz description",
            start_date=timezone.now().date(),
            start_time=timezone.now().time(),
            end_date=(timezone.now() + timedelta(days=7)).date(),
            end_time=timezone.now().time(),
            duration_minutes=60
        )
        
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123"
        )

    def test_quiz_creation(self):
        """Test quiz creation with valid data"""
        self.assertEqual(self.quiz.title, "Test Quiz")
        self.assertEqual(self.quiz.description, "Test quiz description")
        self.assertEqual(self.quiz.duration_minutes, 60)
        
    def test_quiz_str(self):
        """Test string representation of Quiz"""
        expected_str = f"{self.quiz.title} (From {self.quiz.start_date} {self.quiz.start_time} to {self.quiz.end_date} {self.quiz.end_time}) (for {self.quiz.duration_minutes} minutes)"
        self.assertEqual(str(self.quiz), expected_str)
        
    def test_quiz_question_creation(self):
        """Test creation of quiz questions"""
        question = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="What is the capital of France?"
        )
        self.assertEqual(question.question_text, "What is the capital of France?")
        self.assertEqual(question.quiz, self.quiz)
        
    def test_quiz_question_str(self):
        """Test string representation of QuizQuestion"""
        question = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="What is the capital of France?"
        )
        self.assertEqual(str(question), "What is the capital of France?")
        
    def test_quiz_option_creation(self):
        """Test creation of quiz options"""
        question = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="What is the capital of France?"
        )
        
        correct_option = QuizOption.objects.create(
            question=question,
            option_text="Paris",
            is_correct=True
        )
        
        incorrect_option = QuizOption.objects.create(
            question=question,
            option_text="London",
            is_correct=False
        )
        
        self.assertEqual(correct_option.option_text, "Paris")
        self.assertTrue(correct_option.is_correct)
        self.assertEqual(incorrect_option.option_text, "London")
        self.assertFalse(incorrect_option.is_correct)
        
    def test_quiz_option_str(self):
        """Test string representation of QuizOption"""
        question = QuizQuestion.objects.create(
            quiz=self.quiz,
            question_text="What is the capital of France?"
        )
        
        option = QuizOption.objects.create(
            question=question,
            option_text="Paris",
            is_correct=True
        )
        
        self.assertEqual(str(option), "Option: Paris (Correct: True)")
        
    def test_quiz_submission_creation(self):
        """Test creation of quiz submissions"""
        submission = QuizSubmission.objects.create(
            user=self.user,
            quiz=self.quiz,
            score=80
        )
        
        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.quiz, self.quiz)
        self.assertEqual(submission.score, 80)
        
    def test_quiz_submission_str(self):
        """Test string representation of QuizSubmission"""
        submission = QuizSubmission.objects.create(
            user=self.user,
            quiz=self.quiz,
            score=80
        )
        
        expected_str = f"{self.user.username} - {self.quiz.title} - Score: 80"
        self.assertEqual(str(submission), expected_str)
        
    def test_quiz_submission_unique_constraint(self):
        """Test that a user cannot submit the same quiz twice"""
        # Create initial submission
        QuizSubmission.objects.create(
            user=self.user,
            quiz=self.quiz,
            score=80
        )
        
        # Attempt to create a duplicate submission should raise IntegrityError
        with self.assertRaises(IntegrityError):
            QuizSubmission.objects.create(
                user=self.user,
                quiz=self.quiz,
                score=90
            )