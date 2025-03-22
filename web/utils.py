from datetime import timedelta

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone

# from web.models import (
#     Challenge,
#     ChallengeSubmission,
#     Points,
#     User,
#     Cart,
# )


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
    from web.models import Cart

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
    from web.models import Points
    return Points.objects.filter(user=user).aggregate(total=models.Sum("amount"))["total"] or 0


def calculate_user_weekly_points(user):
    """Calculate weekly points for a user"""
    from web.models import Points

    one_week_ago = timezone.now() - timedelta(days=7)

    return (
        Points.objects.filter(user=user, awarded_at__gte=one_week_ago).aggregate(total=models.Sum("amount"))["total"]
        or 0
    )


def calculate_user_monthly_points(user):
    """Calculate monthly points for a user"""
    from web.models import Points

    one_month_ago = timezone.now() - timedelta(days=30)
    return (
        Points.objects.filter(user=user, awarded_at__gte=one_month_ago).aggregate(total=models.Sum("amount"))["total"]
        or 0
    )


def calculate_user_streak(user):
    """Calculate current streak for a user"""
    from web.models import Points
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
    from web.models import User

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

    # Determine filter and sort field based on period
    filter_field = "total_points"
    sort_field = "points"
    if period == "weekly":
        filter_field = "weekly_points_sum"
        sort_field = "weekly_points"
    elif period == "monthly":
        filter_field = "monthly_points_sum"
        sort_field = "monthly_points"
    
    # Filter users based on the period
    users = users.filter(**{f"{filter_field}__gt": 0})

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

    # Sort by the determined field
    leaderboard_data.sort(key=lambda x: x[sort_field], reverse=True)

    return leaderboard_data[:limit]


def calculate_and_update_user_streak(user, challenge):
    from web.models import Challenge, ChallengeSubmission, Points
    # Calculate and update streak
    last_week = challenge.week_number - 1
    if last_week > 0:
        last_week_challenge = Challenge.objects.filter(week_number=last_week).first()
        if last_week_challenge:
            last_week_submission = ChallengeSubmission.objects.filter(
                user=user, challenge=last_week_challenge
            ).exists()

            if last_week_submission:
                # User completed consecutive weeks, calculate their current streak
                streak_points = (
                    Points.objects.filter(user=user, point_type="streak")
                    .order_by("-awarded_at")
                    .first()
                )

                current_streak = 1
                if streak_points and "Current streak:" in streak_points.reason:
                    try:
                        current_streak = int(streak_points.reason.split(":")[1].strip()) + 1
                    except (ValueError, IndexError):
                        current_streak = 2
                else:
                    current_streak = 2

                # Record the updated streak
                Points.objects.create(
                    user=user,
                    challenge=None,
                    amount=0,  # Just a record, no points awarded for the streak itself
                    reason=f"Current streak: {current_streak}",
                    point_type="streak",
                )

                # Award bonus points for streak milestones
                if current_streak > 0 and current_streak % 5 == 0:
                    bonus = current_streak // 5 * 5  # 5 points per milestone
                    Points.objects.create(
                        user=user,
                        challenge=None,
                        amount=bonus,
                        reason=f"Streak milestone bonus ({current_streak} weeks)",
                        point_type="bonus",
                    )

