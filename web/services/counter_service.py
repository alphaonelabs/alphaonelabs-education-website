from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from web.models import CounterStatistic, CourseProgress, Enrollment, User, UserActivity, WebRequest


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
    def update_total_learners():
        """Calculate and update the count of total registered users."""
        # Count all non-staff users
        users_count = User.objects.filter(is_staff=False).count()

        counter, created = CounterStatistic.objects.get_or_create(counter_type="total_learners")
        counter.value = users_count
        counter.save()
        return users_count

    @staticmethod
    def update_total_enrollments():
        """Calculate and update the count of total enrollments."""
        enrollments_count = Enrollment.objects.count()

        counter, created = CounterStatistic.objects.get_or_create(counter_type="total_enrollments")
        counter.value = enrollments_count
        counter.save()
        return enrollments_count

    @staticmethod
    def update_total_courses_completed():
        """Calculate and update the count of total completed courses."""
        # Count course progress records with 100% completion
        completed_courses = CourseProgress.objects.filter(completion_percentage=100).count()

        counter, created = CounterStatistic.objects.get_or_create(counter_type="total_courses_completed")
        counter.value = completed_courses
        counter.save()
        return completed_courses

    @staticmethod
    def update_total_quizzes_taken():
        """Calculate and update the count of total completed quizzes."""
        # Count completed user quizzes
        from web.models import UserQuiz

        completed_quizzes = UserQuiz.objects.filter(completed=True).count()

        counter, created = CounterStatistic.objects.get_or_create(counter_type="total_quizzes_taken")
        counter.value = completed_quizzes
        counter.save()
        return completed_quizzes

    @staticmethod
    def update_all_counters():
        """Update all counter statistics."""
        CounterService.update_active_users_count()
        CounterService.update_enrollments_today()
        CounterService.update_total_learners()
        CounterService.update_total_enrollments()
        CounterService.update_total_courses_completed()
        CounterService.update_total_quizzes_taken()
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
        CounterStatistic.increment_counter("total_enrollments")
        CounterService.update_active_users_count()


@receiver(post_save, sender="web.UserQuiz")  # Using string reference to avoid circular imports
def quiz_completed(sender, instance, created, **kwargs):
    """Update counters when a quiz is completed."""
    if not created and instance.completed:  # If an existing attempt is marked as completed
        # Record activity
        UserActivity.record_activity(
            user=instance.user,
            activity_type="quiz_completion",
            content_object=instance.quiz,
            show_full_name=False,
            location="",
        )

        # Update counters
        CounterStatistic.increment_counter("quizzes_completed")
        CounterStatistic.increment_counter("total_quizzes_taken")


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
        CounterStatistic.increment_counter("total_courses_completed")
