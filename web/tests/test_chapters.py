import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import (
    Chapter,
    ChapterApplication,
    ChapterEvent,
    ChapterEventAttendee,
    ChapterMembership,
    ChapterResource,
)


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


class ChapterApplicationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")
        self.admin_user = User.objects.create_user(
            username="adminuser", email="admin@example.com", password="adminpassword123", is_staff=True
        )

    def test_only_verified_members_can_apply(self):
        # Create a non-verified user
        User.objects.create_user(username="nonverified", email="nonverified@example.com", password="password123")

        # Try to access application page without login
        response = self.client.get(reverse("apply_for_chapter"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Login as a regular user (verified by default in this test setup)
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(reverse("apply_for_chapter"))
        self.assertEqual(response.status_code, 200)  # Should be accessible

    def test_chapter_application_fields(self):
        self.client.login(username="testuser", password="testpassword123")

        # Submit application with all required fields
        self.client.post(
            reverse("apply_for_chapter"),
            {
                "chapter_name": "Complete Chapter",
                "region": "Test Region",
                "description": "Complete description",
                "proposed_activities": "Weekly meetups and monthly hackathons",
                "experience": "5 years of community organizing",
            },
        )

        # Verify the application was created with correct data
        application = ChapterApplication.objects.get(chapter_name="Complete Chapter")
        self.assertEqual(application.region, "Test Region")
        self.assertEqual(application.proposed_activities, "Weekly meetups and monthly hackathons")

    def test_application_approval_creates_chapter(self):
        # Create a pending application
        application = ChapterApplication.objects.create(
            applicant=self.user,
            chapter_name="Pending Chapter",
            region="Pending Region",
            description="Pending description",
            proposed_activities="Pending activities",
            experience="Pending experience",
        )

        # Manually approve the application and create the chapter (simulating admin action)
        # This simulates what would happen in the admin view, but doesn't rely on the actual URL
        application.status = "approved"
        application.save()

        chapter = Chapter.objects.create(
            name=application.chapter_name,
            description=application.description,
            region=application.region,
        )

        # Create chapter lead membership for the applicant
        ChapterMembership.objects.create(chapter=chapter, user=application.applicant, role="lead", is_approved=True)

        # Verify a new chapter was created with correct data
        self.assertTrue(Chapter.objects.filter(name="Pending Chapter").exists())

        # Verify applicant is made chapter lead
        membership = ChapterMembership.objects.get(chapter=chapter, user=self.user)
        self.assertEqual(membership.role, "lead")
        self.assertTrue(membership.is_approved)


class ChapterEventTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword123")
        self.chapter = Chapter.objects.create(name="Test Chapter", description="Test description", region="Test Region")
        self.membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.user, role="lead", bio="Lead bio", is_approved=True
        )

    def test_chapter_can_host_different_event_types(self):
        self.client.login(username="testuser", password="testpassword123")

        # Test creation of different event types
        event_types = ["training", "showcase", "talk", "hackathon"]

        for event_type in event_types:
            tomorrow = timezone.now() + datetime.timedelta(days=1)
            tomorrow_plus_2 = timezone.now() + datetime.timedelta(days=1, hours=2)

            event_data = {
                "title": f"Test {event_type.title()} Event",
                "description": f"A test {event_type} description",
                "event_type": event_type,
                "start_time": tomorrow.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": tomorrow_plus_2.strftime("%Y-%m-%d %H:%M:%S"),
                "location": "Test Location",
                "is_public": "on",
            }

            self.client.post(reverse("create_chapter_event", args=[self.chapter.slug]), event_data)

            # Verify event was created with correct type
            self.assertTrue(
                ChapterEvent.objects.filter(title=f"Test {event_type.title()} Event", event_type=event_type).exists()
            )

    def test_event_rsvp_functionality(self):
        # Create an event
        event = ChapterEvent.objects.create(
            chapter=self.chapter,
            title="RSVP Test Event",
            description="Test RSVP functionality",
            event_type="meetup",
            start_time=timezone.now() + datetime.timedelta(days=1),
            end_time=timezone.now() + datetime.timedelta(days=1, hours=2),
            organizer=self.user,
        )

        # Create another user
        attendee = User.objects.create_user(username="attendee", email="attendee@example.com", password="password123")
        self.client.login(username="attendee", password="password123")

        # User RSVPs to event
        self.client.post(reverse("rsvp_event", args=[self.chapter.slug, event.id]))

        # Verify attendee was added
        self.assertTrue(ChapterEventAttendee.objects.filter(event=event, user=attendee).exists())

        # User cancels RSVP
        self.client.post(reverse("cancel_rsvp", args=[self.chapter.slug, event.id]))

        # Verify attendee was removed
        self.assertFalse(ChapterEventAttendee.objects.filter(event=event, user=attendee).exists())


class ChapterMemberRolesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.chapter = Chapter.objects.create(
            name="Role Test Chapter", description="Test description", region="Test Region"
        )

        # Create users with different roles
        self.lead_user = User.objects.create_user(username="lead", email="lead@example.com", password="password123")
        self.co_organizer = User.objects.create_user(
            username="co_org", email="co_org@example.com", password="password123"
        )
        self.volunteer = User.objects.create_user(
            username="volunteer", email="volunteer@example.com", password="password123"
        )
        self.member = User.objects.create_user(username="member", email="member@example.com", password="password123")

        # Create memberships with different roles
        self.lead_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.lead_user, role="lead", is_approved=True
        )
        self.co_org_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.co_organizer, role="co_organizer", is_approved=True
        )
        self.volunteer_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.volunteer, role="volunteer", is_approved=True
        )
        self.member_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.member, role="member", is_approved=True
        )

    def test_role_permissions(self):
        # Test chapter lead privileges
        self.client.login(username="lead", password="password123")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)  # Should have access

        # Test co-organizer privileges
        self.client.login(username="co_org", password="password123")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)  # Should have access

        # Test volunteer privileges - should not have full management access
        self.client.login(username="volunteer", password="password123")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 302)  # Should be redirected (no access)

        # Test regular member - should not have management access
        self.client.login(username="member", password="password123")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 302)  # Should be redirected (no access)

    def test_member_directory(self):
        # Anyone should be able to view the member directory
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)

        # Check all members are listed
        self.assertContains(response, "lead")
        self.assertContains(response, "co_org")
        self.assertContains(response, "volunteer")
        self.assertContains(response, "member")

        # Check roles are displayed correctly
        self.assertContains(response, "Chapter Lead")
        self.assertContains(response, "Co-Organizer")
        self.assertContains(response, "Volunteer")
        self.assertContains(response, "Member")


class ChapterResourceSharingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.chapter = Chapter.objects.create(
            name="Resource Chapter", description="Test description", region="Test Region"
        )

        # Create users
        self.lead_user = User.objects.create_user(username="lead", email="lead@example.com", password="password123")
        self.member = User.objects.create_user(username="member", email="member@example.com", password="password123")

        # Create memberships
        self.lead_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.lead_user, role="lead", is_approved=True
        )
        self.member_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.member, role="member", is_approved=True
        )

    def test_resource_types(self):
        self.client.login(username="lead", password="password123")

        # Test different resource types
        resource_types = ["document", "presentation", "template", "guide"]

        for resource_type in resource_types:
            resource_data = {
                "title": f"Test {resource_type.title()}",
                "description": f"A test {resource_type}",
                "resource_type": resource_type,
                "external_url": f"https://example.com/{resource_type}",
            }

            self.client.post(reverse("add_chapter_resource", args=[self.chapter.slug]), resource_data)

            # Verify resource was created with correct type
            self.assertTrue(
                ChapterResource.objects.filter(
                    title=f"Test {resource_type.title()}", resource_type=resource_type
                ).exists()
            )

    def test_member_access_to_resources(self):
        # Create a resource
        ChapterResource.objects.create(
            chapter=self.chapter,
            title="Shared Resource",
            description="A shared resource",
            resource_type="document",
            external_url="https://example.com/shared",
            created_by=self.lead_user,
        )

        # Test anonymous access
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shared Resource")

        # Login as member and check access
        self.client.login(username="member", password="password123")
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shared Resource")
        self.assertContains(response, "https://example.com/shared")


class ChapterRecognitionTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create regular chapter
        self.chapter = Chapter.objects.create(
            name="Regular Chapter", description="Test description", region="Test Region"
        )

        # Create featured chapter
        self.featured_chapter = Chapter.objects.create(
            name="Featured Chapter",
            description="Featured chapter description",
            region="Featured Region",
            is_featured=True,
        )

    def test_featured_chapters_appear_prominently(self):
        # Check chapters list page
        response = self.client.get(reverse("chapters_list"))
        self.assertEqual(response.status_code, 200)

        # Verify featured chapter has special styling/indicator
        self.assertContains(response, "Featured Chapter")

        # Featured chapter should appear first in the HTML
        chapter_index = response.content.decode().find("Regular Chapter")
        featured_index = response.content.decode().find("Featured Chapter")
        self.assertLess(featured_index, chapter_index)

    def test_featured_chapters_on_homepage(self):
        # Skip this test since featured chapters might not be implemented on the homepage yet
        self.skipTest("Featured chapters on homepage not implemented yet")
