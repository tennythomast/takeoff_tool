from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import (
    AgentViewSet, AgentToolViewSet, AgentParameterViewSet, AgentExecutionViewSet,
    AgentConfigurationStepViewSet, AgentOptimizationViewSet, AgentToolExecutionViewSet,
    AgentInstructionsViewSet
)

router = DefaultRouter()
router.register(r'agents', AgentViewSet, basename='agent')
router.register(r'executions', AgentExecutionViewSet, basename='execution')
router.register(r'tool-executions', AgentToolExecutionViewSet, basename='tool-execution')
router.register(r'config-steps', AgentConfigurationStepViewSet, basename='config-step')
router.register(r'optimizations', AgentOptimizationViewSet, basename='optimization')

# Register agent instructions endpoint
router.register(r'agent-instructions', AgentInstructionsViewSet, basename='agent-instructions')

# Nested routes for agent tools and parameters
agent_router = NestedDefaultRouter(router, r'agents', lookup='agent')
agent_router.register(r'tools', AgentToolViewSet, basename='agent-tool')
agent_router.register(r'parameters', AgentParameterViewSet, basename='agent-parameter')
agent_router.register(r'config', AgentConfigurationStepViewSet, basename='agent-config')
agent_router.register(r'optimizations', AgentOptimizationViewSet, basename='agent-optimization')

# Nested routes for execution tool executions
execution_router = NestedDefaultRouter(router, r'executions', lookup='execution')
execution_router.register(r'tool-executions', AgentToolExecutionViewSet, basename='execution-tool-execution')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(agent_router.urls)),
    path('', include(execution_router.urls)),
]
