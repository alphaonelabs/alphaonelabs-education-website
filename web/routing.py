# web/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/quiz/(?P<quiz_id>\w+)/$', consumers.QuizConsumer.as_asgi()),
]