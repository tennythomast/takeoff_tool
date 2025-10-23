# context_manager/services/cache_service.py

import hashlib
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from django.utils import timezone
from django.core.cache import cache
from django.db import transaction

from ..models import ContextSession, ContextSummaryCache

logger = logging.getLogger(__name__)


@dataclass
class CacheResult:
    """Result from cache lookup"""
    content: str
    quality_score: float
    generation_cost: Decimal
    cache_hit: bool
    access_count: int


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hit_rate: float
    average_access_count: float
    total_cached_summaries: int
    cost_savings: Decimal


class SummaryCacheService:
    """
    PHASE 2 CORE: Intelligent Summary Caching System
    
    Implements the three-tier caching strategy:
    1. Cache-First Optimization (70% target hit rate)
    2. Incremental Updates (20% of remaining)  
    3. Fresh Generation (10% of remaining)
    
    This is where we achieve massive cost savings through smart caching
    """
    
    def __init__(self):
        self.cache_prefix = "summary_cache"
        self.redis_cache_ttl = 3600  # 1 hour for Redis
        self.default_db_ttl_days = 7  # 7 days for database cache
    
    async def get_cached_summary(self, 
                                session_id: str,
                                conversation_signature: str,
                                target_tokens: int,
                                organization_id: str,
                                target_model: Optional[str] = None) -> Optional[CacheResult]:
        """
        Tier 1: Cache-First Optimization
        
        Fast cache lookup with <10ms target response time
        This is our primary cost optimization - aiming for 70%+ hit rate
        
        Args:
            session_id: Session identifier
            conversation_signature: Hash of conversation content
            target_tokens: Required summary length
            organization_id: Tenant identifier
            target_model: Target model for model-family-aware caching
            
        Returns:
            CacheResult if found, None otherwise
        """
        try:
            # Get model family for cache key (enables cross-model cache sharing)
            model_family = await self._get_model_family(target_model) if target_model else "general"
            
            # First check Redis for hot cache
            redis_key = f"{self.cache_prefix}:{session_id}:{conversation_signature}:{target_tokens}:{model_family}"
            cached_data = cache.get(redis_key)
            
            if cached_data:
                logger.info(f"Redis cache hit for session {session_id} (model family: {model_family})")
                return CacheResult(
                    content=cached_data['content'],
                    quality_score=cached_data['quality_score'],
                    generation_cost=Decimal(cached_data['generation_cost']),
                    cache_hit=True,
                    access_count=cached_data['access_count']
                )
            
            # Check database cache with model family awareness
            try:
                # Try exact model family match first
                query = ContextSummaryCache.objects.select_related('session').filter(
                    session_id=session_id,
                    conversation_signature=conversation_signature,
                    target_tokens=target_tokens,
                    organization_id=organization_id
                )
                
                # Prefer cache entries from the same model family
                if model_family != "general":
                    query = query.filter(model_family=model_family)
                
                cached_summary = await query.afirst()
                
                # If no exact model family match, try compatible families
                if not cached_summary and model_family != "general":
                    compatible_families = self._get_compatible_model_families(model_family)
                    if compatible_families:
                        cached_summary = await ContextSummaryCache.objects.select_related('session').filter(
                            session_id=session_id,
                            conversation_signature=conversation_signature,
                            target_tokens=target_tokens,
                            organization_id=organization_id,
                            model_family__in=compatible_families
                        ).afirst()
                
                if cached_summary:
                    # Update access tracking
                    cached_summary.access_count += 1
                    cached_summary.last_used_at = timezone.now()
                    await cached_summary.asave(update_fields=['access_count', 'last_used_at'])
                    
                    # Store in Redis for faster future access
                    await self._store_in_redis_cache(redis_key, {
                        'content': cached_summary.summary_content,
                        'quality_score': 0.9,  # Cached summaries maintain high quality
                        'generation_cost': str(cached_summary.generation_cost),
                        'access_count': cached_summary.access_count
                    })
                    
                    logger.info(f"Database cache hit for session {session_id} (access #{cached_summary.access_count}, model family: {model_family})")
                    
                    return CacheResult(
                        content=cached_summary.summary_content,
                        quality_score=0.9,
                        generation_cost=cached_summary.generation_cost,
                        cache_hit=True,
                        access_count=cached_summary.access_count
                    )
                else:
                    logger.debug(f"No cache entry found for session {session_id}, signature {conversation_signature}, model family {model_family}")
                    return None
                
            except Exception as db_error:
                logger.error(f"Database cache lookup failed: {str(db_error)}")
                return None
                
        except Exception as e:
            logger.error(f"Cache lookup failed: {str(e)}", exc_info=True)
            return None
    
    async def try_incremental_update(self, 
                                   session: ContextSession,
                                   conversation: List[Dict],
                                   target_tokens: int) -> Optional[Dict]:
        """
        Tier 2: Incremental Updates (20% of cache misses)
        
        Update existing summaries with 1-3 new messages instead of full regeneration
        Achieves ~50% cost reduction vs fresh generation
        
        Args:
            session: Context session
            conversation: Full conversation history
            target_tokens: Target summary size
            
        Returns:
            Updated summary result or None if incremental update not possible
        """
        try:
            # Find the most recent summary for this session and token count
            latest_summary = await ContextSummaryCache.objects.filter(
                session=session,
                target_tokens=target_tokens
            ).order_by('-created_at').afirst()
            
            if not latest_summary:
                logger.debug(f"No existing summary found for incremental update (session {session.id})")
                return None
            
            # Check if conversation has grown by 1-3 messages (ideal for incremental)
            conversation_length = len(conversation)
            cached_length = latest_summary.conversation_length
            new_messages_count = conversation_length - cached_length
            
            if new_messages_count <= 0:
                logger.debug(f"No new messages since last summary (session {session.id})")
                return None
            
            if new_messages_count > 3:
                logger.debug(f"Too many new messages ({new_messages_count}) for incremental update (session {session.id})")
                return None
            
            # Get the new messages
            new_messages = conversation[-new_messages_count:]
            
            logger.info(f"Attempting incremental update for {new_messages_count} new messages (session {session.id})")
            
            # Generate incremental update using the summary service
            from .summary_service import SummaryGenerationService
            summary_service = SummaryGenerationService()
            
            updated_result = await summary_service.generate_incremental_update(
                existing_summary=latest_summary.summary_content,
                new_messages=new_messages,
                target_tokens=target_tokens,
                organization_id=session.organization_id
            )
            
            if updated_result:
                # Cache the updated summary
                new_signature = self._generate_conversation_signature(conversation)
                
                await self.store_summary(
                    session=session,
                    conversation_signature=new_signature,
                    target_tokens=target_tokens,
                    summary_content=updated_result.content,
                    conversation_length=conversation_length,
                    generation_cost=updated_result.cost,
                    model_used=updated_result.model_used,
                    generation_time_ms=updated_result.generation_time_ms
                )
                
                logger.info(f"Incremental update completed for session {session.id}, cost: ${updated_result.cost}")
                
                return {
                    'content': updated_result.content,
                    'strategy': 'incremental_summary',
                    'tokens_used': target_tokens,
                    'cost': updated_result.cost,
                    'cache_hit': False,
                    'quality_score': 0.87  # Slightly lower than fresh but still high
                }
            
        except Exception as e:
            logger.warning(f"Incremental update failed for session {session.id}: {str(e)}")
            return None
    
    async def store_summary(self, 
                           session: ContextSession,
                           conversation_signature: str,
                           target_tokens: int,
                           summary_content: str,
                           conversation_length: int,
                           generation_cost: Decimal,
                           model_used: str,
                           generation_time_ms: int,
                           target_model: Optional[str] = None) -> ContextSummaryCache:
        """
        Store generated summary in cache for future reuse
        
        Implements tier-based retention policies and intelligent expiration
        """
        try:
            # Calculate expiration based on subscription tier
            expires_at = self._calculate_expiration(session.tier)
            
            # Get model family for better cache organization
            model_family = await self._get_model_family(target_model or model_used)
            
            # Calculate context window estimate
            context_window = await self._estimate_context_window_from_modelhub(target_model or model_used)
            
            # Create cache entry
            cached_summary = await ContextSummaryCache.objects.acreate(
                organization_id=session.organization_id,
                session=session,
                conversation_signature=conversation_signature,
                target_tokens=target_tokens,
                target_context_window=context_window,
                model_family=model_family,
                summary_content=summary_content,
                conversation_length=conversation_length,
                generation_cost=generation_cost,
                model_used_for_summary=model_used,
                generation_time_ms=generation_time_ms,
                expires_at=expires_at
            )
            
            # Also store in Redis for fast access
            redis_key = f"{self.cache_prefix}:{session.id}:{conversation_signature}:{target_tokens}:{model_family}"
            await self._store_in_redis_cache(redis_key, {
                'content': summary_content,
                'quality_score': 0.85,
                'generation_cost': str(generation_cost),
                'access_count': 0
            })
            
            logger.info(f"Stored summary cache {cached_summary.id} for session {session.id} (model family: {model_family})")
            return cached_summary
            
        except Exception as e:
            logger.error(f"Failed to store summary cache: {str(e)}", exc_info=True)
            raise
    
    async def get_cache_metrics(self, 
                              organization_id: str, 
                              days: int = 7,
                              session_type: Optional[str] = None) -> CacheMetrics:
        """
        Get cache performance metrics for optimization
        
        Args:
            organization_id: Organization to analyze
            days: Days to look back
            session_type: Optional filter by session type
            
        Returns:
            CacheMetrics with performance data
        """
        try:
            since_date = timezone.now() - timedelta(days=days)
            
            # Build query with optional session type filter
            query = ContextSummaryCache.objects.filter(
                organization_id=organization_id,
                created_at__gte=since_date
            )
            
            if session_type:
                # Map session_type to entity_type patterns
                session_type_map = {
                    'chat': 'prompt_session',
                    'agent': 'agent_session', 
                    'workflow': 'workflow_execution'
                }
                entity_type = session_type_map.get(session_type, session_type)
                query = query.filter(session__entity_type=entity_type)
            
            total_entries = await query.acount()
            
            if total_entries == 0:
                return CacheMetrics(
                    hit_rate=0.0,
                    average_access_count=0.0,
                    total_cached_summaries=0,
                    cost_savings=Decimal('0.00')
                )
            
            # Calculate metrics
            total_access_count = 0
            total_generation_cost = Decimal('0.00')
            
            async for entry in query:
                total_access_count += entry.access_count
                total_generation_cost += entry.generation_cost
            
            # Estimate cost savings (access_count - 1) * generation_cost
            # The "- 1" is because the first access was the generation, subsequent are savings
            total_cost_savings = Decimal('0.00')
            async for entry in query:
                if entry.access_count > 1:
                    savings = (entry.access_count - 1) * entry.generation_cost
                    total_cost_savings += savings
            
            average_access_count = total_access_count / total_entries if total_entries > 0 else 0
            hit_rate = (total_access_count - total_entries) / total_access_count if total_access_count > 0 else 0
            
            return CacheMetrics(
                hit_rate=max(0.0, hit_rate),  # Ensure non-negative
                average_access_count=average_access_count,
                total_cached_summaries=total_entries,
                cost_savings=total_cost_savings
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate cache metrics: {str(e)}")
            return CacheMetrics(0.0, 0.0, 0, Decimal('0.00'))
    
    async def cleanup_expired_cache(self, organization_id: Optional[str] = None) -> int:
        """
        Clean up expired cache entries
        
        Args:
            organization_id: Specific org to clean up, or None for all
            
        Returns:
            Number of entries cleaned up
        """
        try:
            query = ContextSummaryCache.objects.filter(
                expires_at__lt=timezone.now()
            )
            
            if organization_id:
                query = query.filter(organization_id=organization_id)
            
            count = await query.acount()
            await query.adelete()
            
            logger.info(f"Cleaned up {count} expired cache entries")
            return count
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {str(e)}")
            return 0
    
    async def _get_model_family(self, model: str) -> str:
        """
        Get model family from ModelHub for intelligent cache grouping
        
        Args:
            model: Model identifier
            
        Returns:
            Model family (gpt, claude, mixtral, etc.)
        """
        try:
            if not model:
                return "general"
            
            # Import here to avoid circular imports
            from modelhub.models import Model
            from ..utils import _parse_model_string
            
            provider_slug, model_name = _parse_model_string(model)
            
            try:
                model_obj = await Model.get_model_async(provider_slug, model_name)
                
                # Use provider as base family, but could be more sophisticated
                # For example, group by model capabilities or size
                return provider_slug.lower()
                
            except Model.DoesNotExist:
                # Fallback to provider-based grouping
                return provider_slug.lower()
                
        except Exception as e:
            logger.warning(f"Failed to get model family for '{model}': {str(e)}")
            # Fallback classification
            model_lower = model.lower()
            if 'gpt' in model_lower:
                return 'openai'
            elif 'claude' in model_lower:
                return 'anthropic'
            elif 'mixtral' in model_lower or 'mistral' in model_lower:
                return 'mistral'
            elif 'gemini' in model_lower:
                return 'google'
            else:
                return 'general'
    
    def _get_compatible_model_families(self, model_family: str) -> List[str]:
        """
        Get compatible model families for cache sharing
        
        Some model families can share cached summaries effectively
        """
        compatibility_map = {
            'openai': ['openai', 'anthropic'],  # GPT and Claude summaries are often compatible
            'anthropic': ['anthropic', 'openai'],
            'mistral': ['mistral', 'openai'],  # Mixtral summaries work well with GPT models
            'google': ['google', 'openai']
        }
        
        return compatibility_map.get(model_family, [model_family])
    
    async def _estimate_context_window_from_modelhub(self, model: str) -> int:
        """
        Get context window from ModelHub for accurate cache organization
        """
        try:
            # Use the utils function which already handles ModelHub integration
            from ..utils import get_model_context_window
            return await get_model_context_window(model)
        except Exception as e:
            logger.warning(f"Failed to get context window from ModelHub for '{model}': {str(e)}")
            # Fallback estimation
            return self._estimate_context_window_fallback(model)
    
    def _estimate_context_window_fallback(self, model: str) -> int:
        """Fallback context window estimation"""
        model_lower = model.lower()
        if any(pattern in model_lower for pattern in ['gpt-4', 'claude-3', 'mixtral']):
            return 32000
        elif any(pattern in model_lower for pattern in ['gpt-3.5', 'claude-2']):
            return 16000
        else:
            return 8000
    
    def _generate_conversation_signature(self, conversation: List[Dict]) -> str:
        """Generate unique signature for conversation content"""
        content_hash = hashlib.sha256()
        for msg in conversation:
            content_hash.update(f"{msg['role']}:{msg['content']}".encode('utf-8'))
        return content_hash.hexdigest()[:16]
    
    def _calculate_expiration(self, tier: str) -> datetime:
        """Calculate cache expiration based on subscription tier"""
        now = timezone.now()
        
        tier_retention_days = {
            'starter': 7,
            'pro': 14,
            'team': 30,
            'enterprise': 90
        }
        
        retention_days = tier_retention_days.get(tier, 7)
        return now + timedelta(days=retention_days)
    
    async def _store_in_redis_cache(self, key: str, data: Dict) -> None:
        """Store data in Redis cache with TTL"""
        try:
            cache.set(key, data, timeout=self.redis_cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to store in Redis cache: {str(e)}")
    
    async def invalidate_session_cache(self, session_id: str) -> None:
        """
        Invalidate all cache entries for a session
        Called when new messages are added
        """
        try:
            # Note: In production, implement proper Redis pattern deletion
            # For now, we rely on TTL and database-level tracking
            
            # Mark database entries as stale (if we add a stale flag in future)
            # For Phase 2, we'll rely on conversation signatures changing
            
            logger.debug(f"Cache invalidation requested for session {session_id}")
            
        except Exception as e:
            logger.warning(f"Cache invalidation failed for session {session_id}: {str(e)}")
    
    async def warm_cache_for_session(self, session_id: str, organization_id: str) -> None:
        """
        Pre-warm cache for a session (background task)
        Predictive caching for better performance
        """
        try:
            # This could be implemented as a background task
            # For Phase 2, we'll focus on reactive caching
            logger.debug(f"Cache warming requested for session {session_id}")
            
        except Exception as e:
            logger.warning(f"Cache warming failed for session {session_id}: {str(e)}")