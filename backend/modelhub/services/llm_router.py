# backend/modelhub/services/llm_router.py
"""
Enhanced LLM Router - Main entry point for intelligent model routing.

This is the main interface that orchestrates:
- Enhanced complexity analysis
- Intelligent model routing  
- Session management
- Entity-aware decisions
- Cost optimization

Supports multiple entity types:
- platform_chat: General platform conversations
- agent_session: Agent-based interactions
- workflow_execution: Agentic workflow processing
- workspace_chat: Workspace-specific conversations
"""
import time
import logging
from typing import List, Dict, Optional, Callable, Tuple, Union
from decimal import Decimal

from .complexity import RequestContext as ComplexityContext
from .complexity import get_complexity_analyzer
from .routing import EnhancedModelRouter, EnhancedSessionManager
from .routing.types import (
    RequestContext, RoutingDecision, OptimizationStrategy, EntityType
)
from .unified_llm_client import UnifiedLLMClient
from ..adapters.base import LLMResponse

logger = logging.getLogger(__name__)


class EnhancedLLMRouter:
    """
    Enhanced LLM Router with full entity support and intelligent routing.
    
    This replaces the old LLM router with:
    - Sophisticated complexity analysis (85% rule-based, 15% LLM escalation)
    - Entity-aware routing decisions
    - Enhanced session management
    - Performance optimization
    - Cost protection
    """
    
    def __init__(self):
        self.complexity_analyzer = get_complexity_analyzer()
        self.model_router = EnhancedModelRouter()
        self.session_manager = EnhancedSessionManager()
        
        # Performance tracking
        self.total_requests = 0
        self.total_time_ms = 0.0
    
    async def execute_with_cost_optimization(
        self,
        organization,
        model_type: str,
        request_context: RequestContext,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        prompt: str = "",
        messages: Optional[List[Dict]] = None,
        stream: bool = False,
        stream_callback: Optional[Callable] = None,
        **llm_kwargs
    ) -> Tuple[LLMResponse, Dict]:
        """
        Main entry point for cost-optimized LLM execution with entity awareness.
        
        Args:
            organization: Organization instance
            model_type: Type of model (TEXT, CODE, etc.)
            request_context: Enhanced request context with entity information
            strategy: Optimization strategy
            prompt: Direct prompt text (alternative to messages)
            messages: Message format for chat
            stream: Whether to stream response
            stream_callback: Callback for streaming
            **llm_kwargs: Additional LLM parameters
            
        Returns:
            Tuple of (LLMResponse, metadata_dict)
        """
        total_start_time = time.time()
        self.total_requests += 1
        
        try:
            # Check for organization's default strategy
            if organization and hasattr(organization, 'default_optimization_strategy') and organization.default_optimization_strategy:
                org_strategy = organization.default_optimization_strategy
                if org_strategy != strategy.value:
                    logger.info(f"Using organization default strategy: {org_strategy} (overriding {strategy.value})")
                    strategy = OptimizationStrategy(org_strategy)
                    # Update request_context with organization strategy
                    if hasattr(request_context, 'metadata') and request_context.metadata is not None:
                        request_context.metadata['organization_strategy'] = org_strategy
                    else:
                        request_context.metadata = {'organization_strategy': org_strategy}
            
            logger.info(
                f"🎯 Enhanced LLM routing started: "
                f"entity={request_context.entity_type}, "
                f"strategy={strategy.value}, "
                f"org={organization.id if organization else 'none'}"
            )
            
            # Phase 1: Prepare request text for analysis
            request_text = self._prepare_request_text(prompt, messages)
            
            # Phase 2: Enhanced complexity analysis (5-15ms rule-based, 150-300ms if escalated)
            complexity_context = self._create_complexity_context(request_context)
            complexity_result = await self.complexity_analyzer.analyze_complexity(
                request_text, complexity_context
            )
            
            logger.info(
                f"📊 Complexity analysis: "
                f"score={complexity_result.score:.2f}, "
                f"level={complexity_result.level.value}, "
                f"confidence={complexity_result.confidence:.2f}, "
                f"path={complexity_result.analysis_path.value}, "
                f"time={complexity_result.analysis_time_ms}ms"
            )
            
            # Phase 3: Check session stickiness (2-5ms)
            should_stick, sticky_provider, sticky_model = await self.session_manager.should_stick_to_model(
                request_context, complexity_result.score
            )
            
            routing_decision = None
            
            if should_stick and sticky_provider and sticky_model:
                # Use sticky session model
                decision_time = int((time.time() - total_start_time) * 1000)
                routing_decision = RoutingDecision(
                    selected_model=sticky_model,
                    selected_provider=sticky_provider,
                    api_type="CHAT",
                    confidence_score=0.95,
                    reasoning=f"session_sticky,entity={request_context.entity_type}",
                    estimated_cost=Decimal('0.01'),  # Rough estimate
                    estimated_tokens=request_context.max_tokens,
                    complexity_score=complexity_result.score,
                    content_type=complexity_result.content_type.value,
                    fallback_chain=[],
                    decision_time_ms=decision_time,
                    session_sticky=True,
                    entity_type=request_context.entity_type
                )
                
                logger.info(f"✅ Using session sticky model: {sticky_provider}:{sticky_model}")
            else:
                # Phase 4: Intelligent model routing (20-40ms)
                routing_decision = await self.model_router.route_request(
                    organization=organization,
                    complexity_score=complexity_result.score,
                    content_type=complexity_result.content_type.value,
                    context=request_context,
                    strategy=strategy
                )
            
            # Phase 5: Get API key for selected model
            api_key = await self._get_api_key_for_model(
                organization, routing_decision.selected_provider
            )
            if not api_key:
                raise Exception(f"No API key found for provider {routing_decision.selected_provider}")
            
            # Phase 6: Prepare context using context manager (if session_id provided)
            context_metadata = None
            if request_context.session_id and (messages or prompt):
                try:
                    context_metadata = await self._prepare_context_integration(
                        request_context, routing_decision, messages, prompt
                    )
                    logger.info(f"✅ Context prepared: {context_metadata.get('strategy_used', 'none')}")
                except Exception as e:
                    logger.error(f"❌ Context preparation failed: {e}")
                    # Continue without context if preparation fails
            
            # Phase 7: Execute LLM call
            execution_start = time.time()
            response = await self._execute_llm_call(
                routing_decision=routing_decision,
                api_key=api_key,
                messages=messages,
                prompt=prompt,
                stream=stream,
                stream_callback=stream_callback,
                context_metadata=context_metadata,
                **llm_kwargs
            )
            
            execution_time = int((time.time() - execution_start) * 1000)
            
            # Phase 8: Record session usage and performance
            performance_score = self._calculate_performance_score(response, execution_time)
            
            await self.session_manager.record_model_usage(
                context=request_context,
                provider=routing_decision.selected_provider,
                model=routing_decision.selected_model,
                complexity=complexity_result.score,
                cost=response.cost if hasattr(response, 'cost') else Decimal('0'),
                performance_score=performance_score
            )
            
            # Phase 9: Prepare response metadata
            total_time = int((time.time() - total_start_time) * 1000)
            self._update_performance_metrics(total_time)
            
            metadata = self._create_response_metadata(
                response=response,
                complexity_result=complexity_result,
                routing_decision=routing_decision,
                context_metadata=context_metadata,
                execution_time=execution_time,
                total_time=total_time,
                performance_score=performance_score
            )
            
            logger.info(
                f"✅ Enhanced routing complete: "
                f"model={routing_decision.selected_provider}:{routing_decision.selected_model}, "
                f"cost=${response.cost if hasattr(response, 'cost') else 0:.6f}, "
                f"total_time={total_time}ms, "
                f"entity={request_context.entity_type}"
            )
            
            return response, metadata
            
        except Exception as e:
            logger.error(f"❌ Enhanced LLM routing failed: {str(e)}", exc_info=True)
            
            # Execute fallback
            fallback_response, fallback_metadata = await self._execute_fallback(
                organization, request_context, prompt, messages, **llm_kwargs
            )
            
            total_time = int((time.time() - total_start_time) * 1000)
            fallback_metadata['total_time_ms'] = total_time
            fallback_metadata['fallback_reason'] = str(e)
            
            return fallback_response, fallback_metadata
    
    def _prepare_request_text(self, prompt: str, messages: Optional[List[Dict]]) -> str:
        """Prepare request text for complexity analysis"""
        if prompt:
            return prompt
        elif messages:
            # Extract user messages for analysis
            user_texts = []
            for msg in messages:
                if msg.get('role') == 'user':
                    user_texts.append(msg.get('content', ''))
            return ' '.join(user_texts)
        else:
            return ""
    
    def _create_complexity_context(self, request_context: RequestContext) -> ComplexityContext:
        """Convert routing context to complexity analysis context"""
        return ComplexityContext(
            session_id=request_context.session_id,
            user_id=request_context.user_id,
            organization_id=request_context.organization_id,
            max_tokens=request_context.max_tokens,
            entity_type=request_context.entity_type,
            conversation_history=request_context.conversation_history,
            rag_documents=request_context.rag_documents,
            user_preferences=request_context.user_preferences,
            require_fast_response=request_context.require_fast_response,
            cost_sensitive=request_context.cost_sensitive,
            quality_critical=request_context.quality_critical
        )
    
    async def _prepare_context_integration(
        self, 
        request_context: RequestContext,
        routing_decision: RoutingDecision,
        messages: Optional[List[Dict]],
        prompt: Optional[str]
    ) -> Dict:
        """Prepare context using context manager"""
        try:
            from context_manager.services.universal_context_service import (
                UniversalContextService, ContextRequest
            )
            
            context_service = UniversalContextService()
            
            # Prepare context request
            user_message = self._prepare_request_text(prompt, messages)
            target_model = f"{routing_decision.selected_provider}:{routing_decision.selected_model}"
            
            context_request = ContextRequest(
                entity_id=request_context.session_id,
                entity_type=request_context.entity_type,
                organization_id=request_context.organization_id or "",
                target_model=target_model,
                user_message=user_message,
                preserve_quality=request_context.quality_critical,
                cost_limit=None
            )
            
            # Get context response
            context_response = await context_service.prepare_context(context_request)
            
            return {
                'strategy_used': context_response.strategy_used,
                'tokens_used': context_response.tokens_used,
                'preparation_cost': float(context_response.preparation_cost),
                'preparation_time_ms': context_response.preparation_time_ms,
                'cache_hit': context_response.cache_hit,
                'information_preservation_score': context_response.information_preservation_score,
                'context_content': context_response.context_content
            }
            
        except Exception as e:
            logger.debug(f"Context integration failed: {e}")
            return {}
    
    async def _execute_llm_call(
        self,
        routing_decision: RoutingDecision,
        api_key: str,
        messages: Optional[List[Dict]],
        prompt: Optional[str],
        stream: bool,
        stream_callback: Optional[Callable],
        context_metadata: Optional[Dict],
        **llm_kwargs
    ) -> LLMResponse:
        """Execute the actual LLM call"""
        
        # Integrate context if available
        if context_metadata and context_metadata.get('context_content'):
            if messages:
                # Remove existing system messages to avoid conflicts
                messages = [msg for msg in messages if msg['role'] != 'system']
                
                # Create context-integrated system message
                system_message = self._create_context_integrated_system_message(
                    context_metadata['context_content'],
                    routing_decision.selected_model
                )
                
                messages.insert(0, {'role': 'system', 'content': system_message})
                
            elif prompt:
                prompt = self._integrate_context_with_prompt(
                    context_metadata['context_content'], prompt
                )
        
        # Execute LLM call
        if stream and stream_callback:
            # Handle streaming
            stream_generator = UnifiedLLMClient.call_llm(
                provider_slug=routing_decision.selected_provider,
                model_name=routing_decision.selected_model,
                api_key=api_key,
                messages=messages,
                prompt=prompt,
                stream=True,
                **llm_kwargs
            )
            
            final_response = None
            # Fix: await the coroutine to get the actual async iterator
            async_iterator = await stream_generator
            async for chunk in async_iterator:
                await stream_callback(chunk)
                final_response = chunk
            
            response = final_response
        else:
            # Non-streaming call
            response = await UnifiedLLMClient.call_llm(
                provider_slug=routing_decision.selected_provider,
                model_name=routing_decision.selected_model,
                api_key=api_key,
                messages=messages,
                prompt=prompt,
                stream=False,
                **llm_kwargs
            )
        
        # Attach context metadata to response
        if context_metadata:
            response.context_metadata = context_metadata
        
        return response
    
    def _create_context_integrated_system_message(
        self, 
        context_content: str, 
        model_name: str
    ) -> str:
        """Create system message that properly integrates context"""
        
        base_instructions = f"""You are an AI assistant powered by {model_name}. You have access to conversation context to provide more helpful and relevant responses.

When provided with conversation history, use it as context to inform your responses, but only respond to the CURRENT USER QUESTION.

IMPORTANT INSTRUCTIONS:
- The conversation history is provided for context only
- Do NOT respond to old messages from the history  
- Focus on answering the current user's question
- Reference previous conversation naturally when relevant
- If asked about "what we discussed" or similar, refer to the conversation history
- Maintain a helpful, professional tone"""
        
        if context_content and context_content.strip():
            if "## CONVERSATION HISTORY" in context_content:
                return f"{base_instructions}\n\n{context_content}"
            else:
                return f"{base_instructions}\n\n## CONVERSATION CONTEXT\n{context_content}"
        else:
            return base_instructions
    
    def _integrate_context_with_prompt(self, context_content: str, user_prompt: str) -> str:
        """Integrate context content with user prompt for non-message format"""
        
        if context_content and context_content.strip():
            return f"""## CONVERSATION CONTEXT
{context_content}

## CURRENT USER QUESTION
Please respond to this current question, using the conversation context above for reference:

{user_prompt}"""
        else:
            return user_prompt
    
    def _calculate_performance_score(self, response: LLMResponse, execution_time: int) -> float:
        """Calculate performance score for session tracking"""
        
        # Base score
        score = 1.0
        
        # Penalize slow responses
        if execution_time > 5000:  # 5 seconds
            score -= 0.3
        elif execution_time > 2000:  # 2 seconds
            score -= 0.1
        
        # Penalize errors
        if hasattr(response, 'error') and response.error:
            score -= 0.5
        
        # Reward successful responses
        if hasattr(response, 'content') and response.content:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _create_response_metadata(
        self,
        response,
        complexity_result,
        routing_decision: RoutingDecision,
        context_metadata: Optional[Dict],
        execution_time: int,
        total_time: int,
        performance_score: float
    ) -> Dict:
        """Create comprehensive response metadata"""
        
        metadata = {
            # Top-level model and provider info for easy access
            'selected_model': routing_decision.selected_model,
            'provider': routing_decision.selected_provider,
            'total_cost': float(response.cost) if hasattr(response, 'cost') else 0.0,
            
            # Complexity analysis
            'complexity': {
                'score': complexity_result.score,
                'level': complexity_result.level.value,
                'confidence': complexity_result.confidence,
                'reasoning': complexity_result.reasoning,
                'analysis_path': complexity_result.analysis_path.value,
                'analysis_time_ms': complexity_result.analysis_time_ms,
                'content_type': complexity_result.content_type.value,
                'cache_hit': complexity_result.cache_hit
            },
            
            # Routing decision
            'routing': {
                'selected_model': routing_decision.selected_model,
                'selected_provider': routing_decision.selected_provider,
                'confidence_score': routing_decision.confidence_score,
                'reasoning': routing_decision.reasoning,
                'estimated_cost': float(routing_decision.estimated_cost),
                'session_sticky': routing_decision.session_sticky,
                'decision_time_ms': routing_decision.decision_time_ms,
                'entity_type': routing_decision.entity_type,
                'api_key_source': routing_decision.api_key_source,
                'organization_strategy': routing_decision.organization_strategy if hasattr(routing_decision, 'organization_strategy') else None
            },
            
            # Performance metrics
            'performance': {
                'execution_time_ms': execution_time,
                'total_time_ms': total_time,
                'performance_score': performance_score
            },
            
            # Cost information
            'cost': {
                'total_cost': float(response.cost) if hasattr(response, 'cost') else 0.0,
                'tokens_input': response.tokens_input if hasattr(response, 'tokens_input') else 0,
                'tokens_output': response.tokens_output if hasattr(response, 'tokens_output') else 0,
                'model_used': routing_decision.selected_model,
                'provider': routing_decision.selected_provider
            },
            
            # Entity information
            'entity': {
                'type': routing_decision.entity_type,
                'session_sticky': routing_decision.session_sticky
            }
        }
        
        # Add context metadata if available
        if context_metadata:
            metadata['context'] = context_metadata
        
        # Add escalation information if applicable
        if complexity_result.escalation_reason:
            metadata['complexity']['escalation_reason'] = complexity_result.escalation_reason.value
        
        return metadata
    
    async def _execute_fallback(
        self,
        organization,
        request_context: RequestContext,
        prompt: str,
        messages: Optional[List[Dict]],
        **llm_kwargs
    ) -> Tuple[LLMResponse, Dict]:
        """Execute fallback routing when main routing fails"""
        
        # Check for organization's default strategy
        strategy = OptimizationStrategy.BALANCED
        if organization and hasattr(organization, 'default_optimization_strategy') and organization.default_optimization_strategy:
            org_strategy = organization.default_optimization_strategy
            strategy = OptimizationStrategy(org_strategy)
            logger.info(f"Using organization default strategy for fallback: {org_strategy}")
        
        logger.info(f"🔄 Executing fallback routing for entity: {request_context.entity_type}, strategy: {strategy.value}")
        
        try:
            # Simple fallback: use GPT-3.5-turbo
            fallback_provider = "openai"
            fallback_model = "gpt-3.5-turbo"
            
            api_key = await self._get_api_key_for_model(organization, fallback_provider)
            if not api_key:
                raise Exception("No fallback API key available")
            
            response = await UnifiedLLMClient.call_llm(
                provider_slug=fallback_provider,
                model_name=fallback_model,
                api_key=api_key,
                messages=messages,
                prompt=prompt,
                stream=False,
                **llm_kwargs
            )
            
            metadata = {
                'routing': {
                    'selected_model': fallback_model,
                    'selected_provider': fallback_provider,
                    'reasoning': f'fallback,entity={request_context.entity_type}',
                    'is_fallback': True,
                    'organization_strategy': strategy.value
                },
                'entity': {
                    'type': request_context.entity_type
                }
            }
            
            return response, metadata
            
        except Exception as e:
            logger.error(f"❌ Fallback routing also failed: {e}")
            raise
    
    async def _get_api_key_for_model(self, organization, provider_slug: str) -> Optional[str]:
        """Get API key for the selected provider"""
        from channels.db import database_sync_to_async
        from ..models import APIKey
        
        @database_sync_to_async
        def get_key():
            # Try organization key first
            if organization:
                api_key = APIKey.objects.filter(
                    organization=organization,
                    provider__slug=provider_slug,
                    is_active=True
                ).first()
                if api_key and api_key.quota_status.get('status') != 'exceeded':
                    return api_key.key
            
            # Try Dataelan fallback key
            dataelan_key = APIKey.objects.filter(
                organization__isnull=True,
                provider__slug=provider_slug,
                is_active=True
            ).first()
            
            if dataelan_key and dataelan_key.quota_status.get('status') != 'exceeded':
                return dataelan_key.key
            
            return None
        
        return await get_key()
    
    def _update_performance_metrics(self, total_time: int):
        """Update router performance metrics"""
        if self.total_requests > 0:
            self.total_time_ms = (
                (self.total_time_ms * (self.total_requests - 1) + total_time) / self.total_requests
            )
    
    # Backward compatibility methods
    
    def analyze_complexity_sync(
        self, 
        text: str, 
        context: RequestContext
    ) -> Tuple[float, str, str]:
        """
        Synchronous complexity analysis for backward compatibility.
        
        Note: This only uses rule-based analysis to maintain sync behavior.
        """
        complexity_context = self._create_complexity_context(context)
        return self.complexity_analyzer.analyze_complexity_sync(text, complexity_context)
    
    async def route_request(
        self,
        organization,
        model_type: str,
        complexity_score: float,
        content_type: str,
        context: RequestContext,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> RoutingDecision:
        """Route request using enhanced router"""
        return await self.model_router.route_request(
            organization, complexity_score, content_type, context, strategy
        )
    
    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics"""
        
        complexity_metrics = self.complexity_analyzer.get_performance_metrics()
        routing_metrics = self.model_router.get_routing_metrics()
        session_metrics = self.session_manager.get_stickiness_stats()
        
        return {
            'router_performance': {
                'total_requests': self.total_requests,
                'avg_total_time_ms': round(self.total_time_ms, 2)
            },
            'complexity_analysis': complexity_metrics,
            'routing_decisions': routing_metrics,
            'session_management': session_metrics
        }


# Main entry point functions for backward compatibility

# Global router instance
_enhanced_router = None

def get_enhanced_router() -> EnhancedLLMRouter:
    """Get global enhanced router instance"""
    global _enhanced_router
    if _enhanced_router is None:
        _enhanced_router = EnhancedLLMRouter()
    return _enhanced_router


async def execute_with_cost_optimization(
    organization,
    model_type: str,
    request_context: RequestContext,
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
    prompt: str = "",
    messages: Optional[List[Dict]] = None,
    stream: bool = False,
    stream_callback: Optional[Callable] = None,
    **llm_kwargs
) -> Tuple[LLMResponse, Dict]:
    """
    Main entry point for enhanced cost-optimized LLM execution.
    
    This is the primary interface that replaces the old execute_with_cost_optimization.
    """
    router = get_enhanced_router()
    return await router.execute_with_cost_optimization(
        organization=organization,
        model_type=model_type,
        request_context=request_context,
        strategy=strategy,
        prompt=prompt,
        messages=messages,
        stream=stream,
        stream_callback=stream_callback,
        **llm_kwargs
    )


# Legacy compatibility classes removed - using EnhancedComplexityAnalyzer directly


class ModelRouter:
    """Legacy compatibility class"""
    
    @staticmethod
    async def route_request(
        organization,
        model_type: str,
        complexity_score: float,
        content_type: str,
        context: RequestContext,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> RoutingDecision:
        router = get_enhanced_router()
        return await router.route_request(
            organization, model_type, complexity_score, content_type, context, strategy
        )


# Export main interfaces
__all__ = [
    'EnhancedLLMRouter',
    'execute_with_cost_optimization',
    'get_enhanced_router',
    'ModelRouter',  
    'RequestContext',
    'OptimizationStrategy',
    'RoutingDecision',
    'EntityType'
]