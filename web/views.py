import calendar
import html
import ipaddress
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import time
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlparse

import requests
import stripe
import tweepy
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db import IntegrityError, models, router, transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Coalesce
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views import generic
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .calendar_sync import generate_google_calendar_link, generate_ical_feed, generate_outlook_calendar_link
from .decorators import teacher_required
from .forms import (
    AccountDeleteForm,
    AwardAchievementForm,
    BlogPostForm,
    ChallengeSubmissionForm,
    CourseForm,
    CourseMaterialForm,
    EducationalVideoForm,
    FeedbackForm,
    ForumCategoryForm,
    ForumTopicForm,
    GoodsForm,
    GradeableLinkForm,
    InviteStudentForm,
    LearnForm,
    LinkGradeForm,
    MemeForm,
    MessageTeacherForm,
    NotificationPreferencesForm,
    ProfileUpdateForm,
    ProgressTrackerForm,
    ReviewForm,
    SessionForm,
    StorefrontForm,
    StudentEnrollmentForm,
    StudyGroupForm,
    SuccessStoryForm,
    TeacherSignupForm,
    TeachForm,
    TeamGoalCompletionForm,
    TeamGoalForm,
    TeamInviteForm,
    UserRegistrationForm,
)
from .marketing import (
    generate_social_share_content,
    get_course_analytics,
    get_promotion_recommendations,
    send_course_promotion_email,
)
from .models import (
    Achievement,
    Badge,
    BlogComment,
    BlogPost,
    CartItem,
    Certificate,
    Challenge,
    ChallengeSubmission,
    Course,
    CourseMaterial,
    CourseProgress,
    Donation,
    EducationalVideo,
    Enrollment,
    EventCalendar,
    FeatureVote,
    ForumCategory,
    ForumReply,
    ForumTopic,
    Goods,
    GradeableLink,
    LearningStreak,
    LinkGrade,
    MembershipPlan,
    MembershipSubscriptionEvent,
    Meme,
    NoteHistory,
    Notification,
    NotificationPreference,
    Order,
    OrderItem,
    PeerConnection,
    PeerMessage,
    ProductImage,
    Profile,
    ProgressTracker,
    Review,
    ScheduledPost,
    SearchLog,
    Session,
    SessionAttendance,
    SessionEnrollment,
    Storefront,
    StudyGroup,
    StudyGroupInvite,
    Subject,
    SuccessStory,
    TeamGoal,
    TeamGoalMember,
    TeamInvite,
    TimeSlot,
    UserBadge,
    WaitingRoom,
    WebRequest,
)
from .notifications import (
    notify_session_reminder,
    notify_teacher_new_enrollment,
    notify_team_goal_completion,
    notify_team_invite,
    notify_team_invite_response,
    send_enrollment_confirmation,
)
from .referrals import send_referral_reward_email
from .social import get_social_stats
from .utils import (
    cancel_subscription,
    create_leaderboard_context,
    create_subscription,
    geocode_address,
    get_cached_challenge_entries,
    get_cached_leaderboard_data,
    get_leaderboard,
    get_or_create_cart,
    get_user_points,
    reactivate_subscription,
    setup_stripe,
)

logger = logging.getLogger(__name__)

GOOGLE_CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, "google_credentials.json")

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def sitemap(request):
    return render(request, "sitemap.html")


def index(request):
    """Homepage view."""
    from django.conf import settings

    # Store referral code in session if present in URL
    ref_code = request.GET.get("ref")

    if ref_code:
        request.session["referral_code"] = ref_code

    # Get top referrers
    top_referrers = Profile.objects.annotate(
        total_signups=models.Count("referrals"),
        total_enrollments=models.Count(
            "referrals__user__enrollments", filter=models.Q(referrals__user__enrollments__status="approved")
        ),
        total_clicks=models.Count(
            "referrals__user",
            filter=models.Q(
                referrals__user__username__in=WebRequest.objects.filter(path__contains="ref=").values_list(
                    "user", flat=True
                )
            ),
        ),
    ).order_by("-total_signups", "-total_enrollments")[:3]

    # Get current user's profile if authenticated
    profile = request.user.profile if request.user.is_authenticated else None

    # Get featured courses
    featured_courses = Course.objects.filter(status="published", is_featured=True).order_by("-created_at")[:3]

    # Get current challenge
    current_challenge_obj = Challenge.objects.filter(
        start_date__lte=timezone.now(), end_date__gte=timezone.now()
    ).first()
    current_challenge = [current_challenge_obj] if current_challenge_obj else []

    # Get latest blog post
    latest_post = BlogPost.objects.filter(status="published").order_by("-published_at").first()

    # Get latest success story
    latest_success_story = SuccessStory.objects.filter(status="published").order_by("-published_at").first()

    # Get top latest 3 leaderboard users
    try:
        top_leaderboard_users, user_rank = get_leaderboard(request.user, period=None, limit=3)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting leaderboard data: {e}")
        top_leaderboard_users = []

    # Get signup form if needed
    form = None
    if not request.user.is_authenticated or not request.user.profile.is_teacher:
        form = TeacherSignupForm()

    context = {
        "profile": profile,
        "featured_courses": featured_courses,
        "current_challenge": current_challenge,
        "latest_post": latest_post,
        "latest_success_story": latest_success_story,
        "top_referrers": top_referrers,
        "top_leaderboard_users": top_leaderboard_users,
        "form": form,
        "is_debug": settings.DEBUG,
    }
    if request.user.is_authenticated:
        user_team_goals = (
            TeamGoal.objects.filter(Q(creator=request.user) | Q(members__user=request.user))
            .distinct()
            .order_by("-created_at")[:3]
        )

        team_invites = TeamInvite.objects.filter(recipient=request.user, status="pending").select_related(
            "goal", "sender"
        )

        context.update(
            {
                "user_team_goals": user_team_goals,
                "team_invites": team_invites,
            }
        )

        # Add courses that the user is teaching if they have any
        teaching_courses = (
            Course.objects.filter(teacher=request.user)
            .annotate(
                view_count=Coalesce(Sum("web_requests__count"), 0),
                enrolled_students=Count("enrollments", filter=Q(enrollments__status="approved")),
            )
            .order_by("-created_at")
        )

        if teaching_courses.exists():
            context.update(
                {
                    "teaching_courses": teaching_courses,
                }
            )
    return render(request, "index.html", context)


def signup_view(request):
    """Custom signup view that properly handles referral codes."""
    if request.method == "POST":
        form = UserRegistrationForm(request.POST, request=request)
        if form.is_valid():
            form.save(request)
            return redirect("account_email_verification_sent")
    else:
        # Initialize form with request to get referral code from session
        form = UserRegistrationForm(request=request)

        # If there's no referral code in session but it's in the URL, store it
        ref_code = request.GET.get("ref")
        if ref_code and not request.session.get("referral_code"):
            request.session["referral_code"] = ref_code
            # Reinitialize form to pick up the new session value
            form = UserRegistrationForm(request=request)

    return render(
        request,
        "account/signup.html",
        {
            "form": form,
            "login_url": reverse("account_login"),
        },
    )


@login_required
def delete_account(request):
    if request.method == "POST":
        form = AccountDeleteForm(request.user, request.POST)
        if form.is_valid():
            if request.POST.get("confirm"):
                user = request.user
                user.delete()
                logout(request)
                messages.success(request, _("Your account has been successfully deleted."))
                return redirect("index")
            else:
                form.add_error(None, _("You must confirm the account deletion."))
    else:
        # Get all related objects that will be deleted
        deleted_objects_collector = NestedObjects(using=router.db_for_write(request.user.__class__))
        deleted_objects_collector.collect([request.user])

        # Transform the nested structure into something more user-friendly
        to_delete = deleted_objects_collector.nested()
        protected = deleted_objects_collector.protected

        # Format the collected objects in a user-friendly way
        model_count = {
            model._meta.verbose_name_plural: len(objs) for model, objs in deleted_objects_collector.model_objs.items()
        }

        # Format as a list of tuples (model name, count)
        formatted_count = [(name, count) for name, count in model_count.items()]

        form = AccountDeleteForm(request.user)
        # Pass the deletion info to the template
        return render(
            request,
            "account/delete_account.html",
            {"form": form, "deleted_objects": to_delete, "protected": protected, "model_count": formatted_count},
        )

    return render(request, "account/delete_account.html", {"form": form})


@login_required
def delete_waiting_room(request, waiting_room_id):
    """View for deleting a waiting room."""
    waiting_room = get_object_or_404(WaitingRoom, id=waiting_room_id)

    # Only allow creator to delete
    if request.user != waiting_room.creator:
        messages.error(request, "You don't have permission to delete this waiting room.")
        return redirect("waiting_room_detail", waiting_room_id=waiting_room_id)

    if request.method == "POST":
        waiting_room.delete()
        messages.success(request, f"Waiting room '{waiting_room.title}' has been deleted.")
        return redirect("waiting_room_list")

    return render(request, "waiting_room/confirm_delete.html", {"waiting_room": waiting_room})


@login_required
def all_leaderboards(request):
    """
    Display all leaderboard types on a single page.
    """
    # Get cached leaderboard data or fetch fresh data
    global_entries, global_rank = get_cached_leaderboard_data(request.user, None, 10, "global_leaderboard", 60 * 60)
    weekly_entries, weekly_rank = get_cached_leaderboard_data(request.user, "weekly", 10, "weekly_leaderboard", 60 * 15)
    monthly_entries, monthly_rank = get_cached_leaderboard_data(
        request.user, "monthly", 10, "monthly_leaderboard", 60 * 30
    )

    # Get user points and challenge entries if authenticated non-teacher
    challenge_entries = []
    user_points = None

    if request.user.is_authenticated and not request.user.profile.is_teacher:
        user_points = get_user_points(request.user)
        challenge_entries = get_cached_challenge_entries()

        context = create_leaderboard_context(
            global_entries,
            weekly_entries,
            monthly_entries,
            challenge_entries,
            global_rank,
            weekly_rank,
            monthly_rank,
            user_points["total"],
            user_points["weekly"],
            user_points["monthly"],
        )
        return render(request, "leaderboards/leaderboards.html", context)
    else:
        context = create_leaderboard_context(
            global_entries,
            weekly_entries,
            monthly_entries,
            [],
            global_rank,
            weekly_rank,
            monthly_rank,
            None,
            None,
            None,
        )
        return render(request, "leaderboards/leaderboards.html", context)


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()  # Save the form data including the is_profile_public field
            request.user.profile.refresh_from_db()  # Refresh the instance so updated Profile is loaded
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        # Use the instance so the form loads all updated fields from the database.
        form = ProfileUpdateForm(instance=request.user)

    badges = UserBadge.objects.filter(user=request.user).select_related("badge")

    context = {
        "form": form,
        "badges": badges,
    }

    # Teacher-specific stats
    if request.user.profile.is_teacher:
        courses = Course.objects.filter(teacher=request.user)
        total_students = sum(course.enrollments.filter(status="approved").count() for course in courses)
        avg_rating = 0
        total_ratings = 0
        for course in courses:
            course_ratings = course.reviews.all()
            if course_ratings:
                avg_rating += sum(review.rating for review in course_ratings)
                total_ratings += len(course_ratings)
        avg_rating = round(avg_rating / total_ratings, 1) if total_ratings > 0 else 0
        context.update(
            {
                "courses": courses,
                "total_students": total_students,
                "avg_rating": avg_rating,
            }
        )
    # Student-specific stats
    else:
        enrollments = Enrollment.objects.filter(student=request.user).select_related("course")
        completed_courses = enrollments.filter(status="completed").count()
        total_progress = 0
        progress_count = 0
        for enrollment in enrollments:
            progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
            if progress.completion_percentage is not None:
                total_progress += progress.completion_percentage
                progress_count += 1
        avg_progress = round(total_progress / progress_count) if progress_count > 0 else 0
        context.update(
            {
                "enrollments": enrollments,
                "completed_courses": completed_courses,
                "avg_progress": avg_progress,
            }
        )

    # Add created calendars with time slots if applicable
    created_calendars = request.user.created_calendars.prefetch_related("time_slots").order_by("-created_at")
    context["created_calendars"] = created_calendars

    return render(request, "profile.html", context)


@login_required
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.status = "published"  # Set status to published
            course.save()
            form.save_m2m()  # Save many-to-many relationships

            # Handle waiting room if course was created from one
            if "waiting_room_data" in request.session:
                waiting_room = get_object_or_404(WaitingRoom, id=request.session["waiting_room_data"]["id"])

                # Update waiting room status and link to course
                waiting_room.status = "fulfilled"
                waiting_room.fulfilled_course = course
                waiting_room.save(update_fields=["status", "fulfilled_course"])

                # Send notifications to all participants
                for participant in waiting_room.participants.all():
                    messages.success(
                        request,
                        f"A new course matching your request has been created: {course.title}",
                        extra_tags=f"course_{course.slug}",
                    )

                # Clear waiting room data from session
                del request.session["waiting_room_data"]

                # Redirect back to waiting room to show the update
                return redirect("waiting_room_detail", waiting_room_id=waiting_room.id)

            return redirect("course_detail", slug=course.slug)
    else:
        form = CourseForm()

    return render(request, "courses/create.html", {"form": form})


@login_required
@teacher_required
def create_course_from_waiting_room(request, waiting_room_id):
    waiting_room = get_object_or_404(WaitingRoom, id=waiting_room_id)

    # Ensure waiting room is open
    if waiting_room.status != "open":
        messages.error(request, "This waiting room is no longer open.")
        return redirect("waiting_room_detail", waiting_room_id=waiting_room_id)

    # Store waiting room data in session for validation
    request.session["waiting_room_data"] = {
        "id": waiting_room.id,
        "subject": waiting_room.subject.strip().lower(),
        "topics": [t.strip().lower() for t in waiting_room.topics.split(",") if t.strip()],
    }

    # Redirect to regular course creation form
    return redirect(reverse("create_course"))


@login_required
@teacher_required
def add_featured_review(request, slug, review_id):
    # Get the course and review
    course = get_object_or_404(Course, slug=slug)
    review = get_object_or_404(Review, id=review_id, course=course)

    # Check if the user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can manage featured reviews.")
        return redirect(reverse("course_detail", kwargs={"slug": slug}))

    # Set the is_featured field to True
    review.is_featured = True
    review.save()
    messages.success(request, "Review has been featured.")

    # Redirect to the course detail page
    url = reverse("course_detail", kwargs={"slug": slug})
    return redirect(f"{url}#course_reviews")


@login_required
@teacher_required
def remove_featured_review(request, slug, review_id):
    # Get the course and review
    course = get_object_or_404(Course, slug=slug)
    review = get_object_or_404(Review, id=review_id, course=course)

    # Check if the user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can manage featured reviews.")
        return redirect(reverse("course_detail", kwargs={"slug": slug}))

    # Set the is_featured field to False
    review.is_featured = False
    review.save()

    # Redirect to the course detail page
    url = reverse("course_detail", kwargs={"slug": slug})
    return redirect(f"{url}#course_reviews")


@login_required
def edit_review(request, slug, review_id):
    course = get_object_or_404(Course, slug=slug)
    review = get_object_or_404(Review, id=review_id, course__slug=slug)

    # Security check - only allow editing own reviews
    if request.user.id != review.student.id:
        messages.error(request, "You can only edit your own reviews.")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.save()
            messages.success(request, "Your review has been updated.")
            url = reverse("course_detail", kwargs={"slug": slug})
            return redirect(f"{url}#course_reviews")
    else:
        form = ReviewForm(instance=review)

    context = {
        "form": form,
        "course": course,
        "review": review,
        "action": "Edit",
    }
    return render(request, "courses/edit_or_add_review.html", context)


@login_required
def delete_review(request, slug, review_id):
    review = get_object_or_404(Review, id=review_id, course__slug=slug)

    # Security check - only allow deleting own reviews
    if request.user.id != review.student.id:
        messages.error(request, "You can only delete your own reviews.")
    else:
        review.delete()
        messages.success(request, "Your review has been deleted.")

    url = reverse("course_detail", kwargs={"slug": slug})
    return redirect(f"{url}#course_reviews")


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    sessions = course.sessions.all().order_by("start_time")
    now = timezone.now()
    is_teacher = request.user == course.teacher
    completed_sessions = []
    # Check if user is the teacher of this course

    # Get enrollment if user is authenticated
    enrollment = None
    is_enrolled = False
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(course=course, student=request.user, status="approved").first()
        is_enrolled = enrollment is not None
        if enrollment:
            # Get completed sessions through SessionAttendance
            completed_sessions = SessionAttendance.objects.filter(
                student=request.user, session__course=course, status="completed"
            ).values_list("session__id", flat=True)
            completed_sessions = course.sessions.filter(id__in=completed_sessions)

    # Get attendance data for all enrolled students
    student_attendance = {}
    total_sessions = sessions.count()

    if is_teacher or is_enrolled:
        for enroll in course.enrollments.all():
            attended_sessions = SessionAttendance.objects.filter(
                student=enroll.student, session__course=course, status__in=["present", "late"]
            ).count()
            student_attendance[enroll.student.id] = {"attended": attended_sessions, "total": total_sessions}

    # Mark past sessions as completed for display
    past_sessions = sessions.filter(end_time__lt=now)
    future_sessions = sessions.filter(end_time__gte=now)
    sessions = list(future_sessions) + list(past_sessions)  # Show future sessions first

    # Calendar data
    today = timezone.now().date()

    # Get the requested month from query parameters, default to current month
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        current_month = today.replace(year=year, month=month, day=1)
    except (ValueError, TypeError):
        current_month = today.replace(day=1)

    # Calculate previous and next month
    if current_month.month == 1:
        prev_month = current_month.replace(year=current_month.year - 1, month=12)
    else:
        prev_month = current_month.replace(month=current_month.month - 1)

    if current_month.month == 12:
        next_month = current_month.replace(year=current_month.year + 1, month=1)
    else:
        next_month = current_month.replace(month=current_month.month + 1)

    # Get the calendar for current month
    cal = calendar.monthcalendar(current_month.year, current_month.month)

    # Get all session dates for this course in current month
    session_dates = set(
        session.start_time.date()
        for session in sessions
        if session.start_time.year == current_month.year and session.start_time.month == current_month.month
    )

    # Prepare calendar weeks data
    calendar_weeks = []
    for week in cal:
        calendar_week = []
        for day in week:
            if day == 0:
                calendar_week.append({"date": None, "in_month": False, "has_session": False})
            else:
                date = current_month.replace(day=day)
                calendar_week.append({"date": date, "in_month": True, "has_session": date in session_dates})
        calendar_weeks.append(calendar_week)

    # Check if the current user has already reviewed this course
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(student=request.user, course=course).first()

    # Get all reviews That not featured for this course
    reviews = course.reviews.filter(is_featured=False).order_by("-created_at")

    # Get the featured review
    featured_review = Review.objects.filter(is_featured=True, course=course)

    # Get all reviews sum
    reviews_num = reviews.count() + featured_review.count()

    # Calculate rating distribution for visualization
    rating_counts = Review.objects.filter(course=course).values("rating").annotate(count=Count("id"))
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for item in rating_counts:
        rating_distribution[item["rating"]] = item["count"]

    context = {
        "course": course,
        "sessions": sessions,
        "now": now,
        "today": today,
        "is_teacher": is_teacher,
        "is_enrolled": is_enrolled,
        "enrollment": enrollment,
        "completed_sessions": completed_sessions,
        "calendar_weeks": calendar_weeks,
        "current_month": current_month,
        "prev_month": prev_month,
        "next_month": next_month,
        "student_attendance": student_attendance,
        "completed_enrollment_count": course.enrollments.filter(status="completed").count(),
        "in_progress_enrollment_count": course.enrollments.filter(status="in_progress").count(),
        "featured_review": featured_review,
        "reviews": reviews,
        "user_review": user_review,
        "rating_distribution": rating_distribution,
        "reviews_num": reviews_num,
    }

    return render(request, "courses/detail.html", context)


@login_required
def enroll_course(request, course_slug):
    """Enroll in a course and handle referral rewards if applicable."""
    course = get_object_or_404(Course, slug=course_slug)

    # Check if user is already enrolled
    if request.user.enrollments.filter(course=course).exists():
        messages.warning(request, "You are already enrolled in this course.")
        return redirect("course_detail", slug=course_slug)

    # Check if course is full
    if course.max_students and course.enrollments.count() >= course.max_students:
        messages.error(request, "This course is full.")
        return redirect("course_detail", slug=course_slug)

    # Check if this is the user's first enrollment and if they were referred
    if not Enrollment.objects.filter(student=request.user).exists():
        if hasattr(request.user.profile, "referred_by") and request.user.profile.referred_by:
            referrer = request.user.profile.referred_by
            if not referrer.is_teacher:  # Regular users get reward on first course enrollment
                referrer.add_referral_earnings(5)
                send_referral_reward_email(referrer.user, request.user, 5, "enrollment")

    # For free courses, create approved enrollment immediately
    if course.price == 0:
        enrollment = Enrollment.objects.create(student=request.user, course=course, status="approved")
        # Send notifications for free courses
        send_enrollment_confirmation(enrollment)
        notify_teacher_new_enrollment(enrollment)
        messages.success(request, "You have successfully enrolled in this free course.")
        return redirect("course_detail", slug=course_slug)
    else:
        # For paid courses, create pending enrollment
        enrollment = Enrollment.objects.create(student=request.user, course=course, status="pending")
        messages.info(request, "Please complete the payment process to enroll in this course.")
        return redirect("course_detail", slug=course_slug)


@login_required
def add_session(request, slug):
    course = Course.objects.get(slug=slug)
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can add sessions!")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.course = course
            session.save()
            # Send session notifications to enrolled students
            notify_session_reminder(session)
            messages.success(request, "Session added successfully!")
            return redirect("course_detail", slug=slug)
    else:
        form = SessionForm()

    return render(request, "courses/session_form.html", {"form": form, "course": course, "is_edit": False})


@login_required
def add_review(request, slug):
    course = Course.objects.get(slug=slug)
    student = request.user

    if not request.user.enrollments.filter(course=course).exists():
        messages.error(request, "Only enrolled students can review the course!")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            if Review.objects.filter(student=student, course=course).exists():
                messages.error(request, "You have already reviewed this course.")
                return redirect("course_detail", slug=slug)
            review = form.save(commit=False)
            review.student = student
            review.course = course
            review.save()
            messages.success(request, "Review added successfully!")
            url = reverse("course_detail", kwargs={"slug": slug})
            return redirect(f"{url}#course_reviews")
    else:
        form = ReviewForm()

    return render(request, "courses/edit_or_add_review.html", {"form": form, "course": course, "action": "Add"})


@login_required
def delete_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can delete the course!")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted successfully!")
        return redirect("profile")

    return render(request, "courses/delete_confirm.html", {"course": course})


@csrf_exempt
def github_update(request):
    send_slack_message("New commit pulled from GitHub")
    root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        subprocess.run(["chmod", "+x", f"{root_directory}/setup.sh"])
        result = subprocess.run(["bash", f"{root_directory}/setup.sh"], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(
                f"setup.sh failed with return code {result.returncode} and output: {result.stdout} {result.stderr}"
            )
        send_slack_message("CHMOD success about to set time on: " + settings.PA_WSGI)

        current_time = time.time()
        os.utime(settings.PA_WSGI, (current_time, current_time))
        send_slack_message("Repository updated successfully")
        return HttpResponse("Repository updated successfully")
    except Exception as e:
        print(f"Deploy error: {e}")
        send_slack_message(f"Deploy error: {e}")
        return HttpResponse("Deploy error see logs.")


def send_slack_message(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Warning: SLACK_WEBHOOK_URL not configured")
        return

    payload = {"text": f"```{message}```"}
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()  # Raise exception for bad status codes
    except Exception as e:
        print(f"Failed to send Slack message: {e}")


def get_wsgi_last_modified_time():
    try:
        return time.ctime(os.path.getmtime(settings.PA_WSGI))
    except Exception:
        return "Unknown"


def subjects(request):
    return render(request, "subjects.html")


def about(request):
    return render(request, "about.html")


def waiting_rooms(request):
    # Get open waiting rooms
    open_rooms = WaitingRoom.objects.filter(status="open").order_by("-created_at")

    # Get fulfilled waiting rooms (ones that have associated courses)
    fulfilled_rooms = WaitingRoom.objects.filter(status="fulfilled").order_by("-created_at")

    # Get rooms created by the user
    user_created_rooms = (
        WaitingRoom.objects.filter(creator=request.user).order_by("-created_at")
        if request.user.is_authenticated
        else []
    )

    # Get rooms the user has joined
    user_joined_rooms = (
        WaitingRoom.objects.filter(participants=request.user).order_by("-created_at")
        if request.user.is_authenticated
        else []
    )

    # Get topics for each room
    room_topics = {}
    all_rooms = list(open_rooms) + list(fulfilled_rooms) + list(user_created_rooms) + list(user_joined_rooms)
    for room in all_rooms:
        # Split topics string into a list
        room_topics[room.id] = [t.strip() for t in room.topics.split(",")] if room.topics else []

    context = {
        "open_rooms": open_rooms,
        "fulfilled_rooms": fulfilled_rooms,
        "user_created_rooms": user_created_rooms,
        "user_joined_rooms": user_joined_rooms,
        "room_topics": room_topics,
    }

    return render(request, "waiting_rooms.html", context)


def learn(request):
    if request.method == "POST":
        form = LearnForm(request.POST)
        if form.is_valid():
            # Create waiting room
            waiting_room = form.save(commit=False)
            waiting_room.status = "open"  # Set initial status
            waiting_room.creator = request.user  # Set the creator

            # Get topics from form and save as comma-separated string
            topics = form.cleaned_data.get("topics", "")
            if isinstance(topics, list):
                topics = ", ".join(topics)
            waiting_room.topics = topics

            waiting_room.save()

            # Redirect to waiting rooms page
            return redirect("waiting_rooms")

            # Get form data
            title = form.cleaned_data["title"]
            description = form.cleaned_data["description"]
            subject = form.cleaned_data["subject"]
            topics = form.cleaned_data["topics"]

            # Prepare email content
            email_subject = f"New Learning Request: {title}"
            email_body = render_to_string(
                "emails/learn_interest.html",
                {
                    "title": title,
                    "description": description,
                    "subject": subject,
                    "topics": topics,
                    "user": request.user.username,
                    "waiting_room_id": waiting_room.id,
                },
            )

            # Send email
            try:
                send_mail(
                    email_subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.DEFAULT_FROM_EMAIL],
                    html_message=email_body,
                    fail_silently=False,
                )
                messages.success(
                    request,
                    "Thank you for your learning request!",
                )
                return redirect("waiting_rooms")
            except Exception:
                logger = logging.getLogger(__name__)
                logger.exception("Error sending email")
                messages.error(request, "Sorry, there was an error sending your inquiry. Please try again later.")
    else:
        initial_data = {}

        # Handle query parameters
        query = request.GET.get("query", "")
        subject_param = request.GET.get("subject", "")
        level = request.GET.get("level", "")

        # Try to match subject
        if subject_param:
            try:
                subject = Subject.objects.get(name=subject_param)
                initial_data["subject"] = subject.id
            except Subject.DoesNotExist:
                # Optionally, you could add the subject name to the description
                initial_data["description"] = f"Looking for courses in {subject_param}"

        # If you want to include other parameters in the description
        if query or level:
            title_parts = []
            description_parts = []
            if query:
                title_parts.append(f"{query}")
            if level:
                description_parts.append(f"Level: {level}")

            if "description" not in initial_data:
                initial_data["title"] = " | ".join(title_parts)
            else:
                initial_data["description"] += " | " + " | ".join(description_parts)

        form = LearnForm(initial=initial_data)
        return render(request, "learn.html", {"form": form})


def teach(request):
    """Handles the course creation process for both authenticated and unauthenticated users."""
    if request.method == "POST":
        form = TeachForm(request.POST, request.FILES)
        if form.is_valid():
            # Extract cleaned data
            email = form.cleaned_data["email"]
            course_title = form.cleaned_data["course_title"]
            course_description = form.cleaned_data["course_description"]
            course_image = form.cleaned_data.get("course_image")
            preferred_session_times = form.cleaned_data["preferred_session_times"]
            _ = form.cleaned_data.get("flexible_timing", False)

            # Determine the user for the course
            user = None
            is_new_user = False

            if request.user.is_authenticated:
                # For authenticated users, always use the logged-in user
                user = request.user

                # Validate that the provided email matches the logged-in user's email
                if email != user.email:
                    form.add_error(
                        "email",
                        "The provided email does not match your account email. Please use your account email.",
                    )
                    return render(request, "teach.html", {"form": form})

                # Backend validation: Check for duplicate course titles for the logged-in user
                if Course.objects.filter(title__iexact=course_title, teacher=user).exists():
                    form.add_error("course_title", "You already have a course with this title.")
                    return render(request, "teach.html", {"form": form})
            else:
                # For unauthenticated users, check if the email exists or create a new user
                try:
                    user = User.objects.get(email=email)
                    # User exists but isn't logged in; check if email is verified
                    email_address = EmailAddress.objects.filter(user=user, email=email, primary=True).first()
                    if email_address and email_address.verified:
                        messages.info(
                            request,
                            "An account with this email exists. Please login to finalize your course.",
                        )
                    else:
                        # Email not verified, resend verification email
                        send_email_confirmation(request, user, signup=False)
                        messages.info(
                            request,
                            "An account with this email exists. Please verify your email to continue.",
                        )
                except User.DoesNotExist:
                    # Create a new user account
                    with transaction.atomic():
                        # Generate a unique username
                        email_prefix = email.split("@")[0]
                        username = email_prefix
                        counter = 1
                        while User.objects.filter(username=username).exists():
                            username = f"{email_prefix}_{get_random_string(4)}_{counter}"
                            counter += 1

                        temp_password = get_random_string(length=8)

                        # Create user with temporary password
                        user = User.objects.create_user(username=username, email=email, password=temp_password)

                        # Update profile to be a teacher
                        profile, created = Profile.objects.get_or_create(user=user)
                        profile.is_teacher = True
                        profile.save()

                        # Add email address for allauth verification
                        EmailAddress.objects.create(user=user, email=email, primary=True, verified=False)

                        # Send verification email via allauth
                        send_email_confirmation(request, user, signup=True)
                        # Send welcome email with username, email, and temp password
                        try:
                            send_welcome_teach_course_email(request, user, temp_password)
                        except Exception:
                            messages.error(request, "Failed to send welcome email. Please try again.")
                            return render(request, "teach.html", {"form": form})

                        is_new_user = True

                # Backend validation: Check for duplicate course titles for unauthenticated users
                if Course.objects.filter(title__iexact=course_title, teacher=user).exists():
                    email_address = EmailAddress.objects.filter(user=user, email=email, primary=True).first()
                    if email_address and not email_address.verified:
                        # If the user is unverified, delete the existing draft and allow a new one
                        Course.objects.filter(title__iexact=course_title, teacher=user).delete()
                    else:
                        form.add_error("course_title", "You already have a course with this title.")
                        return render(request, "teach.html", {"form": form})

            # Create a draft course
            course = Course.objects.create(
                title=course_title,
                description=course_description,
                teacher=user,
                price=0,
                max_students=12,
                status="draft",
                subject=Subject.objects.first() or Subject.objects.create(name="General"),
                level="beginner",
            )

            # Handle course image if uploaded
            if course_image:
                course.image = course_image
                course.save()

            # Create initial session if preferred time provided
            if preferred_session_times:
                Session.objects.create(
                    course=course,
                    title=f"{course_title} - Session 1",
                    description="First session of the course",
                    start_time=preferred_session_times,
                    end_time=preferred_session_times + timezone.timedelta(hours=1),
                    is_virtual=True,
                )

            # Handle redirection based on authentication status
            if request.user.is_authenticated:
                # If authenticated, mark as teacher and redirect to course setup
                request.user.profile.is_teacher = True
                request.user.profile.save()
                messages.success(
                    request, f"Welcome! Your course '{course_title}' has been created. Please complete your setup."
                )
                return redirect("course_detail", slug=course.slug)
            else:
                # Store course primary key in session for post-verification redirect
                request.session["pending_course_id"] = course.pk
                if is_new_user:
                    messages.success(
                        request,
                        "Your course has been created! "
                        "Please check your email for your username, password, and verification link to continue.",
                    )
                    return redirect("account_email_verification_sent")
                else:
                    # For existing users, redirect to login page
                    return redirect("account_login")

    else:
        initial_data = {}
        if request.GET.get("subject"):
            initial_data["course_title"] = request.GET.get("subject")
        form = TeachForm(initial=initial_data)

    return render(request, "teach.html", {"form": form})


def send_welcome_teach_course_email(request, user, temp_password):
    """Send welcome email with account and password setup instructions."""
    reset_url = request.build_absolute_uri(reverse("account_reset_password"))

    email_context = {"user": user, "reset_url": reset_url, "temp_password": temp_password}

    html_message = render_to_string("emails/welcome_teach_course.html", email_context)
    text_message = render_to_string("emails/welcome_teach_course.txt", email_context)

    send_mail(
        subject="Welcome to Your New Teaching Account.",
        message=text_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def course_search(request):
    query = request.GET.get("q", "")
    subject = request.GET.get("subject", "")
    level = request.GET.get("level", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sort_by = request.GET.get("sort", "-created_at")

    courses = Course.objects.filter(status="published")

    # Apply filters
    if query:
        courses = courses.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
            | Q(learning_objectives__icontains=query)
            | Q(prerequisites__icontains=query)
            | Q(teacher__username__icontains=query)
            | Q(teacher__first_name__icontains=query)
            | Q(teacher__last_name__icontains=query)
            | Q(teacher__profile__expertise__icontains=query)
        )

    if subject:
        # Handle subject filtering based on whether it's an ID (number) or a string (slug/name)
        try:
            # Check if subject is an integer ID
            subject_id = int(subject)
            courses = courses.filter(subject_id=subject_id)
        except ValueError:
            # If not an integer, treat as a slug or name
            courses = courses.filter(Q(subject__slug=subject) | Q(subject__name__iexact=subject))

    if level:
        courses = courses.filter(level=level)

    if min_price:
        try:
            min_price = float(min_price)
            courses = courses.filter(price__gte=min_price)
        except ValueError:
            pass

    if max_price:
        try:
            max_price = float(max_price)
            courses = courses.filter(price__lte=max_price)
        except ValueError:
            pass

    # Annotate with average rating for sorting
    courses = courses.annotate(
        avg_rating=Avg("reviews__rating"),
        total_students=Count("enrollments", filter=Q(enrollments__status="approved")),
    )

    # Apply sorting
    if sort_by == "price":
        courses = courses.order_by("price", "-avg_rating")
    elif sort_by == "-price":
        courses = courses.order_by("-price", "-avg_rating")
    elif sort_by == "title":
        courses = courses.order_by("title")
    elif sort_by == "rating":
        courses = courses.order_by("-avg_rating", "-total_students")
    else:  # Default to newest
        courses = courses.order_by("-created_at")

    # Get total count before pagination
    total_results = courses.count()

    # Log the search
    if query or subject or level or min_price or max_price:
        filters = {
            "subject": subject,
            "level": level,
            "min_price": min_price,
            "max_price": max_price,
            "sort_by": sort_by,
        }
        SearchLog.objects.create(
            query=query,
            results_count=total_results,
            user=request.user if request.user.is_authenticated else None,
            filters_applied=filters,
            search_type="course",
        )

    # Pagination
    paginator = Paginator(courses, 12)  # Show 12 courses per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    is_teacher = getattr(getattr(request.user, "profile", None), "is_teacher", False)

    context = {
        "page_obj": page_obj,
        "query": query,
        "subject": subject,
        "level": level,
        "min_price": min_price,
        "max_price": max_price,
        "sort_by": sort_by,
        "subject_choices": Course._meta.get_field("subject").choices,
        "level_choices": Course._meta.get_field("level").choices,
        "total_results": total_results,
        "is_teacher": is_teacher,
    }

    return render(request, "courses/search.html", context)


@login_required
def create_payment_intent(request, slug):
    """Create a payment intent for Stripe."""
    course = get_object_or_404(Course, slug=slug)

    # Prevent creating payment intents for free courses
    if course.price == 0:
        # Find the enrollment and update its status to approved if it's pending
        enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
        if enrollment.status == "pending":
            enrollment.status = "approved"
            enrollment.save()

            # Send notifications
            send_enrollment_confirmation(enrollment)
            notify_teacher_new_enrollment(enrollment)

        return JsonResponse({"free_course": True, "message": "Enrollment approved for free course"})

    # Ensure user has a pending enrollment
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course, status="pending")

    # Validate price is greater than zero for Stripe
    if course.price <= 0:
        enrollment.status = "approved"
        enrollment.save()

        # Send notifications
        send_enrollment_confirmation(enrollment)
        notify_teacher_new_enrollment(enrollment)

        return JsonResponse({"free_course": True, "message": "Enrollment approved for free course"})

    try:
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(course.price * 100),  # Convert to cents
            currency="usd",
            metadata={
                "course_id": course.id,
                "user_id": request.user.id,
            },
        )
        return JsonResponse({"clientSecret": intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=403)


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook endpoint for handling payment events."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        handle_successful_payment(payment_intent)
    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object
        handle_failed_payment(payment_intent)

    return HttpResponse(status=200)


def handle_successful_payment(payment_intent):
    """Handle successful payment by enrolling the user in the course."""
    # Get metadata from the payment intent
    course_id = payment_intent.metadata.get("course_id")
    user_id = payment_intent.metadata.get("user_id")

    # Create enrollment and payment records
    course = Course.objects.get(id=course_id)
    user = User.objects.get(id=user_id)

    # Create enrollment with pending status
    enrollment = Enrollment.objects.get_or_create(student=user, course=course, defaults={"status": "pending"})[0]

    # Update status to approved after successful payment
    enrollment.status = "approved"
    enrollment.save()

    # Send notifications
    send_enrollment_confirmation(enrollment)
    notify_teacher_new_enrollment(enrollment)


def handle_failed_payment(payment_intent):
    """Handle failed payment."""
    course_id = payment_intent.metadata.get("course_id")
    user_id = payment_intent.metadata.get("user_id")

    try:
        course = Course.objects.get(id=course_id)
        user = User.objects.get(id=user_id)
        enrollment = Enrollment.objects.get(student=user, course=course)
        enrollment.status = "pending"
        enrollment.save()
    except (Course.DoesNotExist, User.DoesNotExist, Enrollment.DoesNotExist):
        pass  # Log error or handle appropriately


@login_required
def update_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user != course.teacher:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            return redirect("course_detail", slug=course.slug)
    else:
        form = CourseForm(instance=course)

    return render(request, "courses/update.html", {"form": form, "course": course})


@login_required
def mark_session_attendance(request, session_id):
    session = Session.objects.get(id=session_id)
    if request.user != session.course.teacher:
        messages.error(request, "Only the course teacher can mark attendance!")
        return redirect("course_detail", slug=session.course.slug)

    if request.method == "POST":
        for student_id, status in request.POST.items():
            if student_id.startswith("student_"):
                student_id = student_id.replace("student_", "")
                student = User.objects.get(id=student_id)
                attendance, created = SessionAttendance.objects.update_or_create(
                    session=session, student=student, defaults={"status": status}
                )
        messages.success(request, "Attendance marked successfully!")
        return redirect("course_detail", slug=session.course.slug)

    enrollments = session.course.enrollments.filter(status="approved")
    attendances = {att.student_id: att.status for att in session.attendances.all()}

    context = {
        "session": session,
        "enrollments": enrollments,
        "attendances": attendances,
    }
    return render(request, "courses/mark_attendance.html", context)


@login_required
def mark_session_completed(request, session_id):
    session = Session.objects.get(id=session_id)
    enrollment = request.user.enrollments.get(course=session.course)

    if enrollment.status != "approved":
        messages.error(request, "You must be enrolled in the course to mark sessions as completed!")
        return redirect("course_detail", slug=session.course.slug)

    progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
    progress.completed_sessions.add(session)

    # Check for achievements
    if progress.completion_percentage == 100:
        Achievement.objects.get_or_create(
            student=request.user,
            course=session.course,
            achievement_type="completion",
            defaults={
                "title": "Course Completed!",
                "description": f"Completed all sessions in {session.course.title}",
            },
        )

    if progress.attendance_rate == 100:
        Achievement.objects.get_or_create(
            student=request.user,
            course=session.course,
            achievement_type="attendance",
            defaults={
                "title": "Perfect Attendance!",
                "description": f"Attended all sessions in {session.course.title}",
            },
        )

    messages.success(request, "Session marked as completed!")
    return redirect("course_detail", slug=session.course.slug)


@login_required
def award_achievement(request):
    try:
        profile = request.user.profile
        if not profile.is_teacher:
            messages.error(request, "You do not have permission to award achievements.")
            return redirect("teacher_dashboard")
    except Profile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect("teacher_dashboard")

    if request.method == "POST":
        form = AwardAchievementForm(request.POST, teacher=request.user)
        if form.is_valid():
            Achievement.objects.create(
                student=form.cleaned_data["student"],
                course=form.cleaned_data["course"],
                achievement_type=form.cleaned_data["achievement_type"],
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                badge_icon=form.cleaned_data["badge_icon"],
            )
            messages.success(
                request,
                f'Achievement "{form.cleaned_data["title"]}" awarded to {form.cleaned_data["student"].username}.',
            )
            return redirect("teacher_dashboard")
        else:
            # Show an error message if the form is invalid
            messages.error(request, "There was an error in the form submission. Please check the form and try again.")
    else:
        form = AwardAchievementForm(teacher=request.user)
    return render(request, "award_achievement.html", {"form": form})


@login_required
def student_progress(request, enrollment_id):
    enrollment = Enrollment.objects.get(id=enrollment_id)

    if request.user != enrollment.student and request.user != enrollment.course.teacher:
        messages.error(request, "You don't have permission to view this progress!")
        return redirect("course_detail", slug=enrollment.course.slug)

    progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
    achievements = Achievement.objects.filter(student=enrollment.student, course=enrollment.course)

    past_sessions = enrollment.course.sessions.filter(start_time__lt=timezone.now())
    upcoming_sessions = enrollment.course.sessions.filter(start_time__gte=timezone.now())

    context = {
        "enrollment": enrollment,
        "progress": progress,
        "achievements": achievements,
        "past_sessions": past_sessions,
        "upcoming_sessions": upcoming_sessions,
        "stripe_public_key": (
            settings.STRIPE_PUBLISHABLE_KEY if enrollment.status == "pending" and enrollment.course.price > 0 else None
        ),
    }
    return render(request, "courses/student_progress.html", context)


@login_required
def course_progress_overview(request, slug):
    course = Course.objects.get(slug=slug)
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can view the progress overview!")
        return redirect("course_detail", slug=slug)

    enrollments = course.enrollments.filter(status="approved")
    progress_data = []

    for enrollment in enrollments:
        progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
        attendance_data = (
            SessionAttendance.objects.filter(student=enrollment.student, session__course=course)
            .values("status")
            .annotate(count=models.Count("status"))
        )

        progress_data.append(
            {
                "enrollment": enrollment,
                "progress": progress,
                "attendance": attendance_data,
            }
        )

    context = {
        "course": course,
        "progress_data": progress_data,
    }
    return render(request, "courses/progress_overview.html", context)


@login_required
def upload_material(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user != course.teacher:
        return HttpResponseForbidden("You are not authorized to upload materials for this course.")

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES, course=course)
        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.save()
            messages.success(request, "Course material uploaded successfully!")
            return redirect("course_detail", slug=course.slug)
    else:
        form = CourseMaterialForm(course=course)

    return render(request, "courses/upload_material.html", {"form": form, "course": course})


@login_required
def delete_material(request, slug, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id, course__slug=slug)
    if request.user != material.course.teacher:
        return HttpResponseForbidden("You are not authorized to delete this material.")

    if request.method == "POST":
        material.delete()
        messages.success(request, "Course material deleted successfully!")
        return redirect("course_detail", slug=slug)

    return render(request, "courses/delete_material_confirm.html", {"material": material})


@login_required
def download_material(request, slug, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id, course__slug=slug)
    if not material.is_downloadable and request.user != material.course.teacher:
        return HttpResponseForbidden("This material is not available for download.")

    try:
        return FileResponse(material.file, as_attachment=True)
    except FileNotFoundError:
        messages.error(request, "The requested file could not be found.")
        return redirect("course_detail", slug=slug)


@login_required
@teacher_required
def course_marketing(request, slug):
    """View for managing course marketing and promotions."""
    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "send_promotional_emails":
            send_course_promotion_email(
                course=course,
                subject=f"New Course Recommendation: {course.title}",
                template_name="course_promotion",
            )
            messages.success(request, "Promotional emails have been sent successfully.")

        elif action == "generate_social_content":
            social_content = generate_social_share_content(course)
            return JsonResponse({"social_content": social_content})

    # Get analytics and recommendations
    analytics = get_course_analytics(course)
    recommendations = get_promotion_recommendations(course)

    context = {
        "course": course,
        "analytics": analytics,
        "recommendations": recommendations,
    }

    return render(request, "courses/marketing.html", context)


@login_required
@teacher_required
def course_analytics(request, slug):
    """View for displaying detailed course analytics."""
    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    analytics = get_course_analytics(course)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"analytics": analytics})

    context = {
        "course": course,
        "analytics": analytics,
    }

    return render(request, "courses/analytics.html", context)


@login_required
def calendar_feed(request):
    """Generate and serve an iCal feed of the user's course sessions."""

    response = HttpResponse(generate_ical_feed(request.user), content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{settings.SITE_NAME}-schedule.ics"'
    return response


@login_required
def calendar_links(request, session_id):
    """Get calendar links for a specific session."""

    session = get_object_or_404(Session, id=session_id)

    # Check if user has access to this session
    if not (
        request.user == session.course.teacher
        or request.user.enrollments.filter(course=session.course, status="approved").exists()
    ):
        return HttpResponseForbidden("You don't have access to this session.")

    links = {
        "google": generate_google_calendar_link(session),
        "outlook": generate_outlook_calendar_link(session),
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"links": links})

    return render(
        request,
        "courses/calendar_links.html",
        {
            "session": session,
            "calendar_links": links,
        },
    )


def forum_categories(request):
    """Display all forum categories."""
    categories = ForumCategory.objects.all()
    return render(request, "web/forum/categories.html", {"categories": categories})


def forum_category(request, slug):
    """Display topics in a specific category."""
    category = get_object_or_404(ForumCategory, slug=slug)
    topics = category.topics.all()
    categories = ForumCategory.objects.all()
    return render(
        request, "web/forum/category.html", {"category": category, "topics": topics, "categories": categories}
    )


def forum_topic(request, category_slug, topic_id):
    """Display a forum topic and its replies."""
    topic = get_object_or_404(ForumTopic, id=topic_id, category__slug=category_slug)
    categories = ForumCategory.objects.all()

    # Get view count from WebRequest model
    view_count = (
        WebRequest.objects.filter(path=request.path).aggregate(total_views=models.Sum("count"))["total_views"] or 0
    )
    topic.views = view_count
    topic.save()

    # Handle POST requests for replies, etc.
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_reply" and request.user.is_authenticated:
            content = request.POST.get("content")
            if content:
                ForumReply.objects.create(topic=topic, author=request.user, content=content)
                messages.success(request, "Reply added successfully.")
                return redirect("forum_topic", category_slug=category_slug, topic_id=topic_id)
        elif action == "delete_reply" and request.user.is_authenticated:
            reply_id = request.POST.get("reply_id")
            reply = get_object_or_404(ForumReply, id=reply_id, author=request.user)
            reply.delete()
            messages.success(request, "Reply deleted successfully.")
            return redirect("forum_topic", category_slug=category_slug, topic_id=topic_id)
        elif action == "delete_topic" and request.user == topic.author:
            topic.delete()
            messages.success(request, "Topic deleted successfully.")
            return redirect("forum_category", slug=category_slug)

    replies = topic.replies.select_related("author").order_by("created_at")
    return render(request, "web/forum/topic.html", {"topic": topic, "replies": replies, "categories": categories})


@login_required
def create_topic(request, category_slug):
    """Create a new forum topic."""
    category = get_object_or_404(ForumCategory, slug=category_slug)
    categories = ForumCategory.objects.all()

    if request.method == "POST":
        form = ForumTopicForm(request.POST)
        if form.is_valid():
            topic = ForumTopic.objects.create(
                category=category,
                author=request.user,
                title=form.cleaned_data["title"],
                content=form.cleaned_data["content"],
            )
            messages.success(request, "Topic created successfully!")
            return redirect("forum_topic", category_slug=category_slug, topic_id=topic.id)
    else:
        form = ForumTopicForm()

    return render(
        request, "web/forum/create_topic.html", {"category": category, "form": form, "categories": categories}
    )


@login_required
def peer_connections(request):
    """Display user's peer connections."""
    sent_connections = request.user.sent_connections.all()
    received_connections = request.user.received_connections.all()
    return render(
        request,
        "web/peer/connections.html",
        {
            "sent_connections": sent_connections,
            "received_connections": received_connections,
        },
    )


@login_required
def send_connection_request(request, user_id):
    """Send a peer connection request."""
    receiver = get_object_or_404(User, id=user_id)

    if request.user == receiver:
        messages.error(request, "You cannot connect with yourself!")
        return redirect("peer_connections")

    connection, created = PeerConnection.objects.get_or_create(
        sender=request.user, receiver=receiver, defaults={"status": "pending"}
    )

    if created:
        messages.success(request, f"Connection request sent to {receiver.username}!")
    else:
        messages.info(request, f"Connection request already sent to {receiver.username}.")

    return redirect("peer_connections")


@login_required
def handle_connection_request(request, connection_id, action):
    """Accept or reject a peer connection request."""
    connection = get_object_or_404(PeerConnection, id=connection_id, receiver=request.user, status="pending")

    if action == "accept":
        connection.status = "accepted"
        messages.success(request, f"Connection with {connection.sender.username} accepted!")
    elif action == "reject":
        connection.status = "rejected"
        messages.info(request, f"Connection with {connection.sender.username} rejected.")

    connection.save()
    return redirect("peer_connections")


@login_required
def peer_messages(request, user_id):
    """Display and handle messages with a peer."""
    peer = get_object_or_404(User, id=user_id)

    # Check if users are connected
    connection = PeerConnection.objects.filter(
        (Q(sender=request.user, receiver=peer) | Q(sender=peer, receiver=request.user)),
        status="accepted",
    ).first()

    if not connection:
        messages.error(request, "You must be connected with this user to send messages.")
        return redirect("peer_connections")

    if request.method == "POST":
        content = request.POST.get("content")
        if content:
            PeerMessage.objects.create(sender=request.user, receiver=peer, content=content)
            messages.success(request, "Message sent!")

    # Get conversation messages
    messages_list = PeerMessage.objects.filter(
        (Q(sender=request.user, receiver=peer) | Q(sender=peer, receiver=request.user))
    ).order_by("created_at")

    # Mark received messages as read
    messages_list.filter(sender=peer, receiver=request.user, is_read=False).update(is_read=True)

    return render(request, "web/peer/messages.html", {"peer": peer, "messages": messages_list})


@login_required
def study_groups(request, course_id):
    """Display study groups for a course."""
    course = get_object_or_404(Course, id=course_id)
    groups = course.study_groups.all()

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        max_members = request.POST.get("max_members", 10)
        is_private = request.POST.get("is_private", False)

        if name and description:
            group = StudyGroup.objects.create(
                course=course,
                creator=request.user,
                name=name,
                description=description,
                max_members=max_members,
                is_private=is_private,
            )
            group.members.add(request.user)
            messages.success(request, "Study group created successfully!")
            return redirect("study_group_detail", group_id=group.id)

    return render(request, "web/study/groups.html", {"course": course, "groups": groups})


@login_required
def study_group_detail(request, group_id):
    """Display study group details and handle join/leave requests."""
    group = get_object_or_404(StudyGroup, id=group_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "join":
            if group.members.count() >= group.max_members:
                messages.error(request, "This group is full!")
            else:
                group.members.add(request.user)
                messages.success(request, f"You have joined {group.name}!")

        elif action == "leave":
            if request.user == group.creator:
                messages.error(request, "Group creator cannot leave the group!")
            else:
                group.members.remove(request.user)
                messages.info(request, f"You have left {group.name}.")

    return render(request, "web/study/group_detail.html", {"group": group})


# API Views
@login_required
def api_course_list(request):
    """API endpoint for listing courses."""
    courses = Course.objects.filter(status="published")
    data = [
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "teacher": course.teacher.username,
            "price": str(course.price),
            "subject": course.subject,
            "level": course.level,
            "slug": course.slug,
        }
        for course in courses
    ]
    return JsonResponse(data, safe=False)


@login_required
@teacher_required
def api_course_create(request):
    """API endpoint for creating a course."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    data = json.loads(request.body)
    course = Course.objects.create(
        teacher=request.user,
        title=data["title"],
        description=data["description"],
        learning_objectives=data["learning_objectives"],
        prerequisites=data.get("prerequisites", ""),
        price=data["price"],
        max_students=data["max_students"],
        subject=data["subject"],
        level=data["level"],
    )
    return JsonResponse(
        {
            "id": course.id,
            "title": course.title,
            "slug": course.slug,
        },
        status=201,
    )


@login_required
def api_course_detail(request, slug):
    """API endpoint for course details."""
    course = get_object_or_404(Course, slug=slug)
    data = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "teacher": course.teacher.username,
        "price": str(course.price),
        "subject": course.subject,
        "level": course.level,
        "prerequisites": course.prerequisites,
        "learning_objectives": course.learning_objectives,
        "max_students": course.max_students,
        "available_spots": course.available_spots,
        "average_rating": course.average_rating,
    }
    return JsonResponse(data)


@login_required
def api_enroll(request, course_slug):
    """API endpoint for course enrollment."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    course = get_object_or_404(Course, slug=course_slug)
    if request.user.enrollments.filter(course=course).exists():
        return JsonResponse({"error": "Already enrolled"}, status=400)

    enrollment = Enrollment.objects.create(
        student=request.user,
        course=course,
        status="pending",
    )
    return JsonResponse(
        {
            "id": enrollment.id,
            "status": enrollment.status,
        },
        status=201,
    )


@login_required
def api_enrollments(request):
    """API endpoint for listing user enrollments."""
    enrollments = request.user.enrollments.all()
    data = [
        {
            "id": enrollment.id,
            "course": {
                "id": enrollment.course.id,
                "title": enrollment.course.title,
                "slug": enrollment.course.slug,
            },
            "status": enrollment.status,
            "enrollment_date": enrollment.enrollment_date.isoformat(),
        }
        for enrollment in enrollments
    ]
    return JsonResponse(data, safe=False)


@login_required
def api_session_list(request, course_slug):
    """API endpoint for listing course sessions."""
    course = get_object_or_404(Course, slug=course_slug)
    sessions = course.sessions.all()
    data = [
        {
            "id": session.id,
            "title": session.title,
            "description": session.description,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat(),
            "is_virtual": session.is_virtual,
        }
        for session in sessions
    ]
    return JsonResponse(data, safe=False)


@login_required
def api_session_detail(request, pk):
    """API endpoint for session details."""
    session = get_object_or_404(Session, pk=pk)
    data = {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat(),
        "is_virtual": session.is_virtual,
        "meeting_link": session.meeting_link if session.is_virtual else None,
        "location": session.location if not session.is_virtual else None,
    }
    return JsonResponse(data)


@login_required
def api_forum_topic_create(request):
    """API endpoint for creating forum topics."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    data = json.loads(request.body)
    category = get_object_or_404(ForumCategory, id=data["category"])
    topic = ForumTopic.objects.create(
        title=data["title"],
        content=data["content"],
        category=category,
        author=request.user,
    )
    return JsonResponse(
        {
            "id": topic.id,
            "title": topic.title,
        },
        status=201,
    )


@login_required
def api_forum_reply_create(request):
    """API endpoint for creating forum replies."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    data = json.loads(request.body)
    topic = get_object_or_404(ForumTopic, id=data["topic"])
    reply = ForumReply.objects.create(
        topic=topic,
        content=data["content"],
        author=request.user,
    )
    return JsonResponse(
        {
            "id": reply.id,
            "content": reply.content,
        },
        status=201,
    )


@login_required
def session_detail(request, session_id):
    try:
        session = get_object_or_404(Session, id=session_id)

        # Check access rights
        if not (
            request.user == session.course.teacher
            or request.user.enrollments.filter(course=session.course, status="approved").exists()
        ):
            return HttpResponseForbidden("You don't have access to this session")

        context = {
            "session": session,
            "is_teacher": request.user == session.course.teacher,
            "now": timezone.now(),
        }

        return render(request, "web/study/session_detail.html", context)

    except Session.DoesNotExist:
        messages.error(request, "Session not found")
        return redirect("course_search")
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, "An error occurred while loading the session")
        return redirect("index")


def blog_list(request):
    blog_posts = BlogPost.objects.filter(status="published").order_by("-published_at")
    tags = BlogPost.objects.values_list("tags", flat=True).distinct()
    # Split comma-separated tags and get unique values
    unique_tags = sorted(set(tag.strip() for tags_str in tags if tags_str for tag in tags_str.split(",")))

    return render(request, "blog/list.html", {"blog_posts": blog_posts, "tags": unique_tags})


def blog_tag(request, tag):
    """View for filtering blog posts by tag."""
    blog_posts = BlogPost.objects.filter(status="published", tags__icontains=tag).order_by("-published_at")
    tags = BlogPost.objects.values_list("tags", flat=True).distinct()
    # Split comma-separated tags and get unique values
    unique_tags = sorted(set(tag.strip() for tags_str in tags if tags_str for tag in tags_str.split(",")))

    return render(request, "blog/list.html", {"blog_posts": blog_posts, "tags": unique_tags, "current_tag": tag})


@login_required
def create_blog_post(request):
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Blog post created successfully!")
            return redirect("blog_detail", slug=post.slug)
    else:
        form = BlogPostForm()

    return render(request, "blog/create.html", {"form": form})


def blog_detail(request, slug):
    """Display a blog post and its comments."""
    post = get_object_or_404(BlogPost, slug=slug, status="published")
    comments = post.comments.filter(is_approved=True).order_by("created_at")

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to comment.")
            return redirect("account_login")

        comment_content = request.POST.get("content")
        if comment_content:
            comment = BlogComment.objects.create(
                post=post, author=request.user, content=comment_content, is_approved=True  # Auto-approve for now
            )
            messages.success(request, f"Comment #{comment.id} added successfully!")
            return redirect("blog_detail", slug=slug)

    # Get view count from WebRequest
    view_count = WebRequest.objects.filter(path=request.path).aggregate(total_views=Sum("count"))["total_views"] or 0

    context = {
        "post": post,
        "comments": comments,
        "view_count": view_count,
    }
    return render(request, "blog/detail.html", context)


@login_required
def student_dashboard(request):
    """
    Dashboard view for students showing enrollments, progress, upcoming sessions, learning streak,
    and an Achievements section.
    """

    # Update the learning streak.
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    streak.update_streak()

    enrollments = Enrollment.objects.filter(student=request.user).select_related("course")
    upcoming_sessions = Session.objects.filter(
        course__enrollments__student=request.user, start_time__gt=timezone.now()
    ).order_by("start_time")[:5]

    progress_data = []
    total_progress = 0
    for enrollment in enrollments:
        progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
        progress_data.append(
            {
                "enrollment": enrollment,
                "progress": progress,
            }
        )
        total_progress += progress.completion_percentage

    avg_progress = round(total_progress / len(progress_data)) if progress_data else 0

    # Query achievements for the user.
    achievements = Achievement.objects.filter(student=request.user).order_by("-awarded_at")

    context = {
        "enrollments": enrollments,
        "upcoming_sessions": upcoming_sessions,
        "progress_data": progress_data,
        "avg_progress": avg_progress,
        "streak": streak,
        "achievements": achievements,
    }
    return render(request, "dashboard/student.html", context)


@login_required
@teacher_required
def teacher_dashboard(request):
    """Dashboard view for teachers showing their courses, student progress, and upcoming sessions."""
    courses = Course.objects.filter(teacher=request.user)
    upcoming_sessions = Session.objects.filter(course__teacher=request.user, start_time__gt=timezone.now()).order_by(
        "start_time"
    )[:5]

    # Get enrollment and progress stats for each course
    course_stats = []
    total_students = 0
    total_completed = 0
    total_earnings = Decimal("0.00")
    for course in courses:
        enrollments = course.enrollments.filter(status="approved")
        course_total_students = enrollments.count()
        course_completed = enrollments.filter(status="completed").count()
        total_students += course_total_students
        total_completed += course_completed
        # Calculate earnings (90% of course price for each enrollment, 10% platform fee)
        course_earnings = Decimal(str(course_total_students)) * course.price * Decimal("0.9")
        total_earnings += course_earnings
        course_stats.append(
            {
                "course": course,
                "total_students": course_total_students,
                "completed": course_completed,
                "completion_rate": (course_completed / course_total_students * 100) if course_total_students > 0 else 0,
                "earnings": course_earnings,
            }
        )

    # Get the teacher's storefront if it exists
    storefront = Storefront.objects.filter(teacher=request.user).first()

    context = {
        "courses": courses,
        "upcoming_sessions": upcoming_sessions,
        "course_stats": course_stats,
        "total_students": total_students,
        "completion_rate": (total_completed / total_students * 100) if total_students > 0 else 0,
        "total_earnings": round(total_earnings, 2),
        "storefront": storefront,
    }
    return render(request, "dashboard/teacher.html", context)


def custom_404(request, exception):
    """Custom 404 error handler"""
    return render(request, "404.html", status=404)


def custom_500(request):
    """Custom 500 error handler"""
    return render(request, "500.html", status=500)


def custom_429(request, exception=None):
    """Custom 429 error page."""
    return render(request, "429.html", status=429)


def cart_view(request):
    """View the shopping cart."""
    cart = get_or_create_cart(request)
    return render(request, "cart/cart.html", {"cart": cart, "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY})


def add_course_to_cart(request, course_id):
    """Add a course to the cart."""
    course = get_object_or_404(Course, id=course_id)
    cart = get_or_create_cart(request)

    # Try to get or create the cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, course=course, defaults={"session": None})

    if created:
        messages.success(request, f"{course.title} added to cart.")
    else:
        messages.info(request, f"{course.title} is already in your cart.")

    return redirect("cart_view")


def add_session_to_cart(request, session_id):
    """Add an individual session to the cart."""
    session = get_object_or_404(Session, id=session_id)
    cart = get_or_create_cart(request)

    # Try to get or create the cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, session=session, defaults={"course": None})

    if created:
        messages.success(request, f"{session.title} added to cart.")
    else:
        messages.info(request, f"{session.title} is already in your cart.")

    return redirect("cart_view")


def remove_from_cart(request, item_id):
    """Remove an item from the shopping cart."""
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect("cart_view")


def create_cart_payment_intent(request):
    """Create a payment intent for the entire cart."""
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    try:
        # Create a PaymentIntent with the cart total
        intent = stripe.PaymentIntent.create(
            amount=int(cart.total * 100),  # Convert to cents
            currency="usd",
            metadata={
                "cart_id": cart.id,
                "user_id": request.user.id if request.user.is_authenticated else None,
                "session_key": request.session.session_key if not request.user.is_authenticated else None,
            },
        )
        return JsonResponse({"clientSecret": intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=403)


def checkout_success(request):
    """Handle successful checkout and payment confirmation."""
    payment_intent_id = request.GET.get("payment_intent")

    if not payment_intent_id:
        messages.error(request, "No payment information found.")
        return redirect("cart_view")

    try:
        # Verify the payment intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if payment_intent.status != "succeeded":
            messages.error(request, "Payment was not successful.")
            return redirect("cart_view")

        cart = get_or_create_cart(request)

        if not cart.items.exists():
            messages.error(request, "Cart is empty.")
            return redirect("cart_view")

        # Handle guest checkout
        if not request.user.is_authenticated:
            email = payment_intent.receipt_email
            if not email:
                messages.error(request, "No email provided for guest checkout.")
                return redirect("cart_view")

            # Create a new user account with transaction and better username generation
            with transaction.atomic():
                base_username = email.split("@")[0][:15]  # Limit length
                timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
                username = f"{base_username}_{timestamp}"

                # In the unlikely case of a collision, append random string
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{timestamp}_{get_random_string(4)}"

                # Create the user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=get_random_string(length=32),  # Random password for reset
                )

                # Associate the cart with the new user
                cart.user = user
                cart.session_key = ""  # Empty string instead of None
                cart.save()

                # Send welcome email with password reset link
                send_welcome_email(user)

                # Log in the new user
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        else:
            user = request.user

        # Lists to track enrollments for the receipt
        enrollments = []
        session_enrollments = []
        goods_items = []
        total_amount = 0

        # Define shipping_address
        shipping_address = request.POST.get("address") if cart.has_goods else None

        # Check if the cart contains goods requiring shipping
        has_goods = any(item.goods for item in cart.items.all())

        # Extract shipping address from Stripe PaymentIntent
        shipping_address = None
        if has_goods:
            shipping_data = getattr(payment_intent, "shipping", None)
            if shipping_data:
                # Construct structured shipping address
                shipping_address = {
                    "line1": shipping_data.address.line1,
                    "line2": shipping_data.address.line2 or "",
                    "city": shipping_data.address.city,
                    "state": shipping_data.address.state,
                    "postal_code": shipping_data.address.postal_code,
                    "country": shipping_data.address.country,
                }

        # Create the Order with shipping address
        order = Order.objects.create(
            user=user,  # User is defined earlier in guest/auth logic
            total_price=0,  # Updated later
            status="completed",
            shipping_address=shipping_address,
            terms_accepted=True,
        )

        storefront = None
        # Process enrollments
        for item in cart.items.all():
            if item.course:
                # Create enrollment for full course
                enrollment = Enrollment.objects.create(
                    student=user, course=item.course, status="approved", payment_intent_id=payment_intent_id
                )
                # Create progress tracker
                CourseProgress.objects.create(enrollment=enrollment)
                enrollments.append(enrollment)
                total_amount += item.course.price

                # Send confirmation emails
                send_enrollment_confirmation(enrollment)
                notify_teacher_new_enrollment(enrollment)

            elif item.session:
                # Create enrollment for individual session
                session_enrollment = SessionEnrollment.objects.create(
                    student=user, session=item.session, status="approved", payment_intent_id=payment_intent_id
                )
                session_enrollments.append(session_enrollment)
                total_amount += item.session.price

            elif item.goods:
                # Track goods items for the receipt
                goods_items.append(item)
                total_amount += item.final_price

                # Create order item for goods
                OrderItem.objects.create(
                    order=order,
                    goods=item.goods,
                    quantity=1,
                    price_at_purchase=item.goods.price,
                    discounted_price_at_purchase=item.goods.discount_price,
                )
                # Capture storefront from the first goods item
                if not storefront:
                    storefront = item.goods.storefront

        # Update order details
        order.total_price = total_amount
        if storefront:
            order.storefront = goods_items[0].goods.storefront
        order.save()

        # Clear the cart
        cart.items.all().delete()

        if storefront:
            order.storefront = storefront
            order.save(update_fields=["storefront"])

        # Render the receipt page
        return render(
            request,
            "cart/receipt.html",
            {
                "payment_intent_id": payment_intent_id,
                "order_date": timezone.now(),
                "user": user,
                "enrollments": enrollments,
                "session_enrollments": session_enrollments,
                "goods_items": goods_items,
                "total": total_amount,
                "order": order,
                "shipping_address": shipping_address,
            },
        )

    except stripe.error.StripeError as e:
        # send slack message
        send_slack_message(f"Payment verification failed: {str(e)}")
        messages.error(request, f"Payment verification failed: {str(e)}")
        return redirect("cart_view")
    except Exception as e:
        # send slack message
        send_slack_message(f"Failed to process checkout: {str(e)}")
        messages.error(request, f"Failed to process checkout: {str(e)}")
        return redirect("cart_view")


def send_welcome_email(user):
    """Send welcome email to newly created users after guest checkout."""
    if not user.email:
        raise ValueError("User must have an email address to send welcome email")

    reset_url = reverse("account_reset_password")
    context = {
        "user": user,
        "reset_url": reset_url,
    }

    html_message = render_to_string("emails/welcome_guest.html", context)
    text_message = render_to_string("emails/welcome_guest.txt", context)

    send_mail(
        subject="Welcome to Your New Learning Account",
        message=text_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@login_required
def edit_session(request, session_id):
    """Edit an existing session."""
    # Get the session and verify that the current user is the course teacher
    session = get_object_or_404(Session, id=session_id)
    course = session.course

    # Check if user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can edit sessions!")
        return redirect("course_detail", slug=course.slug)

    if request.method == "POST":
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Session updated successfully!")
            return redirect("course_detail", slug=session.course.slug)
    else:
        form = SessionForm(instance=session)

    return render(
        request, "courses/session_form.html", {"form": form, "session": session, "course": course, "is_edit": True}
    )


@login_required
def invite_student(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Check if user is the teacher of this course
    if course.teacher != request.user:
        messages.error(request, "You are not authorized to invite students to this course.")
        return redirect("course_detail", slug=course.slug)

    if request.method == "POST":
        form = InviteStudentForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            message = form.cleaned_data.get("message", "")

            # Generate course URL
            course_url = request.build_absolute_uri(reverse("course_detail", args=[course.slug]))

            # Send invitation email
            context = {
                "course": course,
                "teacher": request.user,
                "message": message,
                "course_url": course_url,
            }
            html_message = render_to_string("emails/course_invitation.html", context)
            text_message = f"""
You have been invited to join {course.title}!

Message from {request.user.get_full_name() or request.user.username}:
{message}

Course Price: ${course.price}

Click here to view the course: {course_url}
"""

            try:
                send_mail(
                    f"Invitation to join {course.title}",
                    text_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message,
                )
                messages.success(request, f"Invitation sent to {email}")
                return redirect("course_detail", slug=course.slug)
            except Exception:
                messages.error(request, "Failed to send invitation email. Please try again.")
    else:
        form = InviteStudentForm()

    context = {
        "course": course,
        "form": form,
    }
    return render(request, "courses/invite.html", context)


def terms(request):
    """Display the terms of service page."""
    return render(request, "terms.html")


@login_required
@teacher_required
def stripe_connect_onboarding(request):
    """Start the Stripe Connect onboarding process for teachers."""
    if not request.user.profile.is_teacher:
        messages.error(request, "Only teachers can set up payment accounts.")
        return redirect("profile")

    try:
        if not request.user.profile.stripe_account_id:
            # Create a new Stripe Connect account
            account = stripe.Account.create(
                type="express",
                country="US",
                email=request.user.email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            )

            # Save the account ID to the user's profile
            request.user.profile.stripe_account_id = account.id
            request.user.profile.save()

        # Create an account link for onboarding
        account_link = stripe.AccountLink.create(
            account=request.user.profile.stripe_account_id,
            refresh_url=request.build_absolute_uri(reverse("stripe_connect_onboarding")),
            return_url=request.build_absolute_uri(reverse("profile")),
            type="account_onboarding",
        )

        return redirect(account_link.url)

    except stripe.error.StripeError as e:
        messages.error(request, f"Failed to set up Stripe account: {str(e)}")
        return redirect("profile")


@csrf_exempt
def stripe_connect_webhook(request):
    """Handle Stripe Connect account updates."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_CONNECT_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event.type == "account.updated":
        account = event.data.object
        try:
            profile = Profile.objects.get(stripe_account_id=account.id)
            if account.charges_enabled and account.payouts_enabled:
                profile.stripe_account_status = "verified"
            else:
                profile.stripe_account_status = "pending"
            profile.save()
        except Profile.DoesNotExist:
            return HttpResponse(status=404)

    return HttpResponse(status=200)


@login_required
def create_forum_category(request):
    """Create a new forum category."""
    if request.method == "POST":
        form = ForumCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            if not category.slug:
                category.slug = slugify(category.name)
            category.save()
            messages.success(request, f"Forum category '{category.name}' created successfully!")
            return redirect("forum_category", slug=category.slug)
    else:
        form = ForumCategoryForm()
        print(form.errors)

    return render(request, "web/forum/create_category.html", {"form": form})


@login_required
def edit_topic(request, topic_id):
    """Edit an existing forum topic."""
    topic = get_object_or_404(ForumTopic, id=topic_id, author=request.user)
    categories = ForumCategory.objects.all()

    if request.method == "POST":
        form = ForumTopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.success(request, "Topic updated successfully!")
            return redirect("forum_topic", category_slug=topic.category.slug, topic_id=topic.id)
    else:
        form = ForumTopicForm(instance=topic)

    return render(request, "web/forum/edit_topic.html", {"topic": topic, "form": form, "categories": categories})


@login_required
def my_forum_topics(request):
    """Display all forum topics created by the current user."""
    topics = ForumTopic.objects.filter(author=request.user).order_by("-created_at")
    categories = ForumCategory.objects.all()
    return render(request, "web/forum/my_topics.html", {"topics": topics, "categories": categories})


@login_required
def my_forum_replies(request):
    """Display all forum replies created by the current user."""
    replies = (
        ForumReply.objects.filter(author=request.user)
        .select_related("topic", "topic__category")
        .order_by("-created_at")
    )
    categories = ForumCategory.objects.all()
    return render(request, "web/forum/my_replies.html", {"replies": replies, "categories": categories})


@login_required
def edit_reply(request, reply_id):
    """Edit a forum reply."""
    reply = get_object_or_404(ForumReply, id=reply_id, author=request.user)
    topic = reply.topic
    categories = ForumCategory.objects.all()

    if request.method == "POST":
        content = request.POST.get("content")
        if content:
            reply.content = content
            reply.save()
            messages.success(request, "Reply updated successfully.")
            return redirect("forum_topic", category_slug=topic.category.slug, topic_id=topic.id)

    return render(request, "web/forum/edit_reply.html", {"reply": reply, "categories": categories})


def get_course_calendar(request, slug):
    """AJAX endpoint to get calendar data for a course."""
    course = get_object_or_404(Course, slug=slug)
    today = timezone.now().date()
    calendar_weeks = []

    # Get current month and year from query parameters
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    current_month = timezone.datetime(year, month, 1).date()

    # Get previous and next month for navigation
    if month == 1:
        prev_month = {"year": year - 1, "month": 12}
    else:
        prev_month = {"year": year, "month": month - 1}

    if month == 12:
        next_month = {"year": year + 1, "month": 1}
    else:
        next_month = {"year": year, "month": month + 1}

    # Get sessions for the current month
    month_sessions = course.sessions.filter(start_time__year=year, start_time__month=month).order_by("start_time")

    # Generate calendar data
    cal = calendar.monthcalendar(year, month)

    for week in cal:
        calendar_week = []
        for day in week:
            if day == 0:
                calendar_week.append({"date": None, "has_session": False, "is_today": False})
            else:
                date = timezone.datetime(year, month, day).date()
                sessions_on_day = [s for s in month_sessions if s.start_time.date() == date]
                calendar_week.append(
                    {
                        "date": date.isoformat() if date else None,
                        "has_session": bool(sessions_on_day),
                        "is_today": date == today,
                    }
                )
        calendar_weeks.append(calendar_week)

    data = {
        "calendar_weeks": calendar_weeks,
        "current_month": current_month.strftime("%B %Y"),
        "prev_month": prev_month,
        "next_month": next_month,
    }

    return JsonResponse(data)


@login_required
def create_calendar(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        try:
            month = int(request.POST.get("month"))
            year = int(request.POST.get("year"))

            # Validate month is between 0-11
            if not 0 <= month <= 11:
                return JsonResponse({"success": False, "error": "Month must be between 0 and 11"}, status=400)

            calendar = EventCalendar.objects.create(
                title=title, description=description, creator=request.user, month=month, year=year
            )

            return JsonResponse({"success": True, "calendar_id": calendar.id, "share_token": calendar.share_token})
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "error": "Invalid month or year"}, status=400)

    return render(request, "calendar/create.html")


def view_calendar(request, share_token):
    calendar = get_object_or_404(EventCalendar, share_token=share_token)
    return render(request, "calendar/view.html", {"calendar": calendar})


@require_POST
def add_time_slot(request, share_token):
    try:
        with transaction.atomic():
            calendar = get_object_or_404(EventCalendar, share_token=share_token)
            name = request.POST.get("name")
            day = int(request.POST.get("day"))
            start_time = request.POST.get("start_time")
            end_time = request.POST.get("end_time")

            # Create the time slot
            TimeSlot.objects.create(calendar=calendar, name=name, day=day, start_time=start_time, end_time=end_time)

            return JsonResponse({"success": True})
    except IntegrityError:
        return JsonResponse({"success": False, "error": "You already have a time slot for this day"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_POST
def remove_time_slot(request, share_token):
    calendar = get_object_or_404(EventCalendar, share_token=share_token)
    name = request.POST.get("name")
    day = int(request.POST.get("day"))

    TimeSlot.objects.filter(calendar=calendar, name=name, day=day).delete()

    return JsonResponse({"success": True})


@require_GET
def get_calendar_data(request, share_token):
    calendar = get_object_or_404(EventCalendar, share_token=share_token)
    slots = TimeSlot.objects.filter(calendar=calendar)

    data = {
        "title": calendar.title,
        "description": calendar.description,
        "month": calendar.month,
        "year": calendar.year,
        "slots": [
            {
                "name": slot.name,
                "day": slot.day,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
            }
            for slot in slots
        ],
    }

    return JsonResponse(data)


def system_status(request):
    """Check system status including SendGrid API connectivity and disk space usage."""
    status = {
        "sendgrid": {"status": "unknown", "message": "", "api_key_configured": False},
        "disk_space": {"status": "unknown", "message": "", "usage": {}},
        "timestamp": timezone.now(),
    }

    # Check SendGrid
    sendgrid_api_key = os.getenv("SENDGRID_PASSWORD")
    if sendgrid_api_key:
        status["sendgrid"]["api_key_configured"] = True
        try:
            print("Checking SendGrid API...")
            response = requests.get(
                "https://api.sendgrid.com/v3/user/account",
                headers={"Authorization": f"Bearer {sendgrid_api_key}"},
                timeout=5,
            )
            if response.status_code == 200:
                status["sendgrid"]["status"] = "ok"
                status["sendgrid"]["message"] = "Successfully connected to SendGrid API"
            else:
                status["sendgrid"]["status"] = "error"
                status["sendgrid"]["message"] = f"Unexpected response: {response.status_code}"
        except requests.exceptions.RequestException as e:
            status["sendgrid"]["status"] = "error"
            status["sendgrid"]["message"] = f"API Error: {str(e)}"
    else:
        status["sendgrid"]["status"] = "error"
        status["sendgrid"]["message"] = "SendGrid API key not configured"

    # Check disk space
    try:
        total, used, free = shutil.disk_usage("/")
        total_gb = total / (2**30)  # Convert to GB
        used_gb = used / (2**30)
        free_gb = free / (2**30)
        usage_percent = (used / total) * 100

        status["disk_space"]["usage"] = {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent": round(usage_percent, 1),
        }

        # Set status based on usage percentage
        if usage_percent >= 90:
            status["disk_space"]["status"] = "error"
            status["disk_space"]["message"] = "Critical: Disk usage above 90%"
        elif usage_percent >= 80:
            status["disk_space"]["status"] = "warning"
            status["disk_space"]["message"] = "Warning: Disk usage above 80%"
        else:
            status["disk_space"]["status"] = "ok"
            status["disk_space"]["message"] = "Disk space usage is normal"
    except Exception as e:
        status["disk_space"]["status"] = "error"
        status["disk_space"]["message"] = f"Error checking disk space: {str(e)}"

    return render(request, "status.html", {"status": status})


@login_required
@teacher_required
def message_enrolled_students(request, slug):
    """Send an email to all enrolled students in a course."""
    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")

        if title and message:
            # Get all enrolled students
            enrolled_students = User.objects.filter(
                enrollments__course=course, enrollments__status="approved"
            ).distinct()

            # Send email to each student
            for student in enrolled_students:
                send_mail(
                    subject=f"[{course.title}] {title}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    fail_silently=True,
                )

            messages.success(request, "Email sent successfully to all enrolled students!")
            return redirect("course_detail", slug=slug)
        else:
            messages.error(request, "Both title and message are required!")

    return render(request, "courses/message_students.html", {"course": course})


def message_teacher(request, teacher_id):
    """Send a message to a teacher."""
    teacher = get_object_or_404(get_user_model(), id=teacher_id)
    if not teacher.profile.is_teacher:
        messages.error(request, "This user is not a teacher.")
        return redirect("index")

    if request.method == "POST":
        form = MessageTeacherForm(request.POST, user=request.user)
        if form.is_valid():
            # Prepare email content
            if request.user.is_authenticated:
                sender_name = request.user.get_full_name() or request.user.username
                sender_email = request.user.email
            else:
                sender_name = form.cleaned_data["name"]
                sender_email = form.cleaned_data["email"]

            # Send email to teacher
            context = {
                "sender_name": sender_name,
                "sender_email": sender_email,
                "message": form.cleaned_data["message"],
            }
            html_message = render_to_string("web/emails/teacher_message.html", context)

            try:
                send_mail(
                    subject=f"New message from {sender_name}",
                    message=form.cleaned_data["message"],
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[teacher.email],
                    html_message=html_message,
                )
                messages.success(request, "Your message has been sent successfully!")

                # Get the next URL from query params, default to course search if not provided
                next_url = request.GET.get("next")
                if next_url:
                    try:
                        return redirect("course_detail", slug=next_url)
                    except NoReverseMatch:
                        pass
                return redirect("course_search")
            except Exception as e:
                messages.error(request, f"Failed to send message: {str(e)}")
                return redirect("message_teacher", teacher_id=teacher_id)
    else:
        form = MessageTeacherForm(user=request.user)

    return render(
        request,
        "web/message_teacher.html",
        {
            "form": form,
            "teacher": teacher,
        },
    )


@login_required
def confirm_rolled_sessions(request, course_slug):
    """View for teachers to confirm rolled over session dates."""
    course = get_object_or_404(Course, slug=course_slug, teacher=request.user)

    # Get all rolled over but unconfirmed sessions
    rolled_sessions = course.sessions.filter(is_rolled_over=True, teacher_confirmed=False).order_by("start_time")

    if request.method == "POST":
        session_ids = request.POST.getlist("confirm_sessions")
        if session_ids:
            # Confirm selected sessions
            course.sessions.filter(id__in=session_ids).update(teacher_confirmed=True)
            messages.success(request, "Selected sessions have been confirmed.")

            # Reset rollover status for unselected sessions
            unselected_sessions = rolled_sessions.exclude(id__in=session_ids)
            for session in unselected_sessions:
                session.start_time = session.original_start_time
                session.end_time = session.original_end_time
                session.is_rolled_over = False
                session.save()

            messages.info(request, "Unselected sessions have been reset to their original dates.")

        return redirect("course_detail", slug=course_slug)

    return render(
        request,
        "courses/confirm_rolled_sessions.html",
        {
            "course": course,
            "rolled_sessions": rolled_sessions,
        },
    )


def feedback(request):
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            # Send feedback notification to admin
            name = form.cleaned_data.get("name", "Anonymous")
            email = form.cleaned_data.get("email", "Not provided")
            description = form.cleaned_data["description"]

            # Send to Slack if webhook URL is configured
            if settings.SLACK_WEBHOOK_URL:
                message = f"*New Feedback*\nFrom: {name}\nEmail: {email}\n\n{description}"
                send_slack_message(message)

            messages.success(request, "Thank you for your feedback! We appreciate your input.")
            return redirect("feedback")
    else:
        form = FeedbackForm()

    return render(request, "feedback.html", {"form": form})


def content_dashboard(request):
    # Get current time and thresholds
    now = timezone.now()
    month_ago = now - timedelta(days=30)

    def get_status(date, threshold_days=None):
        if not date:
            return "neutral"
        if not threshold_days:
            return "success"
        threshold = now - timedelta(days=threshold_days)
        if date >= threshold:
            return "success"
        elif date >= (threshold - timedelta(days=threshold_days)):
            return "warning"
        return "danger"

    # Web traffic stats
    web_stats = {
        "total_views": WebRequest.objects.aggregate(total=Sum("count"))["total"] or 0,
        "unique_visitors": WebRequest.objects.values("ip_address").distinct().count(),
        "date": WebRequest.objects.order_by("-created").first().created if WebRequest.objects.exists() else None,
    }
    web_stats["status"] = get_status(web_stats["date"])

    # Generate traffic data for chart (last 30 days)
    traffic_data = []
    for i in range(30):
        date = now - timedelta(days=i)
        day_views = WebRequest.objects.filter(created__date=date.date()).aggregate(total=Sum("count"))["total"] or 0
        traffic_data.append({"date": date.strftime("%Y-%m-%d"), "views": day_views})
    traffic_data.reverse()  # Most recent last for chart

    # Blog stats
    blog_stats = {
        "posts": BlogPost.objects.filter(status="published").count(),
        "views": (WebRequest.objects.filter(path__startswith="/blog/").aggregate(total=Sum("count"))["total"] or 0),
        "date": (
            BlogPost.objects.filter(status="published").order_by("-published_at").first().published_at
            if BlogPost.objects.exists()
            else None
        ),
    }
    blog_stats["status"] = get_status(blog_stats["date"], 7)

    # Forum stats
    forum_stats = {
        "topics": ForumTopic.objects.count(),
        "replies": ForumReply.objects.count(),
        "date": ForumTopic.objects.order_by("-created_at").first().created_at if ForumTopic.objects.exists() else None,
    }
    forum_stats["status"] = get_status(forum_stats["date"], 1)  # 1 day threshold

    # Course stats
    course_stats = {
        "active": Course.objects.filter(status="published").count(),
        "students": Enrollment.objects.filter(status="approved").count(),
        "date": Course.objects.order_by("-created_at").first().created_at if Course.objects.exists() else None,
    }
    course_stats["status"] = get_status(course_stats["date"], 30)  # 1 month threshold

    # User stats
    user_stats = {
        "total": User.objects.count(),
        "active": User.objects.filter(last_login__gte=month_ago).count(),
        "date": User.objects.order_by("-date_joined").first().date_joined if User.objects.exists() else None,
    }

    def get_status(date, threshold_days):
        if not date:
            return "danger"
        days_since = (now - date).days
        if days_since > threshold_days * 2:
            return "danger"
        elif days_since > threshold_days:
            return "warning"
        return "success"

    # Calculate overall health score
    connected_platforms = 0
    healthy_platforms = 0
    platforms_data = [
        (blog_stats["date"], 7),  # Blog: 1 week threshold
        (forum_stats["date"], 7),  # Forum: 1 week threshold
        (course_stats["date"], 7),  # Courses: 1 week threshold
        (user_stats["date"], 7),  # Users: 1 week threshold
    ]

    for date, threshold in platforms_data:
        if date:
            connected_platforms += 1
            if get_status(date, threshold) != "danger":
                healthy_platforms += 1

    overall_score = int((healthy_platforms / max(connected_platforms, 1)) * 100)

    # Get social media stats
    social_stats = get_social_stats()
    content_data = {
        "blog": {
            "stats": blog_stats,
            "status": get_status(blog_stats["date"], 7),
            "date": blog_stats["date"],
        },
        "forum": {
            "stats": forum_stats,
            "status": get_status(forum_stats["date"], 7),
            "date": forum_stats["date"],
        },
        "courses": {
            "stats": course_stats,
            "status": get_status(course_stats["date"], 7),
            "date": course_stats["date"],
        },
        "users": {
            "stats": user_stats,
            "status": get_status(user_stats["date"], 7),
            "date": user_stats["date"],
        },
    }

    # Add social media stats
    content_data.update(social_stats)

    return render(
        request,
        "web/dashboard/content_status.html",
        {
            "content_data": content_data,
            "overall_score": overall_score,
            "web_stats": web_stats,
            "traffic_data": json.dumps(traffic_data),
            "blog_stats": blog_stats,
            "forum_stats": forum_stats,
            "course_stats": course_stats,
            "user_stats": user_stats,
        },
    )


# Challenges views
def current_weekly_challenge(request):
    current_time = timezone.now()
    weekly_challenge = Challenge.objects.filter(
        challenge_type="weekly", start_date__lte=current_time, end_date__gte=current_time
    ).first()

    one_time_challenges = Challenge.objects.filter(
        challenge_type="one_time", start_date__lte=current_time, end_date__gte=current_time
    )
    user_submissions = {}
    if request.user.is_authenticated:
        # Get all active challenges
        all_challenges = []
        if weekly_challenge:
            all_challenges.append(weekly_challenge)
            all_challenges.extend(list(one_time_challenges))

        # Get all submissions for active challenges
        if all_challenges:
            submissions = ChallengeSubmission.objects.filter(user=request.user, challenge__in=all_challenges)
            # Create a dictionary mapping challenge IDs to submissions
            for submission in submissions:
                user_submissions[submission.challenge_id] = submission

    return render(
        request,
        "web/current_weekly_challenge.html",
        {
            "current_challenge": weekly_challenge,
            "one_time_challenges": one_time_challenges,
            "user_submissions": user_submissions if request.user.is_authenticated else {},
        },
    )


def challenge_detail(request, challenge_id):
    try:
        challenge = get_object_or_404(Challenge, id=challenge_id)
        submissions = ChallengeSubmission.objects.filter(challenge=challenge)
        # Check if the current user has submitted this challenge
        user_submission = None
        if request.user.is_authenticated:
            user_submission = ChallengeSubmission.objects.filter(user=request.user, challenge=challenge).first()

        return render(
            request,
            "web/challenge_detail.html",
            {"challenge": challenge, "submissions": submissions, "user_submission": user_submission},
        )
    except Http404:
        # Redirect to weekly challenges list if specific challenge not found
        messages.info(request, "Challenge not found. Returning to challenges list.")
        return redirect("current_weekly_challenge")


@login_required
def challenge_submit(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    # Check if the user has already submitted this challenge
    existing_submission = ChallengeSubmission.objects.filter(user=request.user, challenge=challenge).first()

    if existing_submission:
        return redirect("challenge_detail", challenge_id=challenge_id)

    if request.method == "POST":
        form = ChallengeSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.challenge = challenge
            submission.save()
            messages.success(request, "Your submission has been recorded!")
            return redirect("challenge_detail", challenge_id=challenge_id)
    else:
        form = ChallengeSubmissionForm()

    return render(request, "web/challenge_submit.html", {"challenge": challenge, "form": form})


@require_GET
def fetch_video_title(request):
    """
    Fetch video title from a URL with proper security measures to prevent SSRF attacks.
    """
    url = request.GET.get("url")
    if not url:
        return JsonResponse({"error": "URL parameter is required"}, status=400)

    # Validate URL
    try:
        parsed_url = urlparse(url)

        # Check for scheme - only allow http and https
        if parsed_url.scheme not in ["http", "https"]:
            return JsonResponse({"error": "Invalid URL scheme. Only HTTP and HTTPS are supported."}, status=400)

        # Check for private/internal IP addresses
        if parsed_url.netloc:
            hostname = parsed_url.netloc.split(":")[0]

            # Block localhost variations and common internal domains
            blocked_hosts = [
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
                "internal",
                "intranet",
                "local",
                "lan",
                "corp",
                "private",
                "::1",
            ]

            if any(blocked in hostname.lower() for blocked in blocked_hosts):
                return JsonResponse({"error": "Access to internal networks is not allowed"}, status=403)

            # Resolve hostname to IP and check if it's private
            try:
                ip_address = socket.gethostbyname(hostname)
                ip_obj = ipaddress.ip_address(ip_address)

                # Check if the IP is private/internal
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
                    return JsonResponse({"error": "Access to internal/private networks is not allowed"}, status=403)
            except (socket.gaierror, ValueError):
                # If hostname resolution fails or IP parsing fails, continue
                pass

    except Exception as e:
        return JsonResponse({"error": f"Invalid URL format: {str(e)}"}, status=400)

    # Set a timeout to prevent hanging requests
    timeout = 5  # seconds

    try:
        # Only allow HEAD and GET methods with limited redirects
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": "Educational-Website-Validator/1.0",
            },
        )
        response.raise_for_status()

        # Extract title from response headers or content
        title = response.headers.get("title", "")
        if not title:
            # Try to extract title from HTML content
            content = response.text
            title_match = re.search(r"<title>(.*?)</title>", content)
            title = title_match.group(1) if title_match else "Untitled Video"

            # Sanitize the title
            title = html.escape(title)

        return JsonResponse({"title": title})

    except requests.RequestException:
        return JsonResponse({"error": "Failed to fetch video title:"}, status=500)


def get_referral_stats():
    """Get statistics for top referrers."""
    return (
        Profile.objects.annotate(
            total_signups=Count("referrals"),
            total_enrollments=Count(
                "referrals__user__enrollments", filter=Q(referrals__user__enrollments__status="approved")
            ),
            total_clicks=Count(
                "referrals__user__webrequest", filter=Q(referrals__user__webrequest__path__contains="ref=")
            ),
        )
        .filter(total_signups__gt=0)
        .order_by("-total_signups")[:10]
    )


def referral_leaderboard(request):
    """Display the referral leaderboard."""
    top_referrers = get_referral_stats()
    return render(request, "web/referral_leaderboard.html", {"top_referrers": top_referrers})


# Goods Views
class GoodsListView(LoginRequiredMixin, generic.ListView):
    model = Goods
    template_name = "goods/goods_list.html"
    context_object_name = "products"

    def get_queryset(self):
        return Goods.objects.filter(storefront__teacher=self.request.user)


class GoodsDetailView(generic.DetailView):
    model = Goods
    template_name = "goods/goods_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_images"] = self.object.goods_images.all()  # Get all images related to the product
        context["other_products"] = Goods.objects.exclude(pk=self.object.pk)[:12]  # Fetch other products
        return context


class GoodsCreateView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Goods
    form_class = GoodsForm
    template_name = "goods/goods_form.html"

    def test_func(self):
        return hasattr(self.request.user, "storefront")

    def form_valid(self, form):
        form.instance.storefront = self.request.user.storefront
        images = self.request.FILES.getlist("images")
        product_type = form.cleaned_data.get("product_type")

        # Validate digital product images
        if product_type == "digital" and not images:
            form.add_error(None, "Digital products require at least one image")
            return self.form_invalid(form)

        # Validate image constraints
        if len(images) > 8:
            form.add_error(None, "Maximum 8 images allowed")
            return self.form_invalid(form)

        for img in images:
            if img.size > 5 * 1024 * 1024:
                form.add_error(None, f"{img.name} exceeds 5MB size limit")
                return self.form_invalid(form)

        # Save main product first
        super().form_valid(form)

        # Save images after product creation
        for image_file in images:
            ProductImage.objects.create(goods=self.object, image=image_file)

        return render(self.request, "goods/goods_create_success.html", {"product": self.object})

    def form_invalid(self, form):
        messages.error(self.request, f"Creation failed: {form.errors.as_text()}")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("goods_list")


class GoodsUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Goods
    form_class = GoodsForm
    template_name = "goods/goods_update.html"

    # Filter by user's products only
    def get_queryset(self):
        return Goods.objects.filter(storefront__teacher=self.request.user)

    # Verify ownership
    def test_func(self):
        return self.get_object().storefront.teacher == self.request.user

    def get_success_url(self):
        return reverse("goods_list")


class GoodsDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Goods
    template_name = "goods/goods_confirm_delete.html"
    success_url = reverse_lazy("goods_list")

    def test_func(self):
        return self.request.user == self.get_object().storefront.teacher


def add_goods_to_cart(request, pk):
    """Add a product (goods) to the cart."""
    product = get_object_or_404(Goods, pk=pk)

    # Prevent adding out-of-stock items
    if product.stock is None or product.stock <= 0:
        messages.error(request, f"{product.name} is out of stock and cannot be added to cart.")
        return redirect("goods_detail", pk=pk)  # Redirect back to product page

    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, goods=product, defaults={"session": None})

    if created:
        messages.success(request, f"{product.name} added to cart.")
    else:
        messages.info(request, f"{product.name} is already in your cart.")

    return redirect("cart_view")


class GoodsListingView(ListView):
    model = Goods
    template_name = "goods/goods_listing.html"
    context_object_name = "products"
    paginate_by = 15

    def get_queryset(self):
        queryset = Goods.objects.all()
        store_name = self.request.GET.get("store_name")
        product_type = self.request.GET.get("product_type")
        category = self.request.GET.get("category")
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")

        if store_name:
            queryset = queryset.filter(storefront__name__icontains=store_name)
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        if category:
            queryset = queryset.filter(category__icontains=category)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["store_names"] = Storefront.objects.values_list("name", flat=True).distinct()
        context["categories"] = Goods.objects.values_list("category", flat=True).distinct()
        return context


# Order Management
class OrderManagementView(LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = Order
    template_name = "orders/order_management.html"
    context_object_name = "orders"
    paginate_by = 20

    def test_func(self):
        storefront = get_object_or_404(Storefront, store_slug=self.kwargs["store_slug"])
        return self.request.user == storefront.teacher

    def get_queryset(self):
        queryset = Order.objects.filter(items__goods__storefront__store_slug=self.kwargs["store_slug"]).distinct()

        # Get status from request and filter
        selected_status = self.request.GET.get("status")
        if selected_status and selected_status != "all":
            queryset = queryset.filter(status=selected_status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Order.STATUS_CHOICES  # Directly from model
        context["selected_status"] = self.request.GET.get("status", "")
        return context


class OrderDetailView(LoginRequiredMixin, generic.DetailView):
    model = Order
    template_name = "orders/order_detail.html"
    context_object_name = "order"


@login_required
@require_POST
def update_order_status(request, item_id):
    order = get_object_or_404(Order, id=item_id, user=request.user)
    new_status = request.POST.get("status").lower()  # Convert to lowercase for consistency

    # Define allowed statuses inside the function
    VALID_STATUSES = ["draft", "pending", "processing", "shipped", "completed", "cancelled", "refunded"]

    if new_status not in VALID_STATUSES:
        messages.error(request, "Invalid status.")
        return redirect("order_detail", pk=item_id)

    order.status = new_status
    order.save()
    messages.success(request, "Order status updated successfully.")
    return redirect("order_detail", pk=item_id)


# Analytics
class StoreAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    template_name = "analytics/analytics_dashboard.html"

    def test_func(self):
        storefront = get_object_or_404(Storefront, store_slug=self.kwargs["store_slug"])
        return self.request.user == storefront.teacher

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        storefront = get_object_or_404(Storefront, store_slug=self.kwargs["store_slug"])

        # Store-specific analytics
        orders = Order.objects.filter(storefront=storefront, status="completed")

        context.update(
            {
                "total_sales": orders.count(),
                "total_revenue": orders.aggregate(Sum("total_price"))["total_price__sum"] or 0,
                "top_products": OrderItem.objects.filter(order__storefront=storefront)
                .values("goods__name")
                .annotate(total_sold=Sum("quantity"))
                .order_by("-total_sold")[:5],
                "storefront": storefront,
            }
        )
        return context


class AdminMerchAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    template_name = "analytics/admin_analytics.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Platform-wide analytics
        context.update(
            {
                "total_sales": Order.objects.filter(status="completed").count(),
                "total_revenue": Order.objects.filter(status="completed").aggregate(Sum("total_price"))[
                    "total_price__sum"
                ]
                or 0,
                "top_storefronts": Storefront.objects.annotate(total_sales=Count("goods__orderitem")).order_by(
                    "-total_sales"
                )[:5],
            }
        )
        return context


@login_required
def sales_analytics(request):
    """View for displaying sales analytics."""
    storefront = get_object_or_404(Storefront, teacher=request.user)

    # Get completed orders for this storefront
    orders = Order.objects.filter(storefront=storefront, status="completed")

    # Calculate metrics
    total_revenue = orders.aggregate(total=Sum("total_price"))["total"] or 0
    total_orders = orders.count()

    # Placeholder conversion rate (to be implemented properly later)
    conversion_rate = 0.00  # Temporary placeholder

    # Best selling products
    best_selling_products = (
        OrderItem.objects.filter(order__storefront=storefront)
        .values("goods__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )

    context = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "conversion_rate": conversion_rate,
        "best_selling_products": best_selling_products,
    }
    return render(request, "analytics/analytics_dashboard.html", context)


@login_required
def sales_data(request):
    # Get the user's storefront
    storefront = get_object_or_404(Storefront, teacher=request.user)

    # Define valid statuses for metrics (e.g., include "completed" and "shipped")
    valid_statuses = ["completed", "shipped"]
    orders = Order.objects.filter(storefront=storefront, status__in=valid_statuses)

    # Calculate total revenue
    total_revenue = orders.aggregate(total=Sum("total_price"))["total"] or 0

    # Calculate total orders
    total_orders = orders.count()

    # Calculate conversion rate (orders / visits * 100)
    total_visits = WebRequest.objects.filter(path__contains="ref=").count()  # Adjust based on visit tracking
    conversion_rate = (total_orders / total_visits * 100) if total_visits > 0 else 0.00

    # Get best-selling products
    best_selling_products = (
        OrderItem.objects.filter(order__storefront=storefront, order__status__in=valid_statuses)
        .values("goods__name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )

    # Prepare response data
    data = {
        "total_revenue": float(total_revenue),
        "total_orders": total_orders,
        "conversion_rate": round(conversion_rate, 2),
        "best_selling_products": list(best_selling_products),
    }
    return JsonResponse(data)


class StorefrontCreateView(LoginRequiredMixin, CreateView):
    model = Storefront
    form_class = StorefrontForm
    template_name = "storefront/storefront_form.html"
    success_url = "/dashboard/teacher/"

    def dispatch(self, request, *args, **kwargs):
        if Storefront.objects.filter(teacher=request.user).exists():
            return redirect("storefront_update", store_slug=request.user.storefront.store_slug)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.teacher = self.request.user  # Set the teacher field to the current user
        return super().form_valid(form)


class StorefrontUpdateView(LoginRequiredMixin, UpdateView):
    model = Storefront
    form_class = StorefrontForm
    template_name = "storefront/storefront_form.html"
    success_url = "/dashboard/teacher/"

    def get_object(self):
        return get_object_or_404(Storefront, teacher=self.request.user)


class StorefrontDetailView(LoginRequiredMixin, generic.DetailView):
    model = Storefront
    template_name = "storefront/storefront_detail.html"
    context_object_name = "storefront"

    def get_object(self):
        return get_object_or_404(Storefront, store_slug=self.kwargs["store_slug"])


def success_story_list(request):
    """View for listing published success stories."""
    success_stories = SuccessStory.objects.filter(status="published").order_by("-published_at")

    # Paginate results
    paginator = Paginator(success_stories, 9)  # 9 stories per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "success_stories": page_obj,
        "is_paginated": paginator.num_pages > 1,
        "page_obj": page_obj,
    }
    return render(request, "success_stories/list.html", context)


def success_story_detail(request, slug):
    """View for displaying a single success story."""
    success_story = get_object_or_404(SuccessStory, slug=slug, status="published")

    # Get related success stories (same author or similar content)
    related_stories = (
        SuccessStory.objects.filter(status="published").exclude(id=success_story.id).order_by("-published_at")[:3]
    )

    context = {
        "success_story": success_story,
        "related_stories": related_stories,
    }
    return render(request, "success_stories/detail.html", context)


@login_required
def create_success_story(request):
    """View for creating a new success story."""
    if request.method == "POST":
        form = SuccessStoryForm(request.POST, request.FILES)
        if form.is_valid():
            success_story = form.save(commit=False)
            success_story.author = request.user
            success_story.save()
            messages.success(request, "Success story created successfully!")
            return redirect("success_story_detail", slug=success_story.slug)
    else:
        form = SuccessStoryForm()

    context = {
        "form": form,
    }
    return render(request, "success_stories/create.html", context)


@login_required
def edit_success_story(request, slug):
    """View for editing an existing success story."""
    success_story = get_object_or_404(SuccessStory, slug=slug, author=request.user)

    if request.method == "POST":
        form = SuccessStoryForm(request.POST, request.FILES, instance=success_story)
        if form.is_valid():
            form.save()
            messages.success(request, "Success story updated successfully!")
            return redirect("success_story_detail", slug=success_story.slug)
    else:
        form = SuccessStoryForm(instance=success_story)

    context = {
        "form": form,
        "success_story": success_story,
        "is_edit": True,
    }
    return render(request, "success_stories/create.html", context)


@login_required
def delete_success_story(request, slug):
    """View for deleting a success story."""
    success_story = get_object_or_404(SuccessStory, slug=slug, author=request.user)

    if request.method == "POST":
        success_story.delete()
        messages.success(request, "Success story deleted successfully!")
        return redirect("success_story_list")

    context = {
        "success_story": success_story,
    }
    return render(request, "success_stories/delete_confirm.html", context)


def gsoc_landing_page(request):
    """
    Renders the GSOC landing page with top GitHub contributors
    based on merged pull requests
    """
    import logging

    import requests
    from django.conf import settings

    # Initialize an empty list for contributors in case the GitHub API call fails
    top_contributors = []

    # GitHub API URL for the education-website repository
    github_repo_url = "https://api.github.com/repos/alphaonelabs/education-website"

    # Users to exclude from the contributor list (bots and automated users)
    excluded_users = ["A1L13N", "dependabot[bot]"]

    try:
        # Fetch contributors from GitHub API
        headers = {}
        # Check if GitHub token is configured
        if hasattr(settings, "GITHUB_TOKEN") and settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        # Get all closed pull requests - we'll filter for merged ones in code
        # The GitHub API doesn't have a direct 'merged' filter in the query params
        # so we get all closed PRs and then check the 'merged_at' field
        pull_requests_response = requests.get(
            f"{github_repo_url}/pulls",
            params={
                "state": "closed",  # closed PRs could be either merged or just closed
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
            },
            headers=headers,
            timeout=5,
        )

        # Check for rate limiting
        if pull_requests_response.status_code == 403 and "X-RateLimit-Remaining" in pull_requests_response.headers:
            remaining = pull_requests_response.headers.get("X-RateLimit-Remaining")
            if remaining == "0":
                reset_time = int(pull_requests_response.headers.get("X-RateLimit-Reset", 0))
                reset_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reset_time))
                logging.warning(f"GitHub API rate limit exceeded. Resets at {reset_datetime}")

        if pull_requests_response.status_code == 200:
            pull_requests = pull_requests_response.json()

            # Create a map of contributors with their PR count
            contributor_stats = defaultdict(
                lambda: {"merged_pr_count": 0, "avatar_url": "", "profile_url": "", "prs_url": ""}
            )

            # Process each pull request
            for pr in pull_requests:
                # Check if the PR was merged
                if pr.get("merged_at"):
                    username = pr["user"]["login"]

                    # Skip excluded users
                    if username in excluded_users:
                        continue

                    contributor_stats[username]["merged_pr_count"] += 1
                    contributor_stats[username]["avatar_url"] = pr["user"]["avatar_url"]
                    contributor_stats[username]["profile_url"] = pr["user"]["html_url"]
                    # Add a direct link to the user's PRs for this repository
                    base_url = "https://github.com/alphaonelabs/education-website/pulls"
                    query = f"?q=is:pr+author:{username}+is:merged"
                    contributor_stats[username]["prs_url"] = base_url + query
                    contributor_stats[username]["username"] = username

            # Convert to list and sort by PR count
            top_contributors = [v for k, v in contributor_stats.items()]
            top_contributors.sort(key=lambda x: x["merged_pr_count"], reverse=True)

            # Get top 10 contributors
            top_contributors = top_contributors[:10]

    except Exception as e:
        logging.error(f"Error fetching GitHub contributors: {str(e)}")

    context = {"top_contributors": top_contributors}

    return render(request, "gsoc_landing_page.html", context)


def whiteboard(request):
    return render(request, "whiteboard.html")


def graphing_calculator(request):
    return render(request, "graphing_calculator.html")


def meme_list(request):
    memes = Meme.objects.all().order_by("-created_at")
    subjects = Subject.objects.filter(memes__isnull=False).distinct()
    # Filter by subject if provided
    subject_filter = request.GET.get("subject")
    if subject_filter:
        memes = memes.filter(subject__slug=subject_filter)
    paginator = Paginator(memes, 12)  # Show 12 memes per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "memes.html", {"memes": page_obj, "subjects": subjects, "selected_subject": subject_filter})


@login_required
def add_meme(request):
    if request.method == "POST":
        form = MemeForm(request.POST, request.FILES)
        if form.is_valid():
            meme = form.save(commit=False)  # The form handles subject creation logic internally
            meme.uploader = request.user
            meme.save()
            messages.success(request, "Your meme has been uploaded successfully!")
            return redirect("meme_list")
    else:
        form = MemeForm()
    subjects = Subject.objects.all().order_by("name")
    return render(request, "add_meme.html", {"form": form, "subjects": subjects})


@login_required
def team_goals(request):
    """List all team goals the user is part of or has created."""
    user_goals = (
        TeamGoal.objects.filter(Q(creator=request.user) | Q(members__user=request.user))
        .distinct()
        .order_by("-created_at")
    )

    paginator = Paginator(user_goals, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    pending_invites = TeamInvite.objects.filter(recipient=request.user, status="pending").select_related(
        "goal", "sender"
    )

    context = {
        "goals": page_obj,
        "pending_invites": pending_invites,
        "is_paginated": paginator.num_pages > 1,
    }
    return render(request, "teams/list.html", context)


@login_required
def create_team_goal(request):
    """Create a new team goal."""
    if request.method == "POST":
        form = TeamGoalForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                goal = form.save(commit=False)
                goal.creator = request.user
                goal.save()

                # Add creator as a member
                TeamGoalMember.objects.create(team_goal=goal, user=request.user, role="leader")

                messages.success(request, "Team goal created successfully!")
                return redirect("team_goal_detail", goal_id=goal.id)
    else:
        form = TeamGoalForm()

    return render(request, "teams/create.html", {"form": form})


@login_required
def team_goal_detail(request, goal_id):
    """View and manage a specific team goal."""
    goal = get_object_or_404(TeamGoal.objects.prefetch_related("members__user"), id=goal_id)

    # Check if user has access to this goal
    if not (goal.creator == request.user or goal.members.filter(user=request.user).exists()):
        messages.error(request, "You do not have access to this team goal.")
        return redirect("team_goals")

    # Get existing team members to exclude from invitation
    existing_members = goal.members.values_list("user_id", flat=True)

    # Handle inviting new members
    if request.method == "POST":
        form = TeamInviteForm(request.POST)
        if form.is_valid():
            # Check for existing invites using the validated User object
            if TeamInvite.objects.filter(
                goal__id=goal.id, recipient=form.cleaned_data["recipient"]  # Changed to use User object
            ).exists():
                messages.warning(request, "An invite for this user is already pending.")
                return redirect("team_goal_detail", goal_id=goal.id)
            invite = form.save(commit=False)
            invite.sender = request.user
            invite.goal = goal
            invite.save()
            messages.success(request, f"Invitation sent to {invite.recipient.email}!")
            notify_team_invite(invite)
            return redirect("team_goal_detail", goal_id=goal.id)

    else:
        form = TeamInviteForm()

    # Get users that can be invited (exclude existing members and the creator)
    available_users = User.objects.exclude(id__in=list(existing_members) + [goal.creator.id]).values(
        "id", "username", "email"
    )

    context = {
        "goal": goal,
        "invite_form": form,
        "user_is_leader": goal.members.filter(user=request.user, role="leader").exists(),
        "available_users": available_users,
    }
    return render(request, "teams/detail.html", context)


@login_required
def accept_team_invite(request, invite_id):
    """Accept a team invitation."""
    invite = get_object_or_404(
        TeamInvite.objects.select_related("goal"), id=invite_id, recipient=request.user, status="pending"
    )

    # Create team member using get_or_create to avoid race conditions
    member, created = TeamGoalMember.objects.get_or_create(
        team_goal=invite.goal, user=request.user, defaults={"role": "member"}
    )

    if not created:
        messages.info(request, f"You are already a member of {invite.goal.title}.")
    else:
        messages.success(request, f"You have joined {invite.goal.title}!")

    # Update invite status
    invite.status = "accepted"
    invite.responded_at = timezone.now()
    invite.save()

    notify_team_invite_response(invite)
    return redirect("team_goal_detail", goal_id=invite.goal.id)


@login_required
def decline_team_invite(request, invite_id):
    """Decline a team invitation."""
    invite = get_object_or_404(TeamInvite, id=invite_id, recipient=request.user, status="pending")

    invite.status = "declined"
    invite.responded_at = timezone.now()
    invite.save()

    notify_team_invite_response(invite)
    messages.info(request, f"You have declined to join {invite.goal.title}.")
    return redirect("team_goals")


@login_required
def edit_team_goal(request, goal_id):
    """Edit an existing team goal."""
    goal = get_object_or_404(TeamGoal, id=goal_id)

    # Check if user is the creator or a leader
    if not (goal.creator == request.user or goal.members.filter(user=request.user, role="leader").exists()):
        messages.error(request, "You don't have permission to edit this team goal.")
        return redirect("team_goal_detail", goal_id=goal_id)

    if request.method == "POST":
        form = TeamGoalForm(request.POST, instance=goal)
        if form.is_valid():
            # Validate that deadline is not in the past
            if form.cleaned_data["deadline"] < timezone.now():
                form.add_error("deadline", "Deadline cannot be in the past.")
                context = {
                    "form": form,
                    "goal": goal,
                    "is_edit": True,
                }
                return render(request, "teams/create.html", context)
            form.save()
            messages.success(request, "Team goal updated successfully!")
            return redirect("team_goal_detail", goal_id=goal.id)
    else:
        form = TeamGoalForm(instance=goal)

    context = {
        "form": form,
        "goal": goal,
        "is_edit": True,
    }
    return render(request, "teams/create.html", context)


@login_required
def mark_team_contribution(request, goal_id):
    """Allow a team member to mark their contribution as complete."""
    goal = get_object_or_404(TeamGoal, id=goal_id)

    # Find the current user's membership in this goal
    member = goal.members.filter(user=request.user).first()

    if not member:
        messages.error(request, "You are not a member of this team goal.")
        return redirect("team_goal_detail", goal_id=goal_id)

    if member.completed:
        messages.info(request, "Your contribution is already marked as complete.")
        return redirect("team_goal_detail", goal_id=goal_id)

    # Mark the user's contribution as complete
    member.mark_completed()
    messages.success(request, "Your contribution has been marked as complete.")
    notify_team_goal_completion(goal, request.user)
    return redirect("team_goal_detail", goal_id=goal_id)


@login_required
def remove_team_member(request, goal_id, member_id):
    """Remove a member from a team goal."""
    goal = get_object_or_404(TeamGoal, id=goal_id)

    # Check if user is the creator or a leader
    if not (goal.creator == request.user or goal.members.filter(user=request.user, role="leader").exists()):
        messages.error(request, "You don't have permission to remove members.")
        return redirect("team_goal_detail", goal_id=goal_id)

    member = get_object_or_404(TeamGoalMember, id=member_id, team_goal=goal)

    # Prevent removing the creator
    if member.user == goal.creator:
        messages.error(request, "The team creator cannot be removed.")
        return redirect("team_goal_detail", goal_id=goal_id)

    member.delete()
    messages.success(request, f"{member.user.username} has been removed from the team.")
    return redirect("team_goal_detail", goal_id=goal_id)


@login_required
def submit_team_proof(request, team_goal_id):
    team_goal = get_object_or_404(TeamGoal, id=team_goal_id)
    member = get_object_or_404(TeamGoalMember, team_goal=team_goal, user=request.user)

    if request.method == "POST":
        form = TeamGoalCompletionForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            if not member.completed:
                member.mark_completed()
            return redirect("team_goal_detail", goal_id=team_goal.id)  # Fixed here

    else:
        form = TeamGoalCompletionForm(instance=member)

    return render(request, "teams/submit_proof.html", {"form": form, "team_goal": team_goal})


@login_required
def delete_team_goal(request, goal_id):
    """Delete a team goal."""
    goal = get_object_or_404(TeamGoal, id=goal_id)

    # Only creator can delete the goal
    if request.user != goal.creator:
        messages.error(request, "Only the creator can delete this team goal.")
        return redirect("team_goal_detail", goal_id=goal_id)

    if request.method == "POST":
        goal.delete()
        messages.success(request, "Team goal has been deleted.")
        return redirect("team_goals")

    return render(request, "teams/delete_confirm.html", {"goal": goal})


@teacher_required
def add_student_to_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if course.teacher != request.user:
        return HttpResponseForbidden("You are not authorized to enroll students in this course.")
    if request.method == "POST":
        form = StudentEnrollmentForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]

            # Check if a user with this email already exists.
            if User.objects.filter(email=email).exists():
                form.add_error("email", "A user with this email already exists.")
            else:
                # Generate a username by combining the first name and the email prefix.
                email_prefix = email.split("@")[0]
                generated_username = f"{first_name}_{email_prefix}".lower()

                # Ensure the username is unique; if not, append a random string.
                while User.objects.filter(username=generated_username).exists():
                    generated_username = f"{generated_username}{get_random_string(4)}"
                # Create a new student account with an auto-generated password.
                random_password = get_random_string(10)
                try:
                    student = User.objects.create_user(
                        username=generated_username,
                        email=email,
                        password=random_password,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    # Mark the new user as a student (not a teacher).
                    student.profile.is_teacher = False
                    student.profile.save()

                    # Enroll the new student in the course if not already enrolled.
                    if Enrollment.objects.filter(course=course, student=student).exists():
                        form.add_error(None, "Student is already enrolled.")
                    else:
                        Enrollment.objects.create(course=course, student=student, status="approved")
                        messages.success(request, f"{first_name} {last_name} has been enrolled in the course.")

                        # Send enrollment notification and password reset link to student
                        reset_link = request.build_absolute_uri(reverse("account_reset_password"))
                        context = {
                            "student": student,
                            "course": course,
                            "teacher": request.user,
                            "reset_link": reset_link,
                        }
                        html_message = render_to_string("emails/student_enrollment.html", context)
                        send_mail(
                            f"You have been enrolled in {course.title}",
                            f"You have been enrolled in {course.title} by\
                                {request.user.get_full_name() or request.user.username}. "
                            f"Please visit {reset_link} to set your password.",
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            html_message=html_message,
                            fail_silently=False,
                        )
                        return redirect("course_detail", slug=course.slug)
                except IntegrityError:
                    form.add_error(None, "Failed to create user account. Please try again.")
    else:
        form = StudentEnrollmentForm()

    return render(request, "courses/add_student.html", {"form": form, "course": course})


def donate(request):
    """Display the donation page with options for one-time donations and subscriptions."""
    # Get recent public donations to display
    recent_donations = Donation.objects.filter(status="completed", anonymous=False).order_by("-created_at")[:5]

    # Calculate total donations
    total_donations = Donation.objects.filter(status="completed").aggregate(total=Sum("amount"))["total"] or 0

    # Get donation amounts for the preset buttons
    donation_amounts = [5, 10, 25, 50, 100]

    context = {
        "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
        "recent_donations": recent_donations,
        "total_donations": total_donations,
        "donation_amounts": donation_amounts,
    }

    return render(request, "donate.html", context)


@login_required
def create_donation_payment_intent(request):
    """Create a payment intent for a one-time donation."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        data = json.loads(request.body)
        amount = data.get("amount")
        message = data.get("message", "")
        anonymous = data.get("anonymous", False)

        if not amount or float(amount) <= 0:
            return JsonResponse({"error": "Invalid donation amount"}, status=400)

        # Convert amount to cents for Stripe
        amount_cents = int(float(amount) * 100)

        # Create a payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            metadata={
                "donation_type": "one_time",
                "user_id": request.user.id,
                "message": message[:100] if message else "",  # Limit message length
                "anonymous": "true" if anonymous else "false",
            },
        )

        # Create a donation record
        donation = Donation.objects.create(
            user=request.user,
            email=request.user.email,
            amount=amount,
            donation_type="one_time",
            status="pending",
            stripe_payment_intent_id=intent.id,
            message=message,
            anonymous=anonymous,
        )

        return JsonResponse(
            {
                "clientSecret": intent.client_secret,
                "donation_id": donation.id,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def create_donation_subscription(request):
    """Create a subscription for recurring donations."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        data = json.loads(request.body)
        amount = data.get("amount")
        message = data.get("message", "")
        anonymous = data.get("anonymous", False)
        payment_method_id = data.get("payment_method_id")

        if not amount or float(amount) <= 0:
            return JsonResponse({"error": "Invalid donation amount"}, status=400)

        if not payment_method_id:
            return JsonResponse({"error": "Payment method is required"}, status=400)

        # Convert amount to cents for Stripe
        amount_cents = int(float(amount) * 100)

        # Check if user already has a Stripe customer ID
        customer_id = None
        if hasattr(request.user, "profile") and request.user.profile.stripe_customer_id:
            customer_id = request.user.profile.stripe_customer_id

        # Create or get customer
        if customer_id:
            customer = stripe.Customer.retrieve(customer_id)
        else:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.get_full_name() or request.user.username,
                payment_method=payment_method_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )

            # Save customer ID to user profile
            if hasattr(request.user, "profile"):
                request.user.profile.stripe_customer_id = customer.id
                request.user.profile.save()

        # Create a subscription product and price if they don't exist
        # Note: In a production environment, you might want to create these
        # products and prices in the Stripe dashboard and reference them here
        product = stripe.Product.create(
            name=f"Monthly Donation - ${amount}",
            type="service",
        )

        price = stripe.Price.create(
            product=product.id,
            unit_amount=amount_cents,
            currency="usd",
            recurring={"interval": "month"},
        )

        # Create the subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price.id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
            metadata={
                "donation_type": "subscription",
                "user_id": request.user.id,
                "message": message[:100] if message else "",
                "anonymous": "true" if anonymous else "false",
                "amount": amount,
            },
        )

        # Create a donation record
        donation = Donation.objects.create(
            user=request.user,
            email=request.user.email,
            amount=amount,
            donation_type="subscription",
            status="pending",
            stripe_subscription_id=subscription.id,
            stripe_customer_id=customer.id,
            message=message,
            anonymous=anonymous,
        )

        return JsonResponse(
            {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                "donation_id": donation.id,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def donation_webhook(request):
    """Handle Stripe webhooks for donations."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle payment intent events
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        handle_successful_donation_payment(payment_intent)
    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object
        handle_failed_donation_payment(payment_intent)

    # Handle subscription events
    elif event.type == "customer.subscription.created":
        subscription = event.data.object
        handle_subscription_created(subscription)
    elif event.type == "customer.subscription.updated":
        subscription = event.data.object
        handle_subscription_updated(subscription)
    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        handle_subscription_cancelled(subscription)
    elif event.type == "invoice.payment_succeeded":
        invoice = event.data.object
        handle_invoice_paid(invoice)
    elif event.type == "invoice.payment_failed":
        invoice = event.data.object
        handle_invoice_failed(invoice)

    return HttpResponse(status=200)


def handle_successful_donation_payment(payment_intent):
    """Handle successful one-time donation payments."""
    try:
        # Find the donation by payment intent ID
        donation = Donation.objects.get(stripe_payment_intent_id=payment_intent.id)
        donation.status = "completed"
        donation.save()

        # Send thank you email
        send_donation_thank_you_email(donation)

    except Donation.DoesNotExist:
        # This might be a payment for something else
        pass


def handle_failed_donation_payment(payment_intent):
    """Handle failed one-time donation payments."""
    try:
        # Find the donation by payment intent ID
        donation = Donation.objects.get(stripe_payment_intent_id=payment_intent.id)
        donation.status = "failed"
        donation.save()

    except Donation.DoesNotExist:
        # This might be a payment for something else
        pass


def handle_subscription_created(subscription):
    """Handle newly created subscriptions."""
    try:
        # Find the donation by subscription ID
        donation = Donation.objects.get(stripe_subscription_id=subscription.id)

        # Update status based on subscription status
        if subscription.status == "active":
            donation.status = "completed"
        elif subscription.status == "incomplete":
            donation.status = "pending"
        elif subscription.status == "canceled":
            donation.status = "cancelled"

        donation.save()

    except Donation.DoesNotExist:
        # This might be a subscription for something else
        pass


def handle_subscription_updated(subscription):
    """Handle subscription updates."""
    try:
        # Find the donation by subscription ID
        donation = Donation.objects.get(stripe_subscription_id=subscription.id)

        # Update status based on subscription status
        if subscription.status == "active":
            donation.status = "completed"
        elif subscription.status == "past_due":
            donation.status = "pending"
        elif subscription.status == "canceled":
            donation.status = "cancelled"

        donation.save()

    except Donation.DoesNotExist:
        # This might be a subscription for something else
        pass


def handle_subscription_cancelled(subscription):
    """Handle cancelled subscriptions."""
    try:
        # Find the donation by subscription ID
        donation = Donation.objects.get(stripe_subscription_id=subscription.id)
        donation.status = "cancelled"
        donation.save()

    except Donation.DoesNotExist:
        # This might be a subscription for something else
        pass


def handle_invoice_paid(invoice):
    """Handle successful subscription invoice payments."""
    if invoice.subscription:
        try:
            # Find the donation by subscription ID
            donation = Donation.objects.get(stripe_subscription_id=invoice.subscription)

            # Create a new donation record for this payment
            Donation.objects.create(
                user=donation.user,
                email=donation.email,
                amount=donation.amount,
                donation_type="subscription",
                status="completed",
                stripe_subscription_id=donation.stripe_subscription_id,
                stripe_customer_id=donation.stripe_customer_id,
                message=donation.message,
                anonymous=donation.anonymous,
            )

            # Send thank you email
            send_donation_thank_you_email(donation)

        except Donation.DoesNotExist:
            # This might be a subscription for something else
            pass


def handle_invoice_failed(invoice):
    """Handle failed subscription invoice payments."""
    if invoice.subscription:
        try:
            # Find the donation by subscription ID
            donation = Donation.objects.get(stripe_subscription_id=invoice.subscription)

            # Create a new donation record for this failed payment
            Donation.objects.create(
                user=donation.user,
                email=donation.email,
                amount=donation.amount,
                donation_type="subscription",
                status="failed",
                stripe_subscription_id=donation.stripe_subscription_id,
                stripe_customer_id=donation.stripe_customer_id,
                message=donation.message,
                anonymous=donation.anonymous,
            )

        except Donation.DoesNotExist:
            # This might be a subscription for something else
            pass


def send_donation_thank_you_email(donation):
    """Send a thank you email for donations."""
    subject = "Thank You for Your Donation!"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.email

    # Prepare context for email template
    context = {
        "donation": donation,
        "site_name": settings.SITE_NAME,
    }

    # Render email template
    html_message = render_to_string("emails/donation_thank_you.html", context)
    plain_message = strip_tags(html_message)

    # Send email
    send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)


def donation_success(request):
    """Display a success page after a successful donation."""
    donation_id = request.GET.get("donation_id")

    if donation_id:
        try:
            donation = Donation.objects.get(id=donation_id)
            context = {
                "donation": donation,
            }
            return render(request, "donation_success.html", context)
        except Donation.DoesNotExist:
            pass

    # If no valid donation ID, redirect to the donate page
    return redirect("donate")


def donation_cancel(request):
    """Handle donation cancellation."""
    return redirect("donate")


def educational_videos_list(request):
    """View for listing educational videos with optional category filtering."""
    # Get category filter from query params
    selected_category = request.GET.get("category")

    # Base queryset
    videos = EducationalVideo.objects.select_related("uploader", "category").order_by("-uploaded_at")

    # Apply category filter if provided
    if selected_category:
        videos = videos.filter(category__slug=selected_category)
        selected_category_obj = get_object_or_404(Subject, slug=selected_category)
        selected_category_display = selected_category_obj.name
    else:
        selected_category_display = None

    # Get category counts for sidebar
    category_counts = dict(
        EducationalVideo.objects.values("category__name", "category__slug")
        .annotate(count=Count("id"))
        .values_list("category__slug", "count")
    )

    # Get all subjects for the dropdown
    subjects = Subject.objects.all().order_by("order", "name")

    # Paginate results
    paginator = Paginator(videos, 12)  # 12 videos per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "videos": page_obj,
        "is_paginated": paginator.num_pages > 1,
        "page_obj": page_obj,
        "subjects": subjects,
        "selected_category": selected_category,
        "selected_category_display": selected_category_display,
        "category_counts": category_counts,
    }

    return render(request, "videos/list.html", context)


@login_required
def upload_educational_video(request):
    """View for uploading a new educational video."""
    if request.method == "POST":
        form = EducationalVideoForm(request.POST)
        if form.is_valid():
            video = form.save(commit=False)
            video.uploader = request.user
            video.save()

            return redirect("educational_videos_list")
    else:
        form = EducationalVideoForm()

    return render(request, "videos/upload.html", {"form": form})


def certificate_detail(request, certificate_id):
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id)
    if request.user != certificate.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view this certificate")
    context = {
        "certificate": certificate,
    }
    return render(request, "courses/certificate_detail.html", context)


@login_required
def generate_certificate(request, enrollment_id):
    # Retrieve the enrollment for the current user
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
    # Ensure the course is completed before generating a certificate
    if enrollment.status != "completed":
        messages.error(request, "You can only generate a certificate for a completed course.")
        return redirect("student_dashboard")

    # Check if a certificate already exists for this course and user
    certificate = Certificate.objects.filter(user=request.user, course=enrollment.course).first()
    if certificate:
        messages.info(request, "Certificate already generated.")
        return redirect("certificate_detail", certificate_id=certificate.certificate_id)

    # Create a new certificate record manually
    certificate = Certificate.objects.create(user=request.user, course=enrollment.course)
    messages.success(request, "Certificate generated successfully!")
    return redirect("certificate_detail", certificate_id=certificate.certificate_id)


@login_required
def tracker_list(request):
    trackers = ProgressTracker.objects.filter(user=request.user).order_by("-updated_at")
    return render(request, "trackers/list.html", {"trackers": trackers})


@login_required
def create_tracker(request):
    if request.method == "POST":
        form = ProgressTrackerForm(request.POST)
        if form.is_valid():
            tracker = form.save(commit=False)
            tracker.user = request.user
            tracker.save()
            return redirect("tracker_detail", tracker_id=tracker.id)
    else:
        form = ProgressTrackerForm()
    return render(request, "trackers/form.html", {"form": form, "title": "Create Progress Tracker"})


@login_required
def update_tracker(request, tracker_id):
    tracker = get_object_or_404(ProgressTracker, id=tracker_id, user=request.user)

    if request.method == "POST":
        form = ProgressTrackerForm(request.POST, instance=tracker)
        if form.is_valid():
            form.save()
            return redirect("tracker_detail", tracker_id=tracker.id)
    else:
        form = ProgressTrackerForm(instance=tracker)
    return render(request, "trackers/form.html", {"form": form, "tracker": tracker, "title": "Update Progress Tracker"})


@login_required
def tracker_detail(request, tracker_id):
    tracker = get_object_or_404(ProgressTracker, id=tracker_id, user=request.user)
    embed_url = request.build_absolute_uri(f"/trackers/embed/{tracker.embed_code}/")
    return render(request, "trackers/detail.html", {"tracker": tracker, "embed_url": embed_url})


@login_required
def update_progress(request, tracker_id):
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        tracker = get_object_or_404(ProgressTracker, id=tracker_id, user=request.user)

        try:
            new_value = int(request.POST.get("current_value", tracker.current_value))
            tracker.current_value = new_value
            tracker.save()

            return JsonResponse(
                {"success": True, "percentage": tracker.percentage, "current_value": tracker.current_value}
            )
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid value"}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


@xframe_options_exempt
def embed_tracker(request, embed_code):
    tracker = get_object_or_404(ProgressTracker, embed_code=embed_code, public=True)
    return render(request, "trackers/embed.html", {"tracker": tracker})


@login_required
def streak_detail(request):
    """Display the user's learning streak."""
    if not request.user.is_authenticated:
        return redirect("account_login")
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    return render(request, "streak_detail.html", {"streak": streak})


@login_required
def waiting_room_list(request):
    """View for displaying waiting rooms categorized by status."""
    # Get waiting rooms by status
    open_rooms = WaitingRoom.objects.filter(status="open")
    fulfilled_rooms = WaitingRoom.objects.filter(status="fulfilled")
    closed_rooms = WaitingRoom.objects.filter(status="closed")

    # Get waiting rooms created by the user
    user_created_rooms = WaitingRoom.objects.filter(creator=request.user)

    # Get waiting rooms joined by the user
    user_joined_rooms = request.user.joined_waiting_rooms.all()

    # Process topics for all waiting rooms
    all_rooms = (
        list(open_rooms)
        + list(fulfilled_rooms)
        + list(closed_rooms)
        + list(user_created_rooms)
        + list(user_joined_rooms)
    )
    room_topics = {}
    for room in all_rooms:
        room_topics[room.id] = [topic.strip() for topic in room.topics.split(",") if topic.strip()]

    context = {
        "open_rooms": open_rooms,
        "fulfilled_rooms": fulfilled_rooms,
        "closed_rooms": closed_rooms,
        "user_created_rooms": user_created_rooms,
        "user_joined_rooms": user_joined_rooms,
        "room_topics": room_topics,
    }
    return render(request, "waiting_room/list.html", context)


def find_matching_courses(waiting_room):
    """Find courses that match the waiting room's subject and topics."""
    # Get courses with matching subject name (case-insensitive)
    matching_courses = Course.objects.filter(subject__iexact=waiting_room.subject, status="published")

    # Filter courses that have all required topics
    required_topics = {t.strip().lower() for t in waiting_room.topics.split(",") if t.strip()}

    # Further filter courses by checking if their topics contain all required topics
    final_matches = []
    for course in matching_courses:
        course_topics = {t.strip().lower() for t in course.topics.split(",") if t.strip()}
        if course_topics.issuperset(required_topics):
            final_matches.append(course)

    return final_matches


def waiting_room_detail(request, waiting_room_id):
    """View for displaying details of a waiting room."""
    waiting_room = get_object_or_404(WaitingRoom, id=waiting_room_id)

    # Check if the user is a participant
    is_participant = request.user.is_authenticated and request.user in waiting_room.participants.all()

    # Check if the user is the creator
    is_creator = request.user.is_authenticated and request.user == waiting_room.creator

    # Check if the user is a teacher
    is_teacher = request.user.is_authenticated and hasattr(request.user, "profile") and request.user.profile.is_teacher

    context = {
        "waiting_room": waiting_room,
        "is_participant": is_participant,
        "is_creator": is_creator,
        "is_teacher": is_teacher,
        "participant_count": waiting_room.participants.count(),
        "topic_list": [topic.strip() for topic in waiting_room.topics.split(",") if topic.strip()],
    }
    return render(request, "waiting_room/detail.html", context)


@login_required
def join_waiting_room(request, waiting_room_id):
    """View for joining a waiting room."""
    waiting_room = get_object_or_404(WaitingRoom, id=waiting_room_id)

    # Check if the waiting room is open
    if waiting_room.status != "open":
        messages.error(request, "This waiting room is no longer open for joining.")
        return redirect("waiting_room_list")

    # Add the user as a participant if not already
    if request.user not in waiting_room.participants.all():
        waiting_room.participants.add(request.user)
        messages.success(request, f"You have joined the waiting room: {waiting_room.title}")
    else:
        messages.info(request, "You are already a participant in this waiting room.")

    return redirect("waiting_room_detail", waiting_room_id=waiting_room.id)


@login_required
def leave_waiting_room(request, waiting_room_id):
    """View for leaving a waiting room."""
    waiting_room = get_object_or_404(WaitingRoom, id=waiting_room_id)

    # Remove the user from participants
    if request.user in waiting_room.participants.all():
        waiting_room.participants.remove(request.user)
        messages.success(request, f"You have left the waiting room: {waiting_room.title}")
    else:
        messages.info(request, "You are not a participant in this waiting room.")

    return redirect("waiting_room_list")


def is_superuser(user):
    return user.is_superuser


@user_passes_test(is_superuser)
def sync_github_milestones(request):
    """Sync GitHub milestones with forum topics."""
    github_repo = "alphaonelabs/alphaonelabs-education-website"
    milestones_url = f"https://api.github.com/repos/{github_repo}/milestones"

    try:
        # Get GitHub milestones
        response = requests.get(milestones_url)
        response.raise_for_status()
        milestones = response.json()

        # Get or create a forum category for milestones
        category, created = ForumCategory.objects.get_or_create(
            name="GitHub Milestones",
            defaults={
                "slug": "github-milestones",
                "description": "Discussions about GitHub milestones and project roadmap",
                "icon": "fa-github",
            },
        )

        # Count for tracking
        created_count = 0
        updated_count = 0

        for milestone in milestones:
            milestone_title = milestone["title"]
            milestone_description = milestone["description"] or "No description provided."
            milestone_url = milestone["html_url"]
            milestone_state = milestone["state"]
            open_issues = milestone["open_issues"]
            closed_issues = milestone["closed_issues"]
            due_date = milestone.get("due_on", "No due date")

            # Format content with progress information
            progress = 0
            if open_issues + closed_issues > 0:
                progress = (closed_issues / (open_issues + closed_issues)) * 100

            content = f"""
## Milestone: {milestone_title}

{milestone_description}

**State:** {milestone_state}
**Progress:** {progress:.1f}% ({closed_issues} closed / {open_issues} open issues)
**Due Date:** {due_date}

[View on GitHub]({milestone_url})
            """

            # Try to find an existing topic for this milestone
            topic = ForumTopic.objects.filter(
                category=category, title__startswith=f"Milestone: {milestone_title}"
            ).first()

            if topic:
                # Update existing topic
                topic.content = content
                topic.is_pinned = milestone_state == "open"  # Pin open milestones
                topic.save()
                updated_count += 1
            else:
                # Create new topic
                # Use the first superuser as the author
                author = User.objects.filter(is_superuser=True).first()
                if author:
                    ForumTopic.objects.create(
                        category=category,
                        title=f"Milestone: {milestone_title}",
                        content=content,
                        author=author,
                        is_pinned=(milestone_state == "open"),
                    )
                    created_count += 1

        if created_count or updated_count:
            messages.success(
                request, f"Successfully synced GitHub milestones: {created_count} created, {updated_count} updated."
            )
        else:
            messages.info(request, "No GitHub milestones to sync.")

    except requests.exceptions.RequestException as e:
        messages.error(request, f"Error fetching GitHub milestones: {str(e)}")
    except Exception as e:
        messages.error(request, f"Error syncing milestones: {str(e)}")

    return redirect("forum_categories")


@login_required
def toggle_course_status(request, slug):
    """Toggle a course between draft and published status"""
    course = get_object_or_404(Course, slug=slug)

    # Check if user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can modify course status!")
        return redirect("course_detail", slug=slug)

    # Toggle the status between draft and published
    if course.status == "draft":
        course.status = "published"
        messages.success(request, "Course has been published successfully!")
    elif course.status == "published":
        course.status = "draft"
        messages.success(request, "Course has been unpublished and is now in draft mode.")
    # Note: We don't toggle from/to 'archived' status as that's a separate action

    course.save()
    return redirect("course_detail", slug=slug)


def public_profile(request, username):
    user = get_object_or_404(User, username=username)

    try:
        profile = user.profile
    except Profile.DoesNotExist:
        # Instead of raising Http404, we call custom_404.
        return custom_404(request, "Profile not found.")

    if not profile.is_profile_public:
        return custom_404(request, "Profile not found.")

    context = {"profile": profile}

    if profile.is_teacher:
        courses = Course.objects.filter(teacher=user)
        total_students = sum(course.enrollments.filter(status="approved").count() for course in courses)
        context.update(
            {
                "teacher_stats": {
                    "courses": courses,
                    "total_courses": courses.count(),
                    "total_students": total_students,
                }
            }
        )
    else:
        enrollments = Enrollment.objects.filter(student=user)
        completed_enrollments = enrollments.filter(status="completed")
        total_courses = enrollments.count()
        total_completed = completed_enrollments.count()
        total_progress = 0
        progress_count = 0
        for enrollment in enrollments:
            progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
            total_progress += progress.completion_percentage
            progress_count += 1
        avg_progress = round(total_progress / progress_count) if progress_count > 0 else 0
        context.update(
            {
                "total_courses": total_courses,
                "total_completed": total_completed,
                "avg_progress": avg_progress,
                "completed_courses": completed_enrollments,
            }
        )

    return render(request, "public_profile_detail.html", context)


class GradeableLinkListView(ListView):
    """View to display all submitted links that can be graded."""

    model = GradeableLink
    template_name = "grade_links/link_list.html"
    context_object_name = "links"
    paginate_by = 10


class GradeableLinkDetailView(DetailView):
    """View to display details about a specific link and its grades."""

    model = GradeableLink
    template_name = "grade_links/link_detail.html"
    context_object_name = "link"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if user is authenticated
        if self.request.user.is_authenticated:
            # Check if the user has already graded this link
            try:
                user_grade = LinkGrade.objects.get(link=self.object, user=self.request.user)
                context["user_grade"] = user_grade
                context["grade_form"] = LinkGradeForm(instance=user_grade)
            except LinkGrade.DoesNotExist:
                context["grade_form"] = LinkGradeForm()

        # Get all grades for this link
        context["grades"] = self.object.grades.all()

        return context


class GradeableLinkCreateView(LoginRequiredMixin, CreateView):
    """View to submit a new link for grading."""

    model = GradeableLink
    form_class = GradeableLinkForm
    template_name = "grade_links/submit_link.html"
    success_url = reverse_lazy("gradeable_link_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Your link has been submitted for grading!")
        return super().form_valid(form)


@login_required
def grade_link(request, pk):
    """View to grade a link."""
    link = get_object_or_404(GradeableLink, pk=pk)

    # Prevent users from grading their own links
    if link.user == request.user:
        messages.error(request, "You cannot grade your own submissions!")
        return redirect("gradeable_link_detail", pk=link.pk)

    # Check if the user has already graded this link
    try:
        user_grade = LinkGrade.objects.get(link=link, user=request.user)
    except LinkGrade.DoesNotExist:
        user_grade = None

    if request.method == "POST":
        form = LinkGradeForm(request.POST, instance=user_grade)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.link = link
            grade.user = request.user
            grade.save()
            messages.success(request, "Your grade has been submitted!")
            return redirect("gradeable_link_detail", pk=link.pk)
    else:
        form = LinkGradeForm(instance=user_grade)

    return render(
        request,
        "grade_links/grade_link.html",
        {
            "form": form,
            "link": link,
        },
    )


def duplicate_session(request, session_id):
    """Duplicate a session to next week."""
    # Get the original session
    session = get_object_or_404(Session, id=session_id)
    course = session.course

    # Check if user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can duplicate sessions!")
        return redirect("course_detail", slug=course.slug)

    # Create a new session with the same properties but dates shifted forward by a week
    new_session = Session(
        course=course,
        title=session.title,
        description=session.description,
        is_virtual=session.is_virtual,
        meeting_link=session.meeting_link,
        meeting_id="",  # Clear meeting ID as it will be a new meeting
        location=session.location,
        price=session.price,
        enable_rollover=session.enable_rollover,
        rollover_pattern=session.rollover_pattern,
    )

    # Set dates one week later
    time_shift = timezone.timedelta(days=7)
    new_session.start_time = session.start_time + time_shift
    new_session.end_time = session.end_time + time_shift

    # Save the new session
    new_session.save()
    msg = f"Session '{session.title}' duplicated for {new_session.start_time.strftime('%b %d, %Y')}"
    messages.success(request, msg)

    return redirect("course_detail", slug=course.slug)


def run_create_test_data(request):
    """Run the create_test_data management command and redirect to homepage."""
    from django.conf import settings

    if not settings.DEBUG:
        messages.error(request, "This action is only available in debug mode.")
        return redirect("index")

    try:
        call_command("create_test_data")
        messages.success(request, "Test data has been created successfully!")
    except Exception as e:
        messages.error(request, f"Error creating test data: {str(e)}")

    return redirect("index")


@login_required
@require_POST
def update_student_attendance(request):
    if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

    try:
        session_id = request.POST.get("session_id")
        student_id = request.POST.get("student_id")
        status = request.POST.get("status")
        notes = request.POST.get("notes", "")

        if not all([session_id, student_id, status]):
            return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)

        session = Session.objects.get(id=session_id)
        student = User.objects.get(id=student_id)

        # Check if the user is the course teacher
        if request.user != session.course.teacher:
            return JsonResponse(
                {"success": False, "message": "Unauthorized: Only the course teacher can update attendance"}, status=403
            )

        # Update or create the attendance record
        attendance, created = SessionAttendance.objects.update_or_create(
            session=session, student=student, defaults={"status": status, "notes": notes}
        )

        return JsonResponse(
            {"success": True, "message": "Attendance updated successfully", "created": created, "status": status}
        )
    except Session.DoesNotExist:
        return JsonResponse({"success": False, "message": "Session not found"}, status=404)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "Student not found"}, status=404)
    except Exception:
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Error updating student attendance", exc_info=True)
        return JsonResponse({"success": False, "message": "An internal error has occurred."}, status=500)


@login_required
def get_student_attendance(request):
    """Get a student's attendance data for a specific course."""
    if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

    student_id = request.GET.get("student_id")
    course_id = request.GET.get("course_id")

    if not all([student_id, course_id]):
        return JsonResponse({"success": False, "message": "Missing required parameters"}, status=400)

    try:
        course = Course.objects.get(id=course_id)
        student = User.objects.get(id=student_id)

        # Check if user is authorized (must be the course teacher)
        if request.user != course.teacher:
            return JsonResponse(
                {"success": False, "message": "Unauthorized: Only the course teacher can view this data"}, status=403
            )

        # Get all attendance records for this student in this course
        attendance_records = SessionAttendance.objects.filter(student=student, session__course=course).select_related(
            "session"
        )

        # Format the data for the frontend
        attendance_data = {}
        for record in attendance_records:
            attendance_data[record.session.id] = {
                "status": record.status,
                "notes": record.notes,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
            }

        return JsonResponse({"success": True, "attendance": attendance_data})

    except Course.DoesNotExist:
        return JsonResponse({"success": False, "message": "Course not found"}, status=404)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "Student not found"}, status=404)
    except Exception:
        return JsonResponse({"success": False, "message": "Error: get_student_attendance"}, status=500)


@login_required
@teacher_required
def student_management(request, course_slug, student_id):
    """
    View for managing a specific student in a course.
    This replaces the modal functionality with a dedicated page.
    """
    course = get_object_or_404(Course, slug=course_slug)
    student = get_object_or_404(User, id=student_id)

    # Check if user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can manage students!")
        return redirect("course_detail", slug=course.slug)

    # Check if student is enrolled in this course
    enrollment = get_object_or_404(Enrollment, course=course, student=student)

    # Get sessions for this course
    sessions = course.sessions.all().order_by("start_time")

    # Get attendance records
    attendance_records = SessionAttendance.objects.filter(student=student, session__course=course).select_related(
        "session"
    )

    # Format attendance data for easier access in template
    attendance_data = {}
    for record in attendance_records:
        attendance_data[record.session.id] = {"status": record.status, "notes": record.notes}

    # Get student progress data
    progress = CourseProgress.objects.filter(enrollment=enrollment).first()
    completed_sessions = []
    if progress:
        completed_sessions = progress.completed_sessions.all()

    # Calculate attendance rate
    total_sessions = sessions.count()
    attended_sessions = SessionAttendance.objects.filter(
        student=student, session__course=course, status__in=["present", "late"]
    ).count()

    attendance_rate = 0
    if total_sessions > 0:
        attendance_rate = int((attended_sessions / total_sessions) * 100)

    # Get badges earned by this student
    user_badges = student.badges.all()

    context = {
        "course": course,
        "student": student,
        "enrollment": enrollment,
        "sessions": sessions,
        "attendance_data": attendance_data,
        "attendance_rate": attendance_rate,
        "progress": progress,
        "completed_sessions": completed_sessions,
        "badges": user_badges,
    }

    return render(request, "courses/student_management.html", context)


@login_required
@teacher_required
def update_student_progress(request, enrollment_id):
    """
    View for updating a student's progress in a course.
    """
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    course = enrollment.course

    # Check if user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can update student progress!")
        return redirect("course_detail", slug=course.slug)

    if request.method == "POST":
        grade = request.POST.get("grade")
        status = request.POST.get("status")
        comments = request.POST.get("comments", "")

        # Update enrollment
        enrollment.grade = grade
        enrollment.status = status
        enrollment.notes = comments
        enrollment.last_grade_update = timezone.now()
        enrollment.save()

        messages.success(request, f"Progress for {enrollment.student.username} updated successfully!")
        return redirect("student_management", course_slug=course.slug, student_id=enrollment.student.id)

    # If not POST, redirect back to student management
    return redirect("student_management", course_slug=course.slug, student_id=enrollment.student.id)


@login_required
@teacher_required
def update_teacher_notes(request, enrollment_id):
    """
    View for updating teacher's private notes for a student.
    """
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    course = enrollment.course

    # Check if user is the course teacher
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can update notes!")
        return redirect("course_detail", slug=course.slug)

    if request.method == "POST":
        notes = request.POST.get("teacher_notes", "")

        # If notes have changed, create a new note history entry
        if enrollment.teacher_notes != notes and notes.strip():
            NoteHistory.objects.create(enrollment=enrollment, content=notes, created_by=request.user)

        # Update enrollment
        enrollment.teacher_notes = notes
        enrollment.save()

        messages.success(request, f"Notes for {enrollment.student.username} updated successfully!")

    return redirect("student_management", course_slug=course.slug, student_id=enrollment.student.id)


@login_required
@teacher_required
@require_POST
def award_badge(request):
    """
    AJAX view for awarding badges to students.
    """
    if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

    student_id = request.POST.get("student_id")
    badge_type = request.POST.get("badge_type")
    course_slug = request.POST.get("course_slug")

    if not all([student_id, badge_type, course_slug]):
        return JsonResponse({"success": False, "message": "Missing required parameters"}, status=400)

    try:
        student = User.objects.get(id=student_id)
        course = Course.objects.get(slug=course_slug)

        # Check if user is the course teacher
        if request.user != course.teacher:
            return JsonResponse(
                {"success": False, "message": "Unauthorized: Only the course teacher can award badges"}, status=403
            )

        # Handle different badge types
        badge = None
        if badge_type == "perfect_attendance":
            badge, created = Badge.objects.get_or_create(
                name="Perfect Attendance",
                defaults={"description": "Awarded for attending all sessions in a course", "points": 50},
            )
        elif badge_type == "participation":
            badge, created = Badge.objects.get_or_create(
                name="Outstanding Participation",
                defaults={"description": "Awarded for exceptional participation in course discussions", "points": 75},
            )
        elif badge_type == "completion":
            badge, created = Badge.objects.get_or_create(
                name="Course Completion",
                defaults={"description": "Awarded for successfully completing the course", "points": 100},
            )
        else:
            return JsonResponse({"success": False, "message": "Invalid badge type"}, status=400)

        # Award the badge to the student
        user_badge, created = UserBadge.objects.get_or_create(
            user=student, badge=badge, defaults={"awarded_by": request.user, "course": course}
        )

        if not created:
            return JsonResponse({"success": False, "message": "Student already has this badge"}, status=400)

        return JsonResponse(
            {"success": True, "message": f"Badge '{badge.name}' awarded successfully to {student.username}"}
        )

    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "Student not found"}, status=404)
    except Course.DoesNotExist:
        return JsonResponse({"success": False, "message": "Course not found"}, status=404)
    except Exception:
        return JsonResponse({"success": False, "message": "Error: award_badge"}, status=500)


def notification_preferences(request):
    """
    Display and update the notification preferences for the logged-in user.
    """
    # Get (or create) the user's notification preferences.
    preference, created = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = NotificationPreferencesForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request, "Your notification preferences have been updated.")
            # Redirect to the profile page after saving
            return redirect("profile")
        else:
            messages.error(request, "There was an error updating your preferences.")
    else:
        form = NotificationPreferencesForm(instance=preference)

    return render(request, "account/notification_preferences.html", {"form": form})


@login_required
def invite_to_study_group(request, group_id):
    """Invite a user to a study group."""
    group = get_object_or_404(StudyGroup, id=group_id)

    # Only allow invitations from current group members.
    if request.user not in group.members.all():
        messages.error(request, "You must be a member of the group to invite others.")
        return redirect("study_group_detail", group_id=group.id)

    if request.method == "POST":
        email_or_username = request.POST.get("email_or_username")
        # Search by email or username.
        recipient = User.objects.filter(Q(email=email_or_username) | Q(username=email_or_username)).first()
        if not recipient:
            messages.error(request, f"No user found with email or username: {email_or_username}")
            return redirect("study_group_detail", group_id=group.id)

        # Prevent duplicate invitations or inviting existing members.
        if recipient in group.members.all():
            messages.warning(request, f"{recipient.username} is already a member of this group.")
            return redirect("study_group_detail", group_id=group.id)

        if StudyGroupInvite.objects.filter(group=group, recipient=recipient, status="pending").exists():
            messages.warning(request, f"An invitation has already been sent to {recipient.username}.")
            return redirect("study_group_detail", group_id=group.id)

        if group.is_full():
            messages.error(request, "The study group is full. No new members can be added.")
            return redirect("study_group_detail", group_id=group.id)

        # Create a notification for the recipient.
        notification_url = request.build_absolute_uri(reverse("user_invitations"))
        notification_text = (
            f"{request.user.username} has invited you to join the study group: {group.name}. "
            f"View invitations here: {notification_url}"
        )
        Notification.objects.create(
            user=recipient, title="Study Group Invitation", message=notification_text, notification_type="info"
        )

        messages.success(request, f"Invitation sent to {recipient.username}.")
        return redirect("study_group_detail", group_id=group.id)

    return redirect("study_group_detail", group_id=group.id)


@login_required
def user_invitations(request):
    """Display pending study group invitations for the user."""
    invitations = StudyGroupInvite.objects.filter(recipient=request.user, status="pending").select_related(
        "group", "sender"
    )
    return render(request, "web/study/invitations.html", {"invitations": invitations})


@login_required
def respond_to_invitation(request, invite_id):
    """Accept or decline a study group invitation."""
    invite = get_object_or_404(StudyGroupInvite, id=invite_id, recipient=request.user)
    if request.method == "POST":
        response = request.POST.get("response")
        if response == "accept":
            if invite.group.is_full():
                messages.error(request, "The study group is full. Cannot join.")
                return redirect("user_invitations")
            invite.accept()
            study_group_url = request.build_absolute_uri(reverse("study_group_detail", args=[invite.group.id]))
            notification_text = f"{request.user.username} has accepted your invitation to join {invite.group.name}.\
                 View group details here: {study_group_url}"
            Notification.objects.create(
                user=invite.sender, title="Invitation Accepted", message=notification_text, notification_type="success"
            )
            messages.success(request, f"You have joined {invite.group.name}.")
            return redirect("user_invitations")
        elif response == "decline":
            invite.decline()
            study_group_url = request.build_absolute_uri(reverse("study_group_detail", args=[invite.group.id]))
            notification_text = f"{request.user.username} has declined your invitation to join {invite.group.name}.\
                 View group details here: {study_group_url}"
            Notification.objects.create(
                user=invite.sender, title="Invitation Declined", message=notification_text, notification_type="warning"
            )
            messages.info(request, f"You have declined the invitation to {invite.group.name}.")
            return redirect("user_invitations")

    return redirect("user_invitations")


@login_required
def create_study_group(request):
    if request.method == "POST":
        form = StudyGroupForm(request.POST)
        if form.is_valid():
            study_group = form.save(commit=False)
            study_group.creator = request.user
            study_group.save()
            # Automatically add the creator as a member
            study_group.members.add(request.user)
            messages.success(request, "Study group created successfully!")
            return redirect("study_group_detail", group_id=study_group.id)
    else:
        form = StudyGroupForm()
    return render(request, "web/study/create_group.html", {"form": form})


def features_page(request):
    """View to display the features page."""
    return render(request, "features.html")


@require_POST
@csrf_protect
def feature_vote(request):
    """API endpoint to handle feature voting."""
    feature_id = request.POST.get("feature_id")
    vote_type = request.POST.get("vote")

    if not feature_id or vote_type not in ["up", "down"]:
        return JsonResponse({"status": "error", "message": "Invalid parameters"}, status=400)

    # Store IP for anonymous users
    ip_address = None
    if not request.user.is_authenticated:
        ip_address = (
            request.META.get("REMOTE_ADDR") or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        )
        if not ip_address:
            return JsonResponse({"status": "error", "message": "Could not identify user"}, status=400)

    # Process the vote
    try:
        # Use transaction to prevent race conditions during vote operations
        with transaction.atomic():
            # Check for existing vote
            existing_vote = None
            if request.user.is_authenticated:
                existing_vote = FeatureVote.objects.filter(feature_id=feature_id, user=request.user).first()
            elif ip_address:
                existing_vote = FeatureVote.objects.filter(
                    feature_id=feature_id, ip_address=ip_address, user__isnull=True
                ).first()

            # Handle the vote logic
            status_message = "Vote recorded"
            if existing_vote:
                if existing_vote.vote == vote_type:
                    status_message = "You've already cast this vote"
                else:
                    # Change vote type if user changed their mind
                    existing_vote.vote = vote_type
                    existing_vote.save()
                    status_message = "Vote changed"
            else:
                # Create new vote
                new_vote = FeatureVote(feature_id=feature_id, vote=vote_type)

                if request.user.is_authenticated:
                    new_vote.user = request.user
                else:
                    new_vote.ip_address = ip_address

                new_vote.save()

            # Get updated counts within the transaction to ensure consistency
            up_count = FeatureVote.objects.filter(feature_id=feature_id, vote="up").count()
            down_count = FeatureVote.objects.filter(feature_id=feature_id, vote="down").count()

        # Calculate percentage for visualization
        total_votes = up_count + down_count
        up_percentage = round((up_count / total_votes) * 100) if total_votes > 0 else 0
        down_percentage = round((down_count / total_votes) * 100) if total_votes > 0 else 0

        return JsonResponse(
            {
                "status": "success",
                "message": status_message,
                "up_count": up_count,
                "down_count": down_count,
                "total_votes": total_votes,
                "up_percentage": up_percentage,
                "down_percentage": down_percentage,
            }
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error processing vote: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"Error processing vote: {str(e)}"}, status=500)


@require_GET
def feature_vote_count(request):
    """Get vote counts for one or more features."""
    feature_ids = request.GET.get("feature_ids", "").split(",")
    if not feature_ids or not feature_ids[0]:
        return JsonResponse({"error": "No feature IDs provided"}, status=400)

    result = {}
    # Get all up and down votes in a single query each for better performance
    up_votes = (
        FeatureVote.objects.filter(feature_id__in=feature_ids, vote="up")
        .values("feature_id")
        .annotate(count=Count("id"))
    )
    down_votes = (
        FeatureVote.objects.filter(feature_id__in=feature_ids, vote="down")
        .values("feature_id")
        .annotate(count=Count("id"))
    )

    # Create lookup dictionaries for efficient access
    up_votes_dict = {str(vote["feature_id"]): vote["count"] for vote in up_votes}
    down_votes_dict = {str(vote["feature_id"]): vote["count"] for vote in down_votes}

    # Check user's votes if authenticated
    user_votes = {}
    if request.user.is_authenticated:
        user_vote_objects = FeatureVote.objects.filter(feature_id__in=feature_ids, user=request.user)
        for vote in user_vote_objects:
            user_votes[str(vote.feature_id)] = vote.vote
    elif request.META.get("REMOTE_ADDR"):
        # Get IP address for anonymous users
        ip_address = (
            request.META.get("REMOTE_ADDR") or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        )
        if ip_address:
            anon_vote_objects = FeatureVote.objects.filter(
                feature_id__in=feature_ids, ip_address=ip_address, user__isnull=True
            )
            for vote in anon_vote_objects:
                user_votes[str(vote.feature_id)] = vote.vote

    for feature_id in feature_ids:
        up_count = up_votes_dict.get(feature_id, 0)
        down_count = down_votes_dict.get(feature_id, 0)
        total_votes = up_count + down_count

        # Calculate percentages
        up_percentage = (up_count / total_votes * 100) if total_votes > 0 else 0
        down_percentage = (down_count / total_votes * 100) if total_votes > 0 else 0

        result[feature_id] = {
            "up_count": up_count,
            "down_count": down_count,
            "total_votes": total_votes,
            "up_percentage": round(up_percentage, 1),
            "down_percentage": round(down_percentage, 1),
            "user_vote": user_votes.get(feature_id, None),
        }

    return JsonResponse(result)


@login_required
def progress_visualization(request):
    """Generate and render progress visualization statistics for a student's enrolled courses."""
    user = request.user

    # Create a unique cache key based on user ID
    cache_key = f"user_progress_{user.id}"
    context = cache.get(cache_key)

    if not context:
        # Cache miss - calculate all data
        enrollments = Enrollment.objects.filter(student=user)
        course_stats = calculate_course_stats(enrollments)
        attendance_stats = calculate_attendance_stats(user, enrollments)
        learning_activity = calculate_learning_activity(user, enrollments)
        completion_pace = calculate_completion_pace(enrollments)
        chart_data = prepare_chart_data(enrollments)

        # Combine all stats into a single context dictionary
        context = {**course_stats, **attendance_stats, **learning_activity, **completion_pace, **chart_data}
        # Cache the results (no expiration, we'll invalidate manually via signals)
        cache.set(cache_key, context, timeout=None)  # None means no expiration

    return render(request, "courses/progress_visualization.html", context)


def calculate_course_stats(enrollments):
    """Calculate statistics on the user's course progress."""
    total_courses = enrollments.count()
    courses_completed = enrollments.filter(status="completed").count()
    topics_mastered = sum(e.progress.completed_sessions.count() for e in enrollments if hasattr(e, "progress"))

    return {
        "total_courses": total_courses,
        "courses_completed": courses_completed,
        "courses_completed_percentage": round((courses_completed / total_courses) * 100) if total_courses else 0,
        "topics_mastered": topics_mastered,
    }


def calculate_attendance_stats(user, enrollments):
    """Calculate the user's attendance statistics."""
    all_attendances = SessionAttendance.objects.filter(
        student=user, session__course__in=[e.course for e in enrollments]
    )
    total_attendance_count = all_attendances.count()
    present_attendance_count = all_attendances.filter(status__in=["present", "late"]).count()

    return {
        "average_attendance": (
            round((present_attendance_count / total_attendance_count) * 100) if total_attendance_count else 0
        )
    }


def calculate_learning_activity(user, enrollments):
    """Calculate learning activity metrics like active days, streaks, and learning hours."""
    all_completed_sessions = [
        s for s in get_all_completed_sessions(enrollments) if s.start_time and s.end_time and s.end_time > s.start_time
    ]
    now = timezone.now()

    # Find the most active day of the week
    most_active_day = Counter(session.start_time.strftime("%A") for session in all_completed_sessions).most_common(1)
    # Find the most recent session date
    last_session_date = (
        max(all_completed_sessions, key=lambda s: s.start_time).start_time.strftime("%b %d, %Y")
        if all_completed_sessions
        else "N/A"
    )

    streak, _ = LearningStreak.objects.get_or_create(user=user)
    current_streak = streak.current_streak

    total_learning_hours = round(
        sum((s.end_time - s.start_time).total_seconds() / 3600 for s in all_completed_sessions), 1
    )

    # Calculate the number of weeks since the first session, minimum 1 week
    weeks_since_first_session = (
        max(1, (now - min(all_completed_sessions, key=lambda s: s.start_time).start_time).days / 7)
        if all_completed_sessions
        else 1
    )
    avg_sessions_per_week = round(len(all_completed_sessions) / weeks_since_first_session, 1)

    return {
        # Extract the day name from the most common day tuple, or default to "N/A"
        "most_active_day": most_active_day[0][0] if most_active_day else "N/A",
        "last_session_date": last_session_date,
        "current_streak": current_streak,
        "total_learning_hours": total_learning_hours,
        "avg_sessions_per_week": avg_sessions_per_week,
    }


def calculate_completion_pace(enrollments):
    """Calculate the average completion pace for completed courses."""
    completed_enrollments = enrollments.filter(status="completed")
    if not completed_enrollments.exists():
        return {"completion_pace": "N/A"}

    total_days = sum(
        (e.completion_date - e.enrollment_date).days
        for e in completed_enrollments
        if e.completion_date and e.enrollment_date
    )
    avg_days_to_complete = total_days / completed_enrollments.count() if completed_enrollments.count() > 0 else 0

    return {"completion_pace": f"{avg_days_to_complete:.0f} days/course"}


def get_all_completed_sessions(enrollments):
    """Retrieve all completed sessions for a user's enrollments."""
    return [s for e in enrollments if hasattr(e, "progress") for s in e.progress.completed_sessions.all()]


def prepare_chart_data(enrollments):
    """Prepare data for visualizing user progress in charts."""
    colors = ["255,99,132", "54,162,235", "255,206,86", "75,192,192", "153,102,255"]

    courses = []
    progress_dates, sessions_completed = [], []

    for i, e in enumerate(enrollments):
        color = colors[i % len(colors)]
        # Basic course data with progress information
        course_data = {
            "title": e.course.title,
            "color": color,
            "progress": getattr(e.progress, "completion_percentage", 0),
            "sessions_completed": e.progress.completed_sessions.count() if hasattr(e, "progress") else 0,
            "total_sessions": e.course.sessions.count(),
        }

        # Add time series data for courses with completed sessions
        if hasattr(e, "progress") and e.progress.completed_sessions.exists():
            # Find the most recent active session date
            last_session = max(e.progress.completed_sessions.all(), key=lambda s: s.start_time)
            course_data["last_active"] = last_session.start_time.strftime("%b %d, %Y")
            # Generate time series data for progress visualization
            time_data = prepare_time_series_data(e, course_data["total_sessions"])
            course_data.update(time_data)
            progress_dates.append(time_data["dates"])
            sessions_completed.append(time_data["sessions_points"])
        else:
            # Default values for courses without progress
            course_data.update({"last_active": "Not started", "progress_over_time": []})
            progress_dates.append([])
            sessions_completed.append([])

        courses.append(course_data)

    return {
        "courses": courses,
        # Create a sorted list of all unique dates by flattening and deduplicating
        "progress_dates": json.dumps(sorted(set(date for dates in progress_dates for date in dates))),
        "sessions_completed": json.dumps(sessions_completed),
        "courses_json": json.dumps(courses),
    }


def prepare_time_series_data(enrollment, total_sessions):
    """Generate time series data for progress visualization."""
    completed_sessions = (
        sorted(enrollment.progress.completed_sessions.all(), key=lambda s: s.start_time)
        if hasattr(enrollment, "progress")
        else []
    )

    return {
        # Calculate progress percentage for each completed session
        "progress_over_time": [
            round(((idx + 1) / total_sessions) * 100, 1) if total_sessions else 0
            for idx, _ in enumerate(completed_sessions)
        ],
        # Create sequential session numbers
        "sessions_points": list(range(1, len(completed_sessions) + 1)),
        # Format session dates consistently
        "dates": [s.start_time.strftime("%Y-%m-%d") for s in completed_sessions],
    }


# map views


@login_required
def classes_map(request):
    """View for displaying classes near the user."""
    now = timezone.now()
    sessions = (
        Session.objects.filter(Q(start_time__gte=now) | Q(start_time__lte=now, end_time__gte=now))
        .filter(is_virtual=False, location__isnull=False)
        .exclude(location="")
        .order_by("start_time")
        .select_related("course", "course__teacher")
    )
    # Get filter parameters
    course_id = request.GET.get("course")
    teaching_style = request.GET.get("teaching_style")
    # Apply filters
    if course_id:
        sessions = sessions.filter(course_id=course_id, status="published")
    if teaching_style:
        sessions = sessions.filter(teaching_style=teaching_style)
    # Fetch only necessary course fields
    courses = Course.objects.only("id", "title").order_by("title")
    age_groups = Course._meta.get_field("level").choices
    teaching_styles = list(set(Session.objects.values_list("teaching_style", flat=True)))
    context = {"sessions": sessions, "courses": courses, "age_groups": age_groups, "teaching_style": teaching_styles}
    return render(request, "web/classes_map.html", context)


@login_required
def map_data_api(request):
    """API to return all live and ongoing class data in JSON format."""
    now = timezone.now()
    sessions = (
        Session.objects.filter(
            Q(start_time__gte=now) | Q(start_time__lte=now, end_time__gte=now)  # Future or Live classes
        )
        .filter(Q(is_virtual=False) & ~Q(location=""))
        .select_related("course", "course__teacher")
    )

    course_id = request.GET.get("course")
    age_group = request.GET.get("age_group")

    if course_id:
        sessions = sessions.filter(course__id=course_id, status="published")
    if age_group:
        sessions = sessions.filter(course__level=age_group)

    logger.debug(f"API call with filters: course={course_id}, age={age_group}")

    map_data = []
    sessions_to_update = []
    # Limit geocoding to a reasonable number per request
    MAX_GEOCODING_PER_REQUEST = 5
    geocoding_count = 0
    geocoding_errors = 0
    coordinate_errors = 0
    for session in sessions:
        if not session.latitude or not session.longitude:
            if geocoding_count >= MAX_GEOCODING_PER_REQUEST:
                logger.warning(f"Geocoding limit reached ({MAX_GEOCODING_PER_REQUEST}). Skipping session {session.id}")
                continue
            geocoding_count += 1
            logger.info(f"Geocoding session {session.id} with location: {session.location}")
            lat, lng = geocode_address(session.location)
            if lat is not None and lng is not None:
                session.latitude = lat
                session.longitude = lng
                sessions_to_update.append(session)
            else:
                geocoding_errors += 1
                logger.warning(f"Skipping session {session.id} due to failed geocoding")
                continue

        try:
            lat = float(session.latitude)
            lng = float(session.longitude)
            map_data.append(
                {
                    "id": session.id,
                    "title": session.title,
                    "course_title": session.course.title,
                    "teacher": session.course.teacher.get_full_name() or session.course.teacher.username,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat(),
                    "location": session.location,
                    "lat": lat,
                    "lng": lng,
                    "price": str(session.price or session.course.price),
                    "url": session.get_absolute_url(),
                    "course": session.course.title,
                    "level": session.course.get_level_display(),
                    "is_virtual": session.is_virtual,
                }
            )
        except (ValueError, TypeError):
            coordinate_errors += 1
            logger.warning(
                f"Skipping session {session.id} due to invalid coordinates: "
                f"lat={session.latitude}, lng={session.longitude}"
            )
            continue

    if sessions_to_update:
        logger.info(f"Batch updating coordinates for {len(sessions_to_update)} sessions")
        Session.objects.bulk_update(sessions_to_update, ["latitude", "longitude"])  # Batch update

    # Log summary of issues
    if geocoding_errors > 0 or coordinate_errors > 0:
        logger.warning(f"Map data issues: {geocoding_errors} geocoding errors, {coordinate_errors} coordinate errors")

    logger.info(f"Found {len(map_data)} sessions with valid coordinates")
    return JsonResponse({"sessions": map_data})


GITHUB_REPO = "alphaonelabs/alphaonelabs-education-website"
GITHUB_API_BASE = "https://api.github.com"

logger = logging.getLogger(__name__)


def github_api_request(endpoint, params=None, headers=None):
    """
    Make a GitHub API request with consistent error handling and timeout.
    Returns JSON response on success, empty dict on failure.
    """
    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed API request to {endpoint}: {response.status_code} - {response.text}")
            return {}
    except requests.RequestException as e:
        logger.error(f"Request error for {endpoint}: {e}")
        return {}


def get_user_contribution_metrics(username, token):
    """
    Use the GitHub GraphQL API to fetch all of the user's merged PRs (across all repos),
    then filter by the target repo, implementing pagination to ensure complete data.
    """
    graphql_endpoint = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}

    query = """
    query($username: String!, $after: String) {
      user(login: $username) {
        pullRequests(
          first: 100
          after: $after
          states: MERGED
          orderBy: { field: CREATED_AT, direction: DESC }
        ) {
          totalCount
          pageInfo {
            endCursor
            hasNextPage
          }
          nodes {
            additions
            deletions
            createdAt
            repository {
              nameWithOwner
            }
          }
        }
      }
    }
    """

    all_filtered_prs = []
    after_cursor = None

    while True:
        variables = {"username": username, "after": after_cursor}
        try:
            response = requests.post(
                graphql_endpoint, json={"query": query, "variables": variables}, headers=headers, timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("user"):
                    pr_data = data["data"]["user"]["pullRequests"]
                    prs = pr_data["nodes"]

                    # Filter PRs to the target repository (case insensitive)
                    target_repo = GITHUB_REPO.lower()
                    filtered_prs = [pr for pr in prs if pr["repository"]["nameWithOwner"].lower() == target_repo]
                    all_filtered_prs.extend(filtered_prs)

                    # Check if there are more pages
                    if pr_data["pageInfo"]["hasNextPage"]:
                        after_cursor = pr_data["pageInfo"]["endCursor"]
                    else:
                        break
                else:
                    logger.error("No user or PR data found in GraphQL response.")
                    break
            else:
                logger.error(f"GraphQL error: {response.status_code} - {response.text}")
                break
        except Exception as e:
            logger.error(f"GraphQL request error: {e}")
            break

    # Prepare final result structure
    final_result = {
        "data": {"user": {"pullRequests": {"totalCount": len(all_filtered_prs), "nodes": all_filtered_prs}}}
    }
    return final_result


def contributor_detail_view(request, username):
    """
    View to display detailed information about a specific GitHub contributor.
    Only accessible to staff members.
    """
    cache_key = f"github_contributor_{username}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return render(request, "web/contributor_detail.html", cached_data)

    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Authorization": f"token {token}"} if token else {}

    # Initialize variables to store contributor data
    user_data = {}
    prs_created = 0
    prs_merged = 0
    issues_created = 0
    pr_reviews = 0
    pr_comments = 0
    issue_comments = 0
    lines_added = 0
    lines_deleted = 0
    first_contribution_date = "N/A"
    issue_assignments = 0

    user_endpoint = f"{GITHUB_API_BASE}/users/{username}"
    user_data = github_api_request(user_endpoint, headers=headers)
    if not user_data:
        logger.error("User profile data could not be retrieved.")

    # Pull requests created
    prs_created_json = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={"q": f"author:{username} type:pr repo:{GITHUB_REPO}"},
        headers=headers,
    )
    prs_created = prs_created_json.get("total_count", 0)

    # Pull requests merged
    prs_merged_json = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={"q": f"author:{username} type:pr repo:{GITHUB_REPO} is:merged"},
        headers=headers,
    )
    prs_merged = prs_merged_json.get("total_count", 0)

    # Issues created
    issues_json = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={"q": f"author:{username} type:issue repo:{GITHUB_REPO}"},
        headers=headers,
    )
    issues_created = issues_json.get("total_count", 0)

    # Pull request reviews
    reviews_json = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={"q": f"reviewer:{username} type:pr repo:{GITHUB_REPO}"},
        headers=headers,
    )
    pr_reviews = reviews_json.get("total_count", 0)

    # Pull requests with comments
    pr_comments_json = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={"q": f"commenter:{username} type:pr repo:{GITHUB_REPO}"},
        headers=headers,
    )
    pr_comments = pr_comments_json.get("total_count", 0)

    # Issues with comments
    issue_comments_json = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={"q": f"commenter:{username} type:issue repo:{GITHUB_REPO}"},
        headers=headers,
    )
    issue_comments = issue_comments_json.get("total_count", 0)

    # Oldest PR creation date
    prs_oldest = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={
            "q": f"author:{username} type:pr repo:{GITHUB_REPO}",
            "sort": "created",
            "order": "asc",
            "per_page": 1,
        },
        headers=headers,
    )
    if prs_oldest.get("total_count", 0) > 0:
        first_contribution_date = prs_oldest["items"][0].get("created_at", "N/A")

    # Issue assignments
    issue_assignments_json = github_api_request(
        f"{GITHUB_API_BASE}/search/issues",
        params={"q": f"assignee:{username} type:issue repo:{GITHUB_REPO}"},
        headers=headers,
    )
    issue_assignments = issue_assignments_json.get("total_count", 0)
    metrics = get_user_contribution_metrics(username, token)
    pr_data = metrics.get("data", {}).get("user", {}).get("pullRequests", {}).get("nodes", [])
    for pr in pr_data:
        lines_added += pr.get("additions", 0)
        lines_deleted += pr.get("deletions", 0)

    # Update user_data with additional metrics
    user_data.update(
        {
            "reactions_received": user_data.get("reactions_received", 0),
            "mentorship_score": user_data.get("mentorship_score", 0),
            "collaboration_score": user_data.get("collaboration_score", 0),
            "issue_assignments": issue_assignments,
        }
    )

    # Prepare context for the template
    context = {
        "user": user_data,
        "prs_created": prs_created,
        "prs_merged": prs_merged,
        "pr_reviews": pr_reviews,
        "issues_created": issues_created,
        "issue_comments": issue_comments,
        "pr_comments": pr_comments,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "first_contribution_date": first_contribution_date,
        "chart_data": {
            "prs_created": prs_created,
            "prs_merged": prs_merged,
            "pr_reviews": pr_reviews,
            "issues_created": issues_created,
            "issue_assignments": issue_assignments,
            "pr_comments": pr_comments,
            "issue_comments": issue_comments,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "first_contribution_date": (first_contribution_date if first_contribution_date != "N/A" else "N/A"),
        },
    }

    # Cache for 1 hour
    cache.set(cache_key, context, 3600)
    return render(request, "web/contributor_detail.html", context)


@login_required
def all_study_groups(request):
    """Display all study groups across courses."""
    # Get all study groups
    groups = StudyGroup.objects.all().order_by("-created_at")

    # Group study groups by course
    courses_with_groups = {}
    for group in groups:
        if group.course not in courses_with_groups:
            courses_with_groups[group.course] = []
        courses_with_groups[group.course].append(group)

    # Handle creating a new study group
    if request.method == "POST":
        course_id = request.POST.get("course")
        name = request.POST.get("name")
        description = request.POST.get("description")
        max_members = request.POST.get("max_members", 10)
        is_private = request.POST.get("is_private", False) == "on"  # Convert checkbox to boolean

        try:
            # Validate the input
            if not course_id or not name or not description:
                raise ValueError("All fields are required")

            # Get the course
            course = Course.objects.get(id=course_id)

            # Create the group
            group = StudyGroup.objects.create(
                course=course,
                creator=request.user,
                name=name,
                description=description,
                max_members=int(max_members),
                is_private=is_private,
            )

            # Add the creator as a member
            group.members.add(request.user)

            messages.success(request, "Study group created successfully!")
            return redirect("study_group_detail", group_id=group.id)
        except Course.DoesNotExist:
            messages.error(request, "Course not found.")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error creating study group: {str(e)}")

    # Get user's enrollments for the create group form
    enrollments = request.user.enrollments.filter(status="approved").select_related("course")
    enrolled_courses = [enrollment.course for enrollment in enrollments]

    return render(
        request,
        "web/study/all_groups.html",
        {
            "courses_with_groups": courses_with_groups,
            "enrolled_courses": enrolled_courses,
        },
    )


@login_required
def membership_checkout(request, plan_id: int) -> HttpResponse:
    """Display the membership checkout page."""
    plan = get_object_or_404(MembershipPlan, id=plan_id)

    # Default to monthly billing
    billing_period = request.GET.get("billing_period", "monthly")

    context = {
        "plan": plan,
        "billing_period": billing_period,
        "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
    }

    return render(request, "checkout.html", context)


@login_required
def create_membership_subscription(request) -> JsonResponse:
    """Create a new membership subscription."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        data = json.loads(request.body)
        plan_id = data.get("plan_id")
        payment_method_id = data.get("payment_method_id")
        billing_period = data.get("billing_period", "monthly")

        if not all([plan_id, payment_method_id, billing_period]):
            return JsonResponse({"error": "Missing required fields"}, status=400)

        # Create subscription using helper function
        result = create_subscription(
            user=request.user,
            plan_id=plan_id,
            payment_method_id=payment_method_id,
            billing_period=billing_period,
        )

        if not result["success"]:
            return JsonResponse({"error": result["error"]}, status=400)

        # Helper function to extract client_secret
        def get_client_secret(subscription):
            """Extract client_secret safely from a subscription object."""
            if (
                hasattr(subscription, "latest_invoice")
                and subscription.latest_invoice
                and hasattr(subscription.latest_invoice, "payment_intent")
            ):
                return subscription.latest_invoice.payment_intent.client_secret
            return None

        return JsonResponse(
            {
                "subscription": result["subscription"],
                "client_secret": get_client_secret(result["subscription"]),
            },
        )

    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {str(e)}"}, status=400)
    except stripe.error.CardError as e:
        return JsonResponse({"error": f"Card error: {str(e)}"}, status=400)
    except stripe.error.StripeError as e:
        return JsonResponse({"error": f"Payment processing error: {str(e)}"}, status=500)
    except KeyError as e:
        return JsonResponse({"error": f"Missing key: {str(e)}"}, status=400)
    except Exception:
        logger.exception("Unexpected error in create_membership_subscription")
        return JsonResponse({"error": "An unexpected error occurred"}, status=500)


@login_required
def membership_success(request) -> HttpResponse:
    """Display the membership success page."""
    try:
        membership = request.user.membership
        context = {
            "membership": membership,
        }
        return render(request, "membership_success.html", context)
    except (AttributeError, ObjectDoesNotExist):
        messages.info(request, "You don't have an active membership subscription.")
        return redirect("index")


@login_required
def membership_settings(request) -> HttpResponse:
    """Display the membership settings page."""
    try:
        membership = request.user.membership

        # Get Stripe invoices
        if membership.stripe_customer_id:
            setup_stripe()
            invoices = stripe.Invoice.list(customer=membership.stripe_customer_id, limit=12)
        else:
            invoices = []

        # Get subscription events
        events = MembershipSubscriptionEvent.objects.filter(user=request.user).order_by("-created_at")[:10]

        context = {
            "membership": membership,
            "invoices": invoices.data if invoices else [],
            "events": events,
        }
        return render(request, "membership_settings.html", context)
    except (AttributeError, ObjectDoesNotExist):
        return redirect("index")


@login_required
def cancel_membership(request) -> HttpResponse:
    """Cancel the user's membership subscription."""
    if request.method != "POST":
        return redirect("membership_settings")

    try:
        result = cancel_subscription(request.user)

        if result["success"]:
            messages.success(
                request,
                "Your subscription has been cancelled and will end at the current billing period.",
            )
        else:
            messages.error(request, result["error"])

    except stripe.error.StripeError as e:
        messages.error(request, f"Stripe error: {str(e)}")
    except ObjectDoesNotExist:
        messages.error(request, "No membership found for your account.")
    except Exception as e:
        logger.error(f"Unexpected error in cancel_membership: {str(e)}")
        messages.error(request, str(e))

    return redirect("membership_settings")


@login_required
def reactivate_membership(request) -> HttpResponse:
    """Reactivate a cancelled membership subscription."""
    if request.method != "POST":
        return redirect("membership_settings")

    try:
        result = reactivate_subscription(request.user)

        if result["success"]:
            messages.success(request, "Your subscription has been reactivated.")
        else:
            messages.error(request, result["error"])

    except stripe.error.StripeError as e:
        messages.error(request, f"Stripe error: {str(e)}")
    except ObjectDoesNotExist:
        messages.error(request, "No membership found for your account.")
    except Exception as e:
        logger.error(f"Unexpected error in reactivate_membership: {str(e)}")
        messages.error(request, str(e))

    return redirect("membership_settings")


@login_required
def update_payment_method(request) -> HttpResponse:
    """Display the update payment method page."""
    try:
        membership = request.user.membership

        # Get current payment method
        if membership.stripe_customer_id:
            setup_stripe()
            payment_methods = stripe.PaymentMethod.list(customer=membership.stripe_customer_id, type="card")
            current_payment_method = payment_methods.data[0] if payment_methods.data else None
        else:
            current_payment_method = None

        context = {
            "membership": membership,
            "current_payment_method": current_payment_method,
            "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
        }
        return render(request, "update_payment_method.html", context)
    except (AttributeError, ObjectDoesNotExist):
        return redirect("membership_settings")


@login_required
def update_payment_method_api(request) -> JsonResponse:
    """Update the payment method for a subscription."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        data = json.loads(request.body)
        payment_method_id = data.get("payment_method_id")

        if not payment_method_id:
            return JsonResponse({"error": "Missing payment method ID"}, status=400)

        membership = request.user.membership

        if not membership.stripe_customer_id:
            return JsonResponse({"error": "No active subscription found"}, status=400)

        setup_stripe()

        # Attach payment method to customer
        stripe.PaymentMethod.attach(payment_method_id, customer=membership.stripe_customer_id)

        # Set as default payment method
        stripe.Customer.modify(
            membership.stripe_customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        return JsonResponse({"success": True})

    except stripe.error.CardError as e:
        return JsonResponse({"error": f"Card error: {str(e)}"}, status=400)
    except stripe.error.InvalidRequestError as e:
        return JsonResponse({"error": f"Invalid request: {str(e)}"}, status=400)
    except stripe.error.StripeError as e:
        return JsonResponse({"error": f"Payment processing error: {str(e)}"}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in update_payment_method_api: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)


def social_media_manager_required(user):
    """Check if user has social media manager permissions."""
    return user.is_authenticated and (user.is_staff or getattr(user.profile, "is_social_media_manager", False))


@user_passes_test(social_media_manager_required)
def get_twitter_client():
    """Initialize the Tweepy client."""
    auth = tweepy.OAuthHandler(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET_KEY)
    auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)
    return tweepy.API(auth)


@user_passes_test(social_media_manager_required)
def social_media_dashboard(request):
    # Fetch all posts that haven't been posted yet
    posts = ScheduledPost.objects.filter(posted=False).order_by("-id")
    return render(request, "social_media_dashboard.html", {"posts": posts})


@user_passes_test(social_media_manager_required)
def post_to_twitter(request, post_id):
    post = get_object_or_404(ScheduledPost, id=post_id)
    if request.method == "POST":
        client = get_twitter_client()
        try:
            if post.image:
                # Upload the image file from disk
                media = client.media_upload(post.image.path)
                client.update_status(post.content, media_ids=[media.media_id])
            else:
                client.update_status(post.content)
            post.posted = True
            post.posted_at = timezone.now()
            post.save()
        except Exception as e:
            print(f"Error posting tweet: {e}")
        return redirect("social_media_dashboard")
    return redirect("social_media_dashboard")


@user_passes_test(social_media_manager_required)
def create_scheduled_post(request):
    if request.method == "POST":
        content = request.POST.get("content")
        image = request.FILES.get("image")  # Get the uploaded image, if provided.
        if not content:
            messages.error(request, "Post content cannot be empty.")
            return redirect("social_media_dashboard")
        ScheduledPost.objects.create(
            content=content, image=image, scheduled_time=timezone.now()  # This saves the image file.
        )
        messages.success(request, "Post created successfully!")
    return redirect("social_media_dashboard")


@user_passes_test(social_media_manager_required)
def delete_post(request, post_id):
    """Delete a scheduled post."""
    post = get_object_or_404(ScheduledPost, id=post_id)
    if request.method == "POST":
        post.delete()
    return redirect("social_media_dashboard")
