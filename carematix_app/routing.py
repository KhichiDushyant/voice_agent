"""
WebSocket routing for carematix_app.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/media-stream/', consumers.MediaStreamConsumer.as_asgi()),
]

