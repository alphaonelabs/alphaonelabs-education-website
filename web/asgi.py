"""
ASGI config for web project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path, re_path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from .consumers import VoiceChatConsumer  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    # Original UUID path
                    path("ws/voice-chat/<uuid:room_id>/", VoiceChatConsumer.as_asgi()),
                    # Additional pattern for dash-separated UUID format
                    re_path(
                        r"^ws/voice-chat/([0-9a-f]{8})\/u002D([0-9a-f]{4})\/u002D"
                        r"([0-9a-f]{4})\/u002D([0-9a-f]{4})\/u002D([0-9a-f]{12})/$",
                        VoiceChatConsumer.as_asgi(),
                    ),
                ]
            )
        ),
    }
)
