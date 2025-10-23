"""
ASGI config for dataelan project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dataelan.settings')
django.setup()

# Import WebSocket URL patterns
from workflows.routing import websocket_urlpatterns as workflow_websocket_urlpatterns
from prompt.routing import websocket_urlpatterns as chat_websocket_urlpatterns

# Define the ASGI application
application = ProtocolTypeRouter({
    # HTTP requests are handled by Django's ASGI application
    'http': get_asgi_application(),
    
    # WebSocket requests are handled by Channels with authentication
    'websocket': AuthMiddlewareStack(
        URLRouter(
            # Include WebSocket URL patterns from different apps
            workflow_websocket_urlpatterns +
            chat_websocket_urlpatterns
        )
    ),
})
