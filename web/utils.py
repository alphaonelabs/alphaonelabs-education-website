import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


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

    streak_record = (
        Points.objects.filter(user=user, point_type="streak", current_streak__isnull=False)
        .order_by("-awarded_at")
        .first()
    )

    return streak_record.current_streak if streak_record else 0


def calculate_and_update_user_streak(user, challenge):
    from django.db import transaction

    from web.models import Challenge, ChallengeSubmission, Points

    with transaction.atomic():
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
                        Points.objects.filter(user=user, point_type="streak").order_by("-awarded_at").first()
                    )

                    current_streak = 1
                    if streak_points and streak_points.current_streak:
                        current_streak = streak_points.current_streak + 1

                    # Record the updated streak
                    Points.objects.create(
                        user=user,
                        challenge=None,
                        amount=0,  # Just a record, no points awarded for the streak itself
                        reason=f"Current streak: {current_streak}",
                        point_type="streak",
                        current_streak=current_streak,
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


# Helper functions that would be defined elsewhere
def get_cached_leaderboard_data(user, period, limit, cache_key, cache_timeout):
    """Get leaderboard data from cache or fetch fresh data"""
    data = cache.get(cache_key)
    if data is None:
        entries, rank = get_leaderboard(user, period=period, limit=limit)
        cache.set(cache_key, (entries, rank), cache_timeout)
    else:
        entries, rank = data
    return entries, rank


def get_user_points(user):
    """Calculate points for a user with error handling"""
    try:
        return {
            "total": calculate_user_total_points(user),
            "weekly": calculate_user_weekly_points(user),
            "monthly": calculate_user_monthly_points(user),
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error calculating user points: {e}")
        return {"total": 0, "weekly": 0, "monthly": 0}


def get_cached_challenge_entries():
    """Get challenge entries from cache or fetch fresh data"""
    from web.models import ChallengeSubmission

    challenge_data = cache.get("challenge_leaderboard")
    if challenge_data is None:
        try:
            challenge_entries = (
                ChallengeSubmission.objects.select_related("user", "challenge")
                .filter(points_awarded__gt=0)
                .order_by("-points_awarded")[:10]
            )
            cache.set("challenge_leaderboard", challenge_entries, 60 * 15)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving challenge entries: {e}")
            challenge_entries = []
    else:
        challenge_entries = challenge_data
    return challenge_entries


def create_leaderboard_context(
    global_entries,
    weekly_entries,
    monthly_entries,
    challenge_entries,
    user_rank,
    user_weekly_rank,
    user_monthly_rank,
    user_total_points,
    user_weekly_points,
    user_monthly_points,
):
    """Create context dictionary for the leaderboard template"""
    return {
        "global_entries": global_entries,
        "weekly_entries": weekly_entries,
        "monthly_entries": monthly_entries,
        "challenge_entries": challenge_entries,
        "user_rank": user_rank,
        "user_weekly_rank": user_weekly_rank,
        "user_monthly_rank": user_monthly_rank,
        "user_total_points": user_total_points,
        "user_weekly_points": user_weekly_points,
        "user_monthly_points": user_monthly_points,
    }


def geocode_address(address):
    """
    Convert a text address to latitude and longitude coordinates using Nominatim API.
    Returns a tuple of (latitude, longitude) or None if geocoding fails.
    Follows OpenStreetMap's Nominatim usage policy with built-in rate limiting.
    """
    # Rate limiting - ensure we don't exceed 1 request per second
    rate_limit_key = "nominatim_last_request"
    last_request_time = cache.get(rate_limit_key)

    if last_request_time:
        import time

        current_time = time.time()
        time_since_last_request = current_time - last_request_time

        if time_since_last_request < 1.0:
            # Sleep to maintain 1 request per second rate limit
            time.sleep(1.0 - time_since_last_request)

    if not address:
        logger.debug("Empty address provided to geocode_address")
        return None

    # Check cache first
    normalized_address = address.strip().lower()
    cache_key = f"geocode:{hash(normalized_address)}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.debug(f"Using cached geocoding result for: {address}")
        return cached_result

    # Nominatim API URL with custom User-Agent as recommended
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}

    # Headers to comply with Nominatim usage policy
    headers = {"User-Agent": "AlphaOneEducation/1.0 (support@alphaonelabs.com)"}

    try:
        # Update last request timestamp
        import time

        cache.set(rate_limit_key, time.time(), 60 * 5)  # Keep for 5 minutes
        # Use requests with custom headers and params
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()

        if data:
            # Get the first result
            first_result = data[0]
            result = (float(first_result["lat"]), float(first_result["lon"]))

            # Cache the result for 24 hours
            cache.set(cache_key, result, 60 * 60 * 24)

            return result

        logger.warning(f"No geocoding results found for address: {address}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during geocoding: {e}")
        return None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None
