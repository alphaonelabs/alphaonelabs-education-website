from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def format_price(value, period=None):
    """Format price based on billing period."""
    if value is None:
        return "$0"
    return f"${value}"

@register.simple_tag
def is_active_membership(user):
    """Check if a user has an active membership."""
    if hasattr(user, 'membership'):
        return user.membership.is_active
    return False

@register.simple_tag
def get_membership_plan_name(user):
    """Get the name of a user's membership plan."""
    if hasattr(user, 'membership') and user.membership.is_active:
        return user.membership.plan.name
    return None
