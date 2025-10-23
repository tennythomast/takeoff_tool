# context_manager/views.py

import logging
from decimal import Decimal
from typing import Dict, Any

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from .services.universal_context_service import UniversalContextService, ContextRequest
from .services.cache_service import SummaryCacheService
from .services.storage_service import FullContextStorageService
from .utils import validator, performance_monitor

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def prepare_context(request):
    """
    Universal Context Preparation API
    
    Supports Chat, Agents, and Workflows with intelligent optimization
    
    POST /api/context/prepare/
    {
        "entity_id": "session_123",
        "entity_type": "prompt_session",  # or "agent_session", "workflow_execution"
        "organization_id": "org_456", 
        "target_model": "gpt-4",
        "user_message": "What were we discussing about the pricing model?",
        "preserve_quality": true,
        "cost_limit": "0.01"
    }
    
    Returns:
    {
        "context_content": "...",
        "strategy_used": "full_context",
        "tokens_used": 1500,
        "preparation_cost": "0.0000",
        "preparation_time_ms": 45,
        "cache_hit": false,
        "information_preservation_score": 1.0
    }
    """
    try:
        data = request.data
        
        # Required fields for universal API
        required_fields = ['entity_id', 'entity_type', 'organization_id', 'target_model', 'user_message']
        for field in required_fields:
            if field not in data or not data[field]:
                return Response(
                    {'error': f'Missing required field: {field}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate entity type
        valid_entity_types = ['prompt_session', 'agent_session', 'workflow_execution', 'custom']
        if data['entity_type'] not in valid_entity_types:
            return Response(
                {'error': f'Invalid entity_type. Must be one of: {valid_entity_types}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate field formats
        if not validator.validate_entity_id(data['entity_id']):
            return Response(
                {'error': 'Invalid entity_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_organization_id(data['organization_id']):
            return Response(
                {'error': 'Invalid organization_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_model_name(data['target_model']):
            return Response(
                {'error': 'Invalid target_model format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_message_content(data['user_message']):
            return Response(
                {'error': 'Invalid user_message content'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create universal context request
        context_request = ContextRequest(
            entity_id=data['entity_id'],
            entity_type=data['entity_type'],
            organization_id=data['organization_id'],
            target_model=data['target_model'],
            user_message=data['user_message'],
            preserve_quality=data.get('preserve_quality', True),
            cost_limit=Decimal(str(data['cost_limit'])) if data.get('cost_limit') else None
        )
        
        # Prepare context using universal service
        context_service = UniversalContextService()
        context_response = await context_service.prepare_context(context_request)
        
        # Record performance metrics
        performance_monitor.record_context_preparation(
            strategy=context_response.strategy_used,
            cost=context_response.preparation_cost,
            time_ms=context_response.preparation_time_ms,
            cache_hit=context_response.cache_hit
        )
        
        return Response({
            'context_content': context_response.context_content,
            'strategy_used': context_response.strategy_used,
            'tokens_used': context_response.tokens_used,
            'preparation_cost': str(context_response.preparation_cost),
            'preparation_time_ms': context_response.preparation_time_ms,
            'cache_hit': context_response.cache_hit,
            'information_preservation_score': context_response.information_preservation_score,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Context preparation failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Context preparation failed', 'details': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def store_interaction(request):
    """
    Store interaction in universal context system
    
    POST /api/context/store/
    {
        "entity_id": "session_123",
        "entity_type": "prompt_session",
        "organization_id": "org_456",
        "role": "user",
        "content": "What's the pricing for the pro plan?",
        "content_type": "text",
        "source_entity_id": "prompt_456",
        "source_entity_type": "prompt",
        "model_used": "gpt-4",
        "context_metadata": {
            "strategy": "full_context",
            "tokens_used": 1500,
            "total_cost": "0.0030"
        }
    }
    """
    try:
        data = request.data
        
        # Required fields
        required_fields = ['entity_id', 'entity_type', 'organization_id', 'role', 'content']
        for field in required_fields:
            if field not in data or not data[field]:
                return Response(
                    {'error': f'Missing required field: {field}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate entity type
        valid_entity_types = ['prompt_session', 'agent_session', 'workflow_execution', 'custom']
        if data['entity_type'] not in valid_entity_types:
            return Response(
                {'error': f'Invalid entity_type. Must be one of: {valid_entity_types}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate role
        valid_roles = ['user', 'assistant', 'system', 'agent', 'workflow', 'tool', 'function']
        if data['role'] not in valid_roles:
            return Response(
                {'error': f'Invalid role. Must be one of: {valid_roles}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate fields
        if not validator.validate_entity_id(data['entity_id']):
            return Response(
                {'error': 'Invalid entity_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_organization_id(data['organization_id']):
            return Response(
                {'error': 'Invalid organization_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_message_content(data['content']):
            return Response(
                {'error': 'Invalid content'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store interaction using universal service
        context_service = UniversalContextService()
        entry = await context_service.store_interaction(
            entity_id=data['entity_id'],
            entity_type=data['entity_type'],
            organization_id=data['organization_id'],
            role=data['role'],
            content=data['content'],
            content_type=data.get('content_type', 'text'),
            source_entity_id=data.get('source_entity_id'),
            source_entity_type=data.get('source_entity_type'),
            model_used=data.get('model_used'),
            context_strategy=data.get('context_metadata', {}).get('strategy'),
            context_tokens_used=data.get('context_metadata', {}).get('tokens_used'),
            total_cost=data.get('context_metadata', {}).get('total_cost', 0),
            context_preparation_cost=data.get('context_metadata', {}).get('preparation_cost', 0),
            importance_score=data.get('importance_score', 1.0),
            structured_data=data.get('structured_data', {}),
            execution_metadata=data.get('execution_metadata', {})
        )
        
        return Response({
            'entry_id': str(entry.id),
            'importance_score': entry.importance_score,
            'stored_at': entry.created_at.isoformat(),
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Interaction storage failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Interaction storage failed', 'details': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def get_session_analytics(request):
    """
    Get analytics for any session type
    
    GET /api/context/analytics/?entity_id=session_123&entity_type=prompt_session&organization_id=org_456
    """
    try:
        entity_id = request.query_params.get('entity_id')
        entity_type = request.query_params.get('entity_type')
        organization_id = request.query_params.get('organization_id')
        
        if not entity_id or not entity_type or not organization_id:
            return Response(
                {'error': 'Missing entity_id, entity_type, or organization_id parameter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate entity type
        valid_entity_types = ['prompt_session', 'agent_session', 'workflow_execution', 'custom']
        if entity_type not in valid_entity_types:
            return Response(
                {'error': f'Invalid entity_type. Must be one of: {valid_entity_types}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_entity_id(entity_id):
            return Response(
                {'error': 'Invalid entity_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_organization_id(organization_id):
            return Response(
                {'error': 'Invalid organization_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get analytics using universal service
        context_service = UniversalContextService()
        analytics = await context_service.get_session_analytics(entity_id, entity_type, organization_id)
        
        if analytics is None:
            return Response(
                {'error': 'Session not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(analytics)
        
    except Exception as e:
        logger.error(f"Analytics retrieval failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Analytics retrieval failed', 'details': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def get_conversation_history(request):
    """
    Get conversation history for any session type
    
    GET /api/context/history/?entity_id=session_123&entity_type=prompt_session&organization_id=org_456&limit=50
    """
    try:
        entity_id = request.query_params.get('entity_id')
        entity_type = request.query_params.get('entity_type')
        organization_id = request.query_params.get('organization_id')
        limit = request.query_params.get('limit')
        
        if not entity_id or not entity_type or not organization_id:
            return Response(
                {'error': 'Missing entity_id, entity_type, or organization_id parameter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate entity type
        valid_entity_types = ['prompt_session', 'agent_session', 'workflow_execution', 'custom']
        if entity_type not in valid_entity_types:
            return Response(
                {'error': f'Invalid entity_type. Must be one of: {valid_entity_types}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_entity_id(entity_id):
            return Response(
                {'error': 'Invalid entity_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_organization_id(organization_id):
            return Response(
                {'error': 'Invalid organization_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if limit:
            try:
                limit = int(limit)
                if limit < 1 or limit > 1000:
                    return Response(
                        {'error': 'Limit must be between 1 and 1000'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Invalid limit parameter'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get conversation history using universal service
        context_service = UniversalContextService()
        conversation = await context_service.get_conversation_history(
            entity_id=entity_id,
            entity_type=entity_type,
            organization_id=organization_id,
            limit=limit
        )
        
        return Response({
            'conversation': conversation,
            'total_messages': len(conversation),
            'entity_id': entity_id,
            'entity_type': entity_type
        })
        
    except Exception as e:
        logger.error(f"Conversation history retrieval failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Conversation history retrieval failed', 'details': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
async def get_cache_metrics(request):
    """
    Get cache performance metrics across all domains
    
    GET /api/context/cache-metrics/?organization_id=org_456&days=7&session_type=chat
    """
    try:
        organization_id = request.query_params.get('organization_id')
        days = int(request.query_params.get('days', 7))
        session_type = request.query_params.get('session_type')  # Optional filter
        
        if not organization_id:
            return Response(
                {'error': 'Missing organization_id parameter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_organization_id(organization_id):
            return Response(
                {'error': 'Invalid organization_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if days < 1 or days > 90:
            return Response(
                {'error': 'Days parameter must be between 1 and 90'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate session type if provided
        if session_type and session_type not in ['chat', 'agent', 'workflow', 'custom']:
            return Response(
                {'error': 'Invalid session_type. Must be chat, agent, workflow, or custom'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get cache metrics
        cache_service = SummaryCacheService()
        metrics = await cache_service.get_cache_metrics(organization_id, days, session_type)
        
        return Response({
            'hit_rate': metrics.hit_rate,
            'average_access_count': metrics.average_access_count,
            'total_cached_summaries': metrics.total_cached_summaries,
            'cost_savings': str(metrics.cost_savings),
            'period_days': days,
            'session_type_filter': session_type
        })
        
    except Exception as e:
        logger.error(f"Cache metrics retrieval failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Cache metrics retrieval failed', 'details': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def get_performance_metrics(request):
    """
    Get real-time performance metrics across all domains
    
    GET /api/context/performance/?organization_id=org_456&session_type=chat
    """
    try:
        organization_id = request.query_params.get('organization_id')
        session_type = request.query_params.get('session_type')  # Optional filter
        
        if not organization_id:
            return Response(
                {'error': 'Missing required parameter: organization_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not validator.validate_organization_id(organization_id):
            return Response(
                {'error': 'Invalid organization_id format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate session type if provided
        if session_type and session_type not in ['chat', 'agent', 'workflow', 'custom']:
            return Response(
                {'error': 'Invalid session_type. Must be chat, agent, workflow, or custom'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get performance metrics from services
        storage_service = FullContextStorageService()
        cache_service = SummaryCacheService()
        
        # Combine metrics from different services
        storage_metrics = await storage_service.get_storage_metrics(organization_id, session_type)
        cache_metrics = await cache_service.get_cache_metrics(organization_id, days=1, session_type=session_type)
        
        # Compile performance data
        performance_data = {
            "avg_context_preparation_time_ms": cache_metrics.get('avg_preparation_time_ms', 0),
            "avg_context_size_tokens": storage_metrics.get('avg_tokens_per_request', 0),
            "avg_cost_per_request": str(storage_metrics.get('avg_cost_per_request', Decimal('0.0'))),
            "total_requests_today": storage_metrics.get('requests_today', 0),
            "cache_hit_rate": cache_metrics.get('hit_rate', 0.0),
            "system_health": "good" if cache_metrics.get('hit_rate', 0) > 0.5 else "needs_optimization",
            "session_type_filter": session_type
        }
        
        return Response(performance_data)
        
    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Performance metrics retrieval failed', 'details': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def cleanup_session_cache(request):
    """
    Clean up low-importance entries across all domains
    
    POST /api/context/cleanup/
    {
        "entity_id": "session_123",    # Optional
        "entity_type": "prompt_session", # Optional
        "organization_id": "org_456",  # Required
        "threshold": 0.5,              # Optional importance threshold
        "older_than_days": 30,         # Optional age threshold
        "session_type": "chat"         # Optional domain filter
    }
    """
    try:
        data = request.data
        
        # Required fields
        if 'organization_id' not in data or not data['organization_id']:
            return Response(
                {'error': 'Missing required field: organization_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Optional parameters with defaults
        entity_id = data.get('entity_id')
        entity_type = data.get('entity_type')
        threshold = float(data.get('threshold', 0.5))
        older_than_days = int(data.get('older_than_days', 30))
        session_type = data.get('session_type')
        
        # Validate entity type if provided
        if entity_type and entity_type not in ['prompt_session', 'agent_session', 'workflow_execution', 'custom']:
            return Response(
                {'error': 'Invalid entity_type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate session type if provided
        if session_type and session_type not in ['chat', 'agent', 'workflow', 'custom']:
            return Response(
                {'error': 'Invalid session_type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate parameters
        if threshold < 0 or threshold > 1.0:
            return Response(
                {'error': 'Invalid threshold: must be between 0.0 and 1.0'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if older_than_days < 0:
            return Response(
                {'error': 'Invalid older_than_days: must be a positive integer'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform cleanup using universal service
        context_service = UniversalContextService()
        cleanup_results = await context_service.cleanup_low_importance_entries(
            organization_id=data['organization_id'],
            entity_id=entity_id,
            entity_type=entity_type,
            session_type=session_type,
            importance_threshold=threshold,
            older_than_days=older_than_days
        )
        
        return Response({
            'entries_removed': cleanup_results.get('entries_removed', 0),
            'tokens_saved': cleanup_results.get('tokens_saved', 0),
            'storage_saved_bytes': cleanup_results.get('storage_saved_bytes', 0),
            'cost_savings': str(cleanup_results.get('cost_savings', Decimal('0.00')))
        })
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Cache cleanup failed', 'details': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def health_check(request):
    """
    Health check for universal context management system
    
    GET /api/context/health/
    """
    try:
        services_status = {}
        
        # Check universal context service
        try:
            context_service = UniversalContextService()
            if hasattr(context_service, 'prepare_context'):
                services_status['universal_context'] = 'ok'
            else:
                services_status['universal_context'] = 'error'
        except Exception:
            services_status['universal_context'] = 'error'
            
        # Check storage service
        try:
            storage_service = FullContextStorageService()
            if hasattr(storage_service, 'store_message'):
                services_status['storage'] = 'ok'
            else:
                services_status['storage'] = 'error'
        except Exception:
            services_status['storage'] = 'error'
            
        # Check cache service
        try:
            cache_service = SummaryCacheService()
            if hasattr(cache_service, 'get_cache_metrics'):
                services_status['cache'] = 'ok'
            else:
                services_status['cache'] = 'error'
        except Exception:
            services_status['cache'] = 'error'
        
        # Overall status
        overall_status = 'healthy'
        if 'error' in services_status.values():
            overall_status = 'degraded'
            
        return Response({
            'status': overall_status,
            'services': services_status,
            'version': '3.0.0',  # Universal architecture version
            'supported_domains': ['chat', 'agent', 'workflow', 'custom']
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return Response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)