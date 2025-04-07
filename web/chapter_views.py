from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from web.models import (
    Chapter,
    ChapterApplication,
    ChapterEvent,
    ChapterEventAttendee,
    ChapterMembership,
    ChapterResource,
)


def chapters_list(request: HttpRequest) -> HttpResponse:
    """List all active chapters."""
    chapters = Chapter.objects.filter(is_active=True).order_by("-is_featured", "name")

    # Filter by region if provided
    region = request.GET.get("region")
    if region:
        chapters = chapters.filter(region__icontains=region)

    # Get distinct regions for filter dropdown
    regions = Chapter.objects.filter(is_active=True).values_list("region", flat=True).distinct()

    return render(
        request,
        "web/chapters/list.html",
        {
            "chapters": chapters,
            "regions": regions,
            "selected_region": region,
        },
    )


def chapter_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Show details of a specific chapter."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)

    # Check if user is a member and get their role
    user_membership = None
    if request.user.is_authenticated:
        user_membership = chapter.members.filter(user=request.user).first()

    # Get upcoming events
    upcoming_events = chapter.events.filter(start_time__gte=timezone.now()).order_by("start_time")

    # Get past events
    past_events = chapter.events.filter(end_time__lt=timezone.now()).order_by("-start_time")

    # Get chapter members with leadership roles first
    members = chapter.members.filter(is_approved=True).order_by(
        models.Case(
            models.When(role="lead", then=0),
            models.When(role="co_organizer", then=1),
            models.When(role="volunteer", then=2),
            default=3,
        ),
        "joined_at",
    )

    # Get chapter resources
    resources = chapter.resources.all().order_by("-created_at")

    return render(
        request,
        "web/chapters/detail.html",
        {
            "chapter": chapter,
            "user_membership": user_membership,
            "upcoming_events": upcoming_events,
            "past_events": past_events,
            "members": members,
            "resources": resources,
        },
    )


@login_required
def join_chapter(request: HttpRequest, slug: str) -> HttpResponse:
    """Handle joining a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)

    # Check if already a member
    if chapter.members.filter(user=request.user).exists():
        messages.info(request, "You are already a member of this chapter.")
        return redirect("chapter_detail", slug=slug)

    if request.method == "POST":
        bio = request.POST.get("bio", "")

        # Create membership
        ChapterMembership.objects.create(
            chapter=chapter,
            user=request.user,
            bio=bio,
            # Auto-approve if there are no other members or admin
            is_approved=chapter.members.count() == 0 or request.user.is_staff,
        )

        # If this is the first member, make them the lead
        if chapter.members.count() == 1:
            membership = chapter.members.first()
            membership.role = "lead"
            membership.is_approved = True
            membership.save()
            messages.success(request, "You are now the Chapter Lead!")
        else:
            messages.success(request, "Your membership request has been submitted and is pending approval.")

        return redirect("chapter_detail", slug=slug)

    return render(
        request,
        "web/chapters/join.html",
        {
            "chapter": chapter,
        },
    )


@login_required
def leave_chapter(request: HttpRequest, slug: str) -> HttpResponse:
    """Handle leaving a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    if request.method == "POST":
        # Check if the user is the lead and there are other members
        if membership.role == "lead" and chapter.members.exclude(user=request.user).exists():
            messages.error(request, "As Chapter Lead, you must transfer leadership before leaving.")
            return redirect("chapter_detail", slug=slug)

        membership.delete()
        messages.success(request, f"You have left the {chapter.name} chapter.")
        return redirect("chapters_list")

    return render(
        request,
        "web/chapters/leave.html",
        {
            "chapter": chapter,
        },
    )


@login_required
def edit_membership(request: HttpRequest, slug: str) -> HttpResponse:
    """Edit user's membership details."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    if request.method == "POST":
        membership.bio = request.POST.get("bio", "")
        membership.save()
        messages.success(request, "Your membership details have been updated.")
        return redirect("chapter_detail", slug=slug)

    return render(
        request,
        "web/chapters/edit_membership.html",
        {
            "chapter": chapter,
            "membership": membership,
        },
    )


@login_required
def apply_for_chapter(request: HttpRequest) -> HttpResponse:
    """Handle applications to create a new chapter."""
    if request.method == "POST":
        chapter_name = request.POST.get("chapter_name")
        region = request.POST.get("region")
        description = request.POST.get("description")
        proposed_activities = request.POST.get("proposed_activities")
        experience = request.POST.get("experience")

        ChapterApplication.objects.create(
            applicant=request.user,
            chapter_name=chapter_name,
            region=region,
            description=description,
            proposed_activities=proposed_activities,
            experience=experience,
        )

        messages.success(request, "Your chapter application has been submitted and is pending review.")
        return redirect("chapters_list")

    return render(request, "web/chapters/apply.html")


@login_required
def chapter_event_detail(request: HttpRequest, slug: str, event_id: int) -> HttpResponse:
    """View details of a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    # Check if user is already attending
    user_attending = False
    if request.user.is_authenticated:
        user_attending = event.attendees.filter(user=request.user).exists()

    # Get attendees
    attendees = event.attendees.all().select_related("user")

    return render(
        request,
        "web/chapters/event_detail.html",
        {
            "chapter": chapter,
            "event": event,
            "user_attending": user_attending,
            "attendees": attendees,
        },
    )


@login_required
def rsvp_event(request: HttpRequest, slug: str, event_id: int) -> HttpResponse:
    """RSVP to a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    # Check if already attending
    if event.attendees.filter(user=request.user).exists():
        messages.info(request, "You are already registered for this event.")
    else:
        # Check if event is full
        if event.is_full:
            messages.error(request, "Sorry, this event has reached its maximum capacity.")
        else:
            ChapterEventAttendee.objects.create(event=event, user=request.user)
            messages.success(request, "You have successfully registered for this event.")

    return redirect("chapter_event_detail", slug=slug, event_id=event_id)


@login_required
def cancel_rsvp(request: HttpRequest, slug: str, event_id: int) -> HttpResponse:
    """Cancel RSVP to a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    # Delete the attendee record if it exists
    event.attendees.filter(user=request.user).delete()
    messages.success(request, "Your event registration has been canceled.")

    return redirect("chapter_event_detail", slug=slug, event_id=event_id)


@login_required
def manage_chapter(request: HttpRequest, slug: str) -> HttpResponse:
    """Chapter management interface for authorized users."""
    chapter = get_object_or_404(Chapter, slug=slug)

    # Check if user has permission to manage the chapter
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to manage this chapter.")
        return redirect("chapter_detail", slug=slug)

    # Get pending memberships
    pending_memberships = chapter.members.filter(is_approved=False).order_by("joined_at")

    # Get approved members
    approved_members = chapter.members.filter(is_approved=True).order_by(
        models.Case(
            models.When(role="lead", then=0),
            models.When(role="co_organizer", then=1),
            models.When(role="volunteer", then=2),
            default=3,
        ),
        "joined_at",
    )

    return render(
        request,
        "web/chapters/manage.html",
        {
            "chapter": chapter,
            "pending_memberships": pending_memberships,
            "approved_members": approved_members,
            "user_role": user_membership.role,
        },
    )


@login_required
def edit_chapter(request: HttpRequest, slug: str) -> HttpResponse:
    """Edit chapter details."""
    chapter = get_object_or_404(Chapter, slug=slug)

    # Check if user has permission to edit the chapter
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role != "lead":
        messages.error(request, "Only Chapter Leads can edit chapter details.")
        return redirect("chapter_detail", slug=slug)

    if request.method == "POST":
        chapter.name = request.POST.get("name", chapter.name)
        chapter.description = request.POST.get("description", chapter.description)
        chapter.region = request.POST.get("region", chapter.region)
        chapter.website = request.POST.get("website", chapter.website)
        chapter.github = request.POST.get("github", chapter.github)
        chapter.twitter = request.POST.get("twitter", chapter.twitter)
        chapter.discord = request.POST.get("discord", chapter.discord)
        chapter.meetup = request.POST.get("meetup", chapter.meetup)
        chapter.save()

        messages.success(request, "Chapter details have been updated.")
        return redirect("manage_chapter", slug=chapter.slug)

    return render(
        request,
        "web/chapters/edit.html",
        {
            "chapter": chapter,
        },
    )


@login_required
def approve_membership(request: HttpRequest, slug: str, user_id: int) -> HttpResponse:
    """Approve a pending membership request."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user_id=user_id, is_approved=False)

    # Check if user has permission to approve memberships
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to approve memberships.")
        return redirect("chapter_detail", slug=slug)

    membership.is_approved = True
    membership.save()

    messages.success(request, f"{membership.user.username} has been approved as a chapter member.")
    return redirect("manage_chapter", slug=slug)


@login_required
def reject_membership(request: HttpRequest, slug: str, user_id: int) -> HttpResponse:
    """Reject a pending membership request."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user_id=user_id, is_approved=False)

    # Check if user has permission to reject memberships
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to reject memberships.")
        return redirect("chapter_detail", slug=slug)

    # Delete the membership
    membership.delete()

    messages.success(request, f"The membership request from {membership.user.username} has been rejected.")
    return redirect("manage_chapter", slug=slug)


@login_required
def manage_member_role(request: HttpRequest, slug: str, user_id: int) -> HttpResponse:
    """Change a member's role within the chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)
    target_membership = get_object_or_404(ChapterMembership, chapter=chapter, user_id=user_id, is_approved=True)

    # Check if user has permission to manage roles
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role != "lead":
        messages.error(request, "Only Chapter Leads can change member roles.")
        return redirect("manage_chapter", slug=slug)

    if request.method == "POST":
        new_role = request.POST.get("role")
        if new_role in ["lead", "co_organizer", "volunteer", "member"]:
            # If changing lead, current lead must be downgraded
            if new_role == "lead":
                current_lead = chapter.members.filter(role="lead").first()
                if current_lead and current_lead.user_id != user_id:
                    current_lead.role = "co_organizer"
                    current_lead.save()

            target_membership.role = new_role
            target_membership.save()
            messages.success(
                request, f"{target_membership.user.username}'s role has been updated to {new_role.replace('_', ' ').title()}."
            )
        else:
            messages.error(request, "Invalid role selected.")

    return redirect("manage_chapter", slug=slug)


@login_required
def create_chapter_event(request: HttpRequest, slug: str) -> HttpResponse:
    """Create a new event for a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)

    # Check if user has permission to create events
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to create events.")
        return redirect("chapter_detail", slug=slug)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        event_type = request.POST.get("event_type")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        location = request.POST.get("location")
        is_online = "is_online" in request.POST
        is_public = "is_public" in request.POST
        max_attendees = request.POST.get("max_attendees", 0)
        if max_attendees == "":
            max_attendees = 0

        # Create the event
        ChapterEvent.objects.create(
            chapter=chapter,
            title=title,
            description=description,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            is_online=is_online,
            is_public=is_public,
            max_attendees=max_attendees,
            organizer=request.user,
        )

        messages.success(request, "The event has been created.")
        return redirect("chapter_detail", slug=slug)

    return render(
        request,
        "web/chapters/create_event.html",
        {
            "chapter": chapter,
        },
    )


@login_required
def edit_chapter_event(request: HttpRequest, slug: str, event_id: int) -> HttpResponse:
    """Edit an existing chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    # Check if user has permission to edit events
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to edit events.")
        return redirect("chapter_event_detail", slug=slug, event_id=event_id)

    if request.method == "POST":
        event.title = request.POST.get("title", event.title)
        event.description = request.POST.get("description", event.description)
        event.event_type = request.POST.get("event_type", event.event_type)
        event.start_time = request.POST.get("start_time", event.start_time)
        event.end_time = request.POST.get("end_time", event.end_time)
        event.location = request.POST.get("location", event.location)
        event.is_online = "is_online" in request.POST
        event.is_public = "is_public" in request.POST

        max_attendees = request.POST.get("max_attendees", "0")
        if max_attendees == "":
            max_attendees = "0"
        event.max_attendees = int(max_attendees)

        event.save()

        messages.success(request, "The event has been updated.")
        return redirect("chapter_event_detail", slug=slug, event_id=event_id)

    return render(
        request,
        "web/chapters/edit_event.html",
        {
            "chapter": chapter,
            "event": event,
        },
    )


@login_required
def delete_chapter_event(request: HttpRequest, slug: str, event_id: int) -> HttpResponse:
    """Delete a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    # Check if user has permission to delete events
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to delete events.")
        return redirect("chapter_event_detail", slug=slug, event_id=event_id)

    if request.method == "POST":
        event.delete()
        messages.success(request, "The event has been deleted.")
        return redirect("chapter_detail", slug=slug)

    return render(
        request,
        "web/chapters/delete_event.html",
        {
            "chapter": chapter,
            "event": event,
        },
    )


@login_required
def mark_attendance(request: HttpRequest, slug: str, event_id: int) -> HttpResponse:
    """Mark attendance for event attendees."""
    chapter = get_object_or_404(Chapter, slug=slug)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    # Check if user has permission to mark attendance
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer", "volunteer"]:
        messages.error(request, "You do not have permission to mark attendance.")
        return redirect("chapter_event_detail", slug=slug, event_id=event_id)

    if request.method == "POST":
        # Get the list of attendees who showed up
        attendee_ids = request.POST.getlist("attendee")

        # Update attendance records
        for attendee in event.attendees.all():
            attendee.attended = str(attendee.user.id) in attendee_ids
            attendee.save()

        messages.success(request, "Attendance has been recorded.")
        return redirect("chapter_event_detail", slug=slug, event_id=event_id)

    attendees = event.attendees.all().select_related("user")
    return render(
        request,
        "web/chapters/mark_attendance.html",
        {
            "chapter": chapter,
            "event": event,
            "attendees": attendees,
        },
    )


@login_required
def add_chapter_resource(request: HttpRequest, slug: str) -> HttpResponse:
    """Add a resource to a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)

    # Check if user has permission to add resources
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to add resources.")
        return redirect("chapter_detail", slug=slug)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        resource_type = request.POST.get("resource_type")
        external_url = request.POST.get("external_url")

        # Create the resource
        ChapterResource.objects.create(
            chapter=chapter,
            title=title,
            description=description,
            resource_type=resource_type,
            external_url=external_url,
            created_by=request.user,
        )

        messages.success(request, "The resource has been added.")
        return redirect("chapter_detail", slug=slug)

    return render(
        request,
        "web/chapters/add_resource.html",
        {
            "chapter": chapter,
        },
    )


@login_required
def edit_chapter_resource(request: HttpRequest, slug: str, resource_id: int) -> HttpResponse:
    """Edit a chapter resource."""
    chapter = get_object_or_404(Chapter, slug=slug)
    resource = get_object_or_404(ChapterResource, id=resource_id, chapter=chapter)

    # Check if user has permission to edit resources
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to edit resources.")
        return redirect("chapter_detail", slug=slug)

    if request.method == "POST":
        resource.title = request.POST.get("title", resource.title)
        resource.description = request.POST.get("description", resource.description)
        resource.resource_type = request.POST.get("resource_type", resource.resource_type)
        resource.external_url = request.POST.get("external_url", resource.external_url)
        resource.save()

        messages.success(request, "The resource has been updated.")
        return redirect("chapter_detail", slug=slug)

    return render(
        request,
        "web/chapters/edit_resource.html",
        {
            "chapter": chapter,
            "resource": resource,
        },
    )


@login_required
def delete_chapter_resource(request: HttpRequest, slug: str, resource_id: int) -> HttpResponse:
    """Delete a chapter resource."""
    chapter = get_object_or_404(Chapter, slug=slug)
    resource = get_object_or_404(ChapterResource, id=resource_id, chapter=chapter)

    # Check if user has permission to delete resources
    user_membership = chapter.members.filter(user=request.user).first()
    if not user_membership or user_membership.role not in ["lead", "co_organizer"]:
        messages.error(request, "You do not have permission to delete resources.")
        return redirect("chapter_detail", slug=slug)

    if request.method == "POST":
        resource.delete()
        messages.success(request, "The resource has been deleted.")
        return redirect("chapter_detail", slug=slug)

    return render(
        request,
        "web/chapters/delete_resource.html",
        {
            "chapter": chapter,
            "resource": resource,
        },
    )
