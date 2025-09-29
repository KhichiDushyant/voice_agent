"""
ASGI config for carematix project.
"""

import os

# Set Django settings module before any Django imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carematix.settings')

import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from carematix_app import routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})

