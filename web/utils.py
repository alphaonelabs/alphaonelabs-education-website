from datetime import timedelta

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import Sum


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


def get_leaderboard(current_user, period=None, limit=10):
    """
    Get leaderboard data based on period (None/global, weekly, or monthly)
    Returns a list of users with their points sorted by total points
    Excludes teachers from the leaderboard
    """
    from django.db.models import Count, Sum
    from web.models import User, ChallengeSubmission, Points, Profile
    from django.utils import timezone
    from datetime import timedelta

    # Define time periods if needed
    one_week_ago = timezone.now() - timedelta(days=7)
    one_month_ago = timezone.now() - timedelta(days=30)
    
    # Get users directly from database with proper sorting
    if period == "weekly":
        # Get weekly leaderboard ordered by points
        leaderboard_entries = Points.objects.filter(
            awarded_at__gte=one_week_ago,
            user__profile__is_teacher=False
        ).values('user').annotate(
            points=Sum('amount')
        ).filter(
            points__gt=0
        ).order_by('-points')[:limit]
        
        # Get full user data
        user_ids = [entry['user'] for entry in leaderboard_entries]
        users = {user.id: user for user in User.objects.filter(id__in=user_ids).annotate(
            challenge_count=Count('challengesubmission', distinct=True)
        )}
        
    elif period == "monthly":
        # Get monthly leaderboard ordered by points
        leaderboard_entries = Points.objects.filter(
            awarded_at__gte=one_month_ago,
            user__profile__is_teacher=False
        ).values('user').annotate(
            points=Sum('amount')
        ).filter(
            points__gt=0
        ).order_by('-points')[:limit]
        
        # Get full user data
        user_ids = [entry['user'] for entry in leaderboard_entries]
        users = {user.id: user for user in User.objects.filter(id__in=user_ids).annotate(
            challenge_count=Count('challengesubmission', distinct=True)
        )}
        
    else:  # Global leaderboard
        # Get global leaderboard ordered by points
        leaderboard_entries = Points.objects.filter(
            user__profile__is_teacher=False
        ).values('user').annotate(
            points=Sum('amount')
        ).filter(
            points__gt=0
        ).order_by('-points')[:limit]
        
        # Get full user data
        user_ids = [entry['user'] for entry in leaderboard_entries]
        users = {user.id: user for user in User.objects.filter(id__in=user_ids).annotate(
            challenge_count=Count('challengesubmission', distinct=True)
        )}
    
    # Prepare the final leaderboard with all necessary data
    leaderboard_data = []
    rank = 1
    user_rank = 0
    
    for entry in leaderboard_entries:
        user_id = entry['user']
        points = entry['points']
        user = users.get(user_id)
        if current_user == user:
            user_rank = rank
        if user:
            
            # Calculate additional stats for each user
            entry_data = {
                "user": user,
                "rank": rank,
                "points": points,
                "weekly_points": calculate_user_weekly_points(user) if period != "weekly" else points,
                "monthly_points": calculate_user_monthly_points(user) if period != "monthly" else points,
                "total_points": calculate_user_total_points(user) if period is not None else points,
                "current_streak": calculate_user_streak(user),
                "challenge_count": getattr(user, 'challenge_count', 0),
            }
            rank += 1
            leaderboard_data.append(entry_data)
    
    print("{{{{{{{{{}}}}}}}}}", leaderboard_data)
    return leaderboard_data, user_rank

# Fix the rank calculation in views.py by adding these helper functions:
def get_user_weekly_rank(user):
    """Calculate a user's rank based on weekly points."""
    from django.db import models
    from django.utils import timezone
    from datetime import timedelta
    from web.models import Points, Profile
    
    one_week_ago = timezone.now() - timedelta(days=7)
    
    # Get all non-teacher users with weekly points, sorted by total
    all_users = list(Points.objects.filter(
        awarded_at__gte=one_week_ago,
        user__profile__is_teacher=False  # Exclude teachers
    ).values("user").annotate(
        total=models.Sum("amount")
    ).order_by("-total"))
    
    # If no users have points this week, return None
    if not all_users:
        return None
    
    # Find the user's position and handle ties
    current_rank = 1
    prev_points = None
    
    for i, entry in enumerate(all_users):
        current_points = entry["total"]
        
        # Handle ties - same points should have same rank
        if prev_points is not None and current_points < prev_points:
            # Points decreased, so rank should jump to account for previous ties
            current_rank = i + 1
        
        # Check if this is our user
        if entry["user"] == user.id:
            return current_rank
        
        prev_points = current_points
    
    # User not found in the list (no weekly points)
    return None


def get_user_monthly_rank(user):
    """Calculate a user's rank based on monthly points."""
    from django.db import models
    from django.utils import timezone
    from datetime import timedelta
    from web.models import Points, Profile
    
    one_month_ago = timezone.now() - timedelta(days=30)
    
    # Get all non-teacher users with monthly points, sorted by total
    all_users = list(Points.objects.filter(
        awarded_at__gte=one_month_ago,
        user__profile__is_teacher=False  # Exclude teachers
    ).values("user").annotate(
        total=models.Sum("amount")
    ).order_by("-total"))
    
    # If no users have points this month, return None
    if not all_users:
        return None
    
    # Find the user's position and handle ties
    current_rank = 1
    prev_points = None
    
    for i, entry in enumerate(all_users):
        current_points = entry["total"]
        
        # Handle ties - same points should have same rank
        if prev_points is not None and current_points < prev_points:
            # Points decreased, so rank should jump to account for previous ties
            current_rank = i + 1
        
        # Check if this is our user
        if entry["user"] == user.id:
            return current_rank
        
        prev_points = current_points
    
    # User not found in the list (no monthly points)
    return None


def get_user_global_rank(user):
    """
    Calculate a user's global rank based on total points.
    Properly handles ties (same points = same rank).
    """
    from django.db import models
    from django.db.models import Count, Sum
    from web.models import Points, User
    
    # Get all users with points, sorted by total points (descending)

    # leaderboard_entries = Points.objects.filter(
    #     awarded_at__gte=one_month_ago,
    #     user__profile__is_teacher=False
    # ).values('user').annotate(
    #     points=Sum('amount')
    # ).filter(
    #     points__gt=0
    # ).order_by('-points')[:limit]
        
    # user_ids = [entry['user'] for entry in leaderboard_entries]
    # users = {user.id: user for user in User.objects.filter(id__in=user_ids).annotate(
    #     challenge_count=Count('challengesubmission', distinct=True)
    # )}
    # print("5555555555555555555555555", users)
    # If the user has no points, they're not ranked
    # if not all_users:
    #     return None
    
    # # Find the user's position and handle ties
    # current_rank = 0
    # prev_points = None
    
    # for i, entry in enumerate(all_users):
    #     current_points = entry["total"]
        
    #     # print("users", i," ; " , entry["user"], " my:", user.id, current_points)
    #     # Handle ties - same points should have same rank
    #     if prev_points is not None and current_points < prev_points:
    #         # Points decreased, so rank should jump to account for previous ties
    #         current_rank = i + 1
        
    #     # Check if this is our user
    #     if entry["user"] == user.id:
    #         return current_rank

    #     prev_points = current_points
    
    # # User not found in the list (no points)
    return None


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

