"""Tests for virtual classroom functionality."""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from web.models import ClassroomSeat, Profile, RaisedHand, UpdateRound, UpdateRoundParticipant, VirtualClassroom


class VirtualClassroomModelTests(TestCase):
    """Test cases for Virtual Classroom models."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(username="teacher", password="testpass")
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher)
        self.teacher_profile.is_teacher = True
        self.teacher_profile.save()

        self.student = User.objects.create_user(username="student", password="testpass")
        Profile.objects.get_or_create(user=self.student)

        self.classroom = VirtualClassroom.objects.create(title="Test Classroom", teacher=self.teacher, rows=3, columns=4)

        # Create seats
        for row in range(3):
            for col in range(4):
                ClassroomSeat.objects.create(classroom=self.classroom, row=row, column=col)

    def test_virtual_classroom_creation(self):
        """Test creating a virtual classroom."""
        self.assertEqual(self.classroom.title, "Test Classroom")
        self.assertEqual(self.classroom.teacher, self.teacher)
        self.assertEqual(self.classroom.rows, 3)
        self.assertEqual(self.classroom.columns, 4)
        self.assertTrue(self.classroom.is_active)

    def test_classroom_total_seats(self):
        """Test total seats calculation."""
        self.assertEqual(self.classroom.total_seats(), 12)

    def test_classroom_seats_created(self):
        """Test that seats are created correctly."""
        seats = ClassroomSeat.objects.filter(classroom=self.classroom)
        self.assertEqual(seats.count(), 12)

    def test_seat_assignment(self):
        """Test assigning a student to a seat."""
        seat = ClassroomSeat.objects.filter(classroom=self.classroom).first()
        seat.student = self.student
        seat.is_occupied = True
        seat.save()

        self.assertEqual(seat.student, self.student)
        self.assertTrue(seat.is_occupied)
        self.assertEqual(self.classroom.occupied_seats_count(), 1)

    def test_raised_hand_creation(self):
        """Test creating a raised hand."""
        seat = ClassroomSeat.objects.filter(classroom=self.classroom).first()
        seat.student = self.student
        seat.is_occupied = True
        seat.save()

        raised_hand = RaisedHand.objects.create(classroom=self.classroom, student=self.student, seat=seat)

        self.assertEqual(raised_hand.student, self.student)
        self.assertTrue(raised_hand.is_active)
        self.assertIsNone(raised_hand.selected_at)

    def test_update_round_creation(self):
        """Test creating an update round."""
        update_round = UpdateRound.objects.create(classroom=self.classroom, duration_seconds=120)

        self.assertEqual(update_round.classroom, self.classroom)
        self.assertEqual(update_round.duration_seconds, 120)
        self.assertFalse(update_round.is_active)


class VirtualClassroomViewTests(TestCase):
    """Test cases for Virtual Classroom views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.teacher = User.objects.create_user(username="teacher", password="testpass")
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher)
        self.teacher_profile.is_teacher = True
        self.teacher_profile.save()

        self.student = User.objects.create_user(username="student", password="testpass")
        Profile.objects.get_or_create(user=self.student)

    def test_classroom_list_view_requires_login(self):
        """Test that classroom list requires authentication."""
        response = self.client.get(reverse("virtual_classroom_list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_classroom_list_view_authenticated(self):
        """Test classroom list view for authenticated users."""
        self.client.login(username="student", password="testpass")
        response = self.client.get(reverse("virtual_classroom_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Virtual Classrooms")

    def test_create_classroom_requires_teacher(self):
        """Test that only teachers can create classrooms."""
        self.client.login(username="student", password="testpass")
        response = self.client.get(reverse("create_virtual_classroom"))
        self.assertEqual(response.status_code, 302)  # Redirect or forbidden

    def test_create_classroom_teacher_access(self):
        """Test that teachers can access create classroom page."""
        self.client.login(username="teacher", password="testpass")
        response = self.client.get(reverse("create_virtual_classroom"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Virtual Classroom")

    def test_create_classroom_post(self):
        """Test creating a classroom via POST."""
        self.client.login(username="teacher", password="testpass")
        response = self.client.post(
            reverse("create_virtual_classroom"), {"title": "New Classroom", "rows": 5, "columns": 6}
        )

        self.assertEqual(VirtualClassroom.objects.count(), 1)
        classroom = VirtualClassroom.objects.first()
        self.assertEqual(classroom.title, "New Classroom")
        self.assertEqual(classroom.rows, 5)
        self.assertEqual(classroom.columns, 6)
        self.assertEqual(classroom.teacher, self.teacher)

        # Check that seats were created
        self.assertEqual(ClassroomSeat.objects.filter(classroom=classroom).count(), 30)

    def test_classroom_detail_view(self):
        """Test classroom detail view."""
        classroom = VirtualClassroom.objects.create(title="Test Classroom", teacher=self.teacher, rows=3, columns=4)

        for row in range(3):
            for col in range(4):
                ClassroomSeat.objects.create(classroom=classroom, row=row, column=col)

        self.client.login(username="student", password="testpass")
        response = self.client.get(reverse("virtual_classroom_detail", args=[classroom.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Classroom")

    def test_classroom_detail_inactive_for_students(self):
        """Test that students cannot access inactive classrooms."""
        classroom = VirtualClassroom.objects.create(
            title="Inactive Classroom", teacher=self.teacher, rows=3, columns=4, is_active=False
        )

        self.client.login(username="student", password="testpass")
        response = self.client.get(reverse("virtual_classroom_detail", args=[classroom.id]))
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_end_classroom_teacher_only(self):
        """Test that only teachers can end a classroom."""
        classroom = VirtualClassroom.objects.create(title="Test Classroom", teacher=self.teacher, rows=3, columns=4)

        self.client.login(username="student", password="testpass")
        response = self.client.post(reverse("end_classroom", args=[classroom.id]))
        self.assertEqual(response.status_code, 302)  # Redirect or forbidden

        # Classroom should still be active
        classroom.refresh_from_db()
        self.assertTrue(classroom.is_active)

    def test_end_classroom_teacher(self):
        """Test that teachers can end a classroom."""
        classroom = VirtualClassroom.objects.create(title="Test Classroom", teacher=self.teacher, rows=3, columns=4)

        self.client.login(username="teacher", password="testpass")
        response = self.client.post(reverse("end_classroom", args=[classroom.id]))

        classroom.refresh_from_db()
        self.assertFalse(classroom.is_active)
