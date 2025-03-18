from allauth.account.signals import user_signed_up
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Certificate, Enrollment
from .utils import send_slack_message


@receiver(user_signed_up)
def notify_slack_on_signup(request, user, **kwargs):
    """Send a Slack notification when a new user signs up"""
    is_teacher = getattr(user.profile, "is_teacher", False)
    user_type = "Teacher" if is_teacher else "Student"

    message = (
        f"🎉 New {user_type} Signup!\n" f"*Name:* {user.get_full_name() or user.email}\n" f"*Email:* {user.email}\n"
    )

    send_slack_message(message)


@receiver(post_save, sender=Enrollment)
def create_certificate_on_completion(sender, instance, created, **kwargs):
    # Check if an enrollment was updated (not created) and marked as completed.
    if not created and instance.status == "completed":
        # Create a certificate only if one doesn't already exist for this student/course.
        if not Certificate.objects.filter(user=instance.student, course=instance.course).exists():
            Certificate.objects.create(user=instance.student, course=instance.course)
