import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Enrollment, Notification, Session
from .slack import send_slack_notification

logger = logging.getLogger(__name__)


def send_notification(user, notification_data):
    """Send a notification to a user and store it in the database."""
    notification = Notification.objects.create(
        user=user,
        title=notification_data["title"],
        message=notification_data["message"],
        notification_type=notification_data.get("notification_type", "info"),
    )

    # Send email notification
    subject = notification_data["title"]
    html_message = render_to_string(
        "emails/notification.html",
        {
            "user": user,
            "notification": notification,
        },
    )
    send_mail(
        subject,
        "",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )

    return notification


def get_user_notifications(user, mark_as_read=False):
    """Get all notifications for a user."""
    notifications = Notification.objects.filter(user=user).order_by("-created_at")
    if mark_as_read:
        notifications.filter(read=False).update(read=True)
    return notifications


def send_enrollment_confirmation(enrollment):
    """Send confirmation email to student after successful enrollment."""
    subject = f"Welcome to {enrollment.course.title}!"
    html_message = render_to_string(
        "emails/enrollment_confirmation.html",
        {
            "student": enrollment.student,
            "course": enrollment.course,
            "teacher": enrollment.course.teacher,
        },
    )
    send_mail(
        subject,
        "",  # Plain text version - we're only sending HTML
        settings.DEFAULT_FROM_EMAIL,
        [enrollment.student.email],
        html_message=html_message,
    )


def notify_teacher_new_enrollment(enrollment):
    """Notify teacher about new student enrollment."""
    subject = f"New Student Enrolled in {enrollment.course.title}"
    html_message = render_to_string(
        "emails/new_enrollment_notification.html",
        {
            "student": enrollment.student,
            "course": enrollment.course,
        },
    )
    send_mail(
        subject,
        "",
        settings.DEFAULT_FROM_EMAIL,
        [enrollment.course.teacher.email],
        html_message=html_message,
    )


def notify_session_reminder(session):
    """Send reminder email to enrolled students about upcoming session."""
    subject = f"Reminder: Upcoming Session - {session.title}"
    enrollments = session.course.enrollments.filter(status="approved")

    for enrollment in enrollments:
        html_message = render_to_string(
            "emails/session_reminder.html",
            {
                "student": enrollment.student,
                "session": session,
                "course": session.course,
            },
        )
        send_mail(
            subject,
            "",
            settings.DEFAULT_FROM_EMAIL,
            [enrollment.student.email],
            html_message=html_message,
        )


def notify_course_update(course, update_message):
    """Notify enrolled students about course updates."""
    subject = f"Course Update - {course.title}"
    enrollments = course.enrollments.filter(status="approved")

    for enrollment in enrollments:
        html_message = render_to_string(
            "emails/course_update.html",
            {
                "student": enrollment.student,
                "course": course,
                "update_message": update_message,
            },
        )
        send_mail(
            subject,
            "",
            settings.DEFAULT_FROM_EMAIL,
            [enrollment.student.email],
            html_message=html_message,
        )


def send_upcoming_session_reminders():
    """Send reminders for sessions happening in the next 24 hours."""
    now = timezone.now()
    reminder_window = now + timedelta(hours=24)

    upcoming_sessions = Session.objects.filter(
        start_time__gt=now,
        start_time__lte=reminder_window,
    )

    for session in upcoming_sessions:
        notify_session_reminder(session)


def send_weekly_progress_updates():
    """Send weekly progress updates to enrolled students."""
    enrollments = Enrollment.objects.filter(status="approved")

    for enrollment in enrollments:
        progress = enrollment.progress
        if not progress:
            continue

        subject = f"Weekly Progress Update - {enrollment.course.title}"
        html_message = render_to_string(
            "emails/weekly_progress.html",
            {
                "student": enrollment.student,
                "course": enrollment.course,
                "progress": progress,
                "completion_percentage": progress.completion_percentage,
                "attendance_rate": progress.attendance_rate,
            },
        )
        send_mail(
            subject,
            "",
            settings.DEFAULT_FROM_EMAIL,
            [enrollment.student.email],
            html_message=html_message,
        )


def send_email(subject, message, recipient_list):
    """
    Send an email to the specified recipients and notify Slack.

    Args:
        subject (str): The email subject
        message (str): The email message body
        recipient_list (list): List of email addresses to send to

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )

        # Send Slack notification
        slack_message = f"📧 Email sent\nSubject: {subject}\nTo: {', '.join(recipient_list)}"
        send_slack_notification(slack_message)

        return True
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(error_msg)

        # Notify Slack about the failure
        slack_message = f"❌ Email sending failed\nSubject: {subject}\nTo: {', '.join(recipient_list)}\nError: {str(e)}"
        send_slack_notification(slack_message)

        return False
