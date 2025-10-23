# context_manager/services/storage_service.py

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from asgiref.sync import sync_to_async
from django.db import DatabaseError

from ..models import ContextSession, ContextEntry

logger = logging.getLogger(__name__)


@dataclass
class StorageMetrics:
    """Storage layer metrics"""
    total_entries: int
    total_sessions: int
    average_session_length: float
    storage_cost: Decimal
    importance_distribution: Dict[str, int]
    avg_tokens_per_request: int
    avg_cost_per_request: Decimal
    requests_today: int


class FullContextStorageService:
    """
    Layer 1: System-Level Full Context Storage (The Source of Truth)
    
    CORE PRINCIPLE: Never summarize, never compress, never lose information
    This layer maintains the complete, immutable conversation history
    
    Key Features:
    - 100% information preservation
    - Multi-tenant isolation
    - Importance scoring for cleanup
    - Audit trail maintenance
    - ModelHub integration for cost tracking
    """
    
    def __init__(self):
        self.importance_calculator = ImportanceCalculator()
    
    async def store_message(self, 
                           session_id: str,
                           organization_id: str,
                           role: str,
                           content: str,
                           model_used: Optional[str] = None,
                           metadata: Optional[Dict] = None,
                           content_type: str = 'text',
                           source_entity_id: Optional[str] = None,
                           source_entity_type: Optional[str] = None,
                           structured_data: Optional[Dict] = None,
                           execution_metadata: Optional[Dict] = None) -> ContextEntry:
        """
        Store a message in the full context store
        
        IMMUTABLE STORAGE: Once stored, never modified or compressed
        
        Args:
            session_id: Session identifier
            organization_id: Tenant identifier  
            role: Message role (user, assistant, system, agent, workflow, etc.)
            content: Complete message content
            model_used: Model that generated this content (for assistant messages)
            metadata: Additional context metadata (strategy, tokens, costs)
            content_type: Content type (text, json, code, etc.)
            source_entity_id: Source entity that created this
            source_entity_type: Type of source entity
            structured_data: Rich data for agents/workflows
            execution_metadata: Execution details
            
        Returns:
            Created ContextEntry
        """
        try:
            # Get or create session
            session = await self._get_or_create_session(session_id, organization_id)
            
            # Calculate importance score for this message
            importance_score = await self.importance_calculator.calculate_importance(
                content=content,
                role=role,
                session=session,
                metadata=metadata,
                content_type=content_type,
                structured_data=structured_data
            )
            
            # Extract costs and tokens from metadata
            total_cost = Decimal('0.00')
            context_preparation_cost = Decimal('0.00')
            context_tokens_used = None
            context_strategy = None
            
            if metadata:
                total_cost = Decimal(str(metadata.get('total_cost', 0)))
                context_preparation_cost = Decimal(str(metadata.get('preparation_cost', 0)))
                context_tokens_used = metadata.get('tokens_used')
                context_strategy = metadata.get('strategy')
            
            # Use sync_to_async to wrap the transaction operation
            @sync_to_async
            def create_entry_in_transaction():
                with transaction.atomic():
                    # Create context entry
                    entry = ContextEntry.objects.create(
                        organization_id=organization_id,
                        session=session,
                        role=role,
                        content=content,
                        content_type=content_type,
                        source_entity_id=source_entity_id,
                        source_entity_type=source_entity_type,
                        model_used=model_used,
                        importance_score=importance_score,
                        context_strategy=context_strategy,
                        context_tokens_used=context_tokens_used,
                        total_cost=total_cost,
                        context_preparation_cost=context_preparation_cost,
                        structured_data=structured_data or {},
                        execution_metadata=execution_metadata or {}
                    )
                    
                    # Update session activity timestamp and costs
                    session.last_activity_at = timezone.now()
                    session.save(update_fields=['last_activity_at'])
                    
                    return entry
            
            # Execute the transaction in a sync context
            entry = await create_entry_in_transaction()
            
            # Update session costs asynchronously
            if context_preparation_cost > 0:
                await session.update_cost_metrics(context_cost=context_preparation_cost)
            
            logger.info(f"Stored message {entry.id} for session {session_id} (importance: {importance_score:.2f}, cost: ${total_cost})")
            return entry
                
        except Exception as e:
            logger.error(f"Failed to store message: {str(e)}", exc_info=True)
            raise
    
    async def get_conversation_history(self, 
                                     session_id: str, 
                                     organization_id: str,
                                     limit: Optional[int] = None,
                                     since: Optional[datetime] = None,
                                     role_filter: Optional[str] = None,
                                     include_structured_data: bool = False) -> List[Dict]:
        """
        Retrieve complete conversation history
        
        IMMUTABLE SOURCE: Returns the complete, unmodified conversation
        
        Args:
            session_id: Session identifier
            organization_id: Tenant identifier
            limit: Maximum number of messages to return (None for all)
            since: Only return messages after this timestamp
            role_filter: Filter by specific role
            include_structured_data: Whether to include structured_data in response
            
        Returns:
            List of conversation messages in chronological order
        """
        try:
            # Find the session first to get the correct session object
            try:
                session = await ContextSession.objects.aget(
                    id=session_id,
                    organization_id=organization_id
                )
            except ContextSession.DoesNotExist:
                logger.warning(f"Session {session_id} not found for organization {organization_id}")
                return []
            
            query = ContextEntry.objects.filter(
                session=session,
                organization_id=organization_id
            ).order_by('created_at')
            
            if since:
                query = query.filter(created_at__gte=since)
            
            if role_filter:
                query = query.filter(role=role_filter)
            
            if limit:
                query = query[:limit]
            
            conversation = []
            async for entry in query:
                entry_data = {
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
                    'source_entity_type': entry.source_entity_type
                }
                
                # Include structured data if requested (useful for agents/workflows)
                if include_structured_data:
                    entry_data['structured_data'] = entry.structured_data
                    entry_data['execution_metadata'] = entry.execution_metadata
                
                conversation.append(entry_data)
            
            logger.debug(f"Retrieved {len(conversation)} messages for session {session_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            return []
    
    async def get_session_info(self, session_id: str, organization_id: str) -> Optional[ContextSession]:
        """Get session information"""
        try:
            return await ContextSession.objects.aget(
                id=session_id,
                organization_id=organization_id
            )
        except ContextSession.DoesNotExist:
            return None
    
    async def update_session_metadata(self, 
                                    session_id: str,
                                    organization_id: str,
                                    **kwargs) -> bool:
        """Update session metadata"""
        try:
            session = await ContextSession.objects.aget(
                id=session_id,
                organization_id=organization_id
            )
            
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            await session.asave()
            logger.info(f"Updated session {session_id} metadata")
            return True
            
        except ContextSession.DoesNotExist:
            logger.warning(f"Session {session_id} not found for metadata update")
            return False
        except Exception as e:
            logger.error(f"Failed to update session metadata: {str(e)}")
            return False
    
    async def get_storage_metrics(self, 
                                organization_id: str, 
                                days: int = 30,
                                session_type: Optional[str] = None) -> StorageMetrics:
        """
        Get comprehensive storage metrics for an organization
        
        Args:
            organization_id: Organization to analyze
            days: Days to look back
            session_type: Optional filter by session type (chat, agent, workflow)
            
        Returns:
            StorageMetrics with comprehensive data
        """
        try:
            since_date = timezone.now() - timezone.timedelta(days=days)
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Build base queries
            entries_query = ContextEntry.objects.filter(
                organization_id=organization_id,
                created_at__gte=since_date
            )
            
            sessions_query = ContextSession.objects.filter(
                organization_id=organization_id,
                created_at__gte=since_date
            )
            
            # Apply session type filter if specified
            if session_type:
                session_type_map = {
                    'chat': 'prompt_session',
                    'agent': 'agent_session',
                    'workflow': 'workflow_execution'
                }
                entity_type = session_type_map.get(session_type, session_type)
                
                sessions_query = sessions_query.filter(entity_type=entity_type)
                entries_query = entries_query.filter(session__entity_type=entity_type)
            
            # Count entries and sessions
            total_entries = await entries_query.acount()
            total_sessions = await sessions_query.acount()
            
            # Calculate today's requests
            requests_today = await ContextEntry.objects.filter(
                organization_id=organization_id,
                created_at__gte=today_start
            ).acount()
            
            # Calculate average session length
            avg_session_length = 0.0
            if total_sessions > 0:
                avg_session_length = total_entries / total_sessions
            
            # Calculate total storage cost and token usage
            total_cost = Decimal('0.00')
            total_tokens = 0
            token_count = 0
            
            async for entry in entries_query:
                total_cost += entry.total_cost
                if entry.context_tokens_used:
                    total_tokens += entry.context_tokens_used
                    token_count += 1
            
            # Calculate averages
            avg_tokens_per_request = total_tokens // token_count if token_count > 0 else 0
            avg_cost_per_request = total_cost / total_entries if total_entries > 0 else Decimal('0.00')
            
            # Importance distribution
            importance_ranges = {
                'low': 0,      # 0.0 - 0.5
                'medium': 0,   # 0.5 - 1.0
                'high': 0,     # 1.0 - 1.5
                'critical': 0  # 1.5+
            }
            
            async for entry in entries_query:
                score = entry.importance_score
                if score >= 1.5:
                    importance_ranges['critical'] += 1
                elif score >= 1.0:
                    importance_ranges['high'] += 1
                elif score >= 0.5:
                    importance_ranges['medium'] += 1
                else:
                    importance_ranges['low'] += 1
            
            return StorageMetrics(
                total_entries=total_entries,
                total_sessions=total_sessions,
                average_session_length=avg_session_length,
                storage_cost=total_cost,
                importance_distribution=importance_ranges,
                avg_tokens_per_request=avg_tokens_per_request,
                avg_cost_per_request=avg_cost_per_request,
                requests_today=requests_today
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate storage metrics: {str(e)}")
            return StorageMetrics(
                total_entries=0,
                total_sessions=0,
                average_session_length=0.0,
                storage_cost=Decimal('0.00'),
                importance_distribution={},
                avg_tokens_per_request=0,
                avg_cost_per_request=Decimal('0.00'),
                requests_today=0
            )
    
    async def cleanup_low_importance_entries(self, 
                                           organization_id: str,
                                           importance_threshold: float = 0.3,
                                           days_old: int = 30,
                                           session_type: Optional[str] = None) -> int:
        """
        Clean up low-importance entries that are old
        
        Only removes entries below importance threshold and older than specified days
        
        Args:
            organization_id: Organization to clean
            importance_threshold: Minimum importance score to keep
            days_old: Minimum age in days for cleanup
            session_type: Optional session type filter
        """
        try:
            cutoff_date = timezone.now() - timezone.timedelta(days=days_old)
            
            query = ContextEntry.objects.filter(
                organization_id=organization_id,
                importance_score__lt=importance_threshold,
                created_at__lt=cutoff_date,
                is_starred=False  # Never delete starred content
            )
            
            # Apply session type filter if specified
            if session_type:
                session_type_map = {
                    'chat': 'prompt_session',
                    'agent': 'agent_session',
                    'workflow': 'workflow_execution'
                }
                entity_type = session_type_map.get(session_type, session_type)
                query = query.filter(session__entity_type=entity_type)
            
            count = await query.acount()
            await query.adelete()
            
            logger.info(f"Cleaned up {count} low-importance entries for org {organization_id} (session_type: {session_type})")
            return count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return 0
    
    async def get_cost_breakdown_by_model(self, organization_id: str, days: int = 30) -> Dict[str, Decimal]:
        """
        Get cost breakdown by model for organization
        
        Useful for understanding which models are driving costs
        """
        try:
            since_date = timezone.now() - timezone.timedelta(days=days)
            
            cost_by_model = {}
            
            async for entry in ContextEntry.objects.filter(
                organization_id=organization_id,
                created_at__gte=since_date,
                model_used__isnull=False
            ).values('model_used').distinct():
                
                model = entry['model_used']
                
                # Calculate total cost for this model
                total_cost = Decimal('0.00')
                async for model_entry in ContextEntry.objects.filter(
                    organization_id=organization_id,
                    created_at__gte=since_date,
                    model_used=model
                ):
                    total_cost += model_entry.total_cost
                
                cost_by_model[model] = total_cost
            
            return cost_by_model
            
        except Exception as e:
            logger.error(f"Failed to get cost breakdown by model: {str(e)}")
            return {}
    
    async def _get_or_create_session(self, session_id: str, organization_id: str) -> ContextSession:
        """Get existing session or create new one with defaults"""
        session_id = session_id.strip()
        
        try:
            # First try exact match
            session = await ContextSession.objects.aget(
                id=session_id,
                organization_id=organization_id
            )
            logger.debug(f"Found existing session {session_id} for org {organization_id}")
            return session
            
        except ContextSession.DoesNotExist:
            # Get organization tier for new session
            tier = await self._get_organization_tier(organization_id)
            
            # Create new session with proper defaults
            session = await ContextSession.objects.acreate(
                id=session_id,
                organization_id=organization_id,
                session_type='chat',  # Default, will be updated by universal context service
                entity_id=session_id,  # Default to session_id
                entity_type='prompt_session',  # Default, will be updated
                tier=tier
            )
            logger.info(f"Created new context session '{session_id}' for org '{organization_id}' (tier: {tier})")
            return session
    
    async def _get_organization_tier(self, organization_id: str) -> str:
        """
        Get organization tier from core.Organization model
        
        This should be integrated with your subscription system
        """
        try:
            # Import here to avoid circular imports
            from core.models import Organization
            
            org = await Organization.objects.aget(id=organization_id)
            return getattr(org, 'tier', 'starter')  # Fallback to starter
            
        except Exception as e:
            logger.warning(f"Failed to get organization tier for {organization_id}: {str(e)}")
            return 'starter'  # Safe fallback


class ImportanceCalculator:
    """
    Enhanced importance calculator for messages across all domains
    
    Calculates importance scores for cleanup decisions with domain awareness
    """
    
    def __init__(self):
        self.base_score = 1.0
        self.role_multipliers = {
            'user': 1.2,       # User messages slightly more important
            'assistant': 1.0,   # Assistant messages baseline
            'system': 0.8,      # System messages less important
            'agent': 1.3,       # Agent messages more important (reasoning chains)
            'workflow': 1.2,    # Workflow messages important (state tracking)
            'tool': 1.1,        # Tool results moderately important
            'function': 1.1     # Function results moderately important
        }
        
        # Keywords that indicate high importance
        self.importance_keywords = [
            'decision', 'requirement', 'goal', 'objective', 'preference',
            'important', 'critical', 'key', 'essential', 'must',
            'remember', 'note', 'warning', 'error', 'issue',
            'configuration', 'setting', 'parameter', 'rule'
        ]
        
        # Agent/workflow specific important keywords
        self.agent_keywords = [
            'reasoning', 'analysis', 'conclusion', 'recommendation',
            'tool_use', 'function_call', 'result', 'output'
        ]
        
        # Keywords that indicate low importance  
        self.low_importance_keywords = [
            'hello', 'hi', 'thanks', 'ok', 'yes', 'no',
            'got it', 'understood', 'sure', 'please'
        ]
    
    async def calculate_importance(self, 
                                 content: str,
                                 role: str,
                                 session: ContextSession,
                                 metadata: Optional[Dict] = None,
                                 content_type: str = 'text',
                                 structured_data: Optional[Dict] = None) -> float:
        """
        Calculate importance score for a message with domain awareness
        
        Args:
            content: Message content
            role: Message role
            session: Context session
            metadata: Additional metadata
            content_type: Content type (text, json, code, etc.)
            structured_data: Rich data for agents/workflows
            
        Returns:
            Importance score (0.0 to 2.5)
        """
        try:
            score = self.base_score
            
            # Role-based scoring
            score *= self.role_multipliers.get(role, 1.0)
            
            # Content type influences
            content_type_multipliers = {
                'text': 1.0,
                'json': 1.2,      # Structured data more important
                'code': 1.3,      # Code snippets very important
                'image_url': 1.1, # Images moderately important
                'tool_result': 1.4, # Tool results very important
                'function_result': 1.4
            }
            score *= content_type_multipliers.get(content_type, 1.0)
            
            # Content length scoring
            content_length = len(content)
            if content_length < 20:
                score *= 0.6  # Very short messages
            elif content_length < 50:
                score *= 0.8  # Short messages
            elif content_length > 500:
                score *= 1.3  # Long messages
            elif content_length > 1000:
                score *= 1.5  # Very long messages
            
            # Keyword-based scoring
            content_lower = content.lower()
            
            # Check for high-importance keywords
            importance_matches = sum(1 for keyword in self.importance_keywords 
                                   if keyword in content_lower)
            score *= (1.0 + importance_matches * 0.1)  # +10% per important keyword
            
            # Agent/workflow specific keyword boost
            if role in ['agent', 'workflow', 'tool', 'function']:
                agent_matches = sum(1 for keyword in self.agent_keywords 
                                  if keyword in content_lower)
                score *= (1.0 + agent_matches * 0.15)  # +15% per agent keyword
            
            # Check for low-importance keywords (only if no high-importance ones)
            if importance_matches == 0:
                low_importance_matches = sum(1 for keyword in self.low_importance_keywords 
                                           if keyword in content_lower)
                if low_importance_matches > 0:
                    score *= 0.7  # Reduce for low-importance content
            
            # Code or technical content (higher importance)
            if any(indicator in content for indicator in ['```', 'def ', 'function', 'class ', 'import ', '{']):
                score *= 1.2
            
            # Error messages or exceptions (higher importance)
            if any(indicator in content_lower for indicator in ['error', 'exception', 'failed', 'warning']):
                score *= 1.3
            
            # Questions (slightly higher importance)
            if content.strip().endswith('?'):
                score *= 1.1
            
            # Structured data importance boost
            if structured_data and len(structured_data) > 0:
                score *= 1.25  # Structured data is valuable
                
                # Tool calls and function calls are especially important
                if any(key in structured_data for key in ['tool_calls', 'function_calls', 'reasoning_steps']):
                    score *= 1.2
            
            # Session tier influence (enterprise content more important)
            tier_multipliers = {
                'starter': 1.0,
                'pro': 1.05,
                'team': 1.1,
                'enterprise': 1.2
            }
            score *= tier_multipliers.get(session.tier, 1.0)
            
            # Metadata influences
            if metadata:
                # High-cost interactions are more important
                total_cost = metadata.get('total_cost', 0)
                if isinstance(total_cost, (int, float, Decimal)) and total_cost > 0.01:
                    score *= 1.15
                
                # Specific strategies might indicate importance
                if metadata.get('strategy') == 'full_context':
                    score *= 1.05  # Full context suggests important conversation
                elif metadata.get('strategy') in ['smart_summary', 'incremental_summary']:
                    score *= 1.03  # Summarized content has some importance boost
            
            # Domain-specific importance adjustments
            if session.entity_type == 'agent_session':
                score *= 1.1  # Agent interactions generally more important
            elif session.entity_type == 'workflow_execution':
                score *= 1.15  # Workflow state is very important
            
            # Cap the maximum score
            return min(score, 2.5)
            
        except Exception as e:
            logger.warning(f"Importance calculation failed: {str(e)}")
            return self.base_score  # Return default score on error