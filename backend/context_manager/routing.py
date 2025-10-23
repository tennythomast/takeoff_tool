# context_manager/routing.py
from django.urls import re_path

websocket_urlpatterns = [
    # Define WebSocket URL patterns for context_manager app
    # Currently no WebSocket consumers are implemented for context_manager
    # This empty list is required for the import in core/routing.py to work
]
