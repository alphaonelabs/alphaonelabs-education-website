from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
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


def chapters_list(request):
    """List all active chapters."""
    chapters = Chapter.objects.filter(is_active=True).order_by('-is_featured', 'name')

    # Filter by region if provided
    region = request.GET.get('region')
    if region:
        chapters = chapters.filter(region__icontains=region)

    # Get distinct regions for filter dropdown
    regions = Chapter.objects.filter(is_active=True).values_list('region', flat=True).distinct()

    return render(request, 'web/chapters/list.html', {
        'chapters': chapters,
        'regions': regions,
        'selected_region': region,
    })


def chapter_detail(request, slug):
    """Show details of a specific chapter."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)

    # Check if user is a member and get their role
    user_membership = None
    if request.user.is_authenticated:
        user_membership = chapter.members.filter(user=request.user).first()

    # Get upcoming events
    upcoming_events = chapter.events.filter(
        start_time__gte=timezone.now()
    ).order_by('start_time')

    # Get past events
    past_events = chapter.events.filter(
        end_time__lt=timezone.now()
    ).order_by('-start_time')

    # Get chapter members with leadership roles first
    members = chapter.members.filter(is_approved=True).order_by(
        models.Case(
            models.When(role='lead', then=0),
            models.When(role='co_organizer', then=1),
            models.When(role='volunteer', then=2),
            default=3,
        ),
        'joined_at'
    )

    # Get chapter resources
    resources = chapter.resources.all().order_by('-created_at')

    return render(request, 'web/chapters/detail.html', {
        'chapter': chapter,
        'user_membership': user_membership,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'members': members,
        'resources': resources,
    })


@login_required
def join_chapter(request, slug):
    """Handle joining a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)

    # Check if already a member
    if chapter.members.filter(user=request.user).exists():
        messages.info(request, "You are already a member of this chapter.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        bio = request.POST.get('bio', '')

        # Create membership
        ChapterMembership.objects.create(
            chapter=chapter,
            user=request.user,
            bio=bio,
            # Auto-approve if there are no other members or admin
            is_approved=chapter.members.count() == 0 or request.user.is_staff
        )

        # If this is the first member, make them the lead
        if chapter.members.count() == 1:
            membership = chapter.members.first()
            membership.role = 'lead'
            membership.is_approved = True
            membership.save()
            messages.success(request, "You are now the Chapter Lead!")
        else:
            messages.success(request, "Your membership request has been submitted and is pending approval.")

        return redirect('chapter_detail', slug=slug)

    return render(request, 'web/chapters/join.html', {
        'chapter': chapter,
    })


@login_required
def leave_chapter(request, slug):
    """Handle leaving a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    if request.method == 'POST':
        # Check if the user is the lead and there are other members
        if membership.role == 'lead' and chapter.members.exclude(user=request.user).exists():
            messages.error(request, "As Chapter Lead, you must transfer leadership before leaving.")
            return redirect('chapter_detail', slug=slug)

        membership.delete()
        messages.success(request, f"You have left the {chapter.name} chapter.")
        return redirect('chapters_list')

    return render(request, 'web/chapters/leave.html', {
        'chapter': chapter,
    })


@login_required
def edit_membership(request, slug):
    """Edit user's membership details."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    if request.method == 'POST':
        membership.bio = request.POST.get('bio', '')
        membership.save()
        messages.success(request, "Your membership details have been updated.")
        return redirect('chapter_detail', slug=slug)

    return render(request, 'web/chapters/edit_membership.html', {
        'chapter': chapter,
        'membership': membership,
    })


@login_required
def apply_for_chapter(request):
    """Handle applications to create a new chapter."""
    if request.method == 'POST':
        chapter_name = request.POST.get('chapter_name')
        region = request.POST.get('region')
        description = request.POST.get('description')
        proposed_activities = request.POST.get('proposed_activities')
        experience = request.POST.get('experience')

        ChapterApplication.objects.create(
            applicant=request.user,
            chapter_name=chapter_name,
            region=region,
            description=description,
            proposed_activities=proposed_activities,
            experience=experience
        )

        messages.success(request, "Your chapter application has been submitted and is pending review.")
        return redirect('chapters_list')

    return render(request, 'web/chapters/apply.html')


@login_required
def chapter_event_detail(request, slug, event_id):
    """View details of a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    # Check if user is already attending
    user_attending = False
    if request.user.is_authenticated:
        user_attending = event.attendees.filter(user=request.user).exists()

    # Get attendees
    attendees = event.attendees.all().select_related('user')

    return render(request, 'web/chapters/event_detail.html', {
        'chapter': chapter,
        'event': event,
        'user_attending': user_attending,
        'attendees': attendees,
    })


@login_required
def rsvp_event(request, slug, event_id):
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
            ChapterEventAttendee.objects.create(
                event=event,
                user=request.user
            )
            messages.success(request, "You have successfully registered for this event.")

    return redirect('chapter_event_detail', slug=slug, event_id=event_id)


@login_required
def cancel_rsvp(request, slug, event_id):
    """Cancel RSVP to a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug, is_active=True)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)

    attendance = event.attendees.filter(user=request.user).first()
    if attendance:
        attendance.delete()
        messages.success(request, "Your registration has been canceled.")
    else:
        messages.info(request, "You were not registered for this event.")

    return redirect('chapter_event_detail', slug=slug, event_id=event_id)


@login_required
def manage_chapter(request, slug):
    """Management dashboard for chapter leaders."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only allow leaders and co-organizers to access
    if membership.role not in ['lead', 'co_organizer']:
        messages.error(request, "You don't have permission to manage this chapter.")
        return redirect('chapter_detail', slug=slug)

    # Get pending membership requests
    pending_memberships = chapter.members.filter(is_approved=False)

    # Get all events
    events = chapter.events.all().order_by('-start_time')

    # Get all resources
    resources = chapter.resources.all().order_by('-created_at')

    return render(request, 'web/chapters/manage.html', {
        'chapter': chapter,
        'pending_memberships': pending_memberships,
        'events': events,
        'resources': resources,
    })


@login_required
def edit_chapter(request, slug):
    """Edit chapter details."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only allow leaders to edit
    if membership.role != 'lead':
        messages.error(request, "Only the Chapter Lead can edit chapter details.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        chapter.name = request.POST.get('name')
        chapter.region = request.POST.get('region')
        chapter.description = request.POST.get('description')
        chapter.website = request.POST.get('website', '')
        chapter.discord_link = request.POST.get('discord_link', '')
        chapter.facebook_link = request.POST.get('facebook_link', '')
        chapter.twitter_link = request.POST.get('twitter_link', '')

        # Handle logo upload
        if 'logo' in request.FILES:
            chapter.logo = request.FILES['logo']

        chapter.save()
        messages.success(request, "Chapter details have been updated.")
        return redirect('chapter_detail', slug=slug)

    return render(request, 'web/chapters/edit.html', {
        'chapter': chapter,
    })


@login_required
def approve_membership(request, slug, user_id):
    """Approve a pending membership request."""
    chapter = get_object_or_404(Chapter, slug=slug)
    leader_membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)
    member_to_approve = get_object_or_404(User, id=user_id)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=member_to_approve, is_approved=False)

    # Only allow leaders and co-organizers to approve
    if leader_membership.role not in ['lead', 'co_organizer']:
        messages.error(request, "You don't have permission to approve memberships.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        membership.is_approved = True
        membership.save()
        messages.success(request, f"{member_to_approve.username}'s membership has been approved.")

    return redirect('manage_chapter', slug=slug)


@login_required
def reject_membership(request, slug, user_id):
    """Reject a pending membership request."""
    chapter = get_object_or_404(Chapter, slug=slug)
    leader_membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)
    member_to_reject = get_object_or_404(User, id=user_id)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=member_to_reject, is_approved=False)

    # Only allow leaders and co-organizers to reject
    if leader_membership.role not in ['lead', 'co_organizer']:
        messages.error(request, "You don't have permission to reject memberships.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        membership.delete()
        messages.success(request, f"{member_to_reject.username}'s membership request has been rejected.")

    return redirect('manage_chapter', slug=slug)


@login_required
def manage_member_role(request, slug, user_id):
    """Change a member's role in the chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)
    leader_membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)
    target_user = get_object_or_404(User, id=user_id)
    target_membership = get_object_or_404(ChapterMembership, chapter=chapter, user=target_user, is_approved=True)

    # Only the lead can change roles
    if leader_membership.role != 'lead':
        messages.error(request, "Only the Chapter Lead can change member roles.")
        return redirect('chapter_detail', slug=slug)

    # Cannot change your own role
    if target_user == request.user:
        messages.error(request, "You cannot change your own role.")
        return redirect('manage_chapter', slug=slug)

    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in [r[0] for r in ChapterMembership.ROLE_CHOICES]:
            target_membership.role = new_role
            target_membership.save()
            messages.success(request, f"{target_user.username}'s role has been updated to {target_membership.get_role_display()}.")
        else:
            messages.error(request, "Invalid role selected.")

    return redirect('manage_chapter', slug=slug)


@login_required
def create_chapter_event(request, slug):
    """Create a new event for the chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only allow leaders and co-organizers to create events
    if membership.role not in ['lead', 'co_organizer']:
        messages.error(request, "You don't have permission to create events.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_type = request.POST.get('event_type')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        location = request.POST.get('location', '')
        meeting_link = request.POST.get('meeting_link', '')
        max_participants = request.POST.get('max_participants', 50)
        is_public = request.POST.get('is_public') == 'on'

        event = ChapterEvent.objects.create(
            chapter=chapter,
            title=title,
            description=description,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            meeting_link=meeting_link,
            max_participants=max_participants,
            is_public=is_public,
            organizer=request.user
        )

        # Handle image upload
        if 'image' in request.FILES:
            event.image = request.FILES['image']
            event.save()

        messages.success(request, "Event has been created successfully.")
        return redirect('chapter_event_detail', slug=slug, event_id=event.id)

    return render(request, 'web/chapters/create_event.html', {
        'chapter': chapter,
        'event_types': ChapterEvent.EVENT_TYPES,
    })


@login_required
def edit_chapter_event(request, slug, event_id):
    """Edit a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only allow organizer, leaders and co-organizers to edit
    if membership.role not in ['lead', 'co_organizer'] and event.organizer != request.user:
        messages.error(request, "You don't have permission to edit this event.")
        return redirect('chapter_event_detail', slug=slug, event_id=event_id)

    if request.method == 'POST':
        event.title = request.POST.get('title')
        event.description = request.POST.get('description')
        event.event_type = request.POST.get('event_type')
        event.start_time = request.POST.get('start_time')
        event.end_time = request.POST.get('end_time')
        event.location = request.POST.get('location', '')
        event.meeting_link = request.POST.get('meeting_link', '')
        event.max_participants = request.POST.get('max_participants', 50)
        event.is_public = request.POST.get('is_public') == 'on'

        # Handle image upload
        if 'image' in request.FILES:
            event.image = request.FILES['image']

        event.save()
        messages.success(request, "Event has been updated successfully.")
        return redirect('chapter_event_detail', slug=slug, event_id=event.id)

    return render(request, 'web/chapters/edit_event.html', {
        'chapter': chapter,
        'event': event,
        'event_types': ChapterEvent.EVENT_TYPES,
    })


@login_required
def delete_chapter_event(request, slug, event_id):
    """Delete a chapter event."""
    chapter = get_object_or_404(Chapter, slug=slug)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only allow organizer, leaders and co-organizers to delete
    if membership.role not in ['lead', 'co_organizer'] and event.organizer != request.user:
        messages.error(request, "You don't have permission to delete this event.")
        return redirect('chapter_event_detail', slug=slug, event_id=event_id)

    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event has been deleted.")
        return redirect('chapter_detail', slug=slug)

    return render(request, 'web/chapters/delete_event.html', {
        'chapter': chapter,
        'event': event,
    })


@login_required
def mark_attendance(request, slug, event_id):
    """Mark attendance for an event."""
    chapter = get_object_or_404(Chapter, slug=slug)
    event = get_object_or_404(ChapterEvent, id=event_id, chapter=chapter)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only allow event organizer, leaders and co-organizers to mark attendance
    if membership.role not in ['lead', 'co_organizer'] and event.organizer != request.user:
        messages.error(request, "You don't have permission to mark attendance.")
        return redirect('chapter_event_detail', slug=slug, event_id=event_id)

    if request.method == 'POST':
        attendee_ids = request.POST.getlist('attendees')

        # Mark all selected users as attended
        ChapterEventAttendee.objects.filter(event=event).update(attended=False)
        ChapterEventAttendee.objects.filter(event=event, user_id__in=attendee_ids).update(attended=True)

        messages.success(request, "Attendance has been updated.")
        return redirect('chapter_event_detail', slug=slug, event_id=event_id)

    return render(request, 'web/chapters/mark_attendance.html', {
        'chapter': chapter,
        'event': event,
        'attendees': event.attendees.all().select_related('user'),
    })


@login_required
def add_chapter_resource(request, slug):
    """Add a resource to a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only approved members can add resources
    if not membership.is_approved:
        messages.error(request, "Your membership needs to be approved before you can add resources.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        resource_type = request.POST.get('resource_type')
        external_url = request.POST.get('external_url', '')

        resource = ChapterResource.objects.create(
            chapter=chapter,
            title=title,
            description=description,
            resource_type=resource_type,
            external_url=external_url,
            created_by=request.user
        )

        # Handle file upload
        if 'file' in request.FILES:
            resource.file = request.FILES['file']
            resource.save()

        messages.success(request, "Resource has been added successfully.")
        return redirect('chapter_detail', slug=slug)

    return render(request, 'web/chapters/add_resource.html', {
        'chapter': chapter,
        'resource_types': ChapterResource.RESOURCE_TYPES,
    })


@login_required
def edit_chapter_resource(request, slug, resource_id):
    """Edit a chapter resource."""
    chapter = get_object_or_404(Chapter, slug=slug)
    resource = get_object_or_404(ChapterResource, id=resource_id, chapter=chapter)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only creator or leaders can edit resources
    if resource.created_by != request.user and membership.role not in ['lead', 'co_organizer']:
        messages.error(request, "You don't have permission to edit this resource.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        resource.title = request.POST.get('title')
        resource.description = request.POST.get('description')
        resource.resource_type = request.POST.get('resource_type')
        resource.external_url = request.POST.get('external_url', '')

        # Handle file upload
        if 'file' in request.FILES:
            resource.file = request.FILES['file']

        resource.save()
        messages.success(request, "Resource has been updated successfully.")
        return redirect('chapter_detail', slug=slug)

    return render(request, 'web/chapters/edit_resource.html', {
        'chapter': chapter,
        'resource': resource,
        'resource_types': ChapterResource.RESOURCE_TYPES,
    })


@login_required
def delete_chapter_resource(request, slug, resource_id):
    """Delete a chapter resource."""
    chapter = get_object_or_404(Chapter, slug=slug)
    resource = get_object_or_404(ChapterResource, id=resource_id, chapter=chapter)
    membership = get_object_or_404(ChapterMembership, chapter=chapter, user=request.user)

    # Only creator or leaders can delete resources
    if resource.created_by != request.user and membership.role not in ['lead', 'co_organizer']:
        messages.error(request, "You don't have permission to delete this resource.")
        return redirect('chapter_detail', slug=slug)

    if request.method == 'POST':
        resource.delete()
        messages.success(request, "Resource has been deleted.")
        return redirect('chapter_detail', slug=slug)

    return render(request, 'web/chapters/delete_resource.html', {
        'chapter': chapter,
        'resource': resource,
    })
