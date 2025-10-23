from django.urls import path, include
from rest_framework_nested import routers
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes
from .views import (
    WorkspaceViewSet, WorkspaceCollaboratorViewSet
)

# Create a router for workspaces
router = routers.DefaultRouter()
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')

workspace_router = routers.NestedDefaultRouter(
    router,
    r'workspaces',
    lookup='workspace'
)
workspace_router.register(
    r'collaborators',
    WorkspaceCollaboratorViewSet,
    basename='workspace-collaborator'
)

urlpatterns = [
    path('', include(router.urls)),
    path('', include(workspace_router.urls)),
]
