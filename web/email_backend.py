import json
import logging

import requests
from django.conf import settings
from django.core.mail.backends.console import EmailBackend as ConsoleBackend

logger = logging.getLogger(__name__)


class SlackNotificationEmailBackend:
    """
    Email backend that sends a notification to Slack whenever an email is sent.
    This is a wrapper around another email backend.
    """

    def __init__(self, **kwargs):
        # Determine which backend to use based on settings
        if settings.DEBUG:
            self.backend = ConsoleBackend(**kwargs)
        else:
            # Use SendGrid backend in production
            from sendgrid_backend.mail import SendgridBackend

            self.backend = SendgridBackend(**kwargs)

        self.webhook_url = getattr(settings, "EMAIL_SLACK_WEBHOOK", None)

    def open(self):
        return self.backend.open()

    def close(self):
        return self.backend.close()

    def send_messages(self, email_messages):
        # First, send the emails using the wrapped backend
        sent_count = self.backend.send_messages(email_messages)

        # Then, send notifications to Slack for each email
        if self.webhook_url and sent_count:
            for message in email_messages:
                self._notify_slack(message)

        return sent_count

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
