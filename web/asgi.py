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

from typing import Any, Awaitable, Callable, Dict  # noqa: E402

# noqa annotations silence E402 (module level import not at top of file)
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware  # noqa: E402

# Local import must happen after Django setup
from web.routing import websocket_urlpatterns  # noqa: E402

_channels_router = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)

# Wrap the entire router so both HTTP and WebSocket errors reach Sentry
channels_application = SentryAsgiMiddleware(_channels_router)


async def application(
    scope: Dict[str, Any],
    receive: Callable[[], Awaitable[Dict[str, Any]]],
    send: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:
    """Unified ASGI application with optional Channels + lifespan handling.

    Provides:
    - Lifespan scope acknowledgement to prevent Django ValueError noise.
    - Optional Channels (websocket) support when dependencies and routes exist.
    - Delegates all other scopes to either Channels router or plain Django.
    """
    scope_type = scope.get("type")

    if scope_type == "lifespan":
        while True:
            message = await receive()
            msg_type = message.get("type")
            if msg_type == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg_type == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        await channels_application(scope, receive, send)
