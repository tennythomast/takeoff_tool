# Core routing for WebSocket connections
from prompt.routing import websocket_urlpatterns as prompt_websocket_urlpatterns
from context_manager.routing import websocket_urlpatterns as context_websocket_urlpatterns

# Combine WebSocket patterns from all apps
websocket_urlpatterns = prompt_websocket_urlpatterns + context_websocket_urlpatterns