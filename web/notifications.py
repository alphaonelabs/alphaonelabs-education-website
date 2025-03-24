import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction  # Moved here
from django.template.loader import render_to_string
from django.utils import timezone

from .models import CourseMaterial, Enrollment, Notification, NotificationPreference, Session
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
    subject = notification_data["title"]
    html_message = render_to_string(
        "emails/notification.html",
        {"user": user, "notification": notification},
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
        {"student": enrollment.student, "course": enrollment.course, "teacher": enrollment.course.teacher},
    )
    send_mail(
        subject,
        "",
        settings.DEFAULT_FROM_EMAIL,
        [enrollment.student.email],
        html_message=html_message,
    )


def notify_teacher_new_enrollment(enrollment):
    """Notify teacher about new student enrollment."""
    subject = f"New Student Enrolled in {enrollment.course.title}"
    html_message = render_to_string(
        "emails/new_enrollment_notification.html",
        {"student": enrollment.student, "course": enrollment.course},
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
            {"student": enrollment.student, "session": session, "course": session.course},
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
            {"student": enrollment.student, "course": course, "update_message": update_message},
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
    upcoming_sessions = Session.objects.filter(start_time__gt=now, start_time__lte=reminder_window)
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


def notify_waiting_room_fulfilled(waiting_room, course):
    """
    Notify all participants in a waiting room that a course has been created.

    Args:
        waiting_room (WaitingRoom): The waiting room that was fulfilled
        course (Course): The course that was created from the waiting room
    """
    subject = f"New Course Created: {course.title}"

    # Notify all participants
    for participant in waiting_room.participants.all():
        notification_data = {
            "title": subject,
            "message": f"A new course has been created based on a waiting room you joined: '{waiting_room.title}'. "
            f"The course '{course.title}' is now available for enrollment.",
            "notification_type": "success",
        }

        # Send notification
        send_notification(participant, notification_data)

        # Send email with more details
        html_message = render_to_string(
            "emails/waiting_room_fulfilled.html",
            {
                "user": participant,
                "waiting_room": waiting_room,
                "course": course,
                "site_url": settings.SITE_URL,
            },
        )

        send_mail(
            subject,
            "",  # Plain text version - we're only sending HTML
            settings.DEFAULT_FROM_EMAIL,
            [participant.email],
            html_message=html_message,
        )

    # Also notify the creator if they're not already a participant
    if waiting_room.creator not in waiting_room.participants.all():
        notification_data = {
            "title": subject,
            "message": f"A new course has been created based on your waiting room: '{waiting_room.title}'. "
            f"The course '{course.title}' is now available.",
            "notification_type": "success",
        }
        send_notification(waiting_room.creator, notification_data)


def send_email(subject, message, recipient_list):
    """
    Send an email to the specified recipients and notify Slack.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        slack_message = f"📧 Email sent\nSubject: {subject}\nTo: {', '.join(recipient_list)}"
        send_slack_notification(slack_message)
        return True
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(error_msg)
        slack_message = f"❌ Email sending failed\nSubject: {subject}\nTo: {', '.join(recipient_list)}\nError: {str(e)}"
        send_slack_notification(slack_message)
        return False


def notify_team_invite(invite):
    """Notify a user about an invitation to join a team goal."""
    notification_data = {
        "title": f"Team Invitation: {invite.goal.title}",
        "message": f"{invite.sender.username} has invited you to join the team goal '{invite.goal.title}'.",
        "notification_type": "info",
    }
    try:
        send_notification(invite.recipient, notification_data)
    except Exception as e:
        logger.error(f"Failed to send team invite notification: {str(e)}")
    try:
        slack_message = (
            f"🤝 {invite.sender.username} invited {invite.recipient.username} to team goal '{invite.goal.title}'"
        )
        send_slack_notification(slack_message)
    except Exception as e:
        logger.error(f"Failed to send Slack notification for team invite: {str(e)}")


def notify_team_invite_response(invite):
    """Notify the sender about the response to their team invitation."""
    status_text = "accepted" if invite.status == "accepted" else "declined"
    notification_data = {
        "title": f"Team Invitation {status_text.capitalize()}: {invite.goal.title}",
        "message": f"{invite.recipient.username} has {status_text} your invite to join goal: '{invite.goal.title}'.",
        "notification_type": "success" if invite.status == "accepted" else "info",
    }
    send_notification(invite.sender, notification_data)


def notify_team_goal_completion(goal, user):
    """Notify team members when a user marks their contribution as complete."""
    if user != goal.creator:
        notification_data = {
            "title": f"Team Goal Progress: {goal.title}",
            "message": f"{user.username} has completed their contribution to the team goal '{goal.title}'.",
            "notification_type": "success",
        }
        send_notification(goal.creator, notification_data)
    if goal.completion_percentage == 100:
        for member in goal.members.all():
            if member.user != user:
                notification_data = {
                    "title": f"Team Goal Completed: {goal.title}",
                    "message": f"The team goal '{goal.title}' has been completed by all members!",
                    "notification_type": "success",
                }
                send_notification(member.user, notification_data)


def send_assignment_reminders():
    """Send early and final reminders for upcoming assignment deadlines."""
    now = timezone.now()

    # Define reminder windows
    early_window = now + timedelta(days=3)  # Early reminders: assignments due in next 3 days.
    final_window = now + timedelta(hours=24)  # Final reminders: assignments due in next 24 hours.

    # Process Early Reminders
    early_assignments = CourseMaterial.objects.filter(
        material_type="assignment", due_date__gt=now, due_date__lte=early_window, reminder_sent=False
    )

    for assignment in early_assignments:
        with transaction.atomic():
            course = assignment.course
            enrollments = course.enrollments.filter(status="approved")
            for enrollment in enrollments:
                student = enrollment.student
                preferences, _ = NotificationPreference.objects.get_or_create(user=student)
                days_before_deadline = (assignment.due_date - now).days
                if days_before_deadline <= preferences.reminder_days_before:
                    subject = f"Upcoming Assignment Deadline: {assignment.title}"
                    html_message = render_to_string(
                        "emails/assignment_reminder.html",
                        {
                            "student": student,
                            "assignment": assignment,
                            "course": course,
                            "due_date": assignment.due_date,
                            "days_remaining": days_before_deadline,
                        },
                    )
                    if preferences.in_app_notifications:
                        send_notification(
                            student,
                            {
                                "title": subject,
                                "message": f"Your assignment '{assignment.title}'\
                                     is due in {days_before_deadline} days.",
                                "notification_type": "warning",
                            },
                        )
                    if preferences.email_notifications:
                        send_mail(
                            subject,
                            "",  # Plain text version
                            settings.DEFAULT_FROM_EMAIL,
                            [student.email],
                            html_message=html_message,
                        )
            assignment.reminder_sent = True
            assignment.save()

    # Process Final Reminders
    final_assignments = CourseMaterial.objects.filter(
        material_type="assignment", due_date__gt=now, due_date__lte=final_window, final_reminder_sent=False
    )

    for assignment in final_assignments:
        course = assignment.course
        enrollments = course.enrollments.filter(status="approved")
        for enrollment in enrollments:
            student = enrollment.student
            preferences, _ = NotificationPreference.objects.get_or_create(user=student)
            hours_remaining = int((assignment.due_date - now).total_seconds() // 3600)
            if hours_remaining <= preferences.reminder_hours_before:
                subject = f"Final Reminder: Assignment Due Soon: {assignment.title}"
                html_message = render_to_string(
                    "emails/assignment_reminder.html",
                    {
                        "student": student,
                        "assignment": assignment,
                        "course": course,
                        "due_date": assignment.due_date,
                        "hours_remaining": hours_remaining,
                    },
                )
                if preferences.in_app_notifications:
                    send_notification(
                        student,
                        {
                            "title": subject,
                            "message": f"Final reminder: Your assignment\
                                 '{assignment.title}' is due in {hours_remaining} hours.",
                            "notification_type": "warning",
                        },
                    )
                if preferences.email_notifications:
                    send_mail(
                        subject,
                        "",  # Plain text version
                        settings.DEFAULT_FROM_EMAIL,
                        [student.email],
                        html_message=html_message,
                    )
        assignment.final_reminder_sent = True
        assignment.save()
