from django.urls import path, re_path

from .consumers import VoiceChatConsumer

websocket_urlpatterns = [
    # Original UUID path
    path("ws/voice-chat/<uuid:room_id>/", VoiceChatConsumer.as_asgi()),
    # Additional pattern for dash-separated UUID format
    re_path(
        r"^ws/voice-chat/([0-9a-f]{8})/u002D([0-9a-f]{4})/u002D"
        r"([0-9a-f]{4})/u002D([0-9a-f]{4})/u002D([0-9a-f]{12})/$",
        VoiceChatConsumer.as_asgi(),
    ),
]
