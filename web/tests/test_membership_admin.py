from datetime import timedelta

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from web.admin import MembershipPlanAdmin, MembershipSubscriptionEventAdmin, UserMembershipAdmin
from web.models import MembershipPlan, MembershipSubscriptionEvent, UserMembership


class MockRequest:
    def __init__(self):
        self.user = None


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class MembershipPlanAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = MembershipPlanAdmin(MembershipPlan, self.site)

        self.monthly_plan = MembershipPlan.objects.create(
            name="Monthly Admin Plan",
            slug="monthly-admin-plan",
            description="Test monthly plan for admin",
            price_monthly=9.99,
            price_yearly=99.99,
            stripe_monthly_price_id="price_monthly_admin",
            stripe_yearly_price_id="price_yearly_admin",
            features=["Feature 1", "Feature 2"],
            is_active=True,
            order=1,
        )

        self.inactive_plan = MembershipPlan.objects.create(
            name="Inactive Plan",
            slug="inactive-plan",
            description="Test inactive plan",
            price_monthly=19.99,
            price_yearly=199.99,
            stripe_monthly_price_id="price_monthly_inactive",
            stripe_yearly_price_id="price_yearly_inactive",
            features=["Feature 1"],
            is_active=False,
            order=2,
        )

    def test_list_display(self):
        """Test that list_display contains the right fields"""
        self.assertIn("name", self.admin.list_display)
        self.assertIn("price_monthly", self.admin.list_display)
        self.assertIn("price_yearly", self.admin.list_display)
        self.assertIn("is_active", self.admin.list_display)
        self.assertIn("order", self.admin.list_display)

    def test_search_fields(self):
        """Test that search_fields contains the right fields"""
        self.assertIn("name", self.admin.search_fields)
        self.assertIn("description", self.admin.search_fields)

    def test_prepopulated_fields(self):
        """Test that slug is prepopulated from name"""
        self.assertEqual(self.admin.prepopulated_fields, {"slug": ("name",)})

    def test_list_filter(self):
        """Test that list_filter contains is_active"""
        self.assertIn("is_active", self.admin.list_filter)

    def test_list_editable(self):
        """Test that list_editable contains the right fields"""
        self.assertIn("is_active", self.admin.list_editable)
        self.assertIn("order", self.admin.list_editable)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class UserMembershipAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = UserMembershipAdmin(UserMembership, self.site)

        self.user = User.objects.create_user(
            username="testadminuser", email="testadmin@example.com", password="testpass123"
        )

        self.plan = MembershipPlan.objects.create(
            name="Admin Test Plan",
            slug="admin-test-plan",
            description="Test plan for admin tests",
            price_monthly=9.99,
            price_yearly=99.99,
            stripe_monthly_price_id="price_monthly_admin_test",
            stripe_yearly_price_id="price_yearly_admin_test",
            features=["Feature 1", "Feature 2"],
        )

        self.membership = UserMembership.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
            billing_period="monthly",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            stripe_subscription_id="sub_admin_test123",
        )

        # Create memberships with different statuses
        statuses = ["trialing", "past_due", "canceled", "incomplete", "inactive"]
        for i, status in enumerate(statuses):
            user = User.objects.create_user(
                username=f"testuser{i}", email=f"test{i}@example.com", password="testpass123"
            )

            UserMembership.objects.create(
                user=user,
                plan=self.plan,
                status=status,
                billing_period="monthly",
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=30),
                stripe_subscription_id=f"sub_test{i}",
            )

    def test_list_display(self):
        """Test that list_display contains the right fields"""
        self.assertIn("user", self.admin.list_display)
        self.assertIn("plan", self.admin.list_display)
        self.assertIn("status", self.admin.list_display)
        self.assertIn("billing_period", self.admin.list_display)
        self.assertIn("start_date", self.admin.list_display)
        self.assertIn("end_date", self.admin.list_display)
        self.assertIn("cancel_at_period_end", self.admin.list_display)

    def test_search_fields(self):
        """Test that search_fields contains the right fields"""
        self.assertIn("user__username", self.admin.search_fields)
        self.assertIn("user__email", self.admin.search_fields)
        self.assertIn("plan__name", self.admin.search_fields)

    def test_list_filter(self):
        """Test that list_filter contains the right fields"""
        self.assertIn("status", self.admin.list_filter)
        self.assertIn("billing_period", self.admin.list_filter)
        self.assertIn("cancel_at_period_end", self.admin.list_filter)

    def test_readonly_fields(self):
        """Test that readonly_fields contains the right fields"""
        self.assertIn("created_at", self.admin.readonly_fields)
        self.assertIn("updated_at", self.admin.readonly_fields)

    def test_fieldsets(self):
        """Test that fieldsets are properly defined"""
        fieldsets = self.admin.fieldsets

        # Check main fieldset
        self.assertIn("user", fieldsets[0][1]["fields"])
        self.assertIn("plan", fieldsets[0][1]["fields"])
        self.assertIn("stripe_subscription_id", fieldsets[0][1]["fields"])

        # Check status fieldset
        self.assertIn("status", fieldsets[1][1]["fields"])
        self.assertIn("billing_period", fieldsets[1][1]["fields"])
        self.assertIn("cancel_at_period_end", fieldsets[1][1]["fields"])

        # Check dates fieldset
        self.assertIn("start_date", fieldsets[2][1]["fields"])
        self.assertIn("end_date", fieldsets[2][1]["fields"])
        self.assertIn("created_at", fieldsets[2][1]["fields"])
        self.assertIn("updated_at", fieldsets[2][1]["fields"])


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class MembershipSubscriptionEventAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = MembershipSubscriptionEventAdmin(MembershipSubscriptionEvent, self.site)

        self.user = User.objects.create_user(
            username="eventadminuser", email="eventadmin@example.com", password="testpass123"
        )

        self.plan = MembershipPlan.objects.create(
            name="Event Admin Test Plan",
            slug="event-admin-test-plan",
            description="Test plan for event admin tests",
            price_monthly=9.99,
            price_yearly=99.99,
            stripe_monthly_price_id="price_monthly_event_admin",
            stripe_yearly_price_id="price_yearly_event_admin",
            features=["Feature 1"],
        )

        self.membership = UserMembership.objects.create(
            user=self.user,
            plan=self.plan,
            status="active",
            billing_period="monthly",
            start_date=timezone.now(),
            stripe_subscription_id="sub_event_admin123",
        )

        # Create events of different types
        event_types = [
            "created",
            "updated",
            "canceled",
            "reactivated",
            "payment_succeeded",
            "payment_failed",
            "past_due",
        ]

        self.events = []
        for i, event_type in enumerate(event_types):
            event = MembershipSubscriptionEvent.objects.create(
                user=self.user,
                membership=self.membership,
                event_type=event_type,
                stripe_event_id=f"evt_admin{i}",
                data={"test_key": f"test_value_{i}"},
            )
            self.events.append(event)

    def test_list_display_fields(self):
        """Test that list_display fields exist on the model"""
        for field in self.admin.list_display:
            self.assertTrue(hasattr(self.events[0], field) or field in self.admin.__dict__)

    def test_search_fields(self):
        """Test that search_fields can be accessed on the model"""
        for field in self.admin.search_fields:
            if field.startswith("user__"):
                # Check that the relationship and the field exist
                relationship, field_name = field.split("__")
                self.assertTrue(hasattr(self.events[0], relationship))
                related_obj = getattr(self.events[0], relationship)
                self.assertTrue(hasattr(related_obj, field_name))
            else:
                self.assertTrue(hasattr(self.events[0], field))

    def test_fieldsets(self):
        """Test that fields in fieldsets exist on the model"""
        for fieldset_name, fieldset_options in self.admin.fieldsets:
            for field in fieldset_options["fields"]:
                if isinstance(field, tuple):
                    # Handle tuple of fields
                    for sub_field in field:
                        self.assertTrue(hasattr(self.events[0], sub_field) or sub_field in self.admin.__dict__)
                else:
                    self.assertTrue(hasattr(self.events[0], field) or field in self.admin.__dict__)

    def test_list_display(self):
        """Test that list_display contains the right fields"""
        self.assertIn("event_type", self.admin.list_display)
        self.assertIn("user", self.admin.list_display)
        self.assertIn("created_at", self.admin.list_display)
        self.assertIn("stripe_event_id", self.admin.list_display)

    def test_list_filter(self):
        """Test that list_filter contains the right fields"""
        self.assertIn("event_type", self.admin.list_filter)
        self.assertIn("created_at", self.admin.list_filter)

    def test_readonly_fields(self):
        """Test that readonly_fields contains created_at"""
        self.assertIn("created_at", self.admin.readonly_fields)

    def test_raw_id_fields(self):
        """Test that raw_id_fields contains the right fields"""
        self.assertIn("user", self.admin.raw_id_fields)
        self.assertIn("membership", self.admin.raw_id_fields)
