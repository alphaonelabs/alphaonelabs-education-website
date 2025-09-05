import json
import logging
from typing import List, Optional

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
        """Initialise the wrapped backend with graceful degradation.

        Behaviour:
        - In DEBUG always use console backend.
        - In production attempt to initialise SendGrid; on any failure (missing
          key, invalid credentials, HTTP 401 during lazy auth) fall back to
          console backend and mark sendgrid as disabled so future sends do not
          keep retrying unnecessarily.
        """
        self.webhook_url = getattr(settings, "EMAIL_SLACK_WEBHOOK", None)
        self.sendgrid_enabled = False
        self._fallback_reason: Optional[str] = None

        if settings.DEBUG:
            self.backend = ConsoleBackend(**kwargs)
            self._fallback_reason = "debug-mode"
        else:
            # Attempt SendGrid initialisation
            try:
                api_key = getattr(settings, "SENDGRID_API_KEY", None) or ""
                if not api_key:
                    raise RuntimeError("SENDGRID_API_KEY missing; disabling SendGrid backend")
                from sendgrid_backend.mail import SendgridBackend  # local import so failure is caught

                self.backend = SendgridBackend(**kwargs)
                self.sendgrid_enabled = True
            except Exception as e:  # broad: we explicitly want to swallow any init error
                self.backend = ConsoleBackend(**kwargs)
                self._fallback_reason = str(e)
                logger.warning(
                    "SendGrid backend disabled; using console backend instead (reason=%s)",
                    self._fallback_reason,
                )

    def open(self):
        return self.backend.open()

    def close(self):
        return self.backend.close()

    def send_messages(self, email_messages):  # type: ignore[override]
        """Send a batch of messages with graceful failure handling.

        If SendGrid returns an Unauthorized (401) or any other exception, we:
        - Log a warning (NOT exception to avoid Sentry noise unless configured)
        - Log each email basic metadata so it's not lost
        - Return 0 to the caller (Django's email API treats that as 'not sent')
        """
        # If previously disabled, don't attempt network sends repeatedly.
        if not self.sendgrid_enabled:
            return self._log_fallback(email_messages)

        try:
            sent_count = self.backend.send_messages(email_messages)
        except Exception as e:  # noqa: BLE001
            # Downgrade to warning; include class name for quick triage.
            logger.warning("Email send failed via SendGrid (%s): %s", e.__class__.__name__, e)
            # Disable further attempts this process lifetime to reduce noise.
            self.sendgrid_enabled = False
            self._fallback_reason = str(e)
            return self._log_fallback(email_messages)

        # Slack notifications only if actual send happened
        if self.webhook_url and sent_count:
            for message in email_messages:
                self._notify_slack(message)
        return sent_count

    def _log_fallback(self, email_messages: List):
        """Log email metadata when we intentionally skip sending."""
        for m in email_messages:
            try:
                logger.info(
                    "EMAIL_FALLBACK to=%s subject=%s reason=%s",
                    m.to,
                    getattr(m, "subject", "(no-subject)"),
                    self._fallback_reason,
                )
            except Exception:  # pragma: no cover - defensive
                pass
        return 0

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
