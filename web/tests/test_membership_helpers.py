import stripe
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from web.models import MembershipPlan, UserMembership, MembershipSubscriptionEvent
from web.helpers import (
    setup_stripe,
    get_stripe_customer,
    create_subscription,
    cancel_subscription,
    reactivate_subscription,
    update_membership_from_subscription
)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class MembershipHelpersTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )
        cls.plan = MembershipPlan.objects.create(
            name="Test Plan",
            slug="test-plan",
            description="Test plan description",
            price_monthly=9.99,
            price_yearly=99.99,
            features=["Feature 1", "Feature 2"],
            stripe_monthly_price_id="price_monthly_123",
            stripe_yearly_price_id="price_yearly_123",
            is_active=True,
            order=1
        )

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.plan.delete()
        super().tearDownClass()

    def setUp(self):
        # Create a user membership
        self.membership = UserMembership.objects.create(
            user=self.user,
            plan=self.plan,
            status="inactive",
            stripe_subscription_id="sub_test123",
            start_date=timezone.now()
        )
        
        # Add this user attribute to simulate stripe customer id storage
        self.user.stripe_customer_id = "cus_test123"
        self.user.save()

    @patch('stripe.api_key', new="")
    def test_setup_stripe(self):
        """Test that setup_stripe configures the Stripe API key"""
        # Make sure stripe.api_key starts empty
        self.assertEqual(stripe.api_key, "")
        
        # Call the function
        setup_stripe()
        
        # Check that the key was set
        self.assertEqual(stripe.api_key, "dummy_key")

    @patch('stripe.Customer.create')
    @patch('stripe.Customer.retrieve')
    def test_get_stripe_customer_existing(self, mock_retrieve, mock_create):
        """Test retrieving an existing Stripe customer"""
        # Setup mock for an existing customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"
        mock_customer.deleted = False
        mock_retrieve.return_value = mock_customer
        
        # Call the function
        customer = get_stripe_customer(self.user)
        
        # Verify mocks were called correctly
        mock_retrieve.assert_called_once_with("cus_test123")
        mock_create.assert_not_called()
        
        # Check the result
        self.assertEqual(customer.id, "cus_test123")

    @patch('stripe.Customer.create')
    @patch('stripe.Customer.retrieve')
    def test_get_stripe_customer_create_new(self, mock_retrieve, mock_create):
        """Test creating a new Stripe customer when retrieve fails"""
        # Setup mock for a failed retrieval
        mock_retrieve.side_effect = stripe.error.InvalidRequestError(
            "No such customer: 'cus_test123'",
            param="id"
        )
        
        # Setup mock for customer creation
        mock_customer = MagicMock()
        mock_customer.id = "cus_new123"
        mock_create.return_value = mock_customer
        
        # Call the function
        customer = get_stripe_customer(self.user)
        
        # Verify mocks were called correctly
        mock_retrieve.assert_called_once_with("cus_test123")
        mock_create.assert_called_once()
        
        # Check the create call had the right parameters
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["email"], "test@example.com")
        self.assertEqual(call_kwargs["name"], "Test User")
        self.assertEqual(call_kwargs["metadata"]["user_id"], self.user.id)
        
        # Check the result
        self.assertEqual(customer.id, "cus_new123")
        
        # Verify the user's stripe_customer_id was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.stripe_customer_id, "cus_new123")

    @patch('web.helpers.get_stripe_customer')
    @patch('stripe.PaymentMethod.attach')
    @patch('stripe.Customer.modify')
    @patch('stripe.Subscription.create')
    def test_create_subscription_success(self, mock_sub_create, mock_cust_modify, 
                                         mock_pm_attach, mock_get_customer):
        """Test creating a subscription successfully"""
        # Setup mocks
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"
        mock_get_customer.return_value = mock_customer
        
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test123"
        mock_subscription.status = "active"
        mock_subscription.current_period_end = int(timezone.now().timestamp()) + 30*86400
        mock_subscription.latest_invoice = MagicMock()
        mock_subscription.latest_invoice.payment_intent = MagicMock()
        mock_subscription.latest_invoice.payment_intent.client_secret = "pi_secret_123"
        mock_sub_create.return_value = mock_subscription
        
        # Reset membership to ensure it's inactive
        self.membership.status = "inactive"
        self.membership.save()
        
        # Call the function
        result = create_subscription(
            user=self.user,
            plan_id=self.plan.id,
            payment_method_id="pm_test123",
            billing_period="monthly"
        )
        
        # Verify mocks were called correctly
        mock_get_customer.assert_called_once_with(self.user)
        mock_pm_attach.assert_called_once_with("pm_test123", customer="cus_test123")
        mock_cust_modify.assert_called_once()
        mock_sub_create.assert_called_once()
        
        # Check the subscription create call had the right parameters
        call_kwargs = mock_sub_create.call_args[1]
        self.assertEqual(call_kwargs["customer"], "cus_test123")
        self.assertEqual(call_kwargs["items"][0]["price"], "price_monthly_123")
        self.assertEqual(call_kwargs["metadata"]["user_id"], self.user.id)
        self.assertEqual(call_kwargs["metadata"]["plan_id"], self.plan.id)
        self.assertEqual(call_kwargs["metadata"]["billing_period"], "monthly")
        
        # Check the result
        self.assertTrue(result["success"])
        self.assertEqual(result["subscription"], mock_subscription)
        self.assertEqual(result["client_secret"], "pi_secret_123")
        
        # Verify the membership was updated
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.status, "active")
        self.assertEqual(self.membership.stripe_subscription_id, "sub_test123")

    @patch('web.helpers.get_stripe_customer')
    @patch('stripe.PaymentMethod.attach')
    def test_create_subscription_invalid_plan(self, mock_pm_attach, mock_get_customer):
        """Test creating a subscription with invalid plan ID"""
        result = create_subscription(
            user=self.user,
            plan_id=999,  # Non-existent plan ID
            payment_method_id="pm_test123",
            billing_period="monthly"
        )
        
        # Verify result indicates failure
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Membership plan not found")
        
        # Verify no mocks were called
        mock_get_customer.assert_not_called()
        mock_pm_attach.assert_not_called()

    @patch('web.helpers.get_stripe_customer')
    @patch('stripe.PaymentMethod.attach')
    def test_create_subscription_invalid_billing_period(self, mock_pm_attach, mock_get_customer):
        """Test creating a subscription with invalid billing period"""
        # Create a plan with only monthly pricing
        monthly_plan = MembershipPlan.objects.create(
            name="Monthly Only Plan",
            slug="monthly-only-plan",
            description="Plan with only monthly billing",
            price_monthly=9.99,
            price_yearly=0.00,  # Set to 0 but provide a value
            stripe_monthly_price_id="price_monthly_only_123",
            # No yearly price ID
            is_active=True,
            order=2
        )
        
        result = create_subscription(
            user=self.user,
            plan_id=monthly_plan.id,
            payment_method_id="pm_test123",
            billing_period="yearly"  # Try to use yearly billing on monthly-only plan
        )
        
        # Verify result indicates failure
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "The yearly billing period is not available for this plan")
        
        # Verify no mocks were called
        mock_get_customer.assert_not_called()
        mock_pm_attach.assert_not_called()
        
        # Clean up
        monthly_plan.delete()

    @patch('stripe.Subscription.modify')
    def test_cancel_subscription_success(self, mock_sub_modify):
        """Test canceling a subscription successfully"""
        # Setup subscription
        self.membership.status = "active"
        self.membership.stripe_subscription_id = "sub_test123"
        self.membership.save()
        
        # Setup mock
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test123"
        mock_sub_modify.return_value = mock_subscription
        
        # Call the function
        result = cancel_subscription(self.user)
        
        # Verify mock was called correctly
        mock_sub_modify.assert_called_once_with("sub_test123", cancel_at_period_end=True)
        
        # Check the result
        self.assertTrue(result["success"])
        self.assertIn("canceled", result["message"])
        
        # Verify the membership was updated
        self.membership.refresh_from_db()
        self.assertTrue(self.membership.cancel_at_period_end)

    @patch('stripe.Subscription.modify')
    def test_cancel_subscription_no_subscription(self, mock_sub_modify):
        """Test canceling when no subscription exists"""
        # Create a different membership with no subscription ID
        self.membership.delete()
        self.membership = UserMembership.objects.create(
            user=self.user,
            plan=self.plan,
            status="inactive",
            stripe_subscription_id="",  # Empty string instead of null
            start_date=timezone.now()
        )
        
        # Call the function
        result = cancel_subscription(self.user)
        
        # Verify no mock was called
        mock_sub_modify.assert_not_called()
        
        # Check the result
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "No active subscription found")

    @patch('stripe.Subscription.modify')
    def test_reactivate_subscription_success(self, mock_sub_modify):
        """Test reactivating a canceled subscription"""
        # Setup subscription as canceled
        self.membership.status = "active"
        self.membership.stripe_subscription_id = "sub_test123"
        self.membership.cancel_at_period_end = True
        self.membership.save()
        
        # Setup mock
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_test123"
        mock_sub_modify.return_value = mock_subscription
        
        # Call the function
        result = reactivate_subscription(self.user)
        
        # Verify mock was called correctly
        mock_sub_modify.assert_called_once_with("sub_test123", cancel_at_period_end=False)
        
        # Check the result
        self.assertTrue(result["success"])
        self.assertIn("reactivated", result["message"])
        
        # Verify the membership was updated
        self.membership.refresh_from_db()
        self.assertFalse(self.membership.cancel_at_period_end)

    @patch('stripe.Subscription.modify')
    def test_reactivate_subscription_not_canceled(self, mock_sub_modify):
        """Test reactivating a subscription that's not canceled"""
        # Setup subscription as not canceled
        self.membership.status = "active"
        self.membership.stripe_subscription_id = "sub_test123"
        self.membership.cancel_at_period_end = False
        self.membership.save()
        
        # Call the function
        result = reactivate_subscription(self.user)
        
        # Verify no mock was called
        mock_sub_modify.assert_not_called()
        
        # Check the result
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Your subscription is not scheduled for cancellation")

    def test_update_membership_from_subscription(self):
        """Test updating membership details from a Stripe subscription object"""
        # Create a mock subscription object
        subscription = MagicMock()
        subscription.id = "sub_update123"
        subscription.status = "active"
        subscription.current_period_end = int(timezone.now().timestamp()) + 30*86400
        subscription.items = MagicMock()
        subscription.items.data = [MagicMock()]
        subscription.items.data[0].price = MagicMock()
        subscription.items.data[0].price.id = "price_monthly_123"
        
        # Call the function
        update_membership_from_subscription(self.user, subscription)
        
        # Verify the membership was updated correctly
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.stripe_subscription_id, "sub_update123")
        self.assertEqual(self.membership.status, "active")
        self.assertEqual(self.membership.plan, self.plan)
        
        # Check that the end date was set correctly (approximately 30 days)
        end_date_timestamp = int(self.membership.end_date.timestamp())
        expected_timestamp = subscription.current_period_end
        self.assertAlmostEqual(end_date_timestamp, expected_timestamp, delta=10)  # Allow small difference due to timezone handling 