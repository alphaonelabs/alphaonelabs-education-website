"""WebSocket URL routing for Django Channels."""

from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/classroom/<int:classroom_id>/", consumers.VirtualClassroomConsumer.as_asgi()),
]
