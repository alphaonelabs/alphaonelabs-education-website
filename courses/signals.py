from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from .models import Course, Enrollment

User = get_user_model()

@receiver(post_save, sender=Enrollment)
def enrollment_created(sender, instance, created, **kwargs):
    """Handle post-save signal for Enrollment model."""
    if created:
        # Add any additional logic needed when a student enrolls in a course
        pass

@receiver(post_delete, sender=Enrollment)
def enrollment_deleted(sender, instance, **kwargs):
    """Handle post-delete signal for Enrollment model."""
    # Add any cleanup logic needed when an enrollment is deleted
    pass 