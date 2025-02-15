import calendar
import json
import os
import re
import shutil
import subprocess
import time
from datetime import timedelta
from decimal import Decimal

import requests
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, models, transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import FileResponse, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .calendar_sync import generate_google_calendar_link, generate_ical_feed, generate_outlook_calendar_link
from .decorators import teacher_required
from .forms import (
    BlogPostForm,
    ChallengeSubmissionForm,
    CourseForm,
    CourseMaterialForm,
    FeedbackForm,
    ForumCategoryForm,
    ForumTopicForm,
    GoodsForm,
    InviteStudentForm,
    LearnForm,
    MessageTeacherForm,
    ProfileUpdateForm,
    ReviewForm,
    SessionForm,
    TeacherSignupForm,
    TeachForm,
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
    BlogComment,
    BlogPost,
    CartItem,
    Challenge,
    ChallengeSubmission,
    Course,
    CourseMaterial,
    CourseProgress,
    Enrollment,
    EventCalendar,
    ForumCategory,
    ForumReply,
    ForumTopic,
    Goods,
    Order,
    OrderItem,
    PeerConnection,
    PeerMessage,
    Profile,
    SearchLog,
    Session,
    SessionAttendance,
    SessionEnrollment,
    StudyGroup,
    TimeSlot,
    WebRequest,
)
from .notifications import notify_session_reminder, notify_teacher_new_enrollment, send_enrollment_confirmation
from .social import get_social_stats
from .utils import get_or_create_cart

GOOGLE_CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, "google_credentials.json")

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def sitemap(request):
    return render(request, "sitemap.html")


def index(request):
    if request.method == "POST":
        form = TeacherSignupForm(request.POST)
        if form.is_valid():
            user, subject = form.save()
            messages.success(
                request,
                (
                    f"Thank you for signing up! We've sent instructions to {user.email} - "
                    "you can continue to create your course"
                ),
            )

            # Use the user object directly instead of querying again
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)

            # TODO: Send welcome email
            # redirect to create a course
            return redirect("create_course")
    else:
        form = TeacherSignupForm()

    # Get featured courses - only published and featured courses
    featured_courses = Course.objects.filter(status="published", is_featured=True).order_by("-created_at")[:3]

    # Get current weekly challenge
    current_challenge = Challenge.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()

    context = {
        "form": form,
        "featured_courses": featured_courses,
        "current_challenge": current_challenge,
    }
    return render(request, "index.html", context)


def signup(request):
    """Handle user signup and referral processing."""
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(request)

            # Handle referral if present in session
            referrer_code = request.session.get("referrer_code")
            if referrer_code:
                handle_referral(user, referrer_code)
                del request.session["referrer_code"]

            return redirect("index")
    else:
        # Store referral code in session if present in URL
        referrer_code = request.GET.get("ref")
        if referrer_code:
            request.session["referrer_code"] = referrer_code

        form = UserRegistrationForm()

    return render(request, "account/signup.html", {"form": form})


@login_required
def profile(request):
    if request.method == "POST":
        if "avatar" in request.FILES:
            # Handle avatar upload
            request.user.profile.avatar = request.FILES["avatar"]
            request.user.profile.save()
            return redirect("profile")

        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            user.profile.bio = form.cleaned_data["bio"]
            user.profile.expertise = form.cleaned_data["expertise"]
            user.profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = ProfileUpdateForm(
            initial={
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "bio": request.user.profile.bio,
                "expertise": request.user.profile.expertise,
            }
        )

    context = {
        "form": form,
    }

    # Add teacher-specific stats
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

    # Add student-specific stats
    else:
        enrollments = Enrollment.objects.filter(student=request.user).select_related("course")
        completed_courses = enrollments.filter(status="completed").count()

        # Calculate average progress
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

    # Add created calendars with prefetched time slots
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
            course.save()
            form.save_m2m()  # Save many-to-many relationships
            return redirect("course_detail", slug=course.slug)
    else:
        form = CourseForm()

    return render(request, "courses/create.html", {"form": form})


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    sessions = course.sessions.all().order_by("start_time")
    now = timezone.now()
    is_teacher = request.user == course.teacher
    completed_sessions = []

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

    # Create enrollment
    enrollment = Enrollment.objects.create(
        student=request.user, course=course, status="pending" if course.price > 0 else "approved"
    )

    # For paid courses, create pending enrollment and redirect to payment
    if course.price > 0:
        messages.info(request, "Please complete the payment process to enroll in this course.")
        return redirect("course_detail", slug=course_slug)

    # For free courses, send notifications
    send_enrollment_confirmation(enrollment)
    notify_teacher_new_enrollment(enrollment)
    messages.success(request, "You have successfully enrolled in this course.")
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

    return render(request, "courses/add_session.html", {"form": form, "course": course})


@login_required
def add_review(request, slug):
    course = Course.objects.get(slug=slug)
    if not request.user.enrollments.filter(course=course).exists():
        messages.error(request, "Only enrolled students can review the course!")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.student = request.user
            review.course = course
            review.save()
            messages.success(request, "Review added successfully!")
            return redirect("course_detail", slug=slug)
    else:
        form = ReviewForm()

    return render(request, "courses/add_review.html", {"form": form, "course": course})


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


def learn(request):
    if request.method == "POST":
        form = LearnForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            email = form.cleaned_data["email"]
            message = form.cleaned_data["message"]

            # Prepare email content
            email_subject = f"Learning Interest: {subject}"
            email_body = render_to_string(
                "emails/learn_interest.html",
                {
                    "subject": subject,
                    "email": email,
                    "message": message,
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
                messages.success(request, "Thank you for your interest! We'll be in touch soon.")
                return redirect("index")
            except Exception as e:
                print(f"Error sending email: {e}")
                messages.error(request, "Sorry, there was an error sending your inquiry. Please try again later.")
    else:
        initial_data = {}
        if request.GET.get("subject"):
            initial_data["subject"] = request.GET.get("subject")
        form = LearnForm(initial=initial_data)

    return render(request, "learn.html", {"form": form})


def teach(request):
    if request.method == "POST":
        form = TeachForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            email = form.cleaned_data["email"]
            expertise = form.cleaned_data["expertise"]

            # Prepare email content
            email_subject = f"Teaching Application: {subject}"
            email_body = render_to_string(
                "emails/teach_application.html",
                {
                    "subject": subject,
                    "email": email,
                    "expertise": expertise,
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
                messages.success(request, "Thank you for your application! We'll review it and get back to you soon.")
                return redirect("index")
            except Exception as e:
                print(f"Error sending email: {e}")
                messages.error(request, "Sorry, there was an error sending your application. Please try again later.")
    else:
        initial_data = {}
        if request.GET.get("subject"):
            initial_data["subject"] = request.GET.get("subject")
        form = TeachForm(initial=initial_data)

    return render(request, "teach.html", {"form": form})


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
        courses = courses.filter(subject=subject)

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
    }

    return render(request, "courses/search.html", context)


@login_required
def create_payment_intent(request, slug):
    """Create a payment intent for Stripe."""
    course = get_object_or_404(Course, slug=slug)

    # Ensure user has a pending enrollment
    get_object_or_404(Enrollment, student=request.user, course=course, status="pending")

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


def handle_referral(user, referrer_code):
    """Handle referral rewards when a new user registers or enrolls."""
    try:
        referrer = Profile.objects.get(referral_code=referrer_code)

        # Set the referrer
        user.profile.referred_by = referrer
        user.profile.save()

        # If the referrer is a teacher, check if this is their first student
        if referrer.is_teacher and referrer.total_referrals == 1:
            referrer.add_referral_earnings(5)
            send_referral_reward_email(referrer.user, user, 5, "first_student")

        # For regular users, reward is given when the referred user enrolls
        # This is handled in the enroll_course view
    except Profile.DoesNotExist:
        pass


def send_referral_reward_email(user, referred_user, amount, reward_type):
    """Send email notification about referral reward."""
    subject = "You've earned a referral reward!"
    if reward_type == "first_student":
        message = (
            f"Congratulations! You've earned ${amount} for getting your first student "
            f"{referred_user.get_full_name()}!"
        )
    else:
        message = (
            f"Congratulations! You've earned ${amount} because {referred_user.get_full_name()} "
            f"enrolled in their first course!"
        )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


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
    return render(request, "web/forum/category.html", {"category": category, "topics": topics})


def forum_topic(request, category_slug, topic_id):
    """Display a forum topic and its replies."""
    topic = get_object_or_404(ForumTopic, id=topic_id, category__slug=category_slug)

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
    return render(request, "web/forum/topic.html", {"topic": topic, "replies": replies})


@login_required
def create_topic(request, category_slug):
    """Create a new forum topic."""
    category = get_object_or_404(ForumCategory, slug=category_slug)

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

    return render(request, "web/forum/create_topic.html", {"category": category, "form": form})


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


# @login_required
# def logout_view(request):
#     if request.method == "POST":
#         logout(request)
#         return redirect("index")
#     return redirect("index")


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
    """Dashboard view for students showing their enrollments, progress, and upcoming sessions."""
    if request.user.profile.is_teacher:
        messages.error(request, "This dashboard is for students only.")
        return redirect("profile")

    enrollments = Enrollment.objects.filter(student=request.user).select_related("course")
    upcoming_sessions = Session.objects.filter(
        course__enrollments__student=request.user, start_time__gt=timezone.now()
    ).order_by("start_time")[:5]

    # Get progress for each enrollment
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

    # Calculate average progress
    avg_progress = round(total_progress / len(progress_data)) if progress_data else 0

    context = {
        "enrollments": enrollments,
        "upcoming_sessions": upcoming_sessions,
        "progress_data": progress_data,
        "avg_progress": avg_progress,
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

    context = {
        "courses": courses,
        "upcoming_sessions": upcoming_sessions,
        "course_stats": course_stats,
        "completion_rate": (total_completed / total_students * 100) if total_students > 0 else 0,
        "total_earnings": round(total_earnings, 2),
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
        total_amount = 0

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

        # Clear the cart
        cart.items.all().delete()

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
                "total": total_amount,
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
    session = get_object_or_404(Session, id=session_id)

    # Check if user is the course teacher
    if request.user != session.course.teacher:
        messages.error(request, "Only the course teacher can edit sessions!")
        return redirect("course_detail", slug=session.course.slug)

    if request.method == "POST":
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, "Session updated successfully!")
            return redirect("course_detail", slug=session.course.slug)
    else:
        form = SessionForm(instance=session)

    return render(request, "courses/edit_session.html", {"form": form, "session": session, "course": session.course})


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
            messages.success(request, f"Forum category '{category.name}' created successfully!")
            return redirect("forum_category", slug=category.slug)
    else:
        form = ForumCategoryForm()

    return render(request, "web/forum/create_category.html", {"form": form})


@login_required
def edit_topic(request, topic_id):
    """Edit an existing forum topic."""
    topic = get_object_or_404(ForumTopic, id=topic_id)

    # Check if user is the author of the topic
    if request.user != topic.author:
        messages.error(request, "You don't have permission to edit this topic.")
        return redirect("forum_topic", category_slug=topic.category.slug, topic_id=topic.id)

    if request.method == "POST":
        form = ForumTopicForm(request.POST)
        if form.is_valid():
            topic.title = form.cleaned_data["title"]
            topic.content = form.cleaned_data["content"]
            topic.save()
            messages.success(request, "Topic updated successfully!")
            return redirect("forum_topic", category_slug=topic.category.slug, topic_id=topic.id)
    else:
        form = ForumTopicForm(initial={"title": topic.title, "content": topic.content})

    return render(
        request,
        "web/forum/create_topic.html",
        {"form": form, "category": topic.category, "is_edit": True, "topic": topic},
    )


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


def current_weekly_challenge(request):
    current_challenge = Challenge.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()
    # Check if the user has submitted the current challenge
    user_submission = None
    if request.user.is_authenticated and current_challenge:
        user_submission = ChallengeSubmission.objects.filter(user=request.user, challenge=current_challenge).first()

    return render(
        request,
        "web/current_weekly_challenge.html",
        {
            "current_challenge": current_challenge,
            "user_submission": user_submission,  # Pass the user's submission to the template
        },
    )


def challenge_detail(request, week_number):
    challenge = get_object_or_404(Challenge, week_number=week_number)
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


@login_required
def challenge_submit(request, week_number):
    challenge = get_object_or_404(Challenge, week_number=week_number)
    # Check if the user has already submitted this challenge
    existing_submission = ChallengeSubmission.objects.filter(user=request.user, challenge=challenge).first()

    if existing_submission:
        return redirect("challenge_detail", week_number=week_number)

    if request.method == "POST":
        form = ChallengeSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = request.user
            submission.challenge = challenge
            submission.save()
            messages.success(request, "Your submission has been recorded!")
            return redirect("challenge_detail", week_number=week_number)
    else:
        form = ChallengeSubmissionForm()

    return render(request, "web/challenge_submit.html", {"challenge": challenge, "form": form})


@require_GET
def fetch_video_title(request):
    url = request.GET.get("url")
    if not url:
        return JsonResponse({"error": "URL parameter is required"}, status=400)

    try:
        response = requests.get(url)
        response.raise_for_status()
        # Extract title from response headers or content
        title = response.headers.get("title", "")
        if not title:
            # Try to extract title from HTML content
            content = response.text
            title_match = re.search(r"<title>(.*?)</title>", content)
            title = title_match.group(1) if title_match else "Untitled Video"
        return JsonResponse({"title": title})
    except requests.RequestException:
        return JsonResponse({"error": "Failed to fetch video title"}, status=500)


@login_required
def goods_list(request):
    """List all goods available for sale."""
    goods = Goods.objects.filter(teacher=request.user)
    return render(request, "goods/goods_list.html", {"goods": goods})


@login_required
def goods_detail(request, pk):
    """View details of a specific product."""
    item = get_object_or_404(Goods, pk=pk)
    return render(request, "goods/goods_detail.html", {"item": item})


@login_required
def goods_create(request):
    """Allow teachers to create goods."""
    if request.method == "POST":
        form = GoodsForm(request.POST, request.FILES)
        if form.is_valid():
            goods = form.save(commit=False)
            goods.teacher = request.user  # Assign logged-in user as the teacher
            goods.save()
            return redirect("goods_list")
    else:
        form = GoodsForm()
    return render(request, "goods/goods_form.html", {"form": form})


@login_required
def create_goods_payment_intent(request, pk):
    """Create a Stripe Payment Intent for purchasing goods."""
    item = get_object_or_404(Goods, pk=pk)

    # Check if stock is available
    if item.stock <= 0:
        return JsonResponse({"error": "This item is out of stock."}, status=400)

    try:
        intent = stripe.PaymentIntent.create(
            amount=int(item.final_price() * 100),  # Convert price to cents
            currency="usd",
            metadata={"goods_id": item.id, "user_id": request.user.id},
        )
        return JsonResponse({"clientSecret": intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=403)


@csrf_exempt
def stripe_goods_webhook(request):
    """Handle Stripe payment events via webhook."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        handle_successful_goods_payment(payment_intent)
    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object
        handle_failed_goods_payment(payment_intent)

    return HttpResponse(status=200)


def handle_successful_goods_payment(payment_intent):
    """Process a successful payment and create an order."""
    goods_id = payment_intent.metadata.get("goods_id")
    user_id = payment_intent.metadata.get("user_id")

    goods = get_object_or_404(Goods, id=goods_id)
    user = get_object_or_404(User, id=user_id)

    # Ensure there is enough stock
    if goods.stock <= 0:
        return

    # Create order and order item
    order = Order.objects.create(
        user=user,
        total_price=goods.final_price(),
        status="completed",
        payment_status="paid",
        transaction_id=payment_intent.id,
    )

    OrderItem.objects.create(
        order=order,
        goods=goods,
        quantity=1,
        price_at_purchase=goods.final_price(),
    )

    # Deduct stock
    goods.stock -= 1
    goods.save()

    # Send confirmation email
    send_order_confirmation(order)


def handle_failed_goods_payment(payment_intent):
    """Handle failed payment by marking order as failed."""
    user_id = payment_intent.metadata.get("user_id")

    try:
        user = User.objects.get(id=user_id)
        order = Order.objects.filter(user=user, status="pending").last()

        if order:
            order.status = "failed"
            order.save()
    except (Goods.DoesNotExist, User.DoesNotExist, Order.DoesNotExist):
        pass  # Log error if needed


def send_order_confirmation(order):
    """Send an email confirmation after a successful order."""
    subject = "Your Order Confirmation"
    message = (
        f"Thank you for your purchase! Your order for {order.items.first().goods.name} "
        f"has been confirmed.\nTotal Price: ${order.total_price}"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=True,
    )


@login_required
def order_management(request):
    """Allow teachers to manage orders for their goods."""
    orders = Order.objects.filter(items__goods__teacher=request.user).distinct()
    return render(request, "goods/order_management.html", {"orders": orders})


@login_required
def order_list(request):
    """List all orders for the logged-in user."""
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "goods/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    """View details of a specific order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "goods/order_detail.html", {"order": order})


@login_required
def analytics_dashboard(request):
    """Provide insights into sales, revenue, and customer engagement."""
    total_sales = Order.objects.filter(status="completed").count()
    total_revenue = Order.objects.filter(status="completed").aggregate(Sum("total_price"))["total_price__sum"] or 0
    unique_customers = Order.objects.filter(status="completed").values("user").distinct().count()

    # Top-selling products
    top_products = (
        OrderItem.objects.values("goods__name").annotate(total_sold=Count("goods")).order_by("-total_sold")[:5]
    )

    # Top customers
    top_customers = (
        Order.objects.values("user__username").annotate(total_spent=Sum("total_price")).order_by("-total_spent")[:5]
    )

    context = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "unique_customers": unique_customers,
        "top_products": top_products,
        "top_customers": top_customers,
    }

    return render(request, "goods/analytics_dashboard.html", context)
