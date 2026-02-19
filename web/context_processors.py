import json
import os
from datetime import datetime

from django.conf import settings
from django.http import HttpRequest


def last_modified(_request: HttpRequest) -> dict[str, datetime | str]:
    """Add last_modified timestamp to the global template context."""
    try:
        # Use the project's root directory modification time
        timestamp = os.path.getmtime(settings.BASE_DIR)
        last_modified_time = datetime.fromtimestamp(timestamp)
    except Exception:
        last_modified_time = "Unknown"

    return {"last_modified": last_modified_time}


def invitation_notifications(request):
    if request.user.is_authenticated:
        pending_invites = request.user.received_group_invites.filter(status="pending").count()
        return {"pending_invites_count": pending_invites}
    return {}


def available_locales(_request: HttpRequest) -> dict[str, str]:
    """Expose available locales from Django settings to the template as JSON."""
    locales = [lang_code for lang_code, _ in settings.LANGUAGES]
    return {"available_locales": json.dumps(locales)}
