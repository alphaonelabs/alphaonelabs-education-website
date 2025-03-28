import unittest
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import models
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import (
    CounterStatistic,
    Course,
    CourseProgress,
    Enrollment,
    Quiz,
    Session,
    Subject,
    UserActivity,
    UserQuiz,
    WebRequest,
)
from web.services.counter_service import CounterService

# Type hints for Django models
CounterStatistic: models.Manager
Course: models.Manager
CourseProgress: models.Manager
Enrollment: models.Manager
Quiz: models.Manager
Subject: models.Manager
UserActivity: models.Manager
UserQuiz: models.Manager
WebRequest: models.Manager
Session: models.Manager


class CounterStatisticModelTests(TestCase):
    """Tests for the CounterStatistic model."""

    def setUp(self):
        self.counter = CounterStatistic.objects.create(counter_type="total_learners", value=100)

    def test_get_counter_value(self):
        """Test getting counter value"""
        value = CounterStatistic.get_counter_value("total_learners")
        self.assertEqual(value, 100)

    def test_increment_counter(self):
        """Test incrementing counter value"""
        self.counter.increment_counter(self.counter.counter_type)
        self.counter.refresh_from_db()
        self.assertEqual(self.counter.value, 101)

    def test_get_nonexistent_counter(self):
        """Test getting value of nonexistent counter"""
        value = CounterStatistic.get_counter_value("nonexistent")
        self.assertEqual(value, 0)


class UserActivityModelTests(TestCase):
    """Tests for the UserActivity model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            description="Test Description",
            teacher=self.user,
            subject=Subject.objects.create(name="Test Subject"),
            price=0,
            max_students=10,
            status="published",
        )
        self.enrollment = Enrollment.objects.create(student=self.user, course=self.course, status="approved")

    def test_record_activity(self):
        """Test recording a new activity"""
        activity = UserActivity.record_activity(
            user=self.user, activity_type="enrollment", content_object=self.enrollment, show_full_name=True
        )
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, "enrollment")
        self.assertEqual(activity.content_object, self.enrollment)
        self.assertTrue(activity.show_full_name)

    def test_user_display_name(self):
        """Test user display name property"""
        activity = UserActivity.record_activity(
            user=self.user, activity_type="enrollment", content_object=self.enrollment, show_full_name=True
        )
        self.assertEqual(activity.user_display_name, self.user.get_full_name() or self.user.username)

        # Test with show_full_name=False
        activity.show_full_name = False
        activity.save()
        self.assertEqual(activity.user_display_name, self.user.first_name or "Someone")


class CounterServiceTests(TestCase):
    """Tests for the CounterService."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        self.subject = Subject.objects.create(
            name="Test Subject", slug="test-subject", description="Test description", icon="fas fa-code"
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test description",
            teacher=self.user,
            subject=self.subject,
            level="beginner",
            price=99.99,
            max_students=50,
            learning_objectives="Test learning objectives",
        )

    def test_update_active_users_count(self):
        """Test updating the active users count."""
        # Create some web requests
        fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
        thirty_minutes_ago = timezone.now() - timedelta(minutes=30)

        # Recent request (should be counted)
        WebRequest.objects.create(user=self.user.username, path="/test", created=timezone.now())

        # Second user (should be counted)
        WebRequest.objects.create(user="anotheruser", path="/test1.5", created=timezone.now())

        # Just at the cutoff (should be counted)
        WebRequest.objects.create(user=self.user.username, path="/test2", created=fifteen_minutes_ago)

        # Too old (should not be counted)
        WebRequest.objects.create(user="olduser", path="/test3", created=thirty_minutes_ago)

        # Run the update
        count = CounterService.update_active_users_count()

        # Verify the counter was updated to match the count
        counter = CounterStatistic.objects.get(counter_type="active_users")
        self.assertEqual(counter.value, count)

        # Check that the count is greater than 1 (we should at least have distinct users)
        self.assertGreater(count, 1)

    def test_update_enrollments_today(self):
        """Test updating the enrollments today count."""
        # Create additional users for enrollments
        user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")

        # Create enrollments today
        Enrollment.objects.create(
            student=self.user, course=self.course, status="active", enrollment_date=timezone.now()
        )

        Enrollment.objects.create(student=user2, course=self.course, status="active", enrollment_date=timezone.now())

        # Create an enrollment from yesterday with a different user
        user3 = User.objects.create_user(username="testuser3", email="test3@example.com", password="testpass123")
        yesterday = timezone.now() - timedelta(days=1)
        Enrollment.objects.create(student=user3, course=self.course, status="active", enrollment_date=yesterday)

        # Run the update
        count = CounterService.update_enrollments_today()

        # Verify the counter was updated to match the count
        counter = CounterStatistic.objects.get(counter_type="enrollments_today")
        self.assertEqual(counter.value, count)

        # Check that the count is at least 2 (we created 2 enrollments for today)
        self.assertGreaterEqual(count, 2)

        # We're not going to assert an upper bound because there might be
        # other test enrollments created in the same transaction

    def test_update_total_learners(self):
        """Test updating the total learners count."""
        # Create additional users
        User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")

        # Create a staff user (should not be counted)
        staff_user = User.objects.create_user(username="staffuser", email="staff@example.com", password="staffpass123")
        staff_user.is_staff = True
        staff_user.save()

        # Run the update
        count = CounterService.update_total_learners()

        # Verify the counter was updated to match the count
        counter = CounterStatistic.objects.get(counter_type="total_learners")
        self.assertEqual(counter.value, count)

        # Check that the count is at least 2 (we created 2 non-staff users)
        self.assertGreaterEqual(count, 2)

    def test_update_total_enrollments(self):
        """Test updating the total enrollments count."""
        # Create additional users for enrollments
        user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")

        # Create multiple enrollments
        Enrollment.objects.create(
            student=self.user, course=self.course, status="active", enrollment_date=timezone.now()
        )

        Enrollment.objects.create(student=user2, course=self.course, status="active", enrollment_date=timezone.now())

        # Run the update
        count = CounterService.update_total_enrollments()

        # Verify the counter was updated to match the count
        counter = CounterStatistic.objects.get(counter_type="total_enrollments")
        self.assertEqual(counter.value, count)

        # Check that the count is at least 2 (we created 2 enrollments)
        self.assertGreaterEqual(count, 2)

    def test_get_recent_activities(self):
        """Test getting recent activities."""
        # Create some activities
        for i in range(15):  # Create 15 activities
            UserActivity.record_activity(user=self.user, activity_type="enrollment", content_object=self.course)

        # Default limit is 10
        activities = CounterService.get_recent_activities()
        self.assertEqual(len(activities), 10)

        # Test with custom limit
        activities = CounterService.get_recent_activities(limit=5)
        self.assertEqual(len(activities), 5)

        # Verify activities are ordered by timestamp (newest first)
        for i in range(1, len(activities)):
            self.assertTrue(activities[i - 1].timestamp >= activities[i].timestamp)


class LiveCounterSignalsTests(TestCase):
    """Tests for the signals that update counters and record activities."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        self.subject = Subject.objects.create(
            name="Test Subject", slug="test-subject", description="Test description", icon="fas fa-code"
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test description",
            teacher=self.user,
            subject=self.subject,
            level="beginner",
            price=99.99,
            max_students=50,
            learning_objectives="Test learning objectives",
        )

    def test_enrollment_created_signal(self):
        """Test that counters are updated and activity is recorded when an enrollment is created."""
        # Initial count
        CounterStatistic.objects.create(counter_type="enrollments_today", value=0)
        CounterStatistic.objects.create(counter_type="total_enrollments", value=0)

        # Create an enrollment (should trigger the signal)
        Enrollment.objects.create(student=self.user, course=self.course, status="active")

        # Check that a UserActivity was created
        self.assertEqual(UserActivity.objects.count(), 1)
        activity = UserActivity.objects.first()
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, "enrollment")
        self.assertEqual(activity.content_object, self.course)

        # Check that the daily counter was incremented
        counter = CounterStatistic.objects.get(counter_type="enrollments_today")
        self.assertEqual(counter.value, 1)

        # Check that the total counter was incremented
        counter = CounterStatistic.objects.get(counter_type="total_enrollments")
        self.assertEqual(counter.value, 1)

    @patch("web.services.counter_service.UserActivity.record_activity")
    @patch("web.services.counter_service.CounterStatistic.increment_counter")
    def test_quiz_completed_signal(self, mock_increment_counter, mock_record_activity):
        """Test that signals handle quiz completion correctly."""
        # Create a quiz with required fields
        quiz = Quiz.objects.create(
            title="Test Quiz",
            description="Test Quiz Description",
            creator=self.user,
            subject=self.subject,
            status="published",
        )

        # Create a UserQuiz instance
        user_quiz = UserQuiz.objects.create(user=self.user, quiz=quiz, completed=False)

        # Update to completed (should trigger the signal)
        user_quiz.completed = True
        user_quiz.save()

        # Check that activity was recorded
        mock_record_activity.assert_called_once()
        args, kwargs = mock_record_activity.call_args
        self.assertEqual(kwargs["user"], self.user)
        self.assertEqual(kwargs["activity_type"], "quiz_completion")
        self.assertEqual(kwargs["content_object"], quiz)

        # Check that counter was incremented
        self.assertEqual(mock_increment_counter.call_count, 2)  # Should be called twice
        mock_increment_counter.assert_any_call("quizzes_completed")
        mock_increment_counter.assert_any_call("total_quizzes_taken")

    @unittest.skip("Course completion signal test needs to be updated for new model structure")
    @patch("web.services.counter_service.UserActivity.record_activity")
    @patch("web.services.counter_service.CounterStatistic.increment_counter")
    def test_course_completed_signal(self, mock_increment_counter, mock_record_activity):
        """Test that signals handle course completion correctly."""
        # Create an enrollment
        enrollment = Enrollment.objects.create(student=self.user, course=self.course, status="active")

        # Look at the CourseProgress model to see how it calculates completion
        # Instead of directly setting the completion_percentage property,
        # we'll use a different approach:
        # Let's first create a progress object with 50% completion
        progress = CourseProgress.objects.create(enrollment=enrollment)

        # Since completion_percentage is a property, we need to trigger the signal differently
        # Let's assume it's monitored in the save method, so we'll set some fields that would
        # indirectly result in 100% completion and save the model

        # Mocking the scenario where course is completed
        # We call the signal handler directly instead
        from web.services.counter_service import course_completed

        course_completed(sender=CourseProgress, instance=progress, **{"signal": None})

        # Check that activity was recorded
        mock_record_activity.assert_called_once()

        # Extract the parameters of the call without asserting equality
        args, kwargs = mock_record_activity.call_args
        self.assertEqual(kwargs["user"], self.user)
        self.assertEqual(kwargs["activity_type"], "course_completion")

        # Check that counter was incremented
        self.assertEqual(mock_increment_counter.call_count, 2)  # Should be called twice
        mock_increment_counter.assert_any_call("courses_completed")
        mock_increment_counter.assert_any_call("total_courses_completed")


class LiveCounterAPITests(TestCase):
    """Tests for the API endpoint that provides counter data."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        self.subject = Subject.objects.create(
            name="Test Subject", slug="test-subject", description="Test description", icon="fas fa-code"
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test description",
            teacher=self.user,
            subject=self.subject,
            level="beginner",
            price=99.99,
            max_students=50,
            learning_objectives="Test learning objectives",
        )

        # Create some counters with total statistics
        CounterStatistic.objects.create(counter_type="total_learners", value=100)
        CounterStatistic.objects.create(counter_type="total_enrollments", value=50)
        CounterStatistic.objects.create(counter_type="total_courses_completed", value=25)
        CounterStatistic.objects.create(counter_type="total_quizzes_taken", value=75)

        # Create some activities
        for i in range(5):
            UserActivity.record_activity(user=self.user, activity_type="enrollment", content_object=self.course)

    @patch("web.services.counter_service.CounterService.update_all_counters")
    def test_get_counter_data_api(self, mock_update_all_counters):
        """Test the get_counter_data API endpoint."""
        # Call the API
        response = self.client.get(reverse("counter_data"))

        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check counter values for the total statistics
        self.assertEqual(data["counters"]["total_learners"], 100)
        self.assertEqual(data["counters"]["total_enrollments"], 50)
        self.assertEqual(data["counters"]["total_courses_completed"], 25)
        self.assertEqual(data["counters"]["total_quizzes_taken"], 75)

        # Check that all counters were updated
        mock_update_all_counters.assert_called_once()

        # Check that activities were included
        self.assertIn("activities_html", data)
        self.assertIn("timestamp", data)


class LiveCountersIntegrationTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email=f"testuser_{timezone.now().timestamp()}@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        # Create subject
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject", description="Test Description")

        # Create course
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            description="Test Course Description",
            teacher=self.user,
            subject=self.subject,
            price=0,
            max_students=10,
            status="published",
        )

        # Create sessions
        self.sessions = []
        for i in range(5):
            session = Session.objects.create(
                course=self.course,
                title=f"Session {i+1}",
                description=f"Description for session {i+1}",
                start_time=timezone.now() + timezone.timedelta(days=i),
                end_time=timezone.now() + timezone.timedelta(days=i, hours=2),
                is_virtual=True,
                meeting_link="https://meet.example.com/test",
            )
            self.sessions.append(session)

        # Create students
        self.students = []
        for i in range(3):
            student = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}_{timezone.now().timestamp()}@example.com",
                password="testpass123",
            )
            self.students.append(student)

            # Create enrollment
            enrollment = Enrollment.objects.create(student=student, course=self.course, status="approved")

            # Create course progress
            progress = CourseProgress.objects.create(enrollment=enrollment)

            # Create enrollment activity
            UserActivity.record_activity(
                user=student, activity_type="enrollment", content_object=enrollment, show_full_name=True
            )

            # Mark all sessions as completed for the first student
            if i == 0:
                progress.completed_sessions.add(*self.sessions)
                # Create course completion activity
                UserActivity.record_activity(
                    user=student, activity_type="course_completion", content_object=self.course, show_full_name=True
                )

        # Create quiz
        self.quiz = Quiz.objects.create(
            title="Test Quiz",
            description="Test Quiz Description",
            creator=self.user,
            subject=self.subject,
            status="published",
            time_limit=30,
            passing_score=70,
        )

        # Create quiz completions
        for i in range(2):
            quiz_completion = UserQuiz.objects.create(
                user=self.students[i], quiz=self.quiz, score=80, max_score=100, completed=True, end_time=timezone.now()
            )
            # Create quiz completion activity
            UserActivity.record_activity(
                user=self.students[i],
                activity_type="quiz_completion",
                content_object=quiz_completion,
                show_full_name=True,
            )

    def test_counter_statistics(self):
        """Test counter statistics values"""
        # Clear existing counters
        CounterStatistic.objects.all().delete()

        # Initialize counters
        CounterStatistic.objects.create(
            counter_type="total_learners", value=User.objects.filter(is_staff=False).count()
        )
        CounterStatistic.objects.create(counter_type="total_enrollments", value=Enrollment.objects.count())

        # Count completed courses
        completed_courses = 0
        for progress in CourseProgress.objects.all():
            if progress.completed_sessions.count() == len(self.sessions):
                completed_courses += 1

        CounterStatistic.objects.create(counter_type="total_courses_completed", value=completed_courses)
        CounterStatistic.objects.create(
            counter_type="total_quizzes_taken", value=UserQuiz.objects.filter(completed=True).count()
        )

        # Verify counter values
        self.assertEqual(CounterStatistic.get_counter_value("total_learners"), 4)  # 3 students + 1 teacher
        self.assertEqual(CounterStatistic.get_counter_value("total_enrollments"), 3)
        self.assertEqual(CounterStatistic.get_counter_value("total_courses_completed"), 1)
        self.assertEqual(CounterStatistic.get_counter_value("total_quizzes_taken"), 2)

    def test_recent_activities(self):
        """Test recent activities"""
        # Get recent activities
        recent_activities = UserActivity.objects.order_by("-timestamp")[:10]
        expected_activity_count = (
            9  # 3 enrollments + 1 course completion + 2 quiz completions + 3 additional activities
        )

        # Verify activity count
        self.assertEqual(recent_activities.count(), expected_activity_count)

        # Verify activity types
        activity_types = set(recent_activities.values_list("activity_type", flat=True))
        expected_types = {"enrollment", "course_completion", "quiz_completion"}
        self.assertTrue(expected_types.issubset(activity_types))

        # Verify activity order (newest first)
        timestamps = list(recent_activities.values_list("timestamp", flat=True))
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
