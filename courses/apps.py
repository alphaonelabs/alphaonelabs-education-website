from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'
    verbose_name = _('Courses')
    
    def ready(self):
        """Perform initialization when the app is ready."""
        # Import signal handlers
        from . import signals
