from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MCPServerRegistryViewSet, MCPServerConnectionViewSet, MCPResourceDiscoveryViewSet,
    MCPWorkspaceAccessViewSet, MCPResourceUsageViewSet, MCPResourceMappingViewSet
)

router = DefaultRouter()
router.register(r'registry', MCPServerRegistryViewSet, basename='mcp-registry')
router.register(r'connections', MCPServerConnectionViewSet, basename='mcp-connection')
router.register(r'resources', MCPResourceDiscoveryViewSet, basename='mcp-resource')
router.register(r'workspace-access', MCPWorkspaceAccessViewSet, basename='mcp-workspace-access')
router.register(r'usage', MCPResourceUsageViewSet, basename='mcp-usage')
router.register(r'mappings', MCPResourceMappingViewSet, basename='mcp-mapping')

urlpatterns = [
    path('', include(router.urls)),
]
