# web/routing.py
from django.urls import path

from web.mass_class import routing as mass_class_routing

# Aggregate all websocket URL patterns here
websocket_urlpatterns = [] + mass_class_routing.websocket_urlpatterns
