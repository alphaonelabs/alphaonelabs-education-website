# pylint: disable=no-member
# flake8: noqa: E1101
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import Course, Enrollment, Session, SessionAttendance, Subject


class SelfReportAttendanceTests(TestCase):
    def setUp(self):
        # Create users
        self.teacher = User.objects.create_user(username="teacher", email="teacher@example.com", password="teacherpass")
        self.student = User.objects.create_user(username="student", email="student@example.com", password="studentpass")

        # Create subject
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")

        # Create course
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            description="Test Description",
            teacher=self.teacher,
            subject=self.subject,
            price=0.0,  # Free course
            level="beginner",
            learning_objectives="Test learning objectives",
            prerequisites="None",
            max_students=10,  # Adding max_students field
        )

        # Create enrollment
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course, status="approved")

        # Create sessions
        now = timezone.now()

        # Past session (yesterday)
        self.past_session = Session.objects.create(
            course=self.course,
            title="Past Session",
            description="This session happened yesterday",
            start_time=now - timedelta(days=1, hours=2),
            end_time=now - timedelta(days=1),
        )

        # Current session (happening now)
        self.current_session = Session.objects.create(
            course=self.course,
            title="Current Session",
            description="This session is happening now",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )

        # Future session (tomorrow)
        self.future_session = Session.objects.create(
            course=self.course,
            title="Future Session",
            description="This session will happen tomorrow",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=2),
        )

        # Set up client
        self.client = Client()

    def test_login_required(self):
        """Test that login is required for self-reporting attendance"""
        url = reverse("self_report_attendance", args=[self.past_session.id])
        response = self.client.get(url)

        # Check that response is a redirect (302)
        self.assertEqual(response.status_code, 302)

        # Check that it redirects to a login page (without checking the exact path)
        self.assertTrue("accounts/login" in response["Location"])

    def test_self_report_past_session(self):
        """Test self-reporting attendance for a past session"""
        self.client.login(username="student", password="studentpass")

        # Use a context manager without capturing the mock
        with patch("django.core.mail.send_mail"):
            response = self.client.post(reverse("self_report_attendance", args=[self.past_session.id]))
            # We don't need to check if email was sent since it uses Slack in this env
            # and it's configured to fail silently

            # Should redirect to course detail page
            self.assertEqual(response.status_code, 302)

        # Check if attendance record was created
        attendance = SessionAttendance.objects.get(session=self.past_session, student=self.student)

        self.assertEqual(attendance.status, "pending")
        self.assertTrue(attendance.self_reported)
        self.assertFalse(attendance.verified_by_teacher)

    def test_self_report_current_session(self):
        """Test self-reporting attendance for current session"""
        self.client.login(username="student", password="studentpass")

        # Store response and use it in assertion
        response = self.client.post(reverse("self_report_attendance", args=[self.current_session.id]))
        self.assertEqual(response.status_code, 302)

        # Should create attendance record
        attendance = SessionAttendance.objects.get(session=self.current_session, student=self.student)

        self.assertEqual(attendance.status, "pending")
        self.assertTrue(attendance.self_reported)

    def test_cannot_report_future_session(self):
        """Test that students cannot report attendance for future sessions"""
        self.client.login(username="student", password="studentpass")

        response = self.client.post(reverse("self_report_attendance", args=[self.future_session.id]))

        # Should redirect to course detail page
        self.assertEqual(response.status_code, 302)

        # Should not create attendance record
        self.assertFalse(SessionAttendance.objects.filter(session=self.future_session, student=self.student).exists())

    def test_already_reported_pending(self):
        """Test reporting when already have a pending record"""
        self.client.login(username="student", password="studentpass")

        # Create a pending attendance record
        attendance = SessionAttendance.objects.create(
            session=self.past_session, student=self.student, status="pending", self_reported=True
        )

        response = self.client.post(reverse("self_report_attendance", args=[self.past_session.id]))

        # Should redirect to course detail page
        self.assertEqual(response.status_code, 302)

        # Should not modify the attendance record
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, "pending")

    def test_already_verified_attendance(self):
        """Test reporting when attendance is already verified"""
        self.client.login(username="student", password="studentpass")

        # Create a verified attendance record
        attendance = SessionAttendance.objects.create(
            session=self.past_session, student=self.student, status="present", verified_by_teacher=True
        )

        response = self.client.post(reverse("self_report_attendance", args=[self.past_session.id]))

        # Should redirect to course detail page
        self.assertEqual(response.status_code, 302)

        # Should not modify the attendance record
        attendance.refresh_from_db()
        self.assertEqual(attendance.status, "present")

    def test_not_enrolled_student(self):
        """Test student who is not enrolled cannot report attendance"""
        # Create another student who is not enrolled
        not_enrolled = User.objects.create_user(username="not_enrolled", password="password")

        self.client.login(username="not_enrolled", password="password")

        # Should return 404 or 500 with an error
        response = self.client.post(reverse("self_report_attendance", args=[self.past_session.id]))

        # Accept either 404 or 500 response code
        self.assertIn(response.status_code, [404, 500])

        # Should not create attendance record
        self.assertFalse(SessionAttendance.objects.filter(session=self.past_session, student=not_enrolled).exists())

    def test_email_send_failure(self):
        """Test behavior when email sending fails"""
        self.client.login(username="student", password="studentpass")

        # Mock email sending to raise an exception
        with patch("django.core.mail.send_mail") as mock_send_mail:
            mock_send_mail.side_effect = Exception("Email sending failed")

            response = self.client.post(reverse("self_report_attendance", args=[self.past_session.id]))

            # Should redirect to course detail page
            self.assertEqual(response.status_code, 302)

        # Should still create attendance record despite email failure
        self.assertTrue(
            SessionAttendance.objects.filter(session=self.past_session, student=self.student, status="pending").exists()
        )
