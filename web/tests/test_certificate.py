import uuid

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from web.models import Certificate, Course, Subject


class CertificateModelTest(TestCase):
    def setUp(self):
        # Create a test user.
        self.user = User.objects.create_user(
            username="testuser", password="testpass", email="test@example.com", first_name="Test", last_name="User"
        )
        # Create a test subject.
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")
        # Create a test course.
        self.course = Course.objects.create(
            title="Testing Course",
            slug="testing-course",
            teacher=self.user,
            description="Test Description",
            learning_objectives="Test Objectives",
            prerequisites="None",
            price=100.00,
            allow_individual_sessions=False,
            invite_only=False,
            status="published",
            max_students=10,
            subject=self.subject,
            level="beginner",
            tags="test",
            is_featured=False,
        )
        # Use a fixed certificate UUID for testing.
        self.certificate_uuid = uuid.UUID("9775783c-9f74-4aeb-8a47-5128a3b7b73a")

    def test_certificate_creation(self):
        # Create a certificate record with the fixed UUID.
        certificate = Certificate.objects.create(
            user=self.user, course=self.course, certificate_id=self.certificate_uuid
        )
        self.assertIsNotNone(certificate.certificate_id)
        expected_str = f"Certificate for {self.user.username} - {self.course.title}"
        self.assertEqual(str(certificate), expected_str)

    def test_certificate_detail_view(self):
        # Create a certificate with the fixed UUID.
        certificate = Certificate.objects.create(
            user=self.user, course=self.course, certificate_id=self.certificate_uuid
        )
        # Build URL using the certificate UUID.
        url = reverse("certificate_detail", args=[str(certificate.certificate_id)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that key certificate details are rendered in the HTML.
        self.assertContains(response, "Certificate of Completion")
        self.assertContains(response, self.user.get_full_name())
        self.assertContains(response, self.course.title)
        # Verify that share button URLs are present.
        self.assertContains(response, "https://www.linkedin.com/sharing/share-offsite/?url=")
        self.assertContains(response, "https://twitter.com/intent/tweet")
        self.assertContains(response, "https://www.facebook.com/sharer/sharer.php?u=")

    def test_student_dashboard_includes_certificates(self):
        # Create a certificate for the test user.
        certificate = Certificate.objects.create(
            user=self.user, course=self.course, certificate_id=self.certificate_uuid
        )
        # Simulate login.
        self.client.login(username="testuser", password="testpass")
        # Assume the dashboard URL is named 'student_dashboard'
        url = reverse("student_dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that the dashboard displays the certificate section.
        self.assertContains(response, "Your Certificates")
        # Verify that the certificate for the course appears as a link.
        expected_link = reverse("certificate_detail", args=[str(certificate.certificate_id)])
        self.assertContains(response, expected_link)
