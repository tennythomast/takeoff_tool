# backend/modelhub/services/routing/session_manager.py
"""
Enhanced session management with support for multiple entity types.
Handles session stickiness across platform_chat, agent_session, workflow_execution, workspace_chat.
"""
import json
import time
import logging
from typing import Optional, Tuple, Dict
from decimal import Decimal

from django.core.cache import cache
from django.conf import settings

from .types import SessionState, RequestContext, EntityType

logger = logging.getLogger(__name__)


class EnhancedSessionManager:
    """
    Enhanced session management with entity-aware stickiness.
    
    Features:
    - Entity-type specific stickiness rules
    - Performance-based model switching
    - Cost tracking per session
    - Redis-based state persistence
    """
    
    # Entity-specific stickiness configurations
    ENTITY_STICKINESS_CONFIG = {
        EntityType.PLATFORM_CHAT.value: {
            'min_messages_before_switch': 3,
            'complexity_drift_threshold': 0.2,
            'max_session_duration_hours': 24,
            'performance_threshold': 0.7
        },
        EntityType.AGENT_SESSION.value: {
            'min_messages_before_switch': 5,  # Agents benefit from more stickiness
            'complexity_drift_threshold': 0.3,
            'max_session_duration_hours': 72,
            'performance_threshold': 0.8
        },
        EntityType.WORKFLOW_EXECUTION.value: {
            'min_messages_before_switch': 1,  # Workflows can switch more freely
            'complexity_drift_threshold': 0.15,
            'max_session_duration_hours': 168,  # 1 week
            'performance_threshold': 0.9  # High performance required
        },
        EntityType.WORKSPACE_CHAT.value: {
            'min_messages_before_switch': 4,
            'complexity_drift_threshold': 0.25,
            'max_session_duration_hours': 48,
            'performance_threshold': 0.75
        },
        EntityType.RAG_QUERY.value: {
            'min_messages_before_switch': 2,
            'complexity_drift_threshold': 0.2,
            'max_session_duration_hours': 12,
            'performance_threshold': 0.8
        }
    }
    
    def __init__(self):
        self.cache_prefix = "routing_session"
        self.default_ttl = 86400  # 24 hours
    
    def get_session_key(self, session_id: str, entity_type: str) -> str:
        """Generate Redis key for session state"""
        return f"{self.cache_prefix}:{entity_type}:{session_id}"
    
    async def get_session_state(self, session_id: str, entity_type: str) -> Optional[SessionState]:
        """Get current session state from cache"""
        if not session_id:
            return None
        
        try:
            key = self.get_session_key(session_id, entity_type)
            data = cache.get(key)
            
            if data:
                state_dict = json.loads(data)
                return SessionState(
                    current_provider=state_dict.get('current_provider'),
                    current_model=state_dict.get('current_model'),
                    message_count=state_dict.get('message_count', 0),
                    avg_complexity=state_dict.get('avg_complexity', 0.5),
                    last_switch_time=state_dict.get('last_switch_time', 0),
                    entity_type=entity_type,
                    total_cost=Decimal(str(state_dict.get('total_cost', '0'))),
                    performance_score=state_dict.get('performance_score', 1.0)
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get session state: {e}")
            return None
    
    async def update_session_state(
        self, 
        session_id: str, 
        entity_type: str,
        state: SessionState
    ):
        """Update session state in cache"""
        if not session_id:
            return
        
        try:
            key = self.get_session_key(session_id, entity_type)
            
            state_dict = {
                'current_provider': state.current_provider,
                'current_model': state.current_model,
                'message_count': state.message_count,
                'avg_complexity': state.avg_complexity,
                'last_switch_time': state.last_switch_time,
                'entity_type': state.entity_type,
                'total_cost': str(state.total_cost),
                'performance_score': state.performance_score,
                'updated_at': time.time()
            }
            
            # Set TTL based on entity type
            config = self.ENTITY_STICKINESS_CONFIG.get(
                entity_type, 
                self.ENTITY_STICKINESS_CONFIG[EntityType.PLATFORM_CHAT.value]
            )
            ttl = config['max_session_duration_hours'] * 3600
            
            cache.set(key, json.dumps(state_dict), ttl)
            
        except Exception as e:
            logger.warning(f"Failed to update session state: {e}")
    
    async def should_stick_to_model(
        self,
        context: RequestContext,
        current_complexity: float
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Determine if we should stick to current session model.
        
        Entity-aware stickiness logic considers:
        - Entity type specific rules
        - Message count thresholds
        - Complexity drift patterns
        - Performance metrics
        - Session duration
        
        Returns:
            tuple: (should_stick, provider, model)
        """
        
        if not context.session_id:
            return False, None, None
        
        session_state = await self.get_session_state(context.session_id, context.entity_type)
        if not session_state:
            return False, None, None
        
        # Get entity-specific configuration
        config = self.ENTITY_STICKINESS_CONFIG.get(
            context.entity_type,
            self.ENTITY_STICKINESS_CONFIG[EntityType.PLATFORM_CHAT.value]
        )
        
        # Check if we have a current model
        if not session_state.current_provider or not session_state.current_model:
            return False, None, None
        
        # Check session age
        session_age_hours = (time.time() - session_state.last_switch_time) / 3600
        if session_age_hours > config['max_session_duration_hours']:
            logger.info(f"Session too old ({session_age_hours:.1f}h), allowing switch")
            return False, None, None
        
        # Check message count threshold
        if session_state.message_count < config['min_messages_before_switch']:
            complexity_drift = abs(current_complexity - session_state.avg_complexity)
            
            if complexity_drift < config['complexity_drift_threshold']:
                logger.info(
                    f"✅ Sticking to {session_state.current_provider}:{session_state.current_model} "
                    f"({context.entity_type}, msg={session_state.message_count}, drift={complexity_drift:.2f})"
                )
                return True, session_state.current_provider, session_state.current_model
        
        # Check performance score
        if session_state.performance_score < config['performance_threshold']:
            logger.info(
                f"Performance below threshold ({session_state.performance_score:.2f} < {config['performance_threshold']}), "
                f"allowing switch"
            )
            return False, None, None
        
        # Entity-specific stickiness logic
        if context.entity_type == EntityType.WORKFLOW_EXECUTION.value:
            # Workflows are less sticky but need consistency within execution
            if session_state.message_count < 10:  # Within single workflow run
                return True, session_state.current_provider, session_state.current_model
        
        elif context.entity_type == EntityType.AGENT_SESSION.value:
            # Agents benefit from more stickiness for consistency
            if session_state.message_count < 15:
                complexity_drift = abs(current_complexity - session_state.avg_complexity)
                if complexity_drift < config['complexity_drift_threshold']:
                    return True, session_state.current_provider, session_state.current_model
        
        # Check if current model can still handle the request
        if await self._model_can_handle_complexity(
            session_state.current_provider,
            session_state.current_model, 
            current_complexity,
            context
        ):
            logger.info(f"Current model can handle complexity, sticking")
            return True, session_state.current_provider, session_state.current_model
        
        logger.info(f"Not sticking - will re-route")
        return False, None, None
    
    async def record_model_usage(
        self,
        context: RequestContext,
        provider: str,
        model: str,
        complexity: float,
        cost: Decimal,
        performance_score: float = 1.0
    ):
        """
        Record model usage and update session state.
        
        This helps with:
        - Session stickiness decisions
        - Performance tracking
        - Cost monitoring
        - Usage analytics
        """
        
        if not context.session_id:
            return
        
        try:
            session_state = await self.get_session_state(context.session_id, context.entity_type)
            
            if not session_state:
                session_state = SessionState(entity_type=context.entity_type)
            
            # Update session state
            session_state.current_provider = provider
            session_state.current_model = model
            session_state.message_count += 1
            
            # Update rolling average complexity
            alpha = 0.3  # Learning rate for exponential moving average
            session_state.avg_complexity = (
                alpha * complexity + (1 - alpha) * session_state.avg_complexity
            )
            
            # Update cost tracking
            session_state.total_cost += cost
            
            # Update performance score (exponential moving average)
            session_state.performance_score = (
                alpha * performance_score + (1 - alpha) * session_state.performance_score
            )
            
            # Record switch time if model changed
            if (session_state.current_provider != provider or 
                session_state.current_model != model):
                session_state.last_switch_time = time.time()
            
            # Save updated state
            await self.update_session_state(context.session_id, context.entity_type, session_state)
            
            logger.debug(
                f"📊 Session updated: {context.entity_type} | "
                f"model={provider}:{model} | "
                f"msgs={session_state.message_count} | "
                f"avg_complexity={session_state.avg_complexity:.2f} | "
                f"cost=${session_state.total_cost:.4f}"
            )
            
        except Exception as e:
            logger.warning(f"Failed to record model usage: {e}")
    
    async def _model_can_handle_complexity(
        self,
        provider: str,
        model: str,
        complexity: float,
        context: RequestContext
    ) -> bool:
        """Check if current model can handle the request complexity"""
        
        try:
            from ...models import Model
            from channels.db import database_sync_to_async
            
            @database_sync_to_async
            def get_model_capabilities():
                try:
                    model_obj = Model.objects.select_related('provider').get(
                        provider__slug=provider,
                        name=model,
                        status='ACTIVE'
                    )
                    return {
                        'capabilities': model_obj.capabilities,
                        'context_window': model_obj.context_window,
                        'cost_input': float(model_obj.cost_input),
                        'cost_output': float(model_obj.cost_output),
                        'config': model_obj.config
                    }
                except Model.DoesNotExist:
                    return None
            
            model_capabilities = await get_model_capabilities()
            if not model_capabilities:
                return False
            
            # Basic capability checking
            if complexity > 0.8 and 'advanced_reasoning' not in model_capabilities.get('capabilities', []):
                return False
            
            if context.max_tokens > model_capabilities.get('context_window', 4000):
                return False
            
            # Entity-specific capability checks
            if context.entity_type == EntityType.WORKFLOW_EXECUTION.value:
                if 'function_calling' not in model_capabilities.get('capabilities', []):
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to check model capabilities: {e}")
            return False
    
    async def get_session_analytics(self, session_id: str, entity_type: str) -> Dict:
        """Get analytics for a specific session"""
        
        session_state = await self.get_session_state(session_id, entity_type)
        if not session_state:
            return {}
        
        return {
            'session_id': session_id,
            'entity_type': entity_type,
            'current_model': f"{session_state.current_provider}:{session_state.current_model}",
            'message_count': session_state.message_count,
            'avg_complexity': round(session_state.avg_complexity, 3),
            'total_cost': float(session_state.total_cost),
            'performance_score': round(session_state.performance_score, 3),
            'session_age_hours': round((time.time() - session_state.last_switch_time) / 3600, 2),
            'stickiness_config': self.ENTITY_STICKINESS_CONFIG.get(entity_type, {})
        }
    
    async def clear_session(self, session_id: str, entity_type: str) -> bool:
        """Clear session state"""
        if not session_id:
            return False
        
        try:
            key = self.get_session_key(session_id, entity_type)
            cache.delete(key)
            logger.info(f"Cleared session: {entity_type}:{session_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear session: {e}")
            return False
    
    def get_stickiness_stats(self) -> Dict:
        """Get stickiness statistics across entity types"""
        
        stats = {
            'entity_configs': self.ENTITY_STICKINESS_CONFIG,
            'cache_prefix': self.cache_prefix,
            'default_ttl_hours': self.default_ttl / 3600
        }
        
        return stats