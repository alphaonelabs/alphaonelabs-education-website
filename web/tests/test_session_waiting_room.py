from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from web.models import Course, Session, SessionWaitingRoom, Subject, Enrollment


class SessionWaitingRoomTestCase(TestCase):
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create users
        self.teacher = User.objects.create_user(
            username='teacher', email='teacher@test.com', password='testpass123'
        )
        self.student = User.objects.create_user(
            username='student', email='student@test.com', password='testpass123'
        )
        
        # Create subject
        self.subject = Subject.objects.create(name='Test Subject', slug='test-subject')
        
        # Create course
        self.course = Course.objects.create(
            title='Test Course',
            slug='test-course',
            teacher=self.teacher,
            description='Test description',
            learning_objectives='Test objectives',
            price=100.00,
            subject=self.subject,
            max_students=10,
            status='published'
        )
        
        # Create sessions - one past and one future
        now = timezone.now()
        self.past_session = Session.objects.create(
            course=self.course,
            title='Past Session',
            description='A past session',
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            is_virtual=True,
            meeting_link='https://example.com/meeting'
        )
        
        self.future_session = Session.objects.create(
            course=self.course,
            title='Future Session', 
            description='A future session',
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            is_virtual=True,
            meeting_link='https://example.com/meeting'
        )
        
        # Create enrollment for student
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status='approved'
        )

    def test_session_waiting_room_model(self):
        """Test the SessionWaitingRoom model."""
        # Create a session waiting room
        waiting_room = SessionWaitingRoom.objects.create(course=self.course)
        
        # Test string representation
        self.assertEqual(str(waiting_room), f"Waiting room for next session of {self.course.title}")
        
        # Test participant count
        self.assertEqual(waiting_room.participant_count(), 0)
        
        # Add participant
        waiting_room.participants.add(self.student)
        self.assertEqual(waiting_room.participant_count(), 1)
        
        # Test get_next_session
        next_session = waiting_room.get_next_session()
        self.assertEqual(next_session, self.future_session)
        
        # Test close_waiting_room
        waiting_room.close_waiting_room()
        waiting_room.refresh_from_db()
        self.assertEqual(waiting_room.status, 'closed')

    def test_join_session_waiting_room_view(self):
        """Test joining a session waiting room."""
        self.client.login(username='student', password='testpass123')
        
        url = reverse('join_session_waiting_room', kwargs={'course_slug': self.course.slug})
        response = self.client.post(url)
        
        # Should redirect to course detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', kwargs={'slug': self.course.slug}))
        
        # Check that waiting room was created and user was added
        waiting_room = SessionWaitingRoom.objects.get(course=self.course)
        self.assertIn(self.student, waiting_room.participants.all())
        self.assertEqual(waiting_room.status, 'open')

    def test_leave_session_waiting_room_view(self):
        """Test leaving a session waiting room."""
        # First create and join a waiting room
        waiting_room = SessionWaitingRoom.objects.create(course=self.course)
        waiting_room.participants.add(self.student)
        
        self.client.login(username='student', password='testpass123')
        
        url = reverse('leave_session_waiting_room', kwargs={'course_slug': self.course.slug})
        response = self.client.post(url)
        
        # Should redirect to course detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course_detail', kwargs={'slug': self.course.slug}))
        
        # Check that user was removed from waiting room
        waiting_room.refresh_from_db()
        self.assertNotIn(self.student, waiting_room.participants.all())

    def test_session_detail_context_with_waiting_room(self):
        """Test that session detail view includes waiting room context."""
        # Create waiting room and add student
        waiting_room = SessionWaitingRoom.objects.create(course=self.course)
        waiting_room.participants.add(self.student)
        
        self.client.login(username='student', password='testpass123')
        
        url = reverse('session_detail', kwargs={'session_id': self.past_session.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('next_session', response.context)
        self.assertIn('user_in_session_waiting_room', response.context)
        self.assertEqual(response.context['next_session'], self.future_session)
        self.assertTrue(response.context['user_in_session_waiting_room'])

    def test_session_detail_no_access(self):
        """Test that users without enrollment can't access session detail."""
        # Create another user not enrolled in the course
        other_user = User.objects.create_user(
            username='other', email='other@test.com', password='testpass123'
        )
        
        self.client.login(username='other', password='testpass123')
        
        url = reverse('session_detail', kwargs={'session_id': self.past_session.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)

    def test_unique_waiting_room_per_course(self):
        """Test that only one waiting room can exist per course."""
        # Create first waiting room
        waiting_room1 = SessionWaitingRoom.objects.create(course=self.course)
        
        # Try to create another - should fail due to unique constraint
        with self.assertRaises(Exception):
            SessionWaitingRoom.objects.create(course=self.course)

    def test_login_required_for_waiting_room_views(self):
        """Test that waiting room views require authentication."""
        # Test join view
        join_url = reverse('join_session_waiting_room', kwargs={'course_slug': self.course.slug})
        response = self.client.post(join_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        
        # Test leave view
        leave_url = reverse('leave_session_waiting_room', kwargs={'course_slug': self.course.slug})
        response = self.client.post(leave_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)