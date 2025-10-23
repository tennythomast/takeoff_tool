# backend/modelhub/services/complexity/analyzer.py
"""
Main complexity analyzer that orchestrates rule-based analysis,
caching, and LLM escalation decisions.
"""
import time
import logging
from typing import Tuple

from .types import ComplexityResult, RequestContext, AnalysisMetrics
from .rule_analyzer import RuleBasedComplexityAnalyzer
from .escalation import LLMEscalationCriteria, QwenComplexityAnalyzer
from .cache import ComplexityCacheService

logger = logging.getLogger(__name__)


class EnhancedComplexityAnalyzer:
    """
    Main complexity analyzer that orchestrates the entire analysis pipeline.
    
    Pipeline:
    1. Check cache for existing results
    2. Rule-based analysis (85% of cases)
    3. Escalation decision (15% of cases)
    4. LLM analysis (future implementation)
    5. Cache the result
    
    Performance Targets:
    - Rule-based path: 5-15ms (85% of requests)
    - LLM escalation path: 150-300ms (15% of requests)
    - Cache hit: 1-2ms
    - Overall average: 25-45ms
    """
    
    def __init__(self):
        self.rule_analyzer = RuleBasedComplexityAnalyzer()
        self.escalation_criteria = LLMEscalationCriteria()
        self.cache_service = ComplexityCacheService()
        self.llm_analyzer = QwenComplexityAnalyzer()
        
        # Performance tracking
        self.metrics = AnalysisMetrics()
    
    async def analyze_complexity(
        self, 
        request_text: str, 
        context: RequestContext
    ) -> ComplexityResult:
        """
        Main complexity analysis entry point.
        
        Args:
            request_text: The user's input text to analyze
            context: Request context including session, org, and usage info
            
        Returns:
            ComplexityResult with score, confidence, and metadata
        """
        total_start_time = time.time()
        
        try:
            # Phase 1: Check cache first (1-2ms)
            cached_result = self.cache_service.get_cached_result(request_text, context)
            if cached_result:
                self.metrics.cache_hits += 1
                self.metrics.total_requests += 1
                logger.debug(f"Cache hit for complexity analysis")
                return cached_result
            
            # Phase 2: Rule-based analysis (5-15ms)
            rule_result = self.rule_analyzer.analyze_complexity(request_text, context)
            self.metrics.rule_based_count += 1
            self.metrics.total_requests += 1
            
            logger.debug(
                f"Rule analysis: score={rule_result.score:.2f}, "
                f"confidence={rule_result.confidence:.2f}, "
                f"level={rule_result.level.value}, "
                f"content_type={rule_result.content_type.value}, "
                f"time={rule_result.analysis_time_ms}ms"
            )
            
            # Phase 3: Escalation decision (2-5ms)
            escalation_decision = await self.escalation_criteria.should_escalate(
                rule_result, request_text, context
            )
            
            final_result = rule_result
            
            # Phase 4: LLM escalation if needed (150-300ms future)
            if escalation_decision.should_escalate:
                logger.info(
                    f"Escalating to LLM: reason={escalation_decision.reason.value}, "
                    f"confidence_gap={escalation_decision.confidence_gap:.3f}"
                )
                
                # Use placeholder for now - will implement actual LLM call later
                llm_result = await self.llm_analyzer.analyze_complexity_with_llm(
                    request_text, context, escalation_decision
                )
                
                final_result = llm_result
                self.metrics.llm_escalation_count += 1
                
                # Log escalation for monitoring and future optimization
                await self._log_escalation_event(request_text, context, escalation_decision, llm_result)
            
            # Phase 5: Cache the result (1-2ms)
            self.cache_service.cache_result(request_text, context, final_result)
            
            # Update performance metrics
            total_time = int((time.time() - total_start_time) * 1000)
            self._update_metrics(total_time)
            
            logger.debug(
                f"Complexity analysis complete: "
                f"score={final_result.score:.2f}, "
                f"level={final_result.level.value}, "
                f"path={final_result.analysis_path.value}, "
                f"total_time={total_time}ms"
            )
            
            return final_result
            
        except Exception as e:
            logger.error(f"Complexity analysis failed: {str(e)}", exc_info=True)
            
            # Return safe default on error
            return self._create_fallback_result(request_text, context, total_start_time)
    
    def analyze_complexity_sync(
        self, 
        request_text: str, 
        context: RequestContext
    ) -> Tuple[float, str, str]:
        """
        Synchronous complexity analysis for backward compatibility.
        
        Note: This only uses rule-based analysis to maintain sync behavior.
        For full analysis including LLM escalation, use analyze_complexity().
        
        Returns:
            tuple: (complexity_score, content_type, reasoning)
        """
        
        try:
            # Check cache first
            cached_result = self.cache_service.get_cached_result(request_text, context)
            if cached_result:
                return (
                    cached_result.score,
                    cached_result.content_type.value,
                    cached_result.reasoning
                )
            
            # Rule-based analysis only (sync)
            rule_result = self.rule_analyzer.analyze_complexity(request_text, context)
            
            # Cache the result
            self.cache_service.cache_result(request_text, context, rule_result)
            
            return (
                rule_result.score,
                rule_result.content_type.value,
                rule_result.reasoning
            )
            
        except Exception as e:
            logger.error(f"Sync complexity analysis failed: {str(e)}")
            # Safe fallback
            return (0.5, "general", f"fallback_error:{str(e)[:50]}")
    
    async def _log_escalation_event(
        self,
        request_text: str,
        context: RequestContext,
        escalation_decision,
        llm_result: ComplexityResult
    ):
        """
        Log escalation events for monitoring and optimization.
        
        This helps us:
        1. Monitor escalation rates across different entity types
        2. Optimize escalation thresholds
        3. Track cost impact of escalations
        4. Identify patterns that need better rules
        """
        try:
            # TODO: Implement proper escalation logging
            # For now, just structured logging
            
            escalation_data = {
                'entity_type': context.entity_type,  # platform_chat, agent_session, workflow_execution, workspace_chat
                'organization_id': context.organization_id,
                'escalation_reason': escalation_decision.reason.value,
                'rule_confidence': escalation_decision.actual_confidence,
                'llm_confidence': llm_result.confidence,
                'complexity_change': llm_result.score - 0.5,  # Assuming rule gave 0.5 baseline
                'estimated_cost': float(escalation_decision.estimated_llm_cost) if escalation_decision.estimated_llm_cost else 0,
                'request_length': len(request_text),
                'has_context': bool(context.conversation_history or context.rag_documents)
            }
            
            logger.debug(f"ESCALATION_EVENT: {escalation_data}")
            
            # Future: Store in dedicated escalation metrics table
            # This will help us optimize the system over time
            
        except Exception as e:
            logger.debug(f"Failed to log escalation event: {e}")
    
    def _update_metrics(self, total_time_ms: int):
        """Update running performance metrics"""
        
        # Update average analysis time
        total_analyses = self.metrics.total_requests
        if total_analyses > 0:
            current_avg = self.metrics.avg_analysis_time_ms
            self.metrics.avg_analysis_time_ms = (
                (current_avg * (total_analyses - 1) + total_time_ms) / total_analyses
            )
    
    def _create_fallback_result(
        self, 
        request_text: str, 
        context: RequestContext,
        start_time: float
    ) -> ComplexityResult:
        """Create safe fallback result on analysis failure"""
        
        from .types import ComplexityLevel, AnalysisPath, ContentType
        
        # Simple fallback based on length
        score = min(0.7, len(request_text) / 1000)  # Cap at 0.7
        
        return ComplexityResult(
            score=score,
            level=ComplexityLevel.MEDIUM,
            confidence=0.6,  # Low confidence due to error
            reasoning="fallback_on_error",
            analysis_path=AnalysisPath.RULE_BASED,
            analysis_time_ms=int((time.time() - start_time) * 1000),
            content_type=ContentType.GENERAL
        )
    
    def get_performance_metrics(self) -> dict:
        """
        Get comprehensive performance metrics for monitoring.
        
        Useful for:
        - Monitoring escalation rates across entity types
        - Optimizing cache performance
        - Tracking analysis speed
        - Understanding usage patterns
        """
        
        rule_stats = self.rule_analyzer.get_performance_stats()
        cache_stats = self.cache_service.get_cache_stats()
        
        return {
            'total_requests': self.metrics.total_requests,
            'rule_based_count': self.metrics.rule_based_count,
            'llm_escalation_count': self.metrics.llm_escalation_count,
            'cache_hits': self.metrics.cache_hits,
            'escalation_rate_percent': self.metrics.escalation_rate,
            'cache_hit_rate_percent': self.metrics.cache_hit_rate,
            'avg_analysis_time_ms': round(self.metrics.avg_analysis_time_ms, 2),
            'rule_analyzer_stats': rule_stats,
            'cache_stats': cache_stats
        }
    
    def clear_cache(self, organization_id: str = None) -> bool:
        """Clear complexity analysis cache"""
        return self.cache_service.clear_cache(organization_id)


# Convenience function for backward compatibility
def analyze_complexity(text: str, context: RequestContext) -> Tuple[float, str, str]:
    """
    Backward-compatible complexity analysis function.
    
    This maintains the original signature for existing code.
    """
    analyzer = EnhancedComplexityAnalyzer()
    return analyzer.analyze_complexity_sync(text, context)