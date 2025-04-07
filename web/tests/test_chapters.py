import datetime

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import Chapter, ChapterApplication, ChapterEvent, ChapterMembership, ChapterResource


class ChapterModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")

        self.chapter = Chapter.objects.create(
            name="Test Chapter", description="A test chapter for unit testing", region="Test Region"
        )

    def test_chapter_creation(self):
        self.assertEqual(self.chapter.name, "Test Chapter")
        self.assertEqual(self.chapter.description, "A test chapter for unit testing")
        self.assertEqual(self.chapter.region, "Test Region")
        self.assertTrue(self.chapter.is_active)
        self.assertFalse(self.chapter.is_featured)

    def test_membership_creation(self):
        membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.user, role="lead", bio="Test bio", is_approved=True
        )

        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.chapter, self.chapter)
        self.assertEqual(membership.role, "lead")
        self.assertEqual(membership.bio, "Test bio")
        self.assertTrue(membership.is_approved)

    def test_event_creation(self):
        event = ChapterEvent.objects.create(
            chapter=self.chapter,
            title="Test Event",
            description="A test event",
            event_type="meetup",
            start_time=timezone.now() + datetime.timedelta(days=1),
            end_time=timezone.now() + datetime.timedelta(days=1, hours=2),
            location="Test Location",
            organizer=self.user,
        )

        self.assertEqual(event.chapter, self.chapter)
        self.assertEqual(event.title, "Test Event")
        self.assertEqual(event.description, "A test event")
        self.assertEqual(event.event_type, "meetup")
        self.assertEqual(event.location, "Test Location")
        self.assertEqual(event.organizer, self.user)

    def test_resource_creation(self):
        resource = ChapterResource.objects.create(
            chapter=self.chapter,
            title="Test Resource",
            description="A test resource",
            resource_type="document",
            external_url="https://example.com/resource",
            created_by=self.user,
        )

        self.assertEqual(resource.chapter, self.chapter)
        self.assertEqual(resource.title, "Test Resource")
        self.assertEqual(resource.description, "A test resource")
        self.assertEqual(resource.resource_type, "document")
        self.assertEqual(resource.external_url, "https://example.com/resource")
        self.assertEqual(resource.created_by, self.user)

    def test_application_creation(self):
        application = ChapterApplication.objects.create(
            applicant=self.user,
            chapter_name="New Chapter Application",
            region="New Region",
            description="A new chapter application",
            proposed_activities="Proposed activities",
            experience="Leadership experience",
        )

        self.assertEqual(application.applicant, self.user)
        self.assertEqual(application.chapter_name, "New Chapter Application")
        self.assertEqual(application.region, "New Region")
        self.assertEqual(application.status, "pending")


class ChapterViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create test users
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")

        self.admin_user = User.objects.create_user(
            username="adminuser", email="admin@example.com", password="adminpassword123", is_staff=True
        )

        # Create test chapter
        self.chapter = Chapter.objects.create(
            name="Test Chapter", description="A test chapter for integration testing", region="Test Region"
        )

        # Create lead membership
        self.lead_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.admin_user, role="lead", is_approved=True
        )

        # Create an event
        self.event = ChapterEvent.objects.create(
            chapter=self.chapter,
            title="Test Event",
            description="A test event",
            event_type="meetup",
            start_time=timezone.now() + datetime.timedelta(days=1),
            end_time=timezone.now() + datetime.timedelta(days=1, hours=2),
            organizer=self.admin_user,
        )

        # Create a resource
        self.resource = ChapterResource.objects.create(
            chapter=self.chapter,
            title="Test Resource",
            description="A test resource",
            resource_type="document",
            external_url="https://example.com/resource",
            created_by=self.admin_user,
        )

    def test_chapters_list_view(self):
        response = self.client.get(reverse("chapters_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Chapter")

    def test_chapter_detail_view(self):
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Chapter")
        self.assertContains(response, "Test Event")
        self.assertContains(response, "Test Resource")

    def test_join_chapter_view(self):
        # Login as normal user
        self.client.login(username="testuser", password="testpassword123")

        # Get the join page
        response = self.client.get(reverse("join_chapter", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)

        # Submit the join form
        response = self.client.post(reverse("join_chapter", args=[self.chapter.slug]), {"bio": "Test member bio"})
        self.assertRedirects(response, reverse("chapter_detail", args=[self.chapter.slug]))

        # Verify membership was created but not approved
        membership = ChapterMembership.objects.get(user=self.user, chapter=self.chapter)
        self.assertEqual(membership.role, "member")
        self.assertFalse(membership.is_approved)

    def test_chapter_management_view(self):
        # Login as chapter lead
        self.client.login(username="adminuser", password="adminpassword123")

        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Chapter")

        # Normal users shouldn't be able to access management page
        self.client.login(username="testuser", password="testpassword123")

        # First create a membership for the test user
        ChapterMembership.objects.create(chapter=self.chapter, user=self.user, role="member", is_approved=True)

        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 302)  # Should redirect

    def test_creating_chapter_event(self):
        # Login as chapter lead
        self.client.login(username="adminuser", password="adminpassword123")

        # Get the create event page
        response = self.client.get(reverse("create_chapter_event", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)

        # Create an event
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        tomorrow_plus_2 = timezone.now() + datetime.timedelta(days=1, hours=2)

        event_data = {
            "title": "New Test Event",
            "description": "A new test event description",
            "event_type": "workshop",
            "start_time": tomorrow.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": tomorrow_plus_2.strftime("%Y-%m-%d %H:%M:%S"),
            "location": "New Location",
            "is_public": "on",
        }

        response = self.client.post(reverse("create_chapter_event", args=[self.chapter.slug]), event_data)

        # Check that the event was created
        self.assertTrue(ChapterEvent.objects.filter(title="New Test Event").exists())

    def test_adding_chapter_resource(self):
        # Login as chapter lead
        self.client.login(username="adminuser", password="adminpassword123")

        # Get the add resource page
        response = self.client.get(reverse("add_chapter_resource", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)

        # Add a resource
        resource_data = {
            "title": "New Test Resource",
            "description": "A new test resource description",
            "resource_type": "template",
            "external_url": "https://example.com/new-resource",
        }

        response = self.client.post(reverse("add_chapter_resource", args=[self.chapter.slug]), resource_data)

        # Check that the resource was created
        self.assertTrue(ChapterResource.objects.filter(title="New Test Resource").exists())

    def test_chapter_application(self):
        # Login as normal user
        self.client.login(username="testuser", password="testpassword123")

        # Get the application page
        response = self.client.get(reverse("apply_for_chapter"))
        self.assertEqual(response.status_code, 200)

        # Submit an application
        application_data = {
            "chapter_name": "New Test Chapter",
            "region": "New Test Region",
            "description": "A new test chapter description",
            "proposed_activities": "Proposed activities for new chapter",
            "experience": "Leadership experience",
        }

        response = self.client.post(reverse("apply_for_chapter"), application_data)

        # Check that the application was created
        self.assertTrue(ChapterApplication.objects.filter(chapter_name="New Test Chapter").exists())
        self.assertRedirects(response, reverse("chapters_list"))
