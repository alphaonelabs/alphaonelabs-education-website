from django.conf import settings
from django.core.mail import send_mail


def handle_referral(user, referrer_code):
    """Handle referral rewards when a new user registers or enrolls."""
    try:
        from .models import Profile

        referrer = Profile.objects.get(referral_code=referrer_code)

        # Set the referrer
        user.profile.referred_by = referrer
        user.profile.save()

        # Check for referral milestones and award rewards
        rewards_earned = referrer.check_referral_milestones()

        # Send notification emails for any milestone rewards earned
        for reward in rewards_earned:
            send_milestone_reward_email(referrer.user, reward)

        # If the referrer is a teacher, check if this is their first student
        if referrer.is_teacher and referrer.total_referrals == 1:
            referrer.add_referral_earnings(5)
            send_referral_reward_email(referrer.user, user, 5, "first_student")

        # For regular users, reward is given when the referred user enrolls
        # This is handled in the enroll_course view
    except Profile.DoesNotExist:
        pass


def send_referral_reward_email(user, referred_user, amount, reward_type):
    """Send email notification about referral reward."""
    subject = "You've earned a referral reward!"
    if reward_type == "first_student":
        message = (
            f"Congratulations! You've earned ${amount} for getting your first student "
            f"{referred_user.get_full_name()}!"
        )
    else:
        message = (
            f"Congratulations! You've earned ${amount} because {referred_user.get_full_name()} "
            f"enrolled in their first course!"
        )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


def send_milestone_reward_email(user, reward):
    """Send email notification about milestone reward achievement."""
    subject = f"🎉 Referral Milestone Achievement: {reward.milestone.title}!"

    message = f"""
Congratulations {user.get_full_name() or user.username}!

You've reached a new referral milestone: {reward.milestone.title}!

{reward.milestone.description}

Your Rewards:
"""

    if reward.monetary_amount > 0:
        message += f"💰 Cash Reward: ${reward.monetary_amount}\n"

    if reward.points_amount > 0:
        message += f"⭐ Points Earned: {reward.points_amount}\n"

    message += f"""
Total Referrals: {user.profile.total_referrals}
Total Referral Earnings: ${user.profile.referral_earnings}

Keep sharing and earning! Check out your next milestone in your profile.

Thanks for being an amazing advocate!
The Alpha One Labs Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )

