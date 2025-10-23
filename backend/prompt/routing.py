from django.urls import re_path
from . import consumers

# WebSocket URL patterns for prompt app
websocket_urlpatterns = [
    # Chat WebSocket with mandatory session_id parameter
    re_path(r'ws/chat/(?P<session_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
    # Fallback for default session
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]
