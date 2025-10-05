from django.contrib.auth.models import User
from django.test import TestCase

from web.models import Course, SessionWaitingRoom


class SessionWaitingRoomTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="testpass")
        self.student1 = User.objects.create_user(username="student1", password="testpass")
        self.student2 = User.objects.create_user(username="student2", password="testpass")

        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            teacher=self.teacher,
            description="Test Description",
            learning_objectives="Test Objectives",
            prerequisites="None",
            price=100.00,
            status="published",
        )

    def test_create_session_waiting_room(self):
        """Test creating a session waiting room for a course"""
        waiting_room = SessionWaitingRoom.objects.create(course=self.course)
        self.assertEqual(waiting_room.course, self.course)
        self.assertEqual(waiting_room.participant_count(), 0)

    def test_unique_course_constraint(self):
        """Test that only one waiting room can exist per course"""
        SessionWaitingRoom.objects.create(course=self.course)

        # Trying to create another waiting room for the same course should fail
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            SessionWaitingRoom.objects.create(course=self.course)

    def test_add_participants(self):
        """Test adding participants to the waiting room"""
        waiting_room = SessionWaitingRoom.objects.create(course=self.course)
        waiting_room.participants.add(self.student1, self.student2)

        self.assertEqual(waiting_room.participant_count(), 2)
        self.assertIn(self.student1, waiting_room.participants.all())
        self.assertIn(self.student2, waiting_room.participants.all())

    def test_str_representation(self):
        """Test the string representation of the waiting room"""
        waiting_room = SessionWaitingRoom.objects.create(course=self.course)
        expected_str = f"Waiting Room for {self.course.title}"
        self.assertEqual(str(waiting_room), expected_str)

    def test_cascade_delete(self):
        """Test that waiting room is deleted when course is deleted"""
        waiting_room = SessionWaitingRoom.objects.create(course=self.course)
        waiting_room_id = waiting_room.id

        self.course.delete()

        # Waiting room should be deleted along with the course
        self.assertFalse(SessionWaitingRoom.objects.filter(id=waiting_room_id).exists())
