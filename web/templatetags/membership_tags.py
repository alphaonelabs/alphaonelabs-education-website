from typing import Optional, Union

from django import template
from django.contrib.auth import get_user_model

User = get_user_model()
register = template.Library()


@register.filter
def format_price(value: Optional[Union[float, int]] = None, period: Optional[str] = None) -> str:
    """Format price based on billing period."""
    if value is None:
        return "$0"
    if period == "yearly":
        return f"${value}/year"
    if period == "monthly":
        return f"${value}/month"
    return f"${value}"


@register.simple_tag
def is_active_membership(user: "User") -> bool:
    """Check if a user has an active membership."""
    if hasattr(user, "membership"):
        return user.membership.is_active
    return False


@register.simple_tag
def get_membership_plan_name(user: "User") -> Optional[str]:
    """Get the name of a user's membership plan."""
    if hasattr(user, "membership") and user.membership.is_active:
        return user.membership.plan.name
    return None


@register.filter
def format_feature(value: str) -> str:
    """Format a feature description for display."""
    return value.strip()
