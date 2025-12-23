from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.test import Client, TestCase
from django.urls import reverse

from web.models import (
    Course,
    Enrollment,
    Points,
    Profile,
    ReferralMilestone,
    ReferralReward,
    Subject,
)


class ReferralMilestonesTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create test users
        self.referrer = User.objects.create_user(username="referrer", email="referrer@example.com", password="testpass123")
        self.referred_user1 = User.objects.create_user(
            username="referred1", email="referred1@example.com", password="testpass123"
        )
        self.referred_user2 = User.objects.create_user(
            username="referred2", email="referred2@example.com", password="testpass123"
        )
        self.referred_user3 = User.objects.create_user(
            username="referred3", email="referred3@example.com", password="testpass123"
        )
        self.referred_user4 = User.objects.create_user(
            username="referred4", email="referred4@example.com", password="testpass123"
        )
        self.referred_user5 = User.objects.create_user(
            username="referred5", email="referred5@example.com", password="testpass123"
        )

        # Create referral milestones
        self.milestone1 = ReferralMilestone.objects.create(
            referral_count=1,
            monetary_reward=Decimal("5.00"),
            points_reward=100,
            title="First Referral",
            description="Your first referral!",
            badge_icon="fas fa-star",
        )
        self.milestone5 = ReferralMilestone.objects.create(
            referral_count=5,
            monetary_reward=Decimal("25.00"),
            points_reward=500,
            title="Bronze Referrer",
            description="5 referrals achieved!",
            badge_icon="fas fa-medal",
        )

        # Create a subject and course for testing enrollments
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            subject=self.subject,
            teacher=self.referrer,
            price=100,
            max_students=50,
            slug="test-course",
        )

    def test_referral_milestone_creation(self):
        """Test that referral milestones are created correctly."""
        self.assertEqual(ReferralMilestone.objects.count(), 2)
        self.assertEqual(self.milestone1.referral_count, 1)
        self.assertEqual(self.milestone1.monetary_reward, Decimal("5.00"))
        self.assertEqual(self.milestone1.points_reward, 100)

    def test_first_referral_milestone(self):
        """Test that first referral triggers milestone reward."""
        # Set referrer relationship
        self.referred_user1.profile.referred_by = self.referrer.profile
        self.referred_user1.profile.save()

        # Check milestone
        rewards = self.referrer.profile.check_referral_milestones()

        # Should have earned one reward
        self.assertEqual(len(rewards), 1)
        self.assertEqual(rewards[0].milestone, self.milestone1)
        self.assertEqual(rewards[0].monetary_amount, Decimal("5.00"))
        self.assertEqual(rewards[0].points_amount, 100)

        # Check earnings were added
        self.referrer.profile.refresh_from_db()
        self.assertEqual(self.referrer.profile.referral_earnings, Decimal("5.00"))

        # Check points were awarded
        points = Points.objects.filter(user=self.referrer, reason__contains="Referral milestone").first()
        self.assertIsNotNone(points)
        self.assertEqual(points.amount, 100)

    def test_multiple_milestones(self):
        """Test that reaching 5 referrals triggers both milestones."""
        # Add 5 referrals
        referrals = [self.referred_user1, self.referred_user2, self.referred_user3, self.referred_user4, self.referred_user5]
        for ref_user in referrals:
            ref_user.profile.referred_by = self.referrer.profile
            ref_user.profile.save()

        # Check milestones
        rewards = self.referrer.profile.check_referral_milestones()

        # Should have earned both milestones
        self.assertEqual(len(rewards), 2)

        # Check total earnings (5 + 25 = 30)
        self.referrer.profile.refresh_from_db()
        self.assertEqual(self.referrer.profile.referral_earnings, Decimal("30.00"))

        # Check total points (100 + 500 = 600)
        total_points = Points.objects.filter(user=self.referrer, reason__contains="Referral milestone").aggregate(
            total=models.Sum("amount")
        )["total"]
        self.assertEqual(total_points, 600)

    def test_no_duplicate_rewards(self):
        """Test that milestones are not awarded twice."""
        # Set referrer relationship
        self.referred_user1.profile.referred_by = self.referrer.profile
        self.referred_user1.profile.save()

        # Check milestone first time
        rewards1 = self.referrer.profile.check_referral_milestones()
        self.assertEqual(len(rewards1), 1)

        # Check milestone second time - should be empty
        rewards2 = self.referrer.profile.check_referral_milestones()
        self.assertEqual(len(rewards2), 0)

    def test_next_milestone_property(self):
        """Test next_referral_milestone property."""
        # With 0 referrals, next should be milestone1
        next_milestone = self.referrer.profile.next_referral_milestone
        self.assertEqual(next_milestone, self.milestone1)

        # Add 1 referral
        self.referred_user1.profile.referred_by = self.referrer.profile
        self.referred_user1.profile.save()

        # Next should be milestone5
        self.referrer.profile.refresh_from_db()
        next_milestone = self.referrer.profile.next_referral_milestone
        self.assertEqual(next_milestone, self.milestone5)

    def test_referral_progress_percentage(self):
        """Test referral progress percentage calculation."""
        # With 0 referrals
        progress = self.referrer.profile.referral_progress_percentage
        self.assertEqual(progress, 0)

        # With 1 referral (1/1 = 100% to first milestone)
        self.referred_user1.profile.referred_by = self.referrer.profile
        self.referred_user1.profile.save()
        self.referrer.profile.refresh_from_db()
        progress = self.referrer.profile.referral_progress_percentage
        self.assertEqual(progress, 25.0)  # 1 out of 5 for next milestone = 25%

    def test_referral_dashboard_view(self):
        """Test that referral dashboard view loads correctly."""
        self.client.login(username="referrer", password="testpass123")

        # Add some referrals
        self.referred_user1.profile.referred_by = self.referrer.profile
        self.referred_user1.profile.save()

        # Trigger milestone
        self.referrer.profile.check_referral_milestones()

        response = self.client.get(reverse("referral_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("referrals", response.context)
        self.assertIn("earned_rewards", response.context)
        self.assertIn("all_milestones", response.context)
        self.assertEqual(response.context["total_referrals"], 1)

    def test_referral_reward_model(self):
        """Test ReferralReward model creation."""
        reward = ReferralReward.objects.create(
            user=self.referrer, milestone=self.milestone1, monetary_amount=Decimal("5.00"), points_amount=100
        )

        self.assertEqual(str(reward), f"{self.referrer.username} - {self.milestone1.title}")
        self.assertFalse(reward.is_claimed)

    def test_inactive_milestones_not_awarded(self):
        """Test that inactive milestones are not awarded."""
        # Make milestone inactive
        self.milestone1.is_active = False
        self.milestone1.save()

        # Add referral
        self.referred_user1.profile.referred_by = self.referrer.profile
        self.referred_user1.profile.save()

        # Check milestones
        rewards = self.referrer.profile.check_referral_milestones()

        # Should have no rewards
        self.assertEqual(len(rewards), 0)
