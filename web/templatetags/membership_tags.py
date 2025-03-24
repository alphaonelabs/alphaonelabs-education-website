from django import template
from django.utils.safestring import mark_safe
from web.models import UserMembership

register = template.Library()

@register.simple_tag(takes_context=True)
def get_user_membership(context):
    """
    Returns the user's membership if they have one, otherwise returns None.
    Usage: {% get_user_membership as membership %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return None
    
    try:
        membership = UserMembership.objects.get(user=request.user)
        return membership
    except UserMembership.DoesNotExist:
        return None

@register.simple_tag(takes_context=True)
def has_active_membership(context):
    """
    Returns True if the user has an active membership, otherwise False.
    Usage: {% has_active_membership as is_member %}
    """
    request = context.get('request')
    if not request or not request.user or not request.user.is_authenticated:
        return False
    
    try:
        membership = UserMembership.objects.get(user=request.user)
        return membership.is_active
    except UserMembership.DoesNotExist:
        return False

@register.filter
def format_price(price, period='monthly'):
    """
    Formats the price for display.
    Usage: {{ plan.price_monthly|format_price:'monthly' }}
    """
    if price is None:
        return "N/A"
    
    if period == 'yearly':
        return f"${price}/year"
    else:
        return f"${price}/month"

@register.simple_tag
def get_membership_badge(membership, css_class=''):
    """
    Returns a badge displaying the membership status.
    Usage: {% get_membership_badge membership %}
    """
    if not membership:
        return mark_safe(f'<span class="badge badge-secondary {css_class}">No Membership</span>')
    
    status = membership.status
    badge_classes = {
        'active': 'badge-success',
        'trialing': 'badge-info',
        'past_due': 'badge-warning',
        'canceled': 'badge-danger',
        'incomplete': 'badge-secondary',
        'incomplete_expired': 'badge-secondary',
        'unpaid': 'badge-warning',
    }
    
    badge_class = badge_classes.get(status, 'badge-secondary')
    return mark_safe(f'<span class="badge {badge_class} {css_class}">{status.title()}</span>') 