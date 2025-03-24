from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from web.models import MembershipPlan, UserMembership, MembershipSubscriptionEvent


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class MembershipPlanModelTests(TestCase):
    def setUp(self):
        self.monthly_plan = MembershipPlan.objects.create(
            name="Monthly Plan",
            slug="monthly-plan",
            description="Test monthly plan",
            price_monthly=9.99,
            price_yearly=99.99,
            stripe_monthly_price_id="price_monthly_test",
            stripe_yearly_price_id="price_yearly_test",
            features=["Feature 1", "Feature 2"],
            is_active=True,
            order=1
        )
        
        self.yearly_plan = MembershipPlan.objects.create(
            name="Yearly Plan",
            slug="yearly-plan",
            description="Test yearly plan",
            price_monthly=19.99,
            price_yearly=199.99,
            stripe_monthly_price_id="price_monthly_test2",
            stripe_yearly_price_id="price_yearly_test2",
            features=["Feature 1", "Feature 2", "Feature 3"],
            is_active=True,
            order=2
        )

    def test_membership_plan_creation(self):
        """Test that membership plans can be created with correct data"""
        self.assertEqual(self.monthly_plan.name, "Monthly Plan")
        self.assertEqual(self.monthly_plan.description, "Test monthly plan")
        self.assertTrue(self.monthly_plan.is_active)
        self.assertEqual(self.monthly_plan.order, 1)
        
        self.assertEqual(self.yearly_plan.name, "Yearly Plan")
    
    def test_membership_plan_str(self):
        """Test the string representation of MembershipPlan"""
        self.assertEqual(str(self.monthly_plan), "Monthly Plan")
        self.assertEqual(str(self.yearly_plan), "Yearly Plan")


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class UserMembershipModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username="testuser", 
            email="test@example.com", 
            password="testpass123"
        )
        cls.plan = MembershipPlan.objects.create(
            name="Test Plan",
            slug="test-plan",
            description="Test plan description",
            price_monthly=9.99,
            price_yearly=99.99,
            stripe_monthly_price_id="price_monthly_test3",
            stripe_yearly_price_id="price_yearly_test3",
            features=["Feature 1", "Feature 2"]
        )

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.plan.delete()
        super().tearDownClass()
    
    def setUp(self):
        # Create a basic membership
        self.membership = UserMembership.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            stripe_subscription_id="sub_test123",
            billing_period="monthly"
        )
        
        # Create a canceled membership
        end_date = timezone.now() + timedelta(days=15)
        self.canceled_membership = UserMembership.objects.create(
            user=User.objects.create_user(
                username="canceleduser", 
                email="canceled@example.com", 
                password="testpass123"
            ),
            plan=self.plan,
            status="active",
            billing_period="monthly",
            start_date=timezone.now(),
            end_date=end_date,
            cancel_at_period_end=True,
            stripe_subscription_id="sub_canceled123"
        )
        
        # Create an expired membership
        self.expired_membership = UserMembership.objects.create(
            user=User.objects.create_user(
                username="expireduser", 
                email="expired@example.com", 
                password="testpass123"
            ),
            plan=self.plan,
            status="inactive",
            billing_period="monthly",
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=30),
            stripe_subscription_id="sub_expired123"
        )

    def test_user_membership_creation(self):
        """Test that user membership can be created with correct data"""
        self.assertEqual(self.membership.user, self.user)
        self.assertEqual(self.membership.plan, self.plan)
        self.assertEqual(self.membership.status, "active")
        self.assertEqual(self.membership.stripe_subscription_id, "sub_test123")
    
    def test_user_membership_str(self):
        """Test the string representation of UserMembership"""
        expected_str = f"{self.user.username}'s Test Plan Membership"
        self.assertEqual(str(self.membership), expected_str)
    
    def test_is_active_property(self):
        """Test the is_active property"""
        # Active status should return True
        self.assertTrue(self.membership.is_active)
        
        # Set status to inactive
        self.membership.status = "inactive"
        self.membership.save()
        self.assertFalse(self.membership.is_active)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class MembershipSubscriptionEventModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="eventuser", 
            email="event@example.com", 
            password="testpass123"
        )
        
        self.plan = MembershipPlan.objects.create(
            name="Event Test Plan",
            slug="event-test-plan",
            description="Test plan for events",
            price_monthly=9.99,
            price_yearly=99.99,
            stripe_monthly_price_id="price_monthly_event",
            stripe_yearly_price_id="price_yearly_event",
            features=["Feature 1"]
        )
        
        self.membership = UserMembership.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
            billing_period="monthly",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            stripe_subscription_id="sub_event123"
        )
        
        self.event = MembershipSubscriptionEvent.objects.create(
            user=self.user,
            membership=self.membership,
            event_type="created",
            stripe_event_id="evt_test123",
            data={"test_key": "test_value"}
        )

    def test_subscription_event_creation(self):
        """Test that subscription events can be created with correct data"""
        self.assertEqual(self.event.user, self.user)
        self.assertEqual(self.event.membership, self.membership)
        self.assertEqual(self.event.event_type, "created")
        self.assertEqual(self.event.stripe_event_id, "evt_test123")
        self.assertEqual(self.event.data, {"test_key": "test_value"})
    
    def test_subscription_event_str(self):
        """Test the string representation of MembershipSubscriptionEvent"""
        expected_str = f"created event for {self.user.username}"
        self.assertEqual(str(self.event), expected_str)
    
    def test_ordering(self):
        """Test that events are ordered by created_at in descending order"""
        # Create another event
        newer_event = MembershipSubscriptionEvent.objects.create(
            user=self.user,
            membership=self.membership,
            event_type="updated",
            stripe_event_id="evt_newer123"
        )
        
        # Get all events for this user
        events = MembershipSubscriptionEvent.objects.filter(
            user=self.user
        ).values_list('event_type', flat=True)
        
        # The newer event should be first
        self.assertEqual(list(events), ['updated', 'created']) 