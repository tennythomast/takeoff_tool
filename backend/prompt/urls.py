from django.urls import path
from rest_framework_nested import routers
from workspaces.urls import router
from . import views

# Create nested routers for proper URL structure
# /workspaces/{workspace_id}/prompt-sessions/
workspace_router = routers.NestedSimpleRouter(
    router,
    r'workspaces',
    lookup='workspace'
)
workspace_router.register(
    r'prompt-sessions', 
    views.PromptSessionViewSet, 
    basename='prompt-session'
)

# /workspaces/{workspace_id}/prompt-sessions/{session_id}/prompts/
prompt_session_router = routers.NestedSimpleRouter(
    workspace_router,
    r'prompt-sessions',
    lookup='session'
)
prompt_session_router.register(
    r'prompts', 
    views.PromptViewSet, 
    basename='prompt'
)

# /workspaces/{workspace_id}/prompt-sessions/{session_id}/metrics/
# Metrics are now associated with sessions via session_id field
session_metrics_router = routers.NestedSimpleRouter(
    workspace_router,
    r'prompt-sessions',
    lookup='session'
)
session_metrics_router.register(
    r'metrics', 
    views.ModelMetricsViewSet, 
    basename='session-metrics'
)

# Include all router URLs
urlpatterns = []
urlpatterns += workspace_router.urls
urlpatterns += prompt_session_router.urls
urlpatterns += session_metrics_router.urls
