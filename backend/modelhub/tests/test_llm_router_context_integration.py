import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from modelhub.services.llm_router import execute_with_cost_optimization, OptimizationStrategy, RequestContext
from context_manager.services.context_service import ContextService, ContextRequest, ContextResponse


@pytest.mark.asyncio
async def test_llm_router_uses_context_manager():
    """Test that the LLM router uses the context manager when a session ID is provided."""
    # Mock the context service
    mock_context_response = ContextResponse(
        context_content="This is the prepared context",
        strategy_used="full_context",
        tokens_used=100,
        preparation_cost=Decimal('0.00'),
        preparation_time_ms=50,
        cache_hit=True,
        information_preservation_score=1.0
    )
    
    mock_context_service = AsyncMock(spec=ContextService)
    mock_context_service.prepare_context.return_value = mock_context_response
    mock_context_service.store_interaction.return_value = None
    
    # Mock the UnifiedLLMClient
    mock_llm_response = MagicMock()
    mock_llm_response.content = "This is the assistant's response"
    mock_llm_response.cost = Decimal('0.001')
    
    # Create request context with session ID
    request_context = RequestContext(
        session_id="test-session-123",
        user_id="test-user",
        organization_id="test-org",
        preferences={}
    )
    
    # Test data
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    # Patch the necessary components
    with patch('modelhub.services.llm_router.context_service', mock_context_service), \
         patch('modelhub.services.llm_router.UnifiedLLMClient.call_llm', return_value=mock_llm_response), \
         patch('modelhub.services.complexity.analyzer.EnhancedComplexityAnalyzer.analyze_complexity_sync', return_value=(0.5, 'text', 'Simple query')), \
         patch('modelhub.services.llm_router.ModelRouter.route_request'), \
         patch('modelhub.services.llm_router._get_api_key_for_model_protected', return_value="fake-api-key"), \
         patch('modelhub.services.llm_router._update_session_after_execution'), \
         patch('modelhub.services.llm_router._log_routing_metrics_protected'):
        
        # Execute the function
        response, metadata = await execute_with_cost_optimization(
            organization=MagicMock(id="test-org"),
            model_type="TEXT",
            request_context=request_context,
            strategy=OptimizationStrategy.BALANCED,
            messages=messages
        )
        
        # Verify context manager was called
        mock_context_service.prepare_context.assert_called_once()
        mock_context_service.store_interaction.assert_called()
        
        # Verify context information is in metadata
        assert 'context' in metadata
        assert metadata['context']['strategy_used'] == 'full_context'
        assert metadata['context']['tokens_used'] == 100
        
        # Verify the response has context_metadata attached
        assert hasattr(response, 'context_metadata')


@pytest.mark.asyncio
async def test_llm_router_fallback_uses_context_manager():
    """Test that the LLM router fallback uses the context manager when a session ID is provided."""
    # Mock the context service
    mock_context_response = ContextResponse(
        context_content="This is the prepared context for fallback",
        strategy_used="full_context",
        tokens_used=100,
        preparation_cost=Decimal('0.00'),
        preparation_time_ms=50,
        cache_hit=True,
        information_preservation_score=1.0
    )
    
    mock_context_service = AsyncMock(spec=ContextService)
    mock_context_service.prepare_context.return_value = mock_context_response
    mock_context_service.store_interaction.return_value = None
    
    # Mock the UnifiedLLMClient for fallback
    mock_llm_response = MagicMock()
    mock_llm_response.content = "This is the fallback response"
    mock_llm_response.cost = Decimal('0.001')
    
    # Create request context with session ID
    request_context = RequestContext(
        session_id="test-session-123",
        user_id="test-user",
        organization_id="test-org",
        preferences={}
    )
    
    # Test data
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    # Patch the necessary components to force fallback
    with patch('modelhub.services.llm_router.context_service', mock_context_service), \
         patch('modelhub.services.llm_router.UnifiedLLMClient.call_llm', side_effect=[Exception("Forced error"), mock_llm_response]), \
         patch('modelhub.services.complexity.analyzer.EnhancedComplexityAnalyzer.analyze_complexity_sync', return_value=(0.5, 'text', 'Simple query')), \
         patch('modelhub.services.llm_router.ModelRouter.route_request', side_effect=Exception("Forced routing error")), \
         patch('modelhub.services.llm_router._execute_fallback_protected') as mock_fallback, \
         patch('modelhub.services.llm_router._get_api_key_for_model_protected', return_value="fake-api-key"):
        
        # Configure fallback to return a response with context_metadata
        mock_fallback.return_value = mock_llm_response
        mock_llm_response.context_metadata = {
            'strategy_used': 'full_context',
            'tokens_used': 100,
            'preparation_cost': 0.0,
            'preparation_time_ms': 50,
            'cache_hit': True
        }
        
        # Execute the function
        response, metadata = await execute_with_cost_optimization(
            organization=MagicMock(id="test-org"),
            model_type="TEXT",
            request_context=request_context,
            strategy=OptimizationStrategy.BALANCED,
            messages=messages
        )
        
        # Verify fallback was called with request_context
        mock_fallback.assert_called_once()
        assert mock_fallback.call_args[0][3] == request_context
        
        # Verify context information is in metadata
        assert 'context' in metadata
        assert metadata['context']['strategy_used'] == 'full_context'
        assert metadata['context']['tokens_used'] == 100
