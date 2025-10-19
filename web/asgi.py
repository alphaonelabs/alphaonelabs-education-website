"""ASGI entrypoint for the project.

We wrap Django's default ASGI application so we can gracefully handle the
"lifespan" scope that uvicorn / ASGI servers may send. Vanilla Django only
implements HTTP (and optionally WebSocket) scopes and will raise:

    ValueError: Django can only handle ASGI/HTTP connections, not lifespan.

That shows up as noisy Sentry events. By intercepting the lifespan scope and
acknowledging startup/shutdown, we prevent the ValueError while keeping the
rest of Django's ASGI behaviour unchanged.
"""

from __future__ import annotations

import os

import django

# Set Django settings module before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")

# Initialize Django before importing anything that requires ORM
django.setup()

# noqa annotations silence E402 (module level import not at top of file)
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

# Local import must happen after Django setup
from web.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
