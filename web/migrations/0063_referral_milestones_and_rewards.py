# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("web", "0062_update_waitingroom_for_sessions"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferralMilestone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "referral_count",
                    models.PositiveIntegerField(
                        unique=True, help_text="Number of referrals needed to reach milestone"
                    ),
                ),
                (
                    "monetary_reward",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Cash reward in USD for reaching this milestone",
                        max_digits=10,
                    ),
                ),
                (
                    "points_reward",
                    models.PositiveIntegerField(default=0, help_text="Points awarded for reaching this milestone"),
                ),
                (
                    "title",
                    models.CharField(
                        max_length=100, help_text="Milestone title (e.g., 'Bronze Referrer', 'Silver Referrer')"
                    ),
                ),
                ("description", models.TextField(blank=True, help_text="Description of the milestone achievement")),
                (
                    "badge_icon",
                    models.CharField(
                        default="fas fa-trophy",
                        help_text="FontAwesome icon class for the milestone badge",
                        max_length=100,
                    ),
                ),
                ("is_active", models.BooleanField(default=True, help_text="Whether this milestone is currently active")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Referral Milestone",
                "verbose_name_plural": "Referral Milestones",
                "ordering": ["referral_count"],
            },
        ),
        migrations.CreateModel(
            name="ReferralReward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("earned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "monetary_amount",
                    models.DecimalField(decimal_places=2, help_text="Cash reward earned", max_digits=10),
                ),
                ("points_amount", models.PositiveIntegerField(help_text="Points earned")),
                (
                    "is_claimed",
                    models.BooleanField(default=False, help_text="Whether the monetary reward has been claimed"),
                ),
                (
                    "milestone",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="rewards", to="web.referralmilestone"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_rewards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Referral Reward",
                "verbose_name_plural": "Referral Rewards",
                "ordering": ["-earned_at"],
                "unique_together": {("user", "milestone")},
            },
        ),
    ]
