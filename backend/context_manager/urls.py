# context_manager/urls.py

from django.urls import path, include
from . import views

app_name = 'context_manager'

# PHASE 2 ENHANCED UNIVERSAL API ENDPOINTS
urlpatterns = [
    # ========================================
    # CORE UNIVERSAL CONTEXT MANAGEMENT
    # ========================================
    
    # Universal context preparation for all domains (Chat, Agents, Workflows)
    path('prepare/', views.prepare_context, name='prepare_context'),
    
    # Universal interaction storage across all domains
    path('store/', views.store_interaction, name='store_interaction'),
    
    # ========================================
    # DATA RETRIEVAL & ANALYTICS
    # ========================================
    
    # Get conversation history for any session type
    path('history/', views.get_conversation_history, name='conversation_history'),
    
    # Get comprehensive analytics for any session type
    path('analytics/', views.get_session_analytics, name='session_analytics'),
    
    # Get performance metrics across all domains
    path('performance/', views.get_performance_metrics, name='performance_metrics'),
    
    # ========================================
    # ENHANCED CACHE MANAGEMENT
    # ========================================
    
    # Get cache performance metrics with domain filtering
    path('cache-metrics/', views.get_cache_metrics, name='cache_metrics'),
    
    # Cache management operations
    # path('cache/invalidate/', views.invalidate_cache, name='invalidate_cache'),
    # path('cache/warm/', views.warm_cache, name='warm_cache'),
    
    # ========================================
    # COST OPTIMIZATION & INSIGHTS
    # ========================================
    
    # Cost breakdown and optimization insights
    # path('costs/breakdown/', views.get_cost_breakdown, name='cost_breakdown'),
    # path('costs/estimate/', views.estimate_costs, name='estimate_costs'),
    # path('costs/optimization/', views.get_optimization_insights, name='optimization_insights'),
    
    # Model usage analytics
    # path('models/usage/', views.get_model_usage_stats, name='model_usage_stats'),
    # path('models/performance/', views.get_model_performance, name='model_performance'),
    
    # ========================================
    # CONTEXT STRATEGY ANALYTICS
    # ========================================
    
    # Context strategy effectiveness
    # path('strategies/effectiveness/', views.get_strategy_effectiveness, name='strategy_effectiveness'),
    # path('strategies/transitions/', views.get_strategy_transitions, name='strategy_transitions'),
    
    # Cache strategy insights
    # path('strategies/cache-performance/', views.get_cache_strategy_performance, name='cache_strategy_performance'),
    
    # ========================================
    # DOMAIN-SPECIFIC ENDPOINTS
    # ========================================
    
    # Chat-specific endpoints
    #path('chat/sessions/', views.get_chat_sessions, name='chat_sessions'),
    #path('chat/summary/', views.get_chat_summary, name='chat_summary'),

    # Agent-specific endpoints
    #path('agents/sessions/', views.get_agent_sessions, name='agent_sessions'),
    #path('agents/reasoning/', views.get_agent_reasoning_chains, name='agent_reasoning'),
    #path('agents/tools/', views.get_agent_tool_usage, name='agent_tool_usage'),

    # Workflow-specific endpoints
    # path('workflows/sessions/', views.get_workflow_sessions, name='workflow_sessions'),
    # path('workflows/state/', views.get_workflow_state, name='workflow_state'),
    # path('workflows/dependencies/', views.get_workflow_dependencies, name='workflow_dependencies'),
    
    # ========================================
    # MAINTENANCE & CLEANUP
    # ========================================
    
    # Enhanced cleanup with domain awareness
    #path('cleanup/', views.cleanup_session_cache, name='cleanup_cache'),
    #path('cleanup/low-importance/', views.cleanup_low_importance, name='cleanup_low_importance'),
    #path('cleanup/expired/', views.cleanup_expired, name='cleanup_expired'),
    
    # Maintenance operations
    #path('maintenance/optimize/', views.optimize_storage, name='optimize_storage'),
    #path('maintenance/rebuild-cache/', views.rebuild_cache, name='rebuild_cache'),
    
    # ========================================
    # ORGANIZATION & TIER MANAGEMENT
    # ========================================
    
    # Organization-level analytics
    #path('organization/overview/', views.get_organization_overview, name='organization_overview'),
    #path('organization/usage/', views.get_organization_usage, name='organization_usage'),
    #path('organization/limits/', views.get_organization_limits, name='organization_limits'),
    
    # Tier-specific insights
    #path('tier/recommendations/', views.get_tier_recommendations, name='tier_recommendations'),
    #path('tier/comparison/', views.get_tier_comparison, name='tier_comparison'),
    
    # ========================================
    # REAL-TIME & MONITORING
    # ========================================
    
    # Health checks and system status
    #path('health/', views.health_check, name='health_check'),
    #path('health/detailed/', views.detailed_health_check, name='detailed_health_check'),
    
    # Real-time metrics for dashboards
    #path('metrics/realtime/', views.get_realtime_metrics, name='realtime_metrics'),
    #path('metrics/alerts/', views.get_metric_alerts, name='metric_alerts'),
    
    # ========================================
    # ADVANCED ANALYTICS & REPORTING
    # ========================================
    
    # Trend analysis
    #path('trends/usage/', views.get_usage_trends, name='usage_trends'),
    #path('trends/costs/', views.get_cost_trends, name='cost_trends'),
    #path('trends/performance/', views.get_performance_trends, name='performance_trends'),
    
    # Comparative analytics
    #path('compare/models/', views.compare_models, name='compare_models'),
    #path('compare/strategies/', views.compare_strategies, name='compare_strategies'),
    #path('compare/periods/', views.compare_periods, name='compare_periods'),
    
    # Export and reporting
    #path('export/sessions/', views.export_sessions, name='export_sessions'),
    #path('export/costs/', views.export_costs, name='export_costs'),
    #path('export/analytics/', views.export_analytics, name='export_analytics'),
    
    # ========================================
    # SEARCH & DISCOVERY
    # ========================================
    
    # Semantic search across conversations
    #path('search/conversations/', views.search_conversations, name='search_conversations'),
    #path('search/similar/', views.find_similar_conversations, name='find_similar'),
    
    # Content discovery
    #path('discover/patterns/', views.discover_patterns, name='discover_patterns'),
    #path('discover/anomalies/', views.discover_anomalies, name='discover_anomalies'),
    
    # ========================================
    # INTEGRATION ENDPOINTS
    # ========================================
    
    # ModelHub integration endpoints
    #path('modelhub/sync/', views.sync_with_modelhub, name='sync_modelhub'),
    #path('modelhub/costs/', views.sync_model_costs, name='sync_model_costs'),
    

    # ========================================
    # ADMIN & DEBUG ENDPOINTS
    # ========================================
    
    # Debug information
    #path('debug/session/<str:session_id>/', views.debug_session, name='debug_session'),
    #path('debug/cache/<str:cache_id>/', views.debug_cache, name='debug_cache'),
    #path('debug/performance/', views.debug_performance, name='debug_performance'),
    
    # Admin utilities
    #path('admin/rebuild-indexes/', views.rebuild_indexes, name='rebuild_indexes'),
    #path('admin/validate-data/', views.validate_data, name='validate_data'),
    #path('admin/system-info/', views.get_system_info, name='system_info'),
]

# ========================================
# CLEAN API STRUCTURE
# ========================================

# All endpoints use the current enhanced universal API structure
# No legacy versioning - clean, modern API design

# ========================================
# CUSTOM ERROR HANDLING
# ========================================

# Custom error views for context manager
#handler400 = 'context_manager.views.bad_request'
#handler403 = 'context_manager.views.permission_denied'
#handler404 = 'context_manager.views.not_found'
#handler500 = 'context_manager.views.server_error'