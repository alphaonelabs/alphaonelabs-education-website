"""Module for handling SendGrid webhook events."""

import json
import logging
from datetime import datetime

import pytz
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import EmailEvent
from .slack import send_slack_notification

logger = logging.getLogger(__name__)


from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings
from sendgrid.helpers.eventwebhook import EventWebhook, EventWebhookHeader

event_verifier = EventWebhook()

@csrf_exempt
def sendgrid_webhook(request):
    """Process SendGrid webhook events."""
    if request.method != "POST":
        return HttpResponse(status=405)  # Method not allowed

    # 1️⃣  Verify signature
    try:
        signature = request.headers.get(EventWebhookHeader.SIGNATURE)
        timestamp  = request.headers.get(EventWebhookHeader.TIMESTAMP)
        public_key = settings.SENDGRID_WEBHOOK_PUBLIC_KEY

        if not (signature and timestamp and public_key):
            logger.warning("Missing SendGrid webhook signature headers")
            return HttpResponseForbidden()

        if not event_verifier.verify_signature(request.body, signature, timestamp, public_key):
            logger.warning("SendGrid webhook signature verification failed")
            return HttpResponseForbidden()
    except Exception:
        logger.exception("Error verifying SendGrid webhook signature")
        return HttpResponseForbidden()
    try:
        # Parse the incoming JSON
        data = json.loads(request.body)
        logger.info(f"Received SendGrid webhook with {len(data)} events")

        # SendGrid sends an array of events
        for event in data:
            try:
                process_sendgrid_event(event)
            except Exception as e:
                logger.exception(f"Error processing SendGrid event: {e}")

        # Send a success response
        return HttpResponse(status=200)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in SendGrid webhook")
        return HttpResponse(status=400)  # Bad request
    except Exception as e:
        logger.exception(f"Error processing SendGrid webhook: {e}")
        return HttpResponse(status=500)  # Internal server error

def process_sendgrid_event(event):
    """Process a single SendGrid event and update user records."""
    # Get event data
    email = event.get("email", "").lower()
    event_type = event.get("event", "other")
    timestamp = event.get("timestamp")
    sg_message_id = event.get("sg_message_id", "")
    sg_event_id = event.get("sg_event_id", "")

    # Skip if no email is provided
    if not email:
        logger.warning("Received SendGrid event with no email address")
        return

    # Convert timestamp to datetime
    if timestamp:
        # SendGrid timestamp is in Unix epoch seconds
        try:
            dt = datetime.fromtimestamp(int(timestamp), tz=pytz.UTC)
        except (ValueError, TypeError):
            dt = timezone.now()
    else:
        dt = timezone.now()

    # Find the associated user
    user = User.objects.filter(email__iexact=email).first()

    # Create an event record
    EmailEvent.objects.create(
        email=email,
        user=user,
        event_type=event_type,
        timestamp=dt,
        sg_message_id=sg_message_id,
        sg_event_id=sg_event_id,
        event_data=event,
    )

    # Update profile statistics if user exists
    if user and hasattr(user, "profile"):
        profile = user.profile

        # Update the event counters
        if event_type == "delivered":
            profile.email_delivered_count += 1
        elif event_type == "open":
            profile.email_open_count += 1
        elif event_type == "click":
            profile.email_click_count += 1
        elif event_type == "bounce":
            profile.email_bounce_count += 1
        elif event_type == "dropped":
            profile.email_drop_count += 1
        elif event_type == "spamreport":
            profile.email_spam_report_count += 1

        # Update last event information
        profile.last_email_event = event_type
        profile.last_email_event_time = dt
        profile.email_last_event_data = event

        # Save the profile
        profile.save(
            update_fields=[
                "email_delivered_count",
                "email_open_count",
                "email_click_count",
                "email_bounce_count",
                "email_drop_count",
                "email_spam_report_count",
                "last_email_event",
                "last_email_event_time",
                "email_last_event_data",
            ]
        )

    # Send notification to Slack
    send_sendgrid_event_to_slack(event, email, event_type, user)


def send_sendgrid_event_to_slack(event, email, event_type, user=None):
    """Send SendGrid event notification to Slack."""
    # Map event types to emojis for better visibility in Slack
    event_emojis = {
        "processed": "🔄",
        "delivered": "✅",
        "open": "👁️",
        "click": "🖱️",
        "bounce": "🔴",
        "dropped": "⛔",
        "spamreport": "🚫",
        "unsubscribe": "👋",
        "group_unsubscribe": "👋",
        "group_resubscribe": "🔄",
        "deferred": "⏳",
        "blocked": "🚧",
    }

    emoji = event_emojis.get(event_type, "📧")
    user_info = f" ({user.username})" if user else ""

    # Format the message based on event type
    header = f"{emoji} SendGrid *{event_type.upper()}* event for {email}{user_info}"

    # Add event details
    details = []
    for key, value in event.items():
        if key in ["email", "event", "timestamp", "sg_message_id", "sg_event_id", "type", "category"]:
            details.append(f"*{key}:* {value}")

    # The full message
    message = header + "\n" + "\n".join(details)

    # Reason for dropped or bounced emails
    if event_type in ["dropped", "bounce"]:
        reason = event.get("reason", "Unknown reason")
        message += f"\n*Reason:* {reason}"

    # Send to Slack
    send_slack_notification(message)
