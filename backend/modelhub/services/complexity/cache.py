# backend/modelhub/services/complexity/cache.py
"""
Caching service for complexity analysis results.
Improves performance by caching identical requests.
"""
import hashlib
import json
import time
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

from django.core.cache import cache
from django.conf import settings

from .types import ComplexityResult, RequestContext, CacheKey, AnalysisPath

logger = logging.getLogger(__name__)


class ComplexityCacheService:
    """
    Intelligent caching for complexity analysis results.
    
    Features:
    - Content-based cache keys
    - Context-aware caching  
    - TTL based on confidence
    - Performance metrics
    """
    
    # Cache configuration
    DEFAULT_TTL = 3600  # 1 hour
    HIGH_CONFIDENCE_TTL = 7200  # 2 hours for high confidence results
    LOW_CONFIDENCE_TTL = 1800   # 30 minutes for low confidence results
    
    def __init__(self):
        self.cache_prefix = "complexity_analysis"
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }
    
    def get_cached_result(
        self, 
        request_text: str, 
        context: RequestContext
    ) -> Optional[ComplexityResult]:
        """
        Get cached complexity result if available.
        
        Returns None if no cache hit or cache is invalid.
        """
        try:
            cache_key = self._generate_cache_key(request_text, context)
            cache_data = cache.get(str(cache_key))
            
            if cache_data:
                # Deserialize and validate cached result
                result = self._deserialize_result(cache_data)
                if result:
                    # Mark as cache hit and update timing
                    result.cache_hit = True
                    result.analysis_time_ms = 1  # Cache retrieval time
                    
                    self.stats['hits'] += 1
                    logger.debug(f"✅ Cache HIT for key: {cache_key}")
                    return result
            
            self.stats['misses'] += 1
            logger.debug(f"❌ Cache MISS for key: {cache_key}")
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"Cache retrieval error: {e}")
            return None
    
    def cache_result(
        self, 
        request_text: str, 
        context: RequestContext, 
        result: ComplexityResult
    ) -> bool:
        """
        Cache complexity analysis result.
        
        TTL is based on confidence level:
        - High confidence (>0.9): 2 hours
        - Medium confidence (0.7-0.9): 1 hour  
        - Low confidence (<0.7): 30 minutes
        """
        try:
            cache_key = self._generate_cache_key(request_text, context)
            cache_data = self._serialize_result(result)
            
            # Determine TTL based on confidence
            if result.confidence > 0.9:
                ttl = self.HIGH_CONFIDENCE_TTL
            elif result.confidence > 0.7:
                ttl = self.DEFAULT_TTL
            else:
                ttl = self.LOW_CONFIDENCE_TTL
            
            # Don't cache LLM escalation results if they're placeholder
            if result.analysis_path == AnalysisPath.LLM_ESCALATION and "placeholder" in result.reasoning:
                logger.debug(f"Skipping cache for LLM placeholder result")
                return False
            
            success = cache.set(str(cache_key), cache_data, ttl)
            
            if success:
                self.stats['sets'] += 1
                logger.debug(f"✅ Cached result with TTL {ttl}s: {cache_key}")
            else:
                self.stats['errors'] += 1
                logger.warning(f"Failed to cache result: {cache_key}")
            
            return success
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"Cache storage error: {e}")
            return False
    
    def _generate_cache_key(self, request_text: str, context: RequestContext) -> CacheKey:
        """
        Generate cache key based on request content and relevant context.
        
        Only includes context factors that affect complexity analysis.
        """
        
        # Hash the request text
        text_hash = hashlib.md5(request_text.encode('utf-8')).hexdigest()[:12]
        
        # Create context signature (only factors that affect analysis)
        context_factors = {
            'max_tokens': context.max_tokens,
            'entity_type': context.entity_type,
            'has_rag': bool(context.rag_documents),
            'rag_count': len(context.rag_documents) if context.rag_documents else 0,
            'has_history': bool(context.conversation_history),
            'history_length': len(context.conversation_history) if context.conversation_history else 0,
            'cost_sensitive': context.cost_sensitive,
            'quality_critical': context.quality_critical,
            'require_fast': context.require_fast_response
        }
        
        # Hash context factors
        context_str = json.dumps(context_factors, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode('utf-8')).hexdigest()[:8]
        
        return CacheKey(
            text_hash=text_hash,
            context_hash=context_hash,
            organization_id=context.organization_id
        )
    
    def _serialize_result(self, result: ComplexityResult) -> Dict[str, Any]:
        """Serialize complexity result for caching"""
        return {
            'score': float(result.score),
            'level': result.level.value,
            'confidence': float(result.confidence),
            'reasoning': result.reasoning,
            'analysis_path': result.analysis_path.value,
            'content_type': result.content_type.value,
            'escalation_reason': result.escalation_reason.value if result.escalation_reason else None,
            'pattern_matches': result.pattern_matches,
            'context_factors': result.context_factors,
            'cached_at': time.time()
        }
    
    def _deserialize_result(self, cache_data: Dict[str, Any]) -> Optional[ComplexityResult]:
        """Deserialize cached complexity result"""
        try:
            from .types import ComplexityLevel, AnalysisPath, ContentType, EscalationReason
            
            return ComplexityResult(
                score=cache_data['score'],
                level=ComplexityLevel(cache_data['level']),
                confidence=cache_data['confidence'],
                reasoning=cache_data['reasoning'],
                analysis_path=AnalysisPath(cache_data['analysis_path']),
                analysis_time_ms=0,  # Will be updated by caller
                content_type=ContentType(cache_data['content_type']),
                escalation_reason=EscalationReason(cache_data['escalation_reason']) if cache_data['escalation_reason'] else None,
                pattern_matches=cache_data.get('pattern_matches'),
                context_factors=cache_data.get('context_factors'),
                cache_hit=True
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Failed to deserialize cached result: {e}")
            return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_requests': total_requests,
            'cache_hits': self.stats['hits'],
            'cache_misses': self.stats['misses'],
            'cache_sets': self.stats['sets'],
            'cache_errors': self.stats['errors'],
            'hit_rate_percent': round(hit_rate, 2)
        }
    
    def clear_cache(self, organization_id: Optional[str] = None) -> bool:
        """
        Clear complexity analysis cache.
        
        Args:
            organization_id: If provided, only clear cache for this org
        """
        try:
            if organization_id:
                # Clear org-specific cache (more complex, requires pattern matching)
                # For now, just log - implementing full pattern clearing is complex
                logger.info(f"TODO: Clear cache for organization {organization_id}")
                return True
            else:
                # Clear all complexity cache
                cache.delete_many(cache.keys(f"{self.cache_prefix}:*"))
                logger.info("Cleared all complexity analysis cache")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False