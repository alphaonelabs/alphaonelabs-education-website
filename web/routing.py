from django.urls import path

from . import consumers_lobby

websocket_urlpatterns = [
    path("ws/lobby/<str:lobby_id>/", consumers_lobby.VirtualLobbyConsumer.as_asgi()),
]
