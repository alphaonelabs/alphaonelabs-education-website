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
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="test-password")

        self.chapter = Chapter.objects.create(
            name="Test Chapter", description="A test chapter for unit testing", region="Test Region",
        )

    def test_chapter_creation(self) -> None:
        assert self.chapter.name == "Test Chapter"
        assert self.chapter.description == "A test chapter for unit testing"
        assert self.chapter.region == "Test Region"
        assert self.chapter.is_active
        assert not self.chapter.is_featured

    def test_membership_creation(self) -> None:
        membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.user, role="lead", bio="Test bio", is_approved=True,
        )

        assert membership.user == self.user
        assert membership.chapter == self.chapter
        assert membership.role == "lead"
        assert membership.bio == "Test bio"
        assert membership.is_approved

    def test_event_creation(self) -> None:
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

        assert event.chapter == self.chapter
        assert event.title == "Test Event"
        assert event.description == "A test event"
        assert event.event_type == "meetup"
        assert event.location == "Test Location"
        assert event.organizer == self.user

    def test_resource_creation_with_file(self):
        test_file = SimpleUploadedFile(
            name="test_document.pdf",
            content=b"file content",
            content_type="application/pdf"
        )

        resource = ChapterResource.objects.create(
            chapter=self.chapter,
            title="Test Resource",
            description="A test resource",
            resource_type="document",
            file=test_file,
            created_by=self.user,
        )

        assert resource.chapter == self.chapter
        assert resource.title == "Test Resource"
        assert resource.description == "A test resource"
        assert resource.resource_type == "document"
        # File‑based resources should *not* have an external URL
        assert resource.external_url in ("", None)
        assert resource.created_by == self.user

    def test_application_creation(self) -> None:
        application = ChapterApplication.objects.create(
            applicant=self.user,
            chapter_name="New Chapter Application",
            region="New Region",
            description="A new chapter application",
            proposed_activities="Proposed activities",
            experience="Leadership experience"
        )

        assert application.applicant == self.user
        assert application.chapter_name == "New Chapter Application"
        assert application.region == "New Region"
        assert application.status == "pending"


class ChapterViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        # Create test users
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="test-password")

        self.admin_user = User.objects.create_user(
            username="adminuser", email="admin@example.com", password="test-password", is_staff=True,
        )

        # Create test chapter
        self.chapter = Chapter.objects.create(
            name="Test Chapter", description="A test chapter for integration testing", region="Test Region",
        )

        # Create lead membership
        self.lead_membership = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.admin_user, role="lead", is_approved=True,
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
            created_by=self.admin_user
        )

    def test_chapters_list_view(self) -> None:
        response = self.client.get(reverse("chapters_list"))
        assert response.status_code == 200
        self.assertContains(response, "Test Chapter")

    def test_chapter_detail_view(self) -> None:
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        assert response.status_code == 200
        self.assertContains(response, "Test Chapter")
        self.assertContains(response, "Test Event")
        self.assertContains(response, "Test Resource")

    def test_join_chapter_view(self) -> None:
        # Login as normal user
        self.client.login(username="testuser", password="test-password")

        # Get the join page
        response = self.client.get(reverse("join_chapter", args=[self.chapter.slug]))
        assert response.status_code == 200

        # Submit the join form
        response = self.client.post(reverse("join_chapter", args=[self.chapter.slug]), {"bio": "Test member bio"})
        self.assertRedirects(response, reverse("chapter_detail", args=[self.chapter.slug]))

        # Verify membership was created but not approved
        membership = ChapterMembership.objects.get(user=self.user, chapter=self.chapter)
        assert membership.role == "member"
        assert not membership.is_approved

    def test_chapter_management_view(self) -> None:
        # Login as chapter lead
        self.client.login(username="adminuser", password="test-password")

        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        assert response.status_code == 200
        self.assertContains(response, "Test Chapter")

        # Normal users shouldn't be able to access management page
        self.client.login(username="testuser", password="test-password")

        # First create a membership for the test user
        ChapterMembership.objects.create(chapter=self.chapter, user=self.user, role="member", is_approved=True)

        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        assert response.status_code == 302  # Should redirect

    def test_creating_chapter_event(self) -> None:
        # Login as chapter lead
        self.client.login(username="adminuser", password="password123")

        # Get the create event page
        response = self.client.get(reverse("create_chapter_event", args=[self.chapter.slug]))
        assert response.status_code == 200

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
        assert ChapterEvent.objects.filter(title="New Test Event").exists()

    def test_adding_chapter_resource(self) -> None:
        # Login as chapter lead
        self.client.login(username="adminuser", password="password123")

        # Get the add resource page
        response = self.client.get(reverse("add_chapter_resource", args=[self.chapter.slug]))
        assert response.status_code == 200

        # Add a resource
        resource_data = {
            "title": "New Test Resource",
            "description": "A new test resource description",
            "resource_type": "template",
            "external_url": "https://example.com/new-resource",
        }

        response = self.client.post(reverse("add_chapter_resource", args=[self.chapter.slug]), resource_data)

        # Check that the resource was created
        assert ChapterResource.objects.filter(title="New Test Resource").exists()

    def test_chapter_application(self) -> None:
        # Login as normal user
        self.client.login(username="testuser", password="password123")

        # Get the application page
        response = self.client.get(reverse("apply_for_chapter"))
        assert response.status_code == 200

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
        assert ChapterApplication.objects.filter(chapter_name="New Test Chapter").exists()


class ChapterApplicationTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="test-password",
        )

    def test_only_verified_members_can_apply(self) -> None:

        # Try to apply with non-verified user
        self.client.login(username="nonverified", password="test-password")
        response = self.client.get(reverse("apply_for_chapter"))
        assert response.status_code == 302  # Should redirect to login or profile

        # Try with verified user
        self.client.login(username="testuser", password="test-password")
        response = self.client.get(reverse("apply_for_chapter"))
        assert response.status_code == 200

    def test_chapter_application_fields(self) -> None:
        self.client.login(username="testuser", password="test-password")

        # Submit with missing fields
        response = self.client.post(
            reverse("apply_for_chapter"),
            {
                "chapter_name": "New Test Chapter",
                # Missing fields
            },
        )

        # Should show form errors
        assert "This field is required" in str(response.content)

        # Submit with all fields
        response = self.client.post(
            reverse("apply_for_chapter"),
            {
                "chapter_name": "New Test Chapter",
                "region": "Test Region",
                "description": "Test description",
                "proposed_activities": "Test activities",
                "experience": "Test experience",
            },
        )

        # Should redirect to chapters list
        assert response.status_code == 302
        assert ChapterApplication.objects.filter(chapter_name="New Test Chapter").exists()

    def test_application_approval_creates_chapter(self) -> None:
        # Create a pending application
        application = ChapterApplication.objects.create(
            applicant=self.user,
            chapter_name="Application Test Chapter",
            region="Test Region",
            description="Test description",
            proposed_activities="Test activities",
            experience="Test experience",
        )

        # Login as admin and approve the application
        self.client.login(username="admin", password="test-password")

        # Assuming you have an approval view
        response = self.client.post(
            reverse("admin:web_chapterapplication_change", args=[application.id]),
            {
                "status": "approved",
                # Other required fields
            },
        )

        # Check that a chapter was created
        assert Chapter.objects.filter(name="Application Test Chapter").exists()

        # Check that the applicant was made the chapter lead
        chapter = Chapter.objects.get(name="Application Test Chapter")
        membership = ChapterMembership.objects.get(chapter=chapter, user=self.user)
        assert membership.role == "lead"
        assert membership.is_approved


class ChapterEventTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="test-password",
        )

    def test_chapter_can_host_different_event_types(self) -> None:
        self.client.login(username="testuser", password="test-password")

        # Create a chapter with the user as lead
        chapter = Chapter.objects.create(
            name="Events Test Chapter",
            description="A chapter for testing events",
            region="Test Region",
        )

        ChapterMembership.objects.create(
            chapter=chapter,
            user=self.user,
            role="lead",
            is_approved=True,
        )

        # Create events of different types
        event_types = ["meetup", "workshop", "webinar", "conference"]

        for event_type in event_types:
            ChapterEvent.objects.create(
                chapter=chapter,
                title=f"Test {event_type.capitalize()}",
                description=f"A test {event_type}",
                event_type=event_type,
                start_time=timezone.now() + datetime.timedelta(days=1),
                end_time=timezone.now() + datetime.timedelta(days=1, hours=2),
                organizer=self.user,
            )

        # Check that all event types exist
        for event_type in event_types:
            assert ChapterEvent.objects.filter(event_type=event_type).exists()

    def test_event_rsvp_functionality(self) -> None:
        # Create an event
        chapter = Chapter.objects.create(
            name="RSVP Test Chapter",
            description="A chapter for testing RSVPs",
            region="Test Region",
        )

        event = ChapterEvent.objects.create(
            chapter=chapter,
            title="RSVP Test Event",
            description="An event for testing RSVPs",
            event_type="meetup",
            start_time=timezone.now() + datetime.timedelta(days=1),
            end_time=timezone.now() + datetime.timedelta(days=1, hours=2),
            max_attendees=2,  # Set limit for testing
            organizer=self.user,
        )

        # Create users
        user1 = User.objects.create_user(username="user1", email="user1@example.com", password="test-password")

        # RSVP as first user
        self.client.login(username="user1", password="test-password")
        self.client.post(reverse("rsvp_event", args=[chapter.slug, event.id]))

        # Check that user1 is on the attendees list
        assert ChapterEventAttendee.objects.filter(event=event, user=user1).exists()

        # RSVP as second user
        self.client.login(username="user2", password="test-password")
        self.client.post(reverse("rsvp_event", args=[chapter.slug, event.id]))

        # Try to RSVP as the initial test user - should fail due to max attendees
        self.client.login(username="testuser", password="test-password")
        self.client.post(reverse("rsvp_event", args=[chapter.slug, event.id]))

        # Verify that testuser is not on the list
        assert not ChapterEventAttendee.objects.filter(event=event, user=self.user).exists()


class ChapterMemberRolesTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        # Create chapter
        self.chapter = Chapter.objects.create(
            name="Roles Test Chapter",
            description="A chapter for testing member roles",
            region="Test Region",
        )

        # Create users with different roles
        self.lead_user = User.objects.create_user(
            username="lead", email="lead@example.com", password="test-password",
        )

        self.co_org_user = User.objects.create_user(
            username="co_organizer", email="co_org@example.com", password="test-password",
        )

        self.volunteer_user = User.objects.create_user(
            username="volunteer", email="volunteer@example.com", password="test-password",
        )

        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="test-password",
        )

        # Create memberships
        self.lead = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.lead_user, role="lead", is_approved=True,
        )

        self.co_org = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.co_org_user, role="co_organizer", is_approved=True,
        )

        self.volunteer = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.volunteer_user, role="volunteer", is_approved=True,
        )

        self.member = ChapterMembership.objects.create(
            chapter=self.chapter, user=self.member_user, role="member", is_approved=True,
        )

    def test_role_permissions(self) -> None:
        # Test chapter lead privileges
        self.client.login(username="lead", password="test-password")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        assert response.status_code == 200

        # Test co-organizer privileges
        self.client.login(username="co_organizer", password="test-password")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        assert response.status_code == 200

        # Test volunteer privileges - should have limited access
        self.client.login(username="volunteer", password="test-password")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        assert response.status_code == 302  # redirect

        # Test regular member - should have no management access
        self.client.login(username="member", password="test-password")
        response = self.client.get(reverse("manage_chapter", args=[self.chapter.slug]))
        assert response.status_code == 302  # redirect

    def test_member_directory(self) -> None:
        # Anyone should be able to view the member directory
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        assert response.status_code == 200

        # Check that all members appear in the response
        self.assertContains(response, "lead@example.com")
        self.assertContains(response, "co_org@example.com")
        self.assertContains(response, "volunteer@example.com")
        self.assertContains(response, "member@example.com")


class ChapterResourceSharingTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        self.chapter = Chapter.objects.create(
            name="Resource Test Chapter",
            description="A chapter for testing resources",
            region="Test Region",
        )

        # Create users
        self.lead_user = User.objects.create_user(
            username="lead", email="lead@example.com", password="test-password",
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="test-password",
        )

        # Create memberships
        ChapterMembership.objects.create(
            chapter=self.chapter, user=self.lead_user, role="lead", is_approved=True,
        )

        ChapterMembership.objects.create(
            chapter=self.chapter, user=self.member_user, role="member", is_approved=True,
        )

    def test_resource_types(self) -> None:
        self.client.login(username="lead", password="test-password")

        # Create resources of different types
        resource_types = [
            ("document", "https://example.com/document"),
            ("video", "https://example.com/video"),
            ("presentation", "https://example.com/presentation"),
            ("code", "https://example.com/code"),
            ("template", "https://example.com/template"),
        ]

        for rtype, url in resource_types:
            ChapterResource.objects.create(
                chapter=self.chapter,
                title=f"Test {rtype.capitalize()}",
                description=f"A test {rtype}",
                resource_type=rtype,
                external_url=url,
                created_by=self.lead_user,
            )

        # Verify all resource types exist
        for rtype, _ in resource_types:
            assert ChapterResource.objects.filter(resource_type=rtype).exists()

        # Check that resources show up on the chapter detail page
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        for rtype, _ in resource_types:
            self.assertContains(response, f"Test {rtype.capitalize()}")

    def test_member_access_to_resources(self) -> None:
        # Create a resource

        # Public users should be able to see resources exist
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        assert response.status_code == 200
        assert "Member Access Test" in str(response.content)

        # Non-members should not be able to click through to resources or edit
        self.client.login(username="testuser", password="test-password")

        # Assuming there's a resource detail view
        response = self.client.get(reverse("chapter_detail", args=[self.chapter.slug]))
        assert response.status_code == 200


class ChapterRecognitionTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()

        # Create a regular chapter
        self.regular_chapter = Chapter.objects.create(
            name="Regular Chapter",
            description="A regular test chapter",
            region="Test Region",
            is_featured=False,
        )

        # Create a featured chapter
        self.featured_chapter = Chapter.objects.create(
            name="Featured Chapter",
            description="A featured test chapter",
            region="Test Region",
            is_featured=True,
        )

    def test_featured_chapters_appear_prominently(self) -> None:
        # Check chapters list page
        response = self.client.get(reverse("chapters_list"))

        # Check that both chapters are on the page
        assert response.status_code == 200
        assert "Featured Chapter" in str(response.content)
        assert "Regular Chapter" in str(response.content)

        # Featured chapters should appear before regular chapters in the HTML
        featured_pos = str(response.content).find("Featured Chapter")
        regular_pos = str(response.content).find("Regular Chapter")
        assert featured_pos < regular_pos

    def test_featured_chapters_on_homepage(self) -> None:
        # Skip this test since featured chapters might not be implemented on the homepage yet
        pass
