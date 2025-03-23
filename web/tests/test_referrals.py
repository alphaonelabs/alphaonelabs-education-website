from django.contrib.auth.models import User
from django.db import models
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from web.models import Course, Enrollment, Profile, Subject, WebRequest


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="optional",
    ACCOUNT_EMAIL_REQUIRED=True,
    ACCOUNT_USERNAME_REQUIRED=False,
    ACCOUNT_AUTHENTICATION_METHOD="email",
)
class ReferralTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        # Create test users
        cls.user1 = User.objects.create_user(username="user1", email="user1@example.com", password="testpass123")
        cls.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="testpass123")
        cls.user3 = User.objects.create_user(username="user3", email="user3@example.com", password="testpass123")

        # Set up referral codes
        cls.user1.profile.referral_code = "CODE1"
        cls.user1.profile.save()
        cls.user2.profile.referral_code = "CODE2"
        cls.user2.profile.save()
        cls.user3.profile.referral_code = "CODE3"
        cls.user3.profile.save()

        # Create some referrals
        cls.referred_user1 = User.objects.create_user(
            username="referred1", email="referred1@example.com", password="testpass123"
        )
        cls.referred_user1.profile.referred_by = cls.user1.profile
        cls.referred_user1.profile.save()

        cls.referred_user2 = User.objects.create_user(
            username="referred2", email="referred2@example.com", password="testpass123"
        )
        cls.referred_user2.profile.referred_by = cls.user1.profile
        cls.referred_user2.profile.save()

        # Create a subject first
        cls.subject = Subject.objects.create(name="Test Subject", slug="test-subject")

        # Create a course and enrollments
        cls.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            subject=cls.subject,
            teacher=cls.user1,
            price=100,
            max_students=50,
            slug="test-course",
        )

        Enrollment.objects.create(student=cls.referred_user1, course=cls.course, status="approved")

        WebRequest.objects.create(path="/some/path?ref=CODE1", ip_address="127.0.0.1", user=cls.referred_user1, count=5)

    def test_referral_stats_calculation(self):
        """Test that referral statistics are calculated correctly"""
        # Get referral stats for user1
        stats = Profile.objects.annotate(
            total_signups=models.Count("referrals"),
            total_enrollments=models.Count(
                "referrals__user__enrollments", filter=models.Q(referrals__user__enrollments__status="approved")
            ),
            total_clicks=models.Count(
                "referrals__user",
                filter=models.Q(
                    referrals__user__username__in=WebRequest.objects.filter(path__contains="ref=").values_list(
                        "user", flat=True
                    )
                ),
            ),
        ).get(user=self.user1)

        # Check the stats
        self.assertEqual(stats.total_signups, 2)  # Two referred users
        self.assertEqual(stats.total_enrollments, 1)  # One enrollment
        self.assertEqual(stats.total_clicks, 1)  # One web request with clicks

    def test_mini_leaderboard_on_homepage(self):
        """Test that the mini leaderboard appears correctly on the homepage"""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

        # Check that the top referrers are in the context
        self.assertIn("top_referrers", response.context)

        # Get the top referrers from the context
        top_referrers = response.context["top_referrers"]

        # Check that user1 is the top referrer
        self.assertTrue(len(top_referrers) > 0)
        top_referrer = top_referrers[0]
        self.assertEqual(top_referrer.user, self.user1)
        self.assertEqual(top_referrer.total_signups, 2)
        self.assertEqual(top_referrer.total_enrollments, 1)
        self.assertEqual(top_referrer.total_clicks, 1)

    def test_referral_earnings(self):
        """Test that referral earnings are added correctly"""
        initial_earnings = self.user1.profile.referral_earnings
        self.user1.profile.add_referral_earnings(5)
        self.assertEqual(self.user1.profile.referral_earnings, initial_earnings + 5)

    def test_referral_code_generation(self):
        """Test that referral codes are generated correctly"""
        new_user = User.objects.create_user(username="newuser", email="newuser@example.com", password="testpass123")
        self.assertIsNotNone(new_user.profile.referral_code)
        self.assertNotEqual(new_user.profile.referral_code, "")

    def test_referral_code_uniqueness(self):
        """Test that referral codes are unique"""
        used_codes = set(Profile.objects.values_list("referral_code", flat=True))
        self.assertEqual(len(used_codes), len(Profile.objects.all()))
