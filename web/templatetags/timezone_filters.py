from datetime import datetime

from django import template
from django.utils import timezone
from django.utils.timezone import is_aware, localtime, make_aware

register = template.Library()


@register.filter(name="localtime")
def localtime_filter(value) -> any:
    """
    Convert a datetime to the user's local timezone.
    Usage: {{ value|localtime }}
    Returns the converted datetime, the original value if not
    a datetime, or an empty string if None.
    """
    if value is None:
        return ""

    # Make sure value is a datetime object
    if not isinstance(value, datetime):
        return value

    # Make naive datetime timezone-aware if needed
    if not is_aware(value):
        try:
            value = make_aware(value)
        except (ValueError, TypeError):
            # If we can't make it aware, just return it as is
            return value

    return localtime(value)

@register.filter(name="localtime_format")
def localtime_format(value, format_string=None) -> str:
    """
    Format a datetime in the user's local timezone.
    Usage: {{ value|localtime_format:"Y-m-d H:i" }}
    Returns the formatted datetime string, the string representation
    if not a datetime, or an empty string if None.
    """
    if value is None:
        return ""

    # Check if value is a datetime object
    if not isinstance(value, datetime):
        return str(value)  # Just return the string representation if not a datetime

    # Make naive datetime timezone-aware if needed
    if not is_aware(value):
        try:
            value = make_aware(value)
        except (ValueError, TypeError):
            # If we can't make it aware, apply the format without timezone conversion
            if format_string:
                try:
                    return value.strftime(format_string)
                except ValueError:
                    # Fallback if format string is invalid
                    return value.isoformat()
            return value.isoformat()

    # Convert to the current active timezone (which has been set by the middleware)
    local_dt = localtime(value)

    # Format according to the specified format or default
    if format_string:
        try:
            return local_dt.strftime(format_string)
        except ValueError:
            # Fallback if format string is invalid
            return local_dt.isoformat()
    return local_dt.isoformat()

@register.simple_tag(takes_context=True)
def current_timezone(context):
    """
    Return the currently active timezone name.
    Usage: {% current_timezone %}
    """
    request = context.get("request")
    if request and request.session.get("user_timezone"):
        return request.session.get("user_timezone")
    return timezone.get_current_timezone_name()
