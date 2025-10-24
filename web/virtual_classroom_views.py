"""Views for virtual classroom functionality."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import teacher_required
from .models import ClassroomSeat, RaisedHand, ScreenShare, UpdateRound, VirtualClassroom


@login_required
def virtual_classroom_list(request):
    """List all virtual classrooms."""
    if request.user.profile.is_teacher:
        # Teachers see their own classrooms
        classrooms = VirtualClassroom.objects.filter(teacher=request.user).order_by("-created_at")
    else:
        # Students see active classrooms
        classrooms = VirtualClassroom.objects.filter(is_active=True).order_by("-created_at")

    context = {
        "classrooms": classrooms,
        "is_teacher": request.user.profile.is_teacher,
    }
    return render(request, "virtual_classroom/classroom_list.html", context)


@login_required
@teacher_required
def create_virtual_classroom(request):
    """Create a new virtual classroom (teachers only)."""
    if request.method == "POST":
        title = request.POST.get("title")
        rows = int(request.POST.get("rows", 5))
        columns = int(request.POST.get("columns", 6))
        session_id = request.POST.get("session_id")

        classroom = VirtualClassroom.objects.create(
            title=title, teacher=request.user, rows=rows, columns=columns
        )

        if session_id:
            from .models import Session

            try:
                session = Session.objects.get(id=session_id)
                classroom.session = session
                classroom.save()
            except Session.DoesNotExist:
                pass

        # Create seats for the classroom
        for row in range(rows):
            for col in range(columns):
                ClassroomSeat.objects.create(classroom=classroom, row=row, column=col)

        messages.success(request, f"Virtual classroom '{title}' created successfully!")
        return redirect("virtual_classroom_detail", classroom_id=classroom.id)

    # Get teacher's sessions for dropdown
    from .models import Session

    sessions = Session.objects.filter(teacher=request.user, is_active=True)

    context = {"sessions": sessions}
    return render(request, "virtual_classroom/create_classroom.html", context)


@login_required
def virtual_classroom_detail(request, classroom_id):
    """View and interact with a virtual classroom."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)

    # Check permissions
    is_teacher = request.user == classroom.teacher
    if not is_teacher and not classroom.is_active:
        messages.error(request, "This classroom is not currently active.")
        return redirect("virtual_classroom_list")

    # Get classroom state
    seats = classroom.seats.all().order_by("row", "column")
    raised_hands = classroom.raised_hands.filter(is_active=True).order_by("created_at")
    active_round = classroom.update_rounds.filter(is_active=True).first()
    screen_shares = classroom.screen_shares.all().order_by("-created_at")[:10]

    # Get user's current seat if any
    user_seat = classroom.seats.filter(student=request.user).first()

    # Organize seats by row for easier template rendering
    seats_by_row = {}
    for seat in seats:
        if seat.row not in seats_by_row:
            seats_by_row[seat.row] = []
        seats_by_row[seat.row].append(seat)

    context = {
        "classroom": classroom,
        "seats_by_row": seats_by_row,
        "raised_hands": raised_hands,
        "active_round": active_round,
        "screen_shares": screen_shares,
        "is_teacher": is_teacher,
        "user_seat": user_seat,
    }
    return render(request, "virtual_classroom/classroom_detail.html", context)


@login_required
@require_POST
def upload_screenshot(request, classroom_id):
    """Upload a screenshot to the virtual classroom."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)

    # Check if user has a seat
    seat = classroom.seats.filter(student=request.user).first()
    if not seat:
        return JsonResponse({"success": False, "message": "You must select a seat first"}, status=400)

    title = request.POST.get("title", "")
    description = request.POST.get("description", "")
    screenshot = request.FILES.get("screenshot")

    if not screenshot:
        return JsonResponse({"success": False, "message": "No screenshot provided"}, status=400)

    screen_share = ScreenShare.objects.create(
        classroom=classroom, student=request.user, seat=seat, title=title, description=description, screenshot=screenshot
    )

    if request.headers.get("HX-Request"):
        # HTMX request - return partial HTML
        return render(
            request,
            "virtual_classroom/partials/screen_share_item.html",
            {"screen_share": screen_share, "is_teacher": request.user == classroom.teacher},
        )
    else:
        return JsonResponse(
            {
                "success": True,
                "screenshot_id": screen_share.id,
                "screenshot_url": screen_share.screenshot.url,
            }
        )


@login_required
def view_screenshot(request, screenshot_id):
    """View a screenshot in detail."""
    screenshot = get_object_or_404(ScreenShare, id=screenshot_id)
    classroom = screenshot.classroom

    # Check permissions
    is_teacher = request.user == classroom.teacher
    is_owner = request.user == screenshot.student

    if not is_teacher and not is_owner:
        messages.error(request, "You don't have permission to view this screenshot.")
        return redirect("virtual_classroom_detail", classroom_id=classroom.id)

    context = {
        "screenshot": screenshot,
        "classroom": classroom,
        "is_teacher": is_teacher,
    }
    return render(request, "virtual_classroom/screenshot_detail.html", context)


@login_required
@teacher_required
@require_POST
def start_update_round_view(request, classroom_id):
    """Start an update round (teacher only)."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id, teacher=request.user)

    duration = int(request.POST.get("duration", 120))

    # This will be handled by WebSocket, but we can also create it here
    # The WebSocket consumer will handle the actual round logic
    return JsonResponse({"success": True, "message": "Update round will be started via WebSocket"})


@login_required
@teacher_required
@require_POST
def end_classroom(request, classroom_id):
    """End/deactivate a classroom (teacher only)."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id, teacher=request.user)

    classroom.is_active = False
    classroom.save()

    # End any active update rounds
    UpdateRound.objects.filter(classroom=classroom, is_active=True).update(
        is_active=False, completed_at=timezone.now()
    )

    # Clear all seats
    ClassroomSeat.objects.filter(classroom=classroom).update(
        student=None, is_occupied=False, is_speaking=False
    )

    # Deactivate all raised hands
    RaisedHand.objects.filter(classroom=classroom, is_active=True).update(is_active=False)

    messages.success(request, "Classroom has been ended successfully.")
    return redirect("virtual_classroom_list")


@login_required
def get_raised_hands(request, classroom_id):
    """Get list of raised hands (HTMX endpoint)."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)

    raised_hands = classroom.raised_hands.filter(is_active=True).order_by("created_at")

    if request.headers.get("HX-Request"):
        return render(
            request,
            "virtual_classroom/partials/raised_hands_list.html",
            {
                "raised_hands": raised_hands,
                "is_teacher": request.user == classroom.teacher,
            },
        )
    else:
        hands_data = [
            {
                "student": hand.student.username,
                "student_id": hand.student.id,
                "seat_id": hand.seat.id,
                "timestamp": hand.created_at.isoformat(),
            }
            for hand in raised_hands
        ]
        return JsonResponse({"raised_hands": hands_data})
