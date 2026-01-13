# Generated manually

from django.db import migrations


def create_default_milestones(apps, schema_editor):
    """Create default referral milestones."""
    ReferralMilestone = apps.get_model("web", "ReferralMilestone")

    # Define default milestones
    milestones = [
        {
            "referral_count": 1,
            "monetary_reward": 5.00,
            "points_reward": 100,
            "title": "First Referral",
            "description": "Congrats on your first successful referral! You're on your way to becoming a top referrer.",
            "badge_icon": "fas fa-star",
        },
        {
            "referral_count": 5,
            "monetary_reward": 10.00,
            "points_reward": 250,
            "title": "Bronze Referrer",
            "description": "You've referred 5 users! You're making a real impact in our community.",
            "badge_icon": "fas fa-medal",
        },
        {
            "referral_count": 10,
            "monetary_reward": 25.00,
            "points_reward": 500,
            "title": "Silver Referrer",
            "description": "Wow! 10 referrals! You're a valuable advocate for Alpha One Labs.",
            "badge_icon": "fas fa-trophy",
        },
        {
            "referral_count": 25,
            "monetary_reward": 75.00,
            "points_reward": 1000,
            "title": "Gold Referrer",
            "description": "Amazing! 25 referrals shows exceptional commitment to growing our community.",
            "badge_icon": "fas fa-crown",
        },
        {
            "referral_count": 50,
            "monetary_reward": 200.00,
            "points_reward": 2500,
            "title": "Platinum Referrer",
            "description": "Outstanding achievement! 50 referrals makes you an elite member of our community.",
            "badge_icon": "fas fa-gem",
        },
        {
            "referral_count": 100,
            "monetary_reward": 500.00,
            "points_reward": 5000,
            "title": "Diamond Referrer",
            "description": "Incredible! 100 referrals! You're a legendary ambassador for Alpha One Labs.",
            "badge_icon": "fas fa-diamond",
        },
    ]

    # Create milestone objects
    for milestone_data in milestones:
        ReferralMilestone.objects.get_or_create(
            referral_count=milestone_data["referral_count"],
            defaults={
                "monetary_reward": milestone_data["monetary_reward"],
                "points_reward": milestone_data["points_reward"],
                "title": milestone_data["title"],
                "description": milestone_data["description"],
                "badge_icon": milestone_data["badge_icon"],
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0063_referral_milestones_and_rewards"),
    ]

    operations = [
        migrations.RunPython(create_default_milestones, reverse_code=migrations.RunPython.noop),
    ]
