import json
import logging

import requests
from django.conf import settings
from django.core.mail.backends.console import EmailBackend as ConsoleBackend
from typing import List, Optional

# Only import SendgridBackend if we have a key configured
if settings.SENDGRID_API_KEY:
    from sendgrid_backend.mail import SendgridBackend
else:
    # Create a dummy class to avoid import errors
    class SendgridBackend:
        pass

logger = logging.getLogger(__name__)


class SlackNotificationEmailBackend:
    """
    Email backend that logs emails to the console and sends a notification to Slack.
    Falls back to console backend if SendGrid API key is not configured.
    """
    def __init__(self, **kwargs):
        self.fail_silently = kwargs.get('fail_silently', False)
        
        # Use the appropriate backend based on configuration
        if settings.SENDGRID_API_KEY:
            self.backend = SendgridBackend(api_key=settings.SENDGRID_API_KEY, **kwargs)
        else:
            self.backend = ConsoleBackend(**kwargs)
            print("Using console email backend (SendGrid API key not configured)")

        self.webhook_url = getattr(settings, "EMAIL_SLACK_WEBHOOK", None)

    def open(self):
        return self.backend.open()

    def close(self):
        return self.backend.close()

    def send_messages(self, email_messages):
        """Send messages to the backend and log to console."""
        # Send email using the selected backend
        sent = self.backend.send_messages(email_messages)
        
        # Log to Slack if webhook URL is configured and valid
        try:
            self._log_to_slack(email_messages)
        except Exception as e:
            print(f"Failed to send to Slack: {e}")
        
        return sent

    def _log_to_slack(self, email_messages: List) -> None:
        """Send a notification to Slack about sent emails."""
        import requests
        webhook_url = getattr(settings, "SLACK_WEBHOOK_URL", "")
        
        # Skip if webhook URL is not configured properly
        if not webhook_url or "://" not in webhook_url:
            return
        
        # Prepare message
        for message in email_messages:
            text = f"Email sent\nTo: {message.to}\nSubject: {message.subject}"
            try:
                requests.post(
                    webhook_url, 
                    json={"text": text},
                    timeout=5
                )
            except Exception:
                # Don't fail if Slack notification fails
                pass

    def _notify_slack(self, email_message):
        """Send a notification to Slack about the email."""
        if not self.webhook_url:
            return

        try:
            # Create a message for Slack
            recipients = ", ".join(email_message.to)
            subject = email_message.subject

            slack_message = {
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": "📧 Email Sent", "emoji": True}},
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*To:*\n{recipients}"},
                            {"type": "mrkdwn", "text": f"*From:*\n{email_message.from_email}"},
                        ],
                    },
                    {"type": "section", "fields": [{"type": "mrkdwn", "text": f"*Subject:*\n{subject}"}]},
                ]
            }

            # Send the notification to Slack
            response = requests.post(
                self.webhook_url, data=json.dumps(slack_message), headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Failed to send Slack notification: {response.status_code} {response.text}")

        except Exception as e:
            logger.exception(f"Error sending Slack notification: {str(e)}")
