from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """Divides the given value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return None