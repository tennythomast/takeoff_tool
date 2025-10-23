from django.urls import re_path
from . import consumers

# WebSocket URL patterns for agents app
websocket_urlpatterns = [
    # Agent execution WebSocket with execution_id parameter
    re_path(r'ws/agents/execution/(?P<execution_id>[^/]+)/$', consumers.AgentExecutionConsumer.as_asgi()),
]
