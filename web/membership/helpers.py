import logging
from datetime import datetime

import stripe
from django.conf import settings
from django.utils import timezone

from .models import MembershipPlan, UserMembership

logger = logging.getLogger(__name__)


def setup_stripe():
    """Configure Stripe with the API key from settings."""
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_customer(user):
    """
    Get or create a Stripe customer for the user.

    Args:
        user: The Django user object

    Returns:
        stripe.Customer: The Stripe customer object
    """
    try:
        # Check if user already has a membership with customer ID
        user_membership = UserMembership.objects.filter(user=user).first()

        if user_membership and user_membership.stripe_customer_id:
            # Verify the customer exists on Stripe
            try:
                customer = stripe.Customer.retrieve(user_membership.stripe_customer_id)
                if not customer.get("deleted", False):
                    return customer
            except stripe.error.InvalidRequestError:
                # Customer doesn't exist on Stripe, create a new one
                pass

        # Create a new customer
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.username,
            metadata={"user_id": user.id},
        )

        # Update or create the user membership with the new customer ID
        if user_membership:
            user_membership.stripe_customer_id = customer.id
            user_membership.save()
        else:
            UserMembership.objects.create(user=user, stripe_customer_id=customer.id)

        return customer
    except Exception as e:
        logger.error(f"Error getting/creating Stripe customer for user {user.id}: {str(e)}")
        raise


def create_subscription(user, plan_id, payment_method_id, billing_period):
    """
    Create a new subscription for a user.

    Args:
        user: The Django user object
        plan_id: The ID of the membership plan
        payment_method_id: The Stripe payment method ID
        billing_period: Either 'monthly' or 'yearly'

    Returns:
        dict: A dictionary with success status and subscription details
    """
    try:
        setup_stripe()

        # Get the membership plan
        try:
            plan = MembershipPlan.objects.get(id=plan_id)
        except MembershipPlan.DoesNotExist:
            return {"success": False, "message": "Membership plan not found"}

        # Get price ID based on billing period
        price_id = plan.stripe_yearly_price_id if billing_period == "yearly" else plan.stripe_monthly_price_id
        if not price_id:
            return {"success": False, "message": f"The {billing_period} billing period is not available for this plan"}

        # Get or create customer
        customer = get_stripe_customer(user)

        # Attach payment method to customer
        stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)

        # Set as default payment method
        stripe.Customer.modify(customer.id, invoice_settings={"default_payment_method": payment_method_id})

        # Check for existing subscription
        user_membership = UserMembership.objects.filter(user=user).first()
        if user_membership and user_membership.status in ["active", "trialing"]:
            return {"success": False, "message": "You already have an active membership"}

        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id}],
            expand=["latest_invoice.payment_intent"],
            metadata={"user_id": user.id, "plan_id": plan.id, "billing_period": billing_period},
        )

        # Update user membership
        update_membership_from_subscription(user, subscription)

        return {
            "success": True,
            "subscription": subscription,
            "client_secret": (
                subscription.latest_invoice.payment_intent.client_secret
                if subscription.latest_invoice.payment_intent
                else None
            ),
        }
    except stripe.error.CardError as e:
        logger.error(f"Card error for user {user.id}: {str(e)}")
        return {"success": False, "message": e.user_message}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error for user {user.id}: {str(e)}")
        return {"success": False, "message": "An error occurred with the payment processor. Please try again."}
    except Exception as e:
        logger.error(f"Error creating subscription for user {user.id}: {str(e)}")
        return {"success": False, "message": "An unexpected error occurred. Please try again later."}


def cancel_subscription(user):
    """
    Cancel a user's subscription at the end of the billing period.

    Args:
        user: The Django user object

    Returns:
        dict: A dictionary with success status and message
    """
    try:
        setup_stripe()

        user_membership = UserMembership.objects.filter(user=user).first()
        if not user_membership or not user_membership.stripe_subscription_id:
            return {"success": False, "message": "No active subscription found"}

        # Cancel at period end
        stripe.Subscription.modify(user_membership.stripe_subscription_id, cancel_at_period_end=True)

        # Update user membership
        user_membership.cancel_at_period_end = True
        user_membership.save()

        return {
            "success": True,
            "message": "Your subscription has been canceled and will end on your next billing date.",
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error canceling subscription for user {user.id}: {str(e)}")
        return {"success": False, "message": "An error occurred with the payment processor. Please try again."}
    except Exception as e:
        logger.error(f"Error canceling subscription for user {user.id}: {str(e)}")
        return {"success": False, "message": "An unexpected error occurred. Please try again later."}


def reactivate_subscription(user):
    """
    Reactivate a canceled subscription.

    Args:
        user: The Django user object

    Returns:
        dict: A dictionary with success status and message
    """
    try:
        setup_stripe()

        user_membership = UserMembership.objects.filter(user=user).first()
        if not user_membership or not user_membership.stripe_subscription_id:
            return {"success": False, "message": "No subscription found"}

        if not user_membership.cancel_at_period_end:
            return {"success": False, "message": "Your subscription is not scheduled for cancellation"}

        # Reactivate subscription
        stripe.Subscription.modify(user_membership.stripe_subscription_id, cancel_at_period_end=False)

        # Update user membership
        user_membership.cancel_at_period_end = False
        user_membership.save()

        return {"success": True, "message": "Your subscription has been reactivated."}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error reactivating subscription for user {user.id}: {str(e)}")
        return {"success": False, "message": "An error occurred with the payment processor. Please try again."}
    except Exception as e:
        logger.error(f"Error reactivating subscription for user {user.id}: {str(e)}")
        return {"success": False, "message": "An unexpected error occurred. Please try again later."}


def update_payment_method(user, payment_method_id):
    """
    Update a user's payment method.

    Args:
        user: The Django user object
        payment_method_id: The Stripe payment method ID

    Returns:
        dict: A dictionary with success status and message
    """
    try:
        setup_stripe()

        user_membership = UserMembership.objects.filter(user=user).first()
        if not user_membership or not user_membership.stripe_customer_id:
            return {"success": False, "message": "No customer record found"}

        # Attach payment method to customer
        stripe.PaymentMethod.attach(payment_method_id, customer=user_membership.stripe_customer_id)

        # Set as default payment method
        stripe.Customer.modify(
            user_membership.stripe_customer_id, invoice_settings={"default_payment_method": payment_method_id}
        )

        return {"success": True, "message": "Payment method updated successfully."}
    except stripe.error.CardError as e:
        logger.error(f"Card error updating payment method for user {user.id}: {str(e)}")
        return {"success": False, "message": e.user_message}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error updating payment method for user {user.id}: {str(e)}")
        return {"success": False, "message": "An error occurred with the payment processor. Please try again."}
    except Exception as e:
        logger.error(f"Error updating payment method for user {user.id}: {str(e)}")
        return {"success": False, "message": "An unexpected error occurred. Please try again later."}


def update_membership_from_subscription(user, subscription):
    """
    Update a user's membership based on a Stripe subscription.

    Args:
        user: The Django user object
        subscription: The Stripe subscription object
    """
    try:
        # Get the metadata
        metadata = subscription.get("metadata", {})
        plan_id = metadata.get("plan_id")

        if not plan_id:
            logger.warning(f"No plan_id in subscription metadata for user {user.id}")
            return

        try:
            plan = MembershipPlan.objects.get(id=plan_id)
        except MembershipPlan.DoesNotExist:
            logger.error(f"Plan {plan_id} not found when updating membership for user {user.id}")
            return

        # Get or create user membership
        user_membership, created = UserMembership.objects.get_or_create(
            user=user, defaults={"status": "inactive", "plan": None}
        )

        # Update membership fields
        user_membership.stripe_subscription_id = subscription.id
        user_membership.status = subscription.status
        user_membership.plan = plan

        # Set end date
        if subscription.current_period_end:
            user_membership.end_date = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)

        # Set cancel at period end
        user_membership.cancel_at_period_end = subscription.cancel_at_period_end

        user_membership.save()
    except Exception as e:
        logger.error(f"Error updating membership from subscription for user {user.id}: {str(e)}")


def handle_subscription_updated(subscription):
    """
    Handle a subscription updated event from Stripe.

    Args:
        subscription: The Stripe subscription object
    """
    try:
        user_id = subscription.get("metadata", {}).get("user_id")
        if not user_id:
            logger.warning(f"No user_id in subscription metadata for subscription {subscription.id}")
            return

        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found when handling subscription update for {subscription.id}")
            return

        update_membership_from_subscription(user, subscription)
    except Exception as e:
        logger.error(f"Error handling subscription update for subscription {subscription.id}: {str(e)}")


def handle_subscription_deleted(subscription):
    """
    Handle a subscription deleted event from Stripe.

    Args:
        subscription: The Stripe subscription object
    """
    try:
        user_id = subscription.get("metadata", {}).get("user_id")
        if not user_id:
            logger.warning(f"No user_id in subscription metadata for subscription {subscription.id}")
            return

        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found when handling subscription deletion for {subscription.id}")
            return

        user_membership = UserMembership.objects.filter(user=user).first()
        if user_membership:
            if user_membership.stripe_subscription_id == subscription.id:
                user_membership.status = "canceled"
                user_membership.save()
    except Exception as e:
        logger.error(f"Error handling subscription deletion for subscription {subscription.id}: {str(e)}")


def handle_invoice_payment_succeeded(invoice):
    """
    Handle a successful invoice payment from Stripe.

    Args:
        invoice: The Stripe invoice object
    """
    try:
        if not invoice.get("subscription"):
            # Not a subscription invoice
            return

        subscription_id = invoice.get("subscription")
        subscription = stripe.Subscription.retrieve(subscription_id)

        user_id = subscription.get("metadata", {}).get("user_id")
        if not user_id:
            logger.warning(f"No user_id in subscription metadata for invoice {invoice.id}")
            return

        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found when handling invoice payment for {invoice.id}")
            return

        user_membership = UserMembership.objects.filter(user=user).first()
        if user_membership and user_membership.stripe_subscription_id == subscription_id:
            user_membership.status = "active"

            # Update end date
            if subscription.current_period_end:
                user_membership.end_date = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)

            user_membership.save()
    except Exception as e:
        logger.error(f"Error handling invoice payment for invoice {invoice.id}: {str(e)}")


def handle_invoice_payment_failed(invoice):
    """
    Handle a failed invoice payment from Stripe.

    Args:
        invoice: The Stripe invoice object
    """
    try:
        if not invoice.get("subscription"):
            # Not a subscription invoice
            return

        subscription_id = invoice.get("subscription")

        user_membership = UserMembership.objects.filter(stripe_subscription_id=subscription_id).first()
        if user_membership:
            user_membership.status = "past_due"
            user_membership.save()
    except Exception as e:
        logger.error(f"Error handling invoice payment failure for invoice {invoice.id}: {str(e)}")
