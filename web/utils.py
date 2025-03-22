from datetime import timedelta

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone


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


def calculate_user_points_for_period(user, days=None):
    """Calculate points for a user within a specific period

    Args:
        user: The user to calculate points for
        days: Number of days to include (None for all-time)
    """
    from web.models import Points

    queryset = Points.objects.filter(user=user)

    if days is not None:
        period_start = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(awarded_at__gte=period_start)

    return queryset.aggregate(total=models.Sum("amount"))["total"] or 0


def calculate_user_weekly_points(user):
    """Calculate weekly points for a user"""
    return calculate_user_points_for_period(user, days=7)


def calculate_user_monthly_points(user):
    """Calculate monthly points for a user"""
    return calculate_user_points_for_period(user, days=30)


def calculate_user_total_points(user):
    """Calculate total points for a user"""
    return calculate_user_points_for_period(user)


def calculate_user_streak(user):
    """Calculate current streak for a user"""
    from web.models import Points

    streak_record = Points.objects.filter(user=user, point_type="streak").order_by("-awarded_at").first()

    if not streak_record:
        return 0

    # Extract streak value with improved parsing
    if "Current streak:" in streak_record.reason:
        try:
            import re

            match = re.search(r"Current streak:\s*(\d+)", streak_record.reason)
            if match:
                return int(match.group(1))
        except (ValueError, IndexError):
            return 0
    return 0


def calculate_and_update_user_streak(user, challenge):
    from web.models import Challenge, ChallengeSubmission, Points

    # Calculate and update streak
    last_week = challenge.week_number - 1
    if last_week > 0:
        last_week_challenge = Challenge.objects.filter(week_number=last_week).first()
        if last_week_challenge:
            last_week_submission = ChallengeSubmission.objects.filter(user=user, challenge=last_week_challenge).exists()

            if last_week_submission:
                # User completed consecutive weeks, calculate their current streak
                streak_points = Points.objects.filter(user=user, point_type="streak").order_by("-awarded_at").first()

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


def get_user_global_rank(user):
    """Calculate a user's global rank based on total points."""
    from django.db.models import Sum

    from web.models import Points

    # Skip if user is a teacher or not authenticated
    if not user or not user.is_authenticated or user.profile.is_teacher:
        return None

    # Get user's points
    user_points = calculate_user_total_points(user)

    # If user has no points, they're not ranked
    if not user_points:
        return None

    # Count users with more points (excluding teachers)
    users_ahead = (
        Points.objects.filter(user__profile__is_teacher=False)
        .values("user")
        .annotate(total=Sum("amount"))
        .filter(total__gt=user_points)
        .count()
    )

    # User's rank is users ahead + 1 (tied users all get same rank)
    return users_ahead + 1


def get_user_weekly_rank(user):
    """Calculate a user's weekly rank based on points in the last 7 days."""
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    from web.models import Points

    # Skip if user is a teacher or not authenticated
    if not user or not user.is_authenticated or user.profile.is_teacher:
        return None

    # Define time period
    one_week_ago = timezone.now() - timedelta(days=7)

    # Get user's weekly points
    user_points = calculate_user_weekly_points(user)

    # If user has no weekly points, they're not ranked
    if not user_points:
        return None

    # Count users with more weekly points (excluding teachers)
    users_ahead = (
        Points.objects.filter(awarded_at__gte=one_week_ago, user__profile__is_teacher=False)
        .values("user")
        .annotate(total=Sum("amount"))
        .filter(total__gt=user_points)
        .count()
    )

    # User's rank is users ahead + 1 (tied users all get same rank)
    return users_ahead + 1


def get_user_monthly_rank(user):
    """Calculate a user's monthly rank based on points in the last 30 days."""
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    from web.models import Points

    # Skip if user is a teacher or not authenticated
    if not user or not user.is_authenticated or user.profile.is_teacher:
        return None

    # Define time period
    one_month_ago = timezone.now() - timedelta(days=30)

    # Get user's monthly points
    user_points = calculate_user_monthly_points(user)

    # If user has no monthly points, they're not ranked
    if not user_points:
        return None

    # Count users with more monthly points (excluding teachers)
    users_ahead = (
        Points.objects.filter(awarded_at__gte=one_month_ago, user__profile__is_teacher=False)
        .values("user")
        .annotate(total=Sum("amount"))
        .filter(total__gt=user_points)
        .count()
    )

    # User's rank is users ahead + 1 (tied users all get same rank)
    return users_ahead + 1


def get_leaderboard(current_user=None, period=None, limit=10):
    """
    Get leaderboard data based on period (None/global, weekly, or monthly)
    Returns a list of users with their points sorted by total points
    Excludes teachers from the leaderboard
    """
    from datetime import timedelta

    from django.db.models import Count, Sum
    from django.utils import timezone

    from web.models import Points, User

    # Define time periods if needed
    one_week_ago = timezone.now() - timedelta(days=7)
    one_month_ago = timezone.now() - timedelta(days=30)

    # Get leaderboard entries from database with proper sorting
    if period == "weekly":
        # Get weekly leaderboard
        leaderboard_entries = (
            Points.objects.filter(awarded_at__gte=one_week_ago, user__profile__is_teacher=False)
            .values("user")
            .annotate(points=Sum("amount"))
            .filter(points__gt=0)
            .order_by("-points")[:limit]
        )

    elif period == "monthly":
        # Get monthly leaderboard
        leaderboard_entries = (
            Points.objects.filter(awarded_at__gte=one_month_ago, user__profile__is_teacher=False)
            .values("user")
            .annotate(points=Sum("amount"))
            .filter(points__gt=0)
            .order_by("-points")[:limit]
        )

    else:  # Global leaderboard
        # Get global leaderboard
        leaderboard_entries = (
            Points.objects.filter(user__profile__is_teacher=False)
            .values("user")
            .annotate(points=Sum("amount"))
            .filter(points__gt=0)
            .order_by("-points")[:limit]
        )

    # Get user IDs and fetch user data efficiently
    user_ids = [entry["user"] for entry in leaderboard_entries]
    users = {
        user.id: user
        for user in User.objects.filter(id__in=user_ids).annotate(
            challenge_count=Count("challengesubmission", distinct=True)
        )
    }

    # Prepare the final leaderboard with all necessary data
    leaderboard_data = []

    # Calculate ranks properly accounting for ties
    current_rank = 1
    prev_points = None

    for i, entry in enumerate(leaderboard_entries):
        user_id = entry["user"]
        points = entry["points"]
        user = users.get(user_id)

        if user:
            # Handle ties properly (same points = same rank)
            if prev_points is not None and points < prev_points:
                current_rank = i + 1

            # Build entry data
            entry_data = {
                "user": user,
                "rank": current_rank,  # Store calculated rank in entry
                "points": points,
                "weekly_points": calculate_user_weekly_points(user) if period != "weekly" else points,
                "monthly_points": calculate_user_monthly_points(user) if period != "monthly" else points,
                "total_points": calculate_user_total_points(user) if period is not None else points,
                "current_streak": calculate_user_streak(user),
                "challenge_count": getattr(user, "challenge_count", 0),
            }
            leaderboard_data.append(entry_data)
            prev_points = points

    # Calculate user's rank using the appropriate function
    user_rank = None
    if current_user and current_user.is_authenticated and not current_user.profile.is_teacher:
        if period == "weekly":
            user_rank = get_user_weekly_rank(current_user)
        elif period == "monthly":
            user_rank = get_user_monthly_rank(current_user)
        else:
            user_rank = get_user_global_rank(current_user)

    return leaderboard_data, user_rank
