from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from web.models import CounterStatistic, UserActivity, Enrollment, CourseProgress, WebRequest


class CounterService:
    """Service to manage counter statistics."""

    @staticmethod
    def update_active_users_count():
        """Calculate and update the count of active users in the last 15 minutes."""
        fifteen_minutes_ago = timezone.now() - timedelta(minutes=15)
        active_users_count = (
            WebRequest.objects.filter(created__gte=fifteen_minutes_ago).values("user").distinct().count()
        )

        counter, created = CounterStatistic.objects.get_or_create(counter_type="active_users")
        counter.value = active_users_count
        counter.save()
        return active_users_count

    @staticmethod
    def update_enrollments_today():
        """Calculate and update the count of enrollments today."""
        today = timezone.now().date()
        enrollments_count = Enrollment.objects.filter(enrollment_date__date=today).count()

        counter, created = CounterStatistic.objects.get_or_create(counter_type="enrollments_today")
        counter.value = enrollments_count
        counter.save()
        return enrollments_count

    @staticmethod
    def update_all_counters():
        """Update all counter statistics."""
        CounterService.update_active_users_count()
        CounterService.update_enrollments_today()
        # Add more counter updates as needed

    @staticmethod
    def get_recent_activities(limit=10):
        """Get the most recent user activities for display."""
        return UserActivity.objects.all()[:limit]


# Signal receivers to update counters and record activities


@receiver(post_save, sender=Enrollment)
def enrollment_created(sender, instance, created, **kwargs):
    """Update counters when a new enrollment is created."""
    if created:
        # Record activity
        UserActivity.record_activity(
            user=instance.student,
            activity_type="enrollment",
            content_object=instance.course,
            show_full_name=False,  # Respect privacy
            location="",  # Could get from user profile or request metadata
        )

        # Update counters
        CounterStatistic.increment_counter("enrollments_today")
        CounterService.update_active_users_count()


# @receiver(post_save, sender=QuizAttempt)  # Assuming you have a QuizAttempt model
# def quiz_completed(sender, instance, created, **kwargs):
#     """Update counters when a quiz is completed."""
#     if not created and instance.is_completed:  # If an existing attempt is marked as completed
#         # Record activity
#         UserActivity.record_activity(
#             user=instance.user,
#             activity_type='quiz_completion',
#             content_object=instance.quiz,
#             show_full_name=False,
#             location=''
#         )

#         # Update counters
#         CounterStatistic.increment_counter('quizzes_completed')


@receiver(post_save, sender=CourseProgress)
def course_completed(sender, instance, **kwargs):
    """Update counters when a course is completed."""
    if instance.completion_percentage == 100:
        # Record activity
        UserActivity.record_activity(
            user=instance.enrollment.student,
            activity_type="course_completion",
            content_object=instance.enrollment.course,
            show_full_name=False,
            location="",
        )

        # Update counters
        CounterStatistic.increment_counter("courses_completed")
