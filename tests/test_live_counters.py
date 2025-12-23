"""Tests for live counters functionality."""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from web.models import Course, Enrollment, LiveActivityEvent, Quiz, Subject, UserQuiz


class LiveCountersTestCase(TestCase):
    """Test case for live counters feature."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.teacher = User.objects.create_user(username="teacher", password="testpass123")

        # Create a subject and course
        self.subject = Subject.objects.create(name="Test Subject")
        self.course = Course.objects.create(
            title="Test Course", teacher=self.teacher, subject=self.subject, price=0, max_students=10
        )

        # Create a quiz
        self.quiz = Quiz.objects.create(title="Test Quiz", course=self.course, time_limit=30)

    def test_live_stats_api(self):
        """Test that the live stats API returns correct data."""
        # Create an enrollment
        Enrollment.objects.create(student=self.user, course=self.course)

        # Test the API
        response = self.client.get(reverse("live_stats_api"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("active_students", data)
        self.assertIn("students_in_session", data)
        self.assertIn("quizzes_completed_today", data)
        self.assertIn("total_students", data)

    def test_live_activity_feed_api(self):
        """Test that the activity feed API returns correct data."""
        # Create a live activity event
        LiveActivityEvent.objects.create(
            event_type="quiz_completed", user=self.user, message="Test user completed a quiz!", location="New York"
        )

        # Test the API
        response = self.client.get(reverse("live_activity_feed_api"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("events", data)
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["message"], "Test user completed a quiz!")

    def test_quiz_completion_creates_activity_event(self):
        """Test that completing a quiz creates a live activity event."""
        # Create a user quiz
        user_quiz = UserQuiz.objects.create(quiz=self.quiz, user=self.user, max_score=10)

        # Complete the quiz
        user_quiz.complete_quiz()

        # Check that an activity event was created
        events = LiveActivityEvent.objects.filter(user=self.user, event_type="quiz_completed")
        self.assertEqual(events.count(), 1)
        self.assertIn("completed a quiz", events.first().message)

    def test_live_activity_event_model(self):
        """Test LiveActivityEvent model creation and string representation."""
        event = LiveActivityEvent.objects.create(
            event_type="enrollment", user=self.user, message="User enrolled in course", location="California"
        )

        self.assertEqual(str(event), "enrollment - User enrolled in course")
        self.assertEqual(event.event_type, "enrollment")
        self.assertEqual(event.location, "California")

    def test_anonymous_quiz_completion_no_event(self):
        """Test that anonymous quiz completion doesn't create activity event."""
        # Create an anonymous user quiz
        user_quiz = UserQuiz.objects.create(quiz=self.quiz, user=None, anonymous_id="test-anon-123", max_score=10)

        # Complete the quiz
        user_quiz.complete_quiz()

        # Check that no activity event was created (since user is None)
        events = LiveActivityEvent.objects.filter(event_type="quiz_completed")
        self.assertEqual(events.count(), 0)
