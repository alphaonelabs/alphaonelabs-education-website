"""WebSocket URL routing for the education website."""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/lobby/<int:lobby_id>/', consumers.LobbyConsumer.as_asgi()),
]
