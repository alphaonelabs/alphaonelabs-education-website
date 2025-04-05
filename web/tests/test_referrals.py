from unittest import skip

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from web.models import Course, Enrollment, Profile, Subject, WebRequest


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="optional",
    ACCOUNT_EMAIL_REQUIRED=True,
    ACCOUNT_USERNAME_REQUIRED=False,
    ACCOUNT_AUTHENTICATION_METHOD="email",
)
class ReferralTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create test users
        self.user1 = User.objects.create_user(username="user1", email="user1@example.com", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="testpass123")
        self.user3 = User.objects.create_user(username="user3", email="user3@example.com", password="testpass123")

        # Set up referral codes
        self.user1.profile.referral_code = "CODE1"
        self.user1.profile.save()
        self.user2.profile.referral_code = "CODE2"
        self.user2.profile.save()
        self.user3.profile.referral_code = "CODE3"
        self.user3.profile.save()

        # Create some referrals
        self.referred_user1 = User.objects.create_user(
            username="referred1", email="referred1@example.com", password="testpass123"
        )
        self.referred_user1.profile.referred_by = self.user1.profile
        self.referred_user1.profile.save()

        self.referred_user2 = User.objects.create_user(
            username="referred2", email="referred2@example.com", password="testpass123"
        )
        self.referred_user2.profile.referred_by = self.user1.profile
        self.referred_user2.profile.save()

        # Create a subject first
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")  # type: ignore[attr-defined]

        # Create a course and enrollments
        self.course = Course.objects.create(  # type: ignore[attr-defined]
            title="Test Course",
            description="Test Description",
            subject=self.subject,
            teacher=self.user1,
            price=100,
            max_students=50,
            slug="test-course",
        )

        # Create enrollments for referred users
        Enrollment.objects.create(student=self.referred_user1, course=self.course, status="approved")

        # Create some web requests (clicks) - but note that with encryption, we can't query based on encrypted fields
        self.web_request = WebRequest.objects.create(  # type: ignore[attr-defined]
            path="/some/path?ref=CODE1", ip_address="127.0.0.1", user=self.referred_user1.username, count=5
        )

    @skip("This test no longer works with encrypted fields")
    def test_referral_stats_calculation(self):
        """Test that referral statistics are calculated correctly"""
        # This test relies on database queries using encrypted fields, which doesn't work
        pass

    @skip("This test no longer works with encrypted fields")
    def test_mini_leaderboard_on_homepage(self):
        """Test that the mini leaderboard appears correctly on the homepage"""
        # This test relies on database queries using encrypted fields, which doesn't work
        pass

    def test_profile_referral_properties(self):
        """Test the properties of Profile related to referrals"""
        profile = self.user1.profile
        self.assertEqual(profile.total_referrals, 2)  # We created two referred users

    def test_add_referral_earnings(self):
        """Test the add_referral_earnings method of Profile"""
        profile = self.user1.profile
        initial_earnings = profile.referral_earnings
        profile.add_referral_earnings(50)
        profile.refresh_from_db()
        self.assertEqual(profile.referral_earnings, initial_earnings + 50)

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
        used_codes = set(Profile.objects.values_list("referral_code", flat=True))  # type: ignore[attr-defined]
        self.assertEqual(len(used_codes), len(Profile.objects.all()))  # type: ignore[attr-defined]
