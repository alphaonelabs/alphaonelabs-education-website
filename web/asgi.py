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
from typing import Any, Awaitable, Callable, Dict

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")

# Obtain the original Django ASGI app
django_asgi_app = get_asgi_application()


async def application(
    scope: Dict[str, Any],
    receive: Callable[[], Awaitable[Dict[str, Any]]],
    send: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:  # type: ignore[override]
    """ASGI application wrapper.

    Handles lifespan scope (startup/shutdown) explicitly so Django's internal
    application is never invoked with an unsupported scope type. Other scopes
    are delegated unchanged.
    """
    scope_type = scope.get("type")

    if scope_type == "lifespan":
        # Minimal lifespan protocol implementation: acknowledge and exit.
        while True:
            message = await receive()
            msg_type = message.get("type")
            if msg_type == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg_type == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        # Delegate HTTP / websocket (future) / other supported scopes to Django
        await django_asgi_app(scope, receive, send)
