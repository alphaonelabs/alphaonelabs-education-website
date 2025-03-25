from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from web.models import FeatureVote


class FeatureVoteModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        cls.user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.user2.delete()
        super().tearDownClass()

    def setUp(self):
        self.feature_id = "test-feature"
        self.test_ip = "192.168.1.1"

    def test_feature_vote_creation_with_user(self):
        """Test that a feature vote can be created with a user"""
        vote = FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")
        self.assertEqual(vote.feature_id, self.feature_id)
        self.assertEqual(vote.user, self.user)
        self.assertEqual(vote.vote, "up")
        self.assertIsNone(vote.ip_address)

    def test_feature_vote_creation_with_ip(self):
        """Test that a feature vote can be created with an IP address"""
        vote = FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, vote="down")
        self.assertEqual(vote.feature_id, self.feature_id)
        self.assertEqual(vote.ip_address, self.test_ip)
        self.assertEqual(vote.vote, "down")
        self.assertIsNone(vote.user)

    def test_feature_vote_str(self):
        """Test the string representation of a FeatureVote"""
        vote = FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")
        self.assertEqual(str(vote), "Thumbs Up for test-feature")

    def test_unique_constraint_user(self):
        """Test that a user can only vote once per feature"""
        # Create first vote
        FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")

        # Try to create another vote for the same feature and user
        with self.assertRaises(IntegrityError):
            FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="down")

    def test_unique_constraint_ip(self):
        """Test that an IP address can only vote once per feature when no user is provided"""
        # Create first vote
        FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, user=None, vote="up")

        # Try to create another vote for the same feature and IP
        with self.assertRaises(IntegrityError):
            FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, user=None, vote="down")

    def test_user_can_vote_multiple_features(self):
        """Test that a user can vote on multiple different features"""
        # Vote on first feature
        FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")

        # Vote on second feature
        second_feature = "another-feature"
        vote2 = FeatureVote.objects.create(feature_id=second_feature, user=self.user, vote="down")

        self.assertEqual(vote2.feature_id, second_feature)
        self.assertEqual(vote2.user, self.user)
        self.assertEqual(vote2.vote, "down")

    def test_ip_can_vote_when_user_exists(self):
        """Test that votes with the same IP but different users are allowed"""
        # Create first vote with user1
        FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, ip_address=self.test_ip, vote="up")

        # Create second vote with user2 but same IP
        vote2 = FeatureVote.objects.create(
            feature_id=self.feature_id, user=self.user2, ip_address=self.test_ip, vote="down"
        )

        self.assertEqual(vote2.feature_id, self.feature_id)
        self.assertEqual(vote2.user, self.user2)
        self.assertEqual(vote2.ip_address, self.test_ip)
        self.assertEqual(vote2.vote, "down")

    def test_vote_choices(self):
        """Test that only valid vote choices can be used"""
        # Valid vote
        valid_vote = FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")
        self.assertEqual(valid_vote.vote, "up")

        # Valid vote
        valid_vote2 = FeatureVote.objects.create(feature_id="another-feature", user=self.user, vote="down")
        self.assertEqual(valid_vote2.vote, "down")

        # Invalid vote - should raise an exception
        with self.assertRaises(ValidationError):
            invalid_vote = FeatureVote(feature_id="invalid-vote-feature", user=self.user, vote="invalid")
            invalid_vote.full_clean()  # This should raise ValidationError
