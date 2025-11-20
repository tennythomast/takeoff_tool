"""
ASGI config for dataelan project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

# Set the Django settings module first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
django.setup()

# Now, import other modules that may depend on Django's settings
from channels.routing import ProtocolTypeRouter, URLRouter
from core.middleware import TokenAuthMiddleware
from core.routing import websocket_urlpatterns as core_websocket_urlpatterns
from prompt.routing import websocket_urlpatterns as prompt_websocket_urlpatterns


# Combine all websocket URL patterns
all_websocket_urlpatterns = core_websocket_urlpatterns + prompt_websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
        URLRouter(
            all_websocket_urlpatterns
        )
    ),
})

