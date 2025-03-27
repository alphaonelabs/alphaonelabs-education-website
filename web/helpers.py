import logging

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from .models import (
    MembershipPlan,
    MembershipSubscriptionEvent,
    UserMembership,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def setup_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_customer(user):
    try:
        setup_stripe()

        if not user.membership.stripe_customer_id:
            # Create a new customer
            customer = stripe.Customer.create(
                email=user.email, name=f"{user.first_name} {user.last_name}".strip(), metadata={"user_id": user.id}
            )

            # Save the customer ID to the user membership
            if hasattr(user, "membership"):
                user.membership.stripe_customer_id = customer.id
                user.membership.save(update_fields=["stripe_customer_id"])
            else:
                logger.error(f"User {user.email} does not have a membership object")

            return customer

        # Get existing customer
        return stripe.Customer.retrieve(user.membership.stripe_customer_id)

    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving Stripe customer for user {user.email}: {str(e)}")
        return None


def create_subscription(user, plan_id, payment_method_id, billing_period):
    try:
        setup_stripe()

        # Get the membership plan
        try:
            plan = MembershipPlan.objects.get(id=plan_id)
        except MembershipPlan.DoesNotExist:
            return {"success": False, "error": "Membership plan not found"}

        # Validate billing period
        if billing_period not in ["monthly", "yearly"]:
            return {"success": False, "error": "Invalid billing period"}

        # Get the price ID based on billing period
        if billing_period == "monthly":
            price_id = plan.stripe_monthly_price_id
        else:
            price_id = plan.stripe_yearly_price_id

        if not price_id:
            return {"success": False, "error": f"No price ID configured for {billing_period} billing"}

        # Get or create customer
        customer = get_stripe_customer(user)
        if not customer:
            return {"success": False, "error": "Failed to create or retrieve customer"}

        # Attach payment method to customer
        stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)

        # Set as default payment method
        stripe.Customer.modify(customer.id, invoice_settings={"default_payment_method": payment_method_id})

        # Check if user already has a subscription
        existing_subscription = user.membership if hasattr(user, "membership") else None

        if existing_subscription and existing_subscription.stripe_subscription_id:
            # Update existing subscription
            subscription = stripe.Subscription.modify(
                existing_subscription.stripe_subscription_id,
                items=[
                    {
                        "price": price_id,
                    }
                ],
                payment_behavior="allow_incomplete",
                proration_behavior="create_prorations",
            )
        else:
            # Create a new subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[
                    {
                        "price": price_id,
                    }
                ],
                payment_behavior="allow_incomplete",
                metadata={"user_id": user.id, "plan_id": plan.id, "billing_period": billing_period},
            )

        # Update user membership
        update_membership_from_subscription(user, subscription)

        return {"success": True, "subscription": subscription}

    except stripe.error.CardError as e:
        logger.error(f"Card error for user {user.email}: {str(e)}")
        return {"success": False, "error": str(e.user_message)}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error for user {user.email}: {str(e)}")
        return {"success": False, "error": "An error occurred with our payment processor"}
    except Exception as e:
        logger.error(f"Error creating subscription for user {user.email}: {str(e)}")
        return {"success": False, "error": "An unexpected error occurred"}


def cancel_subscription(user):
    try:
        setup_stripe()

        if not hasattr(user, "membership") or not user.membership.stripe_subscription_id:
            return {"success": False, "error": "No active subscription found"}

        membership = user.membership

        # Cancel subscription at period end
        subscription = stripe.Subscription.modify(membership.stripe_subscription_id, cancel_at_period_end=True)

        # Update membership status
        membership.cancel_at_period_end = True
        membership.save(update_fields=["cancel_at_period_end"])

        # Record cancellation event
        MembershipSubscriptionEvent.objects.create(
            user=user,
            membership=membership,
            event_type="canceled",
            data={"subscription_id": subscription.id, "canceled_at": timezone.now().isoformat()},
        )

        return {"success": True, "subscription": subscription}

    except stripe.error.StripeError as e:
        logger.error(f"Error canceling subscription for user {user.email}: {str(e)}")
        return {"success": False, "error": "An error occurred with our payment processor"}
    except Exception as e:
        logger.error(f"Error canceling subscription for user {user.email}: {str(e)}")
        return {"success": False, "error": "An unexpected error occurred"}


def reactivate_subscription(user):
    try:
        setup_stripe()

        if not hasattr(user, "membership") or not user.membership.stripe_subscription_id:
            return {"success": False, "error": "No subscription found"}

        membership = user.membership

        # Check if the subscription is scheduled to be canceled
        if not membership.cancel_at_period_end:
            return {"success": False, "error": "Subscription is not scheduled for cancellation"}

        # Reactivate subscription
        subscription = stripe.Subscription.modify(membership.stripe_subscription_id, cancel_at_period_end=False)

        # Update membership status
        membership.cancel_at_period_end = False
        membership.save(update_fields=["cancel_at_period_end"])

        # Record reactivation event
        MembershipSubscriptionEvent.objects.create(
            user=user,
            membership=membership,
            event_type="reactivated",
            data={"subscription_id": subscription.id, "reactivated_at": timezone.now().isoformat()},
        )

        return {"success": True, "subscription": subscription}

    except stripe.error.StripeError as e:
        logger.error(f"Error reactivating subscription for user {user.email}: {str(e)}")
        return {"success": False, "error": "An error occurred with our payment processor"}
    except Exception as e:
        logger.error(f"Error reactivating subscription for user {user.email}: {str(e)}")
        return {"success": False, "error": "An unexpected error occurred"}


def update_membership_from_subscription(user, subscription):
    try:
        # Get the subscription item
        subscription_item = subscription["items"]["data"][0]
        price_id = subscription_item["price"]["id"]

        # Find the plan based on price ID
        try:
            plan = MembershipPlan.objects.filter(
                models.Q(stripe_monthly_price_id=price_id) | models.Q(stripe_yearly_price_id=price_id)
            ).first()

            if not plan:
                logger.error(f"No plan found for price ID {price_id}")
                return False
        except Exception as e:
            logger.error(f"Error finding plan for price ID {price_id}: {str(e)}")
            return False

        # Determine billing period
        if price_id == plan.stripe_monthly_price_id:
            billing_period = "monthly"
        else:
            billing_period = "yearly"

        # Get or create user membership
        membership, created = UserMembership.objects.get_or_create(
            user=user,
            defaults={
                "plan": plan,
                "status": subscription["status"],
                "billing_period": billing_period,
                "stripe_subscription_id": subscription["id"],
                "stripe_customer_id": subscription["customer"],
            },
        )

        if not created:
            # Update existing membership
            membership.plan = plan
            membership.status = subscription["status"]
            membership.billing_period = billing_period
            membership.stripe_subscription_id = subscription["id"]
            membership.stripe_customer_id = subscription["customer"]

        # Update dates
        if subscription["status"] in ["active", "trialing"]:
            membership.start_date = timezone.datetime.fromtimestamp(
                subscription["current_period_start"], tz=timezone.utc
            )
            membership.end_date = timezone.datetime.fromtimestamp(subscription["current_period_end"], tz=timezone.utc)

        # Update cancellation status
        membership.cancel_at_period_end = subscription["cancel_at_period_end"]

        # Save changes
        membership.save()

        # Create subscription event
        event_type = "created" if created else "updated"
        MembershipSubscriptionEvent.objects.create(
            user=user,
            membership=membership,
            event_type=event_type,
            data={
                "subscription_id": subscription["id"],
                "status": subscription["status"],
                "billing_period": billing_period,
                "plan_id": plan.id,
            },
        )

        return True

    except Exception as e:
        logger.error(f"Error updating membership for user {user.email}: {str(e)}")
        return False
