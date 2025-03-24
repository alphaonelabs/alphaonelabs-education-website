import logging

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
        # Check if user already has a customer ID
        if hasattr(user, "stripe_customer_id") and user.stripe_customer_id:
            # Verify the customer exists on Stripe
            try:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                if hasattr(customer, "deleted") and not customer.deleted:
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

        # Store the customer ID on the user
        user.stripe_customer_id = customer.id
        user.save()

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


def update_membership_from_subscription(user, subscription):
    """
    Update a user's membership based on a Stripe subscription object.

    Args:
        user: The Django user object
        subscription: The Stripe subscription object
    """
    try:
        # Get or create the user membership
        user_membership, created = UserMembership.objects.get_or_create(
            user=user,
            defaults={
                "start_date": timezone.now(),
            },
        )

        # Update the subscription ID and status
        user_membership.stripe_subscription_id = subscription.id
        user_membership.status = subscription.status

        # Set the end date based on the subscription end
        if hasattr(subscription, "current_period_end"):
            user_membership.end_date = timezone.datetime.fromtimestamp(
                subscription.current_period_end, tz=timezone.get_current_timezone()
            )

        # Try to find the plan based on the price ID
        if hasattr(subscription, "items") and subscription.items.data:
            price_id = subscription.items.data[0].price.id
            try:
                plan = None
                # Check both monthly and yearly price IDs
                plan = (
                    MembershipPlan.objects.filter(stripe_monthly_price_id=price_id).first()
                    or MembershipPlan.objects.filter(stripe_yearly_price_id=price_id).first()
                )

                if plan:
                    user_membership.plan = plan

                    # Set the billing period
                    if price_id == plan.stripe_yearly_price_id:
                        user_membership.billing_period = "yearly"
                    else:
                        user_membership.billing_period = "monthly"
            except Exception as e:
                logger.error(f"Error finding plan for price ID {price_id}: {str(e)}")

        user_membership.save()

        # Create a subscription event
        from .models import MembershipSubscriptionEvent

        MembershipSubscriptionEvent.objects.create(
            user=user,
            membership=user_membership,
            event_type="created" if created else "updated",
            data={"subscription_id": subscription.id, "status": subscription.status},
        )

        return user_membership
    except Exception as e:
        logger.error(f"Error updating membership from subscription for user {user.id}: {str(e)}")
        raise
