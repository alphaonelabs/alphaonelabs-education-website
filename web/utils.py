from datetime import timedelta

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone

from web.models import (
    Cart,
    Points,
    User,
)


def send_slack_message(message):
    """Send message to Slack webhook"""
    webhook_url = settings.SLACK_WEBHOOK_URL
    if not webhook_url:
        return False

    try:
        response = requests.post(webhook_url, json={"text": message})
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:.2f}"


def get_or_create_cart(request):
    """Helper function to get or create a cart for both logged in and guest users."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def calculate_user_total_points(user):
    """Calculate total points for a user"""
    return Points.objects.filter(user=user).aggregate(total=models.Sum("amount"))["total"] or 0


def calculate_user_weekly_points(user):
    """Calculate weekly points for a user"""
    one_week_ago = timezone.now() - timedelta(days=7)

    return (
        Points.objects.filter(user=user, awarded_at__gte=one_week_ago).aggregate(total=models.Sum("amount"))["total"]
        or 0
    )


def calculate_user_monthly_points(user):
    """Calculate monthly points for a user"""
    one_month_ago = timezone.now() - timedelta(days=30)
    return (
        Points.objects.filter(user=user, awarded_at__gte=one_month_ago).aggregate(total=models.Sum("amount"))["total"]
        or 0
    )


def calculate_user_streak(user):
    """Calculate current streak for a user"""
    streak_record = Points.objects.filter(user=user, point_type="streak").order_by("-awarded_at").first()

    if streak_record and "Current streak:" in streak_record.reason:
        try:
            return int(streak_record.reason.split(":")[1].strip())
        except (ValueError, IndexError):
            return 0
    return 0


def get_leaderboard(period=None, limit=10):
    """
    Get leaderboard data based on period (None for all-time, 'weekly', or 'monthly')
    Returns a list of users with their points sorted by total points
    """
    from django.db.models import Count, Q, Sum

    # Get time periods for filtering
    one_week_ago = timezone.now() - timedelta(days=7)
    one_month_ago = timezone.now() - timedelta(days=30)

    # Annotate users with their total points - using different annotation names
    users = User.objects.annotate(
        total_points=Sum("points__amount"),
        weekly_points_sum=Sum("points__amount", filter=Q(points__awarded_at__gte=one_week_ago)),
        monthly_points_sum=Sum("points__amount", filter=Q(points__awarded_at__gte=one_month_ago)),
        challenge_count=Count("challengesubmission", distinct=True),
    )

    # Filter users based on the period
    if period == "weekly":
        users = users.filter(weekly_points_sum__gt=0)
    elif period == "monthly":
        users = users.filter(monthly_points_sum__gt=0)
    else:
        users = users.filter(total_points__gt=0)

    # Streaks still need to be calculated individually as they're stored in the reason field
    leaderboard_data = []
    for user in users:
        current_streak = calculate_user_streak(user)
        entry_data = {
            "user": user,
            "points": user.total_points or 0,
            "weekly_points": user.weekly_points_sum or 0,
            "monthly_points": user.monthly_points_sum or 0,
            "current_streak": current_streak,
            "challenge_count": user.challenge_count,
        }
        leaderboard_data.append(entry_data)

    # Sort by the appropriate field based on period
    if period == "weekly":
        leaderboard_data.sort(key=lambda x: x["weekly_points"], reverse=True)
    elif period == "monthly":
        leaderboard_data.sort(key=lambda x: x["monthly_points"], reverse=True)
    else:
        leaderboard_data.sort(key=lambda x: x["points"], reverse=True)

    return leaderboard_data[:limit]
