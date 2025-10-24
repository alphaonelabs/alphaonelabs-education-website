from allauth.account.signals import user_signed_up
from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import CourseProgress, Enrollment, LearningStreak, Profile, Session, SessionAttendance
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


def invalidate_progress_cache(user):
    """Helper function to invalidate a student's progress cache."""
    cache_key = f"user_progress_{user.id}"
    cache.delete(cache_key)


@receiver(post_save, sender=Enrollment)
@receiver(post_delete, sender=Enrollment)
def invalidate_enrollment_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when an enrollment is added or deleted."""
    invalidate_progress_cache(instance.student)


@receiver(post_save, sender=SessionAttendance)
@receiver(post_delete, sender=SessionAttendance)
def invalidate_attendance_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when a session attendance record is added or deleted."""
    invalidate_progress_cache(instance.student)


@receiver(post_save, sender=CourseProgress)
@receiver(post_delete, sender=CourseProgress)
def invalidate_course_progress_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when a student's course progress is updated or deleted."""
    invalidate_progress_cache(instance.enrollment.student)


@receiver(m2m_changed, sender=CourseProgress.completed_sessions.through)
def invalidate_completed_sessions_cache(sender, instance, action, **kwargs):
    """Invalidate the progress cache when a completed session is added, removed, or cleared."""
    if action in ["post_add", "post_remove", "post_clear"]:
        invalidate_progress_cache(instance.enrollment.student)


@receiver(post_save, sender=LearningStreak)
def invalidate_streak_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when a student's learning streak is updated."""
    invalidate_progress_cache(instance.user)


@receiver(post_save, sender=Session)
@receiver(post_delete, sender=Session)
def invalidate_session_cache(sender, instance, **kwargs):
    """Invalidate the progress cache for all students when a session is added or deleted."""
    enrollments = Enrollment.objects.filter(course=instance.course)
    for enrollment in enrollments:
        invalidate_progress_cache(enrollment.student)


@receiver(post_save, sender=Profile)
def sync_profile_encrypted_fields(sender, instance, created, **kwargs):
    """
    Automatically sync encrypted fields from User model when Profile is saved.
    This ensures encrypted fields stay in sync with User model.
    """
    # Prevent recursion - only sync if we're not already in a save operation
    if not hasattr(instance, "_syncing_encrypted_fields"):
        instance._syncing_encrypted_fields = True
        try:
            # Sync encrypted fields from user
            needs_save = False
            if instance.user.email and instance.encrypted_email != instance.user.email:
                instance.encrypted_email = instance.user.email
                needs_save = True
            if instance.user.first_name and instance.encrypted_first_name != instance.user.first_name:
                instance.encrypted_first_name = instance.user.first_name
                needs_save = True
            if instance.user.last_name and instance.encrypted_last_name != instance.user.last_name:
                instance.encrypted_last_name = instance.user.last_name
                needs_save = True

            if needs_save:
                Profile.objects.filter(pk=instance.pk).update(
                    encrypted_email=instance.encrypted_email,
                    encrypted_first_name=instance.encrypted_first_name,
                    encrypted_last_name=instance.encrypted_last_name,
                )
        finally:
            delattr(instance, "_syncing_encrypted_fields")
