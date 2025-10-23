# context_manager/services/universal_context_service.py

import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass

from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async

from ..models import ContextSession, ContextEntry, ContextTransition
from .decision_service import ContextDecisionService, ContextDecision
from .cache_service import SummaryCacheService, CacheResult
from .storage_service import FullContextStorageService
from .summary_service import SummaryGenerationService, SummaryResult
from .entity_registry import EntityContextRegistry

logger = logging.getLogger(__name__)


@dataclass
class ContextRequest:
    """Universal context request for any domain"""
    entity_id: str
    entity_type: str  # 'prompt_session', 'agent_session', 'workflow_execution'
    organization_id: str
    target_model: str
    user_message: str
    preserve_quality: bool = True
    cost_limit: Optional[Decimal] = None


@dataclass
class ContextResponse:
    """Response with prepared context"""
    context_content: str
    strategy_used: str
    tokens_used: int
    preparation_cost: Decimal
    preparation_time_ms: int
    cache_hit: bool
    information_preservation_score: float


class UniversalContextService:
    """
    Universal Context Management Service for All Domains
    
    This service provides consistent context management across Chat, Agents,
    and Workflows while optimizing for each domain's specific needs.
    
    Key Features:
    - Domain-agnostic context preparation
    - Intelligent routing based on entity type
    - Unified caching and optimization
    - Cross-domain analytics and insights
    """
    
    def __init__(self):
        self.decision_service = ContextDecisionService()
        self.cache_service = SummaryCacheService()
        self.storage_service = FullContextStorageService()
        self.summary_service = SummaryGenerationService()
        self.entity_registry = EntityContextRegistry()
    
    async def prepare_context(self, request: ContextRequest) -> ContextResponse:
        """
        Universal context preparation for any domain
        
        Adapts strategy based on entity type while maintaining consistent optimization
        """
        start_time = time.time()
        preparation_cost = Decimal('0.00')
        
        try:
            # Get or create context session
            context_session = await self._get_or_create_context_session(
                request.entity_id, request.entity_type, request.organization_id
            )
            
            # Get conversation history
            conversation = await self._get_conversation_history(context_session)
            
            # Domain-specific context preparation
            if request.entity_type == 'prompt_session':
                context_result = await self._prepare_chat_context(
                    conversation, request, context_session
                )
            elif request.entity_type == 'agent_session':
                context_result = await self._prepare_agent_context(
                    conversation, request, context_session
                )
            else:
                # Generic preparation for custom types
                context_result = await self._prepare_generic_context(
                    conversation, request, context_session
                )
            
            preparation_cost = context_result.get('cost', Decimal('0.00'))
            
            # Update session metrics
            await self._update_session_metrics(
                context_session, context_result, preparation_cost
            )
            
            # Record transition
            await self._record_context_transition(
                request, context_result, preparation_cost, context_session
            )
            
            preparation_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"Context prepared for {request.entity_type} {request.entity_id}: "
                       f"{context_result['strategy']}, "
                       f"{context_result['tokens_used']} tokens, "
                       f"${preparation_cost}, "
                       f"{preparation_time_ms}ms")
            
            return ContextResponse(
                context_content=context_result['content'],
                strategy_used=context_result['strategy'],
                tokens_used=context_result['tokens_used'],
                preparation_cost=preparation_cost,
                preparation_time_ms=preparation_time_ms,
                cache_hit=context_result.get('cache_hit', False),
                information_preservation_score=context_result.get('quality_score', 1.0)
            )
            
        except Exception as e:
            logger.error(f"Context preparation failed: {str(e)}", exc_info=True)
            return await self._emergency_fallback(request, start_time)
    
    async def store_interaction(self,
                              entity_id: str,
                              entity_type: str,
                              organization_id: str,
                              role: str,
                              content: str,
                              content_type: str = 'text',
                              source_entity_id: Optional[str] = None,
                              source_entity_type: Optional[str] = None,
                              model_used: Optional[str] = None,
                              context_strategy: Optional[str] = None,
                              context_tokens_used: Optional[int] = None,
                              total_cost: Decimal = Decimal('0.00'),
                              context_preparation_cost: Decimal = Decimal('0.00'),
                              importance_score: float = 1.0,
                              structured_data: Optional[Dict] = None,
                              execution_metadata: Optional[Dict] = None,
                              parent_entry_id: Optional[str] = None) -> ContextEntry:
        """
        Store interaction in universal context system
        
        Args:
            entity_id: Domain entity ID (PromptSession, AgentSession, etc.)
            entity_type: Type of entity ('prompt_session', 'agent_session', etc.)
            organization_id: Tenant identifier
            role: Message role (user, assistant, agent, workflow, etc.)
            content: Message content
            content_type: Content type (text, json, code, etc.)
            source_entity_id: Source entity that created this (Prompt, AgentAction, etc.)
            source_entity_type: Type of source entity
            model_used: Model that generated the content
            context_strategy: Context strategy used
            context_tokens_used: Tokens used for context
            total_cost: Total cost including model execution
            context_preparation_cost: Cost specific to context preparation
            importance_score: Importance score for cleanup
            structured_data: Rich data for agents/workflows
            execution_metadata: Execution details
            parent_entry_id: For threaded conversations
            
        Returns:
            Created ContextEntry
        """
        try:
            # Get or create context session
            context_session = await self._get_or_create_context_session(
                entity_id, entity_type, organization_id
            )
            
            # Store interaction
            entry = await ContextEntry.objects.acreate(
                organization_id=organization_id,
                session=context_session,
                role=role,
                content=content,
                content_type=content_type,
                source_entity_id=source_entity_id,
                source_entity_type=source_entity_type,
                model_used=model_used,
                context_strategy=context_strategy,
                context_tokens_used=context_tokens_used,
                total_cost=total_cost,
                context_preparation_cost=context_preparation_cost,
                importance_score=importance_score,
                structured_data=structured_data or {},
                execution_metadata=execution_metadata or {},
                parent_entry_id=parent_entry_id
            )
            
            # Update session costs
            await context_session.update_cost_metrics(
                context_cost=context_preparation_cost
            )
            
            # Invalidate caches since conversation changed
            await self.cache_service.invalidate_session_cache(str(context_session.id))
            
            logger.debug(f"Stored interaction {entry.id} for {entity_type} {entity_id}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to store interaction: {str(e)}", exc_info=True)
            raise
    
    async def get_conversation_history(self,
                                     entity_id: str,
                                     entity_type: str,
                                     organization_id: str,
                                     limit: Optional[int] = None,
                                     role_filter: Optional[str] = None) -> List[Dict]:
        """
        Get conversation history for any entity type
        
        Args:
            entity_id: Domain entity ID
            entity_type: Type of entity
            organization_id: Tenant identifier
            limit: Maximum messages to return
            role_filter: Filter by specific role
            
        Returns:
            List of conversation messages
        """
        try:
            context_session = await self._get_context_session(
                entity_id, entity_type, organization_id
            )
            
            if not context_session:
                return []
            
            query = ContextEntry.objects.filter(
                session=context_session,
                organization_id=organization_id
            ).order_by('created_at')
            
            if role_filter:
                query = query.filter(role=role_filter)
            
            if limit:
                query = query[:limit]
            
            conversation = []
            async for entry in query:
                conversation.append({
                    'role': entry.role,
                    'content': entry.content,
                    'content_type': entry.content_type,
                    'timestamp': entry.created_at.isoformat(),
                    'model_used': entry.model_used,
                    'entry_id': str(entry.id),
                    'importance_score': entry.importance_score,
                    'context_strategy': entry.context_strategy,
                    'tokens_used': entry.context_tokens_used,
                    'source_entity_id': entry.source_entity_id,
                    'source_entity_type': entry.source_entity_type,
                    'structured_data': entry.structured_data,
                    'execution_metadata': entry.execution_metadata,
                    'parent_entry_id': entry.parent_entry_id
                })
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            return []
    
    async def get_session_analytics(self,
                                  entity_id: str,
                                  entity_type: str,
                                  organization_id: str) -> Optional[Dict]:
        """
        Get analytics for any session type
        """
        try:
            context_session = await self._get_context_session(
                entity_id, entity_type, organization_id
            )
            
            if not context_session:
                return None
            
            # Get domain entity
            domain_entity = context_session.get_entity()
            
            # Get basic session metrics
            total_entries = await context_session.entries.acount()
            
            # Get cost breakdown
            total_context_cost = (
                context_session.total_context_preparation_cost +
                context_session.total_summarization_cost +
                context_session.total_embedding_cost
            )
            
            # Get recent activity
            recent_entries = []
            async for entry in context_session.entries.order_by('-created_at')[:5]:
                recent_entries.append({
                    'role': entry.role,
                    'content_preview': entry.content[:100] + '...' if len(entry.content) > 100 else entry.content,
                    'timestamp': entry.created_at.isoformat(),
                    'model_used': entry.model_used,
                    'cost': float(entry.total_cost)
                })
            
            # Get performance metrics
            performance_metrics = {
                'cache_hit_rate': context_session.cache_hit_rate,
                'avg_preparation_time_ms': context_session.avg_preparation_time_ms,
                'total_context_requests': context_session.total_context_requests
            }
            
            return {
                'session_info': {
                    'id': str(context_session.id),
                    'entity_id': entity_id,
                    'entity_type': entity_type,
                    'session_type': context_session.session_type,
                    'tier': context_session.tier,
                    'created_at': context_session.created_at.isoformat(),
                    'last_activity': context_session.last_activity_at.isoformat(),
                    'total_entries': total_entries
                },
                'cost_breakdown': {
                    'context_preparation': float(context_session.total_context_preparation_cost),
                    'summarization': float(context_session.total_summarization_cost),
                    'embedding': float(context_session.total_embedding_cost),
                    'total': float(total_context_cost)
                },
                'performance_metrics': performance_metrics,
                'recent_activity': recent_entries,
                'domain_entity': {
                    'type': entity_type,
                    'exists': domain_entity is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get session analytics: {str(e)}")
            return None
    
    async def cleanup_low_importance_entries(self,
                                           organization_id: str,
                                           entity_id: Optional[str] = None,
                                           entity_type: Optional[str] = None,
                                           session_type: Optional[str] = None,
                                           importance_threshold: float = 0.5,
                                           older_than_days: int = 30) -> Dict:
        """
        Clean up low-importance entries across domains
        """
        try:
            cutoff_date = timezone.now() - timezone.timedelta(days=older_than_days)
            
            query = ContextEntry.objects.filter(
                organization_id=organization_id,
                importance_score__lt=importance_threshold,
                created_at__lt=cutoff_date,
                is_starred=False
            )
            
            # Apply filters
            if entity_id and entity_type:
                context_session = await self._get_context_session(
                    entity_id, entity_type, organization_id
                )
                if context_session:
                    query = query.filter(session=context_session)
            elif session_type:
                query = query.filter(session__session_type=session_type)
            
            # Calculate metrics before deletion
            entries_to_delete = []
            total_tokens = 0
            total_cost_savings = Decimal('0.00')
            
            async for entry in query:
                entries_to_delete.append(entry)
                if entry.context_tokens_used:
                    total_tokens += entry.context_tokens_used
                total_cost_savings += entry.context_preparation_cost
            
            # Delete entries
            count = len(entries_to_delete)
            if count > 0:
                entry_ids = [entry.id for entry in entries_to_delete]
                await ContextEntry.objects.filter(id__in=entry_ids).adelete()
            
            # Estimate storage savings (rough calculation)
            avg_entry_size = 500  # Average bytes per entry
            storage_saved_bytes = count * avg_entry_size
            
            logger.info(f"Cleaned up {count} entries, saved {total_tokens} tokens, ${total_cost_savings}")
            
            return {
                'entries_removed': count,
                'tokens_saved': total_tokens,
                'storage_saved_bytes': storage_saved_bytes,
                'cost_savings': total_cost_savings
            }
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return {
                'entries_removed': 0,
                'tokens_saved': 0,
                'storage_saved_bytes': 0,
                'cost_savings': Decimal('0.00')
            }
    
    # Domain-specific context preparation methods
    
    async def _prepare_chat_context(self,
                                   conversation: List[Dict],
                                   request: ContextRequest,
                                   context_session: ContextSession) -> Dict:
        """Prepare context optimized for chat interactions"""
        return await self._prepare_standard_context(conversation, request, context_session)
    
    async def _prepare_agent_context(self,
                                   conversation: List[Dict],
                                   request: ContextRequest,
                                   context_session: ContextSession) -> Dict:
        """Prepare context optimized for agent interactions"""
        # Agents need more emphasis on reasoning chains and tool usage
        # Filter for agent reasoning and tool results
        agent_conversation = []
        for msg in conversation:
            if msg['role'] in ['agent', 'tool', 'function'] or msg.get('structured_data'):
                agent_conversation.append(msg)
            elif msg['role'] in ['user', 'assistant']:
                agent_conversation.append(msg)
        
        return await self._prepare_standard_context(agent_conversation, request, context_session)
    
    # _prepare_workflow_context method removed
    
    async def _prepare_generic_context(self,
                                     conversation: List[Dict],
                                     request: ContextRequest,
                                     context_session: ContextSession) -> Dict:
        """Generic context preparation for custom entity types"""
        return await self._prepare_standard_context(conversation, request, context_session)
    
    async def _prepare_standard_context(self,
                                      conversation: List[Dict],
                                      request: ContextRequest,
                                      context_session: ContextSession) -> Dict:
        """Standard context preparation algorithm"""
        try:
            # Calculate conversation size
            conversation_tokens = await self._count_conversation_tokens(conversation)
            
            # Make intelligent decision
            decision = await self.decision_service.make_context_decision(
                conversation_tokens=conversation_tokens,
                target_model=request.target_model,
                preserve_quality=request.preserve_quality,
                cost_limit=request.cost_limit
            )
            
            if decision.use_full_context:
                # Use full context
                context_content = await self._format_conversation_for_model(
                    conversation, request.target_model
                )
                
                return {
                    'content': context_content,
                    'strategy': 'full_context',
                    'tokens_used': decision.target_context_tokens,
                    'cost': Decimal('0.00'),
                    'cache_hit': False,
                    'quality_score': 1.0
                }
            else:
                # Use smart summarization
                return await self._execute_smart_summary_strategy(
                    conversation, request, decision, context_session
                )
                
        except Exception as e:
            logger.error(f"Standard context preparation failed: {str(e)}")
            # Fallback to recent messages
            return await self._fallback_to_recent_messages(conversation, 2000)
    
    async def _execute_smart_summary_strategy(self,
                                            conversation: List[Dict],
                                            request: ContextRequest,
                                            decision: ContextDecision,
                                            context_session: ContextSession) -> Dict:
        """Execute smart summarization with caching"""
        try:
            # Generate conversation signature
            conversation_signature = await self._generate_conversation_signature(conversation)
            
            # Check cache
            cache_result = await self.cache_service.get_cached_summary(
                session_id=str(context_session.id),
                conversation_signature=conversation_signature,
                target_tokens=decision.target_context_tokens,
                organization_id=request.organization_id
            )
            
            if cache_result:
                return {
                    'content': cache_result.content,
                    'strategy': 'cached_summary',
                    'tokens_used': decision.target_context_tokens,
                    'cost': Decimal('0.00'),
                    'cache_hit': True,
                    'quality_score': cache_result.quality_score
                }
            
            # Try incremental update
            incremental_result = await self.cache_service.try_incremental_update(
                session=context_session,
                conversation=conversation,
                target_tokens=decision.target_context_tokens
            )
            
            if incremental_result:
                return incremental_result
            
            # Generate fresh summary
            summary_result = await self.summary_service.generate_fresh_summary(
                conversation=conversation,
                target_tokens=decision.target_context_tokens,
                organization_id=request.organization_id,
                preserve_quality=request.preserve_quality
            )
            
            # Cache the result
            if summary_result.cost > 0:
                await self.cache_service.store_summary(
                    session=context_session,
                    conversation_signature=conversation_signature,
                    target_tokens=decision.target_context_tokens,
                    summary_content=summary_result.content,
                    conversation_length=len(conversation),
                    generation_cost=summary_result.cost,
                    model_used=summary_result.model_used,
                    generation_time_ms=summary_result.generation_time_ms
                )
            
            return {
                'content': summary_result.content,
                'strategy': 'fresh_summary',
                'tokens_used': decision.target_context_tokens,
                'cost': summary_result.cost,
                'cache_hit': False,
                'quality_score': summary_result.quality_score
            }
            
        except Exception as e:
            logger.error(f"Smart summary strategy failed: {str(e)}")
            return await self._fallback_to_recent_messages(conversation, decision.target_context_tokens)
    
    # Helper methods
    
    async def _get_or_create_context_session(self,
                                           entity_id: str,
                                           entity_type: str,
                                           organization_id: str) -> ContextSession:
        """Get or create context session for any entity type"""
        try:
            session = await ContextSession.objects.aget(
                entity_id=entity_id,
                entity_type=entity_type,
                organization_id=organization_id
            )
            
            # Update domain entity even for existing sessions (in case it wasn't set before)
            await self.entity_registry.update_entity_context_session_id(
                entity_type=entity_type,
                entity_id=entity_id,
                context_session_id=str(session.id)
            )
            
            return session
        except ContextSession.DoesNotExist:
            # Determine session type from entity type
            session_type_map = {
                'prompt_session': 'chat',
                'agent_session': 'agent'
            }
            
            session = await ContextSession.objects.acreate(
                entity_id=entity_id,
                entity_type=entity_type,
                organization_id=organization_id,
                session_type=session_type_map.get(entity_type, 'custom'),
                tier='starter'  # Should get from organization
            )
            
            # Update domain entity with context session ID
            await self.entity_registry.update_entity_context_session_id(
                entity_type=entity_type,
                entity_id=entity_id,
                context_session_id=str(session.id)
            )
            
            logger.info(f"Created context session for {entity_type} {entity_id}")
            return session
    
    async def _get_context_session(self,
                                 entity_id: str,
                                 entity_type: str,
                                 organization_id: str) -> Optional[ContextSession]:
        """Get existing context session"""
        try:
            return await ContextSession.objects.aget(
                entity_id=entity_id,
                entity_type=entity_type,
                organization_id=organization_id
            )
        except ContextSession.DoesNotExist:
            return None
    
    async def _get_conversation_history(self, context_session: ContextSession) -> List[Dict]:
        """Get conversation history from context session"""
        conversation = []
        async for entry in context_session.entries.order_by('created_at'):
            conversation.append({
                'role': entry.role,
                'content': entry.content,
                'content_type': entry.content_type,
                'timestamp': entry.created_at.isoformat(),
                'model_used': entry.model_used,
                'structured_data': entry.structured_data,
                'execution_metadata': entry.execution_metadata
            })
        
        return conversation
    
    async def _update_session_metrics(self,
                                    context_session: ContextSession,
                                    context_result: Dict,
                                    preparation_cost: Decimal) -> None:
        """Update session performance metrics"""
        try:
            cache_hit = context_result.get('cache_hit', False)
            preparation_time_ms = 50  # Placeholder - should come from timing
            
            await context_session.update_performance_metrics(
                cache_hit=cache_hit,
                preparation_time_ms=preparation_time_ms
            )
            
            if preparation_cost > 0:
                await context_session.update_cost_metrics(
                    context_cost=preparation_cost
                )
                
        except Exception as e:
            logger.warning(f"Failed to update session metrics: {str(e)}")
    
    async def _record_context_transition(self,
                                       request: ContextRequest,
                                       context_result: Dict,
                                       preparation_cost: Decimal,
                                       context_session: ContextSession) -> None:
        """Record context transition for analytics"""
        try:
            await ContextTransition.objects.acreate(
                organization_id=request.organization_id,
                session=context_session,
                to_model=request.target_model,
                to_context_strategy=context_result['strategy'],
                transition_type='context_preparation',
                context_tokens_used=context_result['tokens_used'],
                context_utilization_percentage=75.0,  # Placeholder
                preparation_cost=preparation_cost,
                preparation_time_ms=50,  # Placeholder
                information_preservation_score=context_result.get('quality_score', 1.0)
            )
        except Exception as e:
            logger.warning(f"Failed to record context transition: {str(e)}")
    
    async def _count_conversation_tokens(self, conversation: List[Dict]) -> int:
        """Count tokens in conversation"""
        total = 0
        for msg in conversation:
            total += len(f"{msg['role']}: {msg['content']}") // 4
        return total
    
    async def _format_conversation_for_model(self, conversation: List[Dict], model: str) -> str:
        """Format conversation for model consumption with clear context separation"""
        if not conversation:
            return ""
        
        # FIXED: Don't try to separate current from historical here - 
        # that should be done by the calling code
        formatted_parts = []
        
        if len(conversation) > 0:
            formatted_parts.append("## RECENT CONVERSATION")
            formatted_parts.append("The following conversation provides context for your response:")
            formatted_parts.append("")
            
            for msg in conversation:
                role = msg['role'].title()
                content = msg['content']
                
                # Add structured data if present (for agent/workflow contexts)
                if msg.get('structured_data') and len(msg['structured_data']) > 0:
                    structured_info = []
                    for key, value in msg['structured_data'].items():
                        if key in ['tool_calls', 'function_calls', 'reasoning_steps']:
                            structured_info.append(f"{key}: {value}")
                    
                    if structured_info:
                        content += f" [Context: {'; '.join(structured_info)}]"
                
                # Add execution metadata for workflows
                if msg.get('execution_metadata') and len(msg['execution_metadata']) > 0:
                    exec_info = []
                    for key, value in msg['execution_metadata'].items():
                        if key in ['step_type', 'status', 'output']:
                            exec_info.append(f"{key}: {value}")
                    
                    if exec_info:
                        content += f" [Execution: {'; '.join(exec_info)}]"
                
                formatted_parts.append(f"**{role}**: {content}")
        
        return "\n".join(formatted_parts)

    async def _generate_conversation_signature(self, conversation: List[Dict]) -> str:
        """Generate conversation signature for caching"""
        import hashlib
        content_hash = hashlib.sha256()
        for msg in conversation:
            content_hash.update(f"{msg['role']}:{msg['content']}".encode('utf-8'))
        return content_hash.hexdigest()[:16]
    
    async def _fallback_to_recent_messages(self, conversation: List[Dict], target_tokens: int) -> Dict:
        """Fallback to recent messages when everything else fails"""
        try:
            recent_messages = []
            used_tokens = 0
            
            for msg in reversed(conversation):
                msg_tokens = len(f"{msg['role']}: {msg['content']}") // 4
                if used_tokens + msg_tokens > target_tokens:
                    break
                recent_messages.insert(0, msg)
                used_tokens += msg_tokens
            
            content = await self._format_conversation_for_model(recent_messages, "fallback")
            
            return {
                'content': content,
                'strategy': 'recent_messages_fallback',
                'tokens_used': used_tokens,
                'cost': Decimal('0.00'),
                'cache_hit': False,
                'quality_score': 0.6
            }
            
        except Exception as e:
            logger.error(f"Fallback failed: {str(e)}")
            return {
                'content': "Context preparation failed.",
                'strategy': 'error_fallback',
                'tokens_used': 5,
                'cost': Decimal('0.00'),
                'cache_hit': False,
                'quality_score': 0.1
            }
    
    async def _emergency_fallback(self, request: ContextRequest, start_time: float) -> ContextResponse:
        """Emergency fallback when everything fails"""
        logger.warning(f"Using emergency fallback for {request.entity_type} {request.entity_id}")
        
        fallback_content = f"User: {request.user_message}"
        preparation_time_ms = int((time.time() - start_time) * 1000)
        
        return ContextResponse(
            context_content=fallback_content,
            strategy_used='emergency_fallback',
            tokens_used=len(fallback_content) // 4,
            preparation_cost=Decimal('0.00'),
            preparation_time_ms=preparation_time_ms,
            cache_hit=False,
            information_preservation_score=0.2
        )