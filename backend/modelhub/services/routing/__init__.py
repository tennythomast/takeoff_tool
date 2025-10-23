# backend/modelhub/services/routing/__init__.py
"""
Enhanced Intelligent Routing System

This package provides sophisticated model routing with entity awareness,
supporting multiple use cases across the platform:

Supported Entity Types:
- platform_chat: General platform conversations
- agent_session: Agent-based interactions  
- workflow_execution: Agentic workflow processing
- workspace_chat: Workspace-specific conversations
- rag_query: RAG-enhanced queries

Features:
- Database-driven routing rules
- Entity-aware model selection
- Session stickiness optimization
- Cost protection and monitoring
- Performance tracking

Usage:
    from modelhub.services.routing import (
        EnhancedModelRouter, EnhancedSessionManager, 
        RequestContext, OptimizationStrategy
    )
    
    # Create router
    router = EnhancedModelRouter()
    
    # Create context for agent session
    context = RequestContext(
        entity_type='agent_session',
        session_id='session-123',
        organization_id='org-456',
        max_tokens=2000
    )
    
    # Route request
    decision = await router.route_request(
        organization=org,
        complexity_score=0.7,
        content_type='code',
        context=context,
        strategy=OptimizationStrategy.BALANCED
    )

Performance Targets:
- Routing decisions: 20-40ms
- Session stickiness: 2-5ms  
- Database rule lookup: 10-15ms
- Overall routing latency: 25-50ms

Entity-Specific Optimizations:
- Workflows: Fast switching, function calling support
- Agents: Quality focus, session consistency
- Platform chat: Balanced approach
- RAG queries: Context window optimization
"""

from .router import EnhancedModelRouter
from .session_manager import EnhancedSessionManager
from .types import (
    RequestContext, RoutingDecision, OptimizationStrategy, 
    EntityType, ModelCandidate, SessionState, RoutingMetrics
)

# Main router classes
__all__ = [
    # Core classes
    'EnhancedModelRouter',
    'EnhancedSessionManager',
    
    # Data types
    'RequestContext',
    'RoutingDecision', 
    'OptimizationStrategy',
    'EntityType',
    'ModelCandidate',
    'SessionState',
    'RoutingMetrics'
]

# Version and metadata
__version__ = '2.0.0'
__author__ = 'AI Cost Optimizer Team'

def get_routing_info():
    """Get routing system information"""
    return {
        'version': __version__,
        'entity_types_supported': [e.value for e in EntityType],
        'optimization_strategies': [s.value for s in OptimizationStrategy],
        'features': [
            'database_routing_rules',
            'entity_aware_routing',
            'session_stickiness',
            'cost_protection', 
            'performance_monitoring',
            'multi_organization_support'
        ],
        'performance_targets': {
            'routing_decision_ms': '20-40',
            'session_check_ms': '2-5',
            'database_lookup_ms': '10-15',
            'total_latency_ms': '25-50'
        }
    }