import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import Course, CourseProgress, Enrollment, Session, SessionAttendance, Subject


class ProgressVisualizationTest(TestCase):
    """Test cases for the progress_visualization view."""

    def setUp(self):
        """Set up test data for progress visualization tests."""
        # Create test user
        self.password = "testpassword123"
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password=self.password,
        )
        self.client = Client()
        self.client.login(username="testuser", password=self.password)

        # Create a subject first
        self.subject = Subject.objects.create(
            name="Programming",
            slug="programming",
        )

        # Create test courses
        self.course1 = Course.objects.create(
            title="Python Basics",
            description="Introduction to Python",
            learning_objectives="Learn Python basics",
            prerequisites="None",
            price=99.99,
            max_students=20,
            subject=self.subject,
            teacher=self.user,
            slug="python-basics",
        )
        self.course2 = Course.objects.create(
            title="Advanced Django",
            description="Advanced web development with Django",
            learning_objectives="Learn advanced Django concepts",
            prerequisites="Basic Django knowledge",
            price=149.99,
            max_students=15,
            subject=self.subject,
            teacher=self.user,
            slug="advanced-django",
        )

        # Create course sessions
        now = timezone.now()

        # Create sessions for course 1
        self.sessions_c1 = []
        for i in range(5):
            session = Session.objects.create(
                course=self.course1,
                title=f"Session {i + 1}",
                description=f"Description for session {i + 1}",
                start_time=now - timedelta(days=10 - i, hours=2),
                end_time=now - timedelta(days=10 - i),
            )
            self.sessions_c1.append(session)

        # Create sessions for course 2
        self.sessions_c2 = []
        for i in range(3):
            session = Session.objects.create(
                course=self.course2,
                title=f"Advanced Session {i + 1}",
                description=f"Advanced description for session {i + 1}",
                start_time=now - timedelta(days=5 - i, hours=2),
                end_time=now - timedelta(days=5 - i),
            )
            self.sessions_c2.append(session)

        # Create enrollments
        self.enrollment1 = Enrollment.objects.create(
            student=self.user,
            course=self.course1,
            enrollment_date=now - timedelta(days=15),
            status="approved",
        )

        self.enrollment2 = Enrollment.objects.create(
            student=self.user,
            course=self.course2,
            enrollment_date=now - timedelta(days=8),
            status="completed",
            completion_date=now - timedelta(days=1),
        )

        # Create progress records
        self.progress1 = CourseProgress.objects.create(enrollment=self.enrollment1)
        self.progress1.completed_sessions.add(self.sessions_c1[0], self.sessions_c1[1], self.sessions_c1[2])

        self.progress2 = CourseProgress.objects.create(enrollment=self.enrollment2)
        self.progress2.completed_sessions.add(*self.sessions_c2)

        # Create attendance records
        for session in self.sessions_c1[:3]:
            SessionAttendance.objects.create(
                student=self.user,
                session=session,
                status="present",
            )

        SessionAttendance.objects.create(
            student=self.user,
            session=self.sessions_c1[3],
            status="absent",
        )

        for session in self.sessions_c2:
            SessionAttendance.objects.create(
                student=self.user,
                session=session,
                status="present" if session != self.sessions_c2[1] else "late",
            )

    def test_progress_visualization_view(self):
        """Test that the progress visualization view returns correct data."""
        url = reverse("progress_visualization")
        response = self.client.get(url)

        # Check basic response properties
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/progress_visualization.html")

        # Check context data calculations
        context = response.context

        # Course statistics
        self.assertEqual(context["total_courses"], 2)
        self.assertEqual(context["courses_completed"], 1)
        self.assertEqual(context["courses_completed_percentage"], 50)

        # Topic mastery should equal completed sessions
        self.assertEqual(context["topics_mastered"], 6)

        # Attendance stats
        self.assertEqual(context["average_attendance"], 86)

        # Check that most_active_day is a valid day of the week
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.assertIn(context["most_active_day"], days_of_week)

        # Course data
        self.assertEqual(len(context["courses"]), 2)

        # Check that JSON data is properly formatted
        try:
            parsed_dates = json.loads(context["progress_dates"])
            self.assertIsInstance(parsed_dates, list)

            parsed_sessions = json.loads(context["sessions_completed"])
            self.assertIsInstance(parsed_sessions, list)
            self.assertEqual(len(parsed_sessions), 2)

            parsed_courses = json.loads(context["courses_json"])
            self.assertIsInstance(parsed_courses, list)
            self.assertEqual(len(parsed_courses), 2)
        except json.JSONDecodeError:
            self.fail("JSON data in context is not properly formatted")

    def test_unauthenticated_access(self):
        """Test that unauthenticated users are redirected to login."""
        self.client.logout()
        url = reverse("progress_visualization")
        response = self.client.get(url)

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/en/accounts/login/"))
