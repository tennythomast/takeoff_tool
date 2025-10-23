# backend/modelhub/services/complexity/parallel_analyzer.py
"""
Parallel complexity analyzer that processes multiple analysis components simultaneously
for improved performance and accuracy through consensus-based decision making.
"""
import asyncio
import time
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .types import (
    ComplexityResult, RequestContext, ComponentResult, 
    ParallelAnalysisConfig, FastPathResult, ComplexityLevel,
    AnalysisPath, ContentType, EscalationReason
)
from .cache import ComplexityCacheService
from .escalation import QwenComplexityAnalyzer

logger = logging.getLogger(__name__)


class ParallelComplexityAnalyzer:
    """
    Parallel complexity analyzer that runs multiple analysis components simultaneously.
    
    Architecture:
    1. Fast-path checks (synchronous, <1ms)
    2. Cache lookup
    3. Parallel execution of 4 components:
       - Pattern Analysis
       - Content Type Detection  
       - Context Factors Analysis
       - Escalation Pattern Matching
    4. Weighted consensus with conflict resolution
    5. Progressive enhancement (early return if high confidence)
    6. LLM escalation if needed
    
    Performance Targets:
    - Average latency: 8-12ms (down from 15-20ms)
    - P95 latency: <15ms
    - Escalation rate: 12-18%
    - Cache hit rate: >40%
    """
    
    def __init__(self, config: Optional[ParallelAnalysisConfig] = None):
        self.config = config or ParallelAnalysisConfig()
        self.cache_service = ComplexityCacheService()
        self.llm_analyzer = QwenComplexityAnalyzer()
        
        # Thread pool for CPU-bound analysis tasks
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="complexity-")
        
        # Fast-path patterns (compiled for performance)
        self._compile_fast_path_patterns()
        
        logger.debug("ParallelComplexityAnalyzer initialized with config: %s", self.config)
    
    def _compile_fast_path_patterns(self):
        """Compile regex patterns for fast-path optimization"""
        self.fast_patterns = {
            'single_word': re.compile(r'^\s*\w+\s*[?!.]?\s*$'),
            'greetings': re.compile(r'^\s*(hi|hello|hey|thanks?|thank\s+you|bye|goodbye)\s*[!.]?\s*$', re.IGNORECASE),
            'basic_math': re.compile(r'^\s*\d+\s*[\+\-\*\/]\s*\d+\s*\??\s*$'),
            'acknowledgments': re.compile(r'^\s*(ok|okay|yes|no|sure|got\s+it|understood)\s*[!.]?\s*$', re.IGNORECASE)
        }
    
    async def analyze_complexity(self, request_text: str, context: RequestContext) -> ComplexityResult:
        """
        Main entry point for parallel complexity analysis.
        
        Args:
            request_text: The text to analyze
            context: Request context with metadata
            
        Returns:
            ComplexityResult with parallel analysis metadata
        """
        start_time = time.time()
        logger.info("Starting parallel complexity analysis")
        
        try:
            # 1. Fast-path checks (synchronous, <1ms)
            fast_result = self._check_fast_path(request_text)
            if fast_result.matched:
                logger.info("Fast path matched for simple request")
                result = self._create_fast_path_result(fast_result, start_time)
                await self._cache_result(request_text, context, result)
                return result
            
            logger.info("Fast path not matched, launching parallel analysis components")
            
            # 2. Check cache
            cached_result = await self._check_cache(request_text, context)
            if cached_result:
                logger.info("Cache hit for complexity analysis")
                cached_result.cache_hit = True
                return cached_result
            
            # 3. Launch parallel analysis
            logger.info("Running parallel analysis components")
            component_results = await self._run_parallel_analysis(request_text, context)
            logger.info(f"Completed {len(component_results)} parallel analysis components")
            
            # 4. Apply weighted consensus
            logger.info("Applying weighted consensus to component results")
            consensus_result = self._apply_weighted_consensus(component_results, start_time)
            
            # 5. Check for conflicts and adjust
            logger.info("Applying conflict resolution")
            final_result = self._resolve_conflicts(consensus_result, component_results)
            
            # 6. Determine if LLM escalation needed
            logger.info("Checking escalation criteria")
            if (final_result.confidence < self.config.universal_confidence_threshold or 
                component_results.get('escalation_patterns', {}).get('should_escalate', False)):
                logger.info("Escalating to LLM for complexity analysis")
                final_result = await self._escalate_to_llm(request_text, context, final_result)
            
            # 7. Cache and return
            logger.info("Caching final complexity result")
            await self._cache_result(request_text, context, final_result)
            
            analysis_time_ms = (time.time() - start_time) * 1000
            logger.info(f"Parallel complexity analysis completed in {analysis_time_ms:.2f}ms")
            final_result.analysis_time_ms = analysis_time_ms
            return final_result
            
        except Exception as e:
            logger.error("Error in parallel complexity analysis: %s", str(e))
            # Fallback to simple result
            return self._create_fallback_result(request_text, start_time, str(e))
    
    def _check_fast_path(self, text: str) -> FastPathResult:
        """
        Fast-path optimization checks that bypass full analysis for obvious cases.
        
        Returns immediately for:
        - Single word queries
        - Greetings  
        - Very long text (>5000 chars)
        - Basic math expressions
        - Simple acknowledgments
        """
        text_len = len(text.strip())
        
        # Very long text
        if text_len > 5000:
            return FastPathResult(
                matched=True,
                pattern_type="long_text",
                score=0.8,
                confidence=0.85,
                reason=f"Text length {text_len} > 5000 chars"
            )
        
        # Single word
        if self.fast_patterns['single_word'].match(text):
            return FastPathResult(
                matched=True,
                pattern_type="single_word",
                score=0.1,
                confidence=0.95,
                reason="Single word query"
            )
        
        # Greetings
        if self.fast_patterns['greetings'].match(text):
            return FastPathResult(
                matched=True,
                pattern_type="greeting",
                score=0.1,
                confidence=0.95,
                reason="Greeting pattern"
            )
        
        # Basic math
        if self.fast_patterns['basic_math'].match(text):
            return FastPathResult(
                matched=True,
                pattern_type="basic_math",
                score=0.15,
                confidence=0.90,
                reason="Basic math expression"
            )
        
        # Acknowledgments
        if self.fast_patterns['acknowledgments'].match(text):
            return FastPathResult(
                matched=True,
                pattern_type="acknowledgment",
                score=0.1,
                confidence=0.95,
                reason="Acknowledgment pattern"
            )
        
        return FastPathResult(
            matched=False,
            pattern_type="none",
            score=0.0,
            confidence=0.0,
            reason="No fast-path match"
        )
    
    async def _run_parallel_analysis(self, text: str, context: RequestContext) -> Dict[str, Any]:
        """
        Run all analysis components in parallel with timeout and progressive enhancement.
        """
        # Create analysis tasks
        tasks = {
            'pattern_analysis': self._analyze_patterns(text),
            'content_detection': self._detect_content_type(text),
            'context_factors': self._analyze_context(context, text),
            'escalation_patterns': self._check_escalation_patterns(text)
        }
        
        # Run with timeout and progressive enhancement
        return await self._gather_with_progressive_return(
            tasks, 
            timeout_ms=self.config.max_analysis_time_ms
        )
    
    async def _gather_with_progressive_return(
        self, 
        tasks: Dict[str, asyncio.Task], 
        timeout_ms: int
    ) -> Dict[str, Any]:
        """
        Gather results with progressive enhancement - return early if high confidence achieved.
        """
        timeout_seconds = timeout_ms / 1000.0
        completed_results = {}
        
        try:
            # Wait for all tasks with timeout
            done, pending = await asyncio.wait(
                tasks.values(),
                timeout=timeout_seconds,
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Collect completed results
            for task_name, task in tasks.items():
                if task in done:
                    try:
                        completed_results[task_name] = await task
                    except Exception as e:
                        logger.debug("Task %s failed: %s", task_name, str(e))
                        completed_results[task_name] = self._create_error_component_result(task_name, str(e))
                else:
                    logger.debug("Task %s timed out", task_name)
                    completed_results[task_name] = self._create_timeout_component_result(task_name)
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                
        except asyncio.TimeoutError:
            logger.debug("Parallel analysis timed out after %dms", timeout_ms)
            # Return whatever we have so far
            for task_name, task in tasks.items():
                if task.done():
                    try:
                        completed_results[task_name] = await task
                    except Exception as e:
                        completed_results[task_name] = self._create_error_component_result(task_name, str(e))
                else:
                    completed_results[task_name] = self._create_timeout_component_result(task_name)
        
        return completed_results
    
    async def _analyze_patterns(self, text: str) -> ComponentResult:
        """Component A: Pattern Analysis"""
        start_time = time.time()
        
        try:
            # Run pattern analysis in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self._analyze_patterns_sync, 
                text
            )
            
            execution_time = (time.time() - start_time) * 1000
            return ComponentResult(
                score=result['score'],
                confidence=result['confidence'],
                signals=result['signals'],
                execution_time_ms=execution_time,
                component_name='pattern_analysis'
            )
            
        except Exception as e:
            logger.error("Pattern analysis failed: %s", str(e))
            return self._create_error_component_result('pattern_analysis', str(e))
    
    def _analyze_patterns_sync(self, text: str) -> Dict[str, Any]:
        """Synchronous pattern analysis logic"""
        text_len = len(text.strip())
        word_count = len(text.split())
        signals = []
        
        # Length-based scoring
        if text_len < 20:
            score = 0.1
            signals.append("very_short_text")
        elif text_len < 100:
            score = 0.2
            signals.append("short_text")
        elif text_len < 500:
            score = 0.4
            signals.append("medium_text")
        else:
            score = 0.7
            signals.append("long_text")
        
        # Word count adjustments
        if word_count == 1:
            score = min(score, 0.15)
            signals.append("single_word")
        elif word_count < 5:
            score = min(score, 0.25)
            signals.append("few_words")
        
        # Pattern-based adjustments
        if '?' in text:
            score += 0.1
            signals.append("question_mark")
        
        if any(word in text.lower() for word in ['analyze', 'explain', 'compare', 'evaluate']):
            score += 0.2
            signals.append("analysis_keywords")
        
        if any(word in text.lower() for word in ['code', 'function', 'class', 'algorithm']):
            score += 0.15
            signals.append("code_keywords")
        
        # Confidence based on pattern clarity
        confidence = 0.8 if len(signals) >= 2 else 0.6
        
        return {
            'score': min(score, 1.0),
            'confidence': confidence,
            'signals': signals
        }
    
    async def _detect_content_type(self, text: str) -> ComponentResult:
        """Component B: Content Type Detection"""
        start_time = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._detect_content_type_sync,
                text
            )
            
            execution_time = (time.time() - start_time) * 1000
            return ComponentResult(
                score=result['score'],
                confidence=result['confidence'],
                signals=result['signals'],
                execution_time_ms=execution_time,
                component_name='content_detection'
            )
            
        except Exception as e:
            logger.error("Content detection failed: %s", str(e))
            return self._create_error_component_result('content_detection', str(e))
    
    def _detect_content_type_sync(self, text: str) -> Dict[str, Any]:
        """Synchronous content type detection logic"""
        text_lower = text.lower()
        signals = []
        score = 0.3  # Default medium complexity
        
        # Code detection
        code_indicators = ['def ', 'function', 'class ', 'import ', 'return ', '{}', '[]', '=>']
        if any(indicator in text for indicator in code_indicators):
            score = 0.6
            signals.append("code_detected")
        
        # Data analysis detection
        data_indicators = ['data', 'analysis', 'chart', 'graph', 'statistics', 'csv', 'dataset']
        if any(indicator in text_lower for indicator in data_indicators):
            score = 0.5
            signals.append("data_analysis")
        
        # Business detection
        business_indicators = ['strategy', 'market', 'revenue', 'business', 'customer', 'roi']
        if any(indicator in text_lower for indicator in business_indicators):
            score = 0.4
            signals.append("business_content")
        
        # Creative detection
        creative_indicators = ['story', 'creative', 'poem', 'write', 'imagine', 'design']
        if any(indicator in text_lower for indicator in creative_indicators):
            score = 0.7
            signals.append("creative_content")
        
        # Technical detection
        technical_indicators = ['technical', 'system', 'architecture', 'database', 'api', 'server']
        if any(indicator in text_lower for indicator in technical_indicators):
            score = 0.6
            signals.append("technical_content")
        
        confidence = 0.8 if signals else 0.5
        
        return {
            'score': score,
            'confidence': confidence,
            'signals': signals
        }
    
    async def _analyze_context(self, context: RequestContext, text: str) -> ComponentResult:
        """Component C: Context Factors Analysis"""
        start_time = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._analyze_context_sync,
                context,
                text
            )
            
            execution_time = (time.time() - start_time) * 1000
            return ComponentResult(
                score=result['score'],
                confidence=result['confidence'],
                signals=result['signals'],
                execution_time_ms=execution_time,
                component_name='context_factors'
            )
            
        except Exception as e:
            logger.error("Context analysis failed: %s", str(e))
            return self._create_error_component_result('context_factors', str(e))
    
    def _analyze_context_sync(self, context: RequestContext, text: str) -> Dict[str, Any]:
        """Synchronous context analysis logic"""
        signals = []
        context_weight = 0.0
        
        # Session history analysis
        if context.conversation_history:
            history_len = len(context.conversation_history)
            if history_len > 10:
                context_weight += 0.2
                signals.append("long_conversation_history")
            elif history_len > 3:
                context_weight += 0.1
                signals.append("medium_conversation_history")
        
        # RAG documents presence
        if context.rag_documents:
            doc_count = len(context.rag_documents)
            if doc_count > 5:
                context_weight += 0.3
                signals.append("many_rag_documents")
            elif doc_count > 0:
                context_weight += 0.15
                signals.append("some_rag_documents")
        
        # Quality requirements
        if context.quality_critical:
            context_weight += 0.2
            signals.append("quality_critical")
        
        # Performance requirements
        if context.require_fast_response:
            context_weight -= 0.1
            signals.append("fast_response_required")
        
        confidence = 0.7 if signals else 0.5
        
        return {
            'score': context_weight,
            'confidence': confidence,
            'signals': signals
        }
    
    async def _check_escalation_patterns(self, text: str) -> ComponentResult:
        """Component D: Escalation Pattern Matching"""
        start_time = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._check_escalation_patterns_sync,
                text
            )
            
            execution_time = (time.time() - start_time) * 1000
            return ComponentResult(
                score=result['escalation_score'],
                confidence=result['confidence'],
                signals=result['patterns_found'],
                execution_time_ms=execution_time,
                component_name='escalation_patterns'
            )
            
        except Exception as e:
            logger.error("Escalation pattern check failed: %s", str(e))
            return self._create_error_component_result('escalation_patterns', str(e))
    
    def _check_escalation_patterns_sync(self, text: str) -> Dict[str, Any]:
        """Synchronous escalation pattern matching logic"""
        text_lower = text.lower()
        patterns_found = []
        escalation_score = 0
        
        # Nuanced language patterns
        nuanced_indicators = ['nuanced', 'subtle', 'complex', 'sophisticated', 'intricate']
        if any(indicator in text_lower for indicator in nuanced_indicators):
            escalation_score += 1
            patterns_found.append("nuanced_language")
        
        # Multi-faceted analysis
        analysis_indicators = ['analyze', 'compare', 'evaluate', 'assess', 'examine']
        if sum(1 for indicator in analysis_indicators if indicator in text_lower) >= 2:
            escalation_score += 1
            patterns_found.append("multi_faceted_analysis")
        
        # Expert knowledge requirements
        expert_indicators = ['expert', 'professional', 'advanced', 'specialized', 'technical']
        if any(indicator in text_lower for indicator in expert_indicators):
            escalation_score += 1
            patterns_found.append("expert_knowledge")
        
        # Context-dependent reasoning
        context_indicators = ['depends', 'context', 'situation', 'circumstances', 'considering']
        if any(indicator in text_lower for indicator in context_indicators):
            escalation_score += 1
            patterns_found.append("context_dependent")
        
        # Creative/subjective tasks
        creative_indicators = ['creative', 'opinion', 'subjective', 'artistic', 'innovative']
        if any(indicator in text_lower for indicator in creative_indicators):
            escalation_score += 1
            patterns_found.append("creative_subjective")
        
        # Complex logical reasoning
        logic_indicators = ['logic', 'reasoning', 'proof', 'theorem', 'hypothesis']
        if any(indicator in text_lower for indicator in logic_indicators):
            escalation_score += 1
            patterns_found.append("complex_reasoning")
        
        # Meta-analysis requests
        meta_indicators = ['meta', 'about', 'analysis of', 'review of', 'critique']
        if any(indicator in text_lower for indicator in meta_indicators):
            escalation_score += 1
            patterns_found.append("meta_analysis")
        
        should_escalate = escalation_score >= 2
        confidence = min(0.9, 0.6 + (escalation_score * 0.1))
        
        return {
            'escalation_score': escalation_score,
            'patterns_found': patterns_found,
            'should_escalate': should_escalate,
            'confidence': confidence
        }
    
    def _apply_weighted_consensus(
        self, 
        component_results: Dict[str, Any], 
        start_time: float
    ) -> ComplexityResult:
        """Apply weighted consensus to combine parallel results"""
        
        # Extract scores and confidences
        scores = {}
        confidences = {}
        all_signals = []
        time_breakdown = {}
        
        for component_name, result in component_results.items():
            if isinstance(result, ComponentResult):
                scores[component_name] = result.score
                confidences[component_name] = result.confidence
                all_signals.extend(result.signals)
                time_breakdown[component_name] = result.execution_time_ms
            elif isinstance(result, dict) and 'escalation_score' in result:
                # Handle escalation patterns result format
                scores[component_name] = result.get('escalation_score', 0) / 7.0  # Normalize to 0-1
                confidences[component_name] = result.get('confidence', 0.5)
                all_signals.extend(result.get('patterns_found', []) or [])
                time_breakdown[component_name] = result.get('execution_time_ms', 0)
        
        # Calculate weighted average score
        weighted_score = 0.0
        weighted_confidence = 0.0
        total_weight = 0.0
        
        for component_name, weight in self.config.consensus_weights.items():
            if component_name in scores:
                weighted_score += scores[component_name] * weight
                weighted_confidence += confidences[component_name] * weight
                total_weight += weight
        
        # Normalize if not all components completed
        if total_weight > 0:
            weighted_score /= total_weight
            weighted_confidence /= total_weight
        
        # Determine complexity level
        if weighted_score < 0.3:
            complexity_level = ComplexityLevel.SIMPLE
        elif weighted_score < 0.7:
            complexity_level = ComplexityLevel.MEDIUM
        else:
            complexity_level = ComplexityLevel.COMPLEX
        
        # Determine content type from signals
        content_type = ContentType.GENERAL
        if 'code_detected' in all_signals:
            content_type = ContentType.CODE
        elif 'data_analysis' in all_signals:
            content_type = ContentType.DATA_ANALYSIS
        elif 'business_content' in all_signals:
            content_type = ContentType.BUSINESS
        elif 'creative_content' in all_signals:
            content_type = ContentType.CREATIVE
        elif 'technical_content' in all_signals:
            content_type = ContentType.TECHNICAL
        
        # Create detailed reasoning with step-by-step analysis
        reasoning_steps = []
        reasoning_steps.append(f"PARALLEL_CONSENSUS_ANALYSIS: {len(component_results)} components completed")
        
        # Log individual component contributions
        for component_name, weight in self.config.consensus_weights.items():
            if component_name in scores:
                component_score = scores[component_name]
                component_confidence = confidences[component_name]
                weighted_contribution = component_score * weight
                reasoning_steps.append(
                    f"{component_name.upper()}: score={component_score:.3f}, confidence={component_confidence:.3f}, "
                    f"weight={weight}, contribution={weighted_contribution:.3f}"
                )
        
        # Log scoring calculation
        reasoning_steps.append(f"WEIGHTED_SCORE_CALCULATION: total_weighted={weighted_score:.3f}, total_weight={total_weight:.3f}")
        
        # Log level determination
        if weighted_score < 0.3:
            level_reasoning = f"LEVEL_DETERMINATION: score={weighted_score:.3f} < 0.3 → SIMPLE"
        elif weighted_score < 0.7:
            level_reasoning = f"LEVEL_DETERMINATION: 0.3 ≤ score={weighted_score:.3f} < 0.7 → MEDIUM"
        else:
            level_reasoning = f"LEVEL_DETERMINATION: score={weighted_score:.3f} ≥ 0.7 → COMPLEX"
        reasoning_steps.append(level_reasoning)
        
        # Log content type determination
        content_type_reasoning = f"CONTENT_TYPE: {content_type.value}"
        if 'code_detected' in all_signals:
            content_type_reasoning += " (code_detected signal)"
        elif 'data_analysis' in all_signals:
            content_type_reasoning += " (data_analysis signal)"
        elif 'business_content' in all_signals:
            content_type_reasoning += " (business_content signal)"
        elif 'creative_content' in all_signals:
            content_type_reasoning += " (creative_content signal)"
        elif 'technical_content' in all_signals:
            content_type_reasoning += " (technical_content signal)"
        else:
            content_type_reasoning += " (default - no specific signals)"
        reasoning_steps.append(content_type_reasoning)
        
        # Log all signals detected
        if all_signals:
            reasoning_steps.append(f"SIGNALS_DETECTED: {', '.join(sorted(all_signals))}")
        else:
            reasoning_steps.append("SIGNALS_DETECTED: none")
        
        # Combine all reasoning steps
        detailed_reasoning = " | ".join(reasoning_steps)
        
        # Create result
        return ComplexityResult(
            score=weighted_score,
            confidence=weighted_confidence,
            level=complexity_level,
            reasoning=detailed_reasoning,
            analysis_path=AnalysisPath.PARALLEL_CONSENSUS,
            analysis_time_ms=(time.time() - start_time) * 1000,
            content_type=content_type,
            signals=list(set(all_signals)),
            analysis_components_completed=list(component_results.keys()),
            component_scores={k: v for k, v in component_results.items() if isinstance(v, ComponentResult)},
            consensus_confidence=weighted_confidence,
            analysis_time_breakdown=time_breakdown
        )
    
    def _resolve_conflicts(
        self, 
        consensus_result: ComplexityResult, 
        component_results: Dict[str, Any]
    ) -> ComplexityResult:
        """Smart conflict resolution when analyzers disagree"""
        
        # Track conflict resolution steps for detailed reasoning
        conflict_steps = []
        original_score = consensus_result.score
        original_confidence = consensus_result.confidence
        
        # Check for conflicting signals
        scores = [r.score for r in component_results.values() if isinstance(r, ComponentResult)]
        if len(scores) >= 2:
            score_range = max(scores) - min(scores)
            conflict_steps.append(f"CONFLICT_CHECK: score_range={score_range:.3f}, threshold={self.config.conflict_detection_threshold}")
            if score_range > self.config.conflict_detection_threshold:
                consensus_result.conflicting_signals_detected = True
                old_confidence = consensus_result.confidence
                consensus_result.confidence *= (1 - self.config.confidence_penalty_conflict)
                conflict_steps.append(f"CONFLICT_DETECTED: confidence_penalty applied {old_confidence:.3f} → {consensus_result.confidence:.3f}")
            else:
                conflict_steps.append("NO_CONFLICT: scores within acceptable range")
        
        # Specific conflict resolution rules
        escalation_result = component_results.get('escalation_patterns', {})
        pattern_result = component_results.get('pattern_analysis')
        content_result = component_results.get('content_detection')
        
        # Check if escalation_result is a dict or ComponentResult
        should_escalate = False
        if isinstance(escalation_result, dict):
            should_escalate = escalation_result.get('should_escalate', False)
        elif hasattr(escalation_result, 'should_escalate'):
            should_escalate = escalation_result.should_escalate
        
        # Rule 1: If escalation patterns detected AND pattern analysis says simple → Trust escalation
        if (should_escalate and 
            pattern_result and pattern_result.score < 0.3):
            old_score = consensus_result.score
            consensus_result.score = max(consensus_result.score, 0.6)
            consensus_result.signals.append("escalation_override")
            conflict_steps.append(f"RULE_1_ESCALATION_OVERRIDE: escalation_detected=True, pattern_score={pattern_result.score:.3f} < 0.3 → score boosted {old_score:.3f} → {consensus_result.score:.3f}")
        else:
            conflict_steps.append(f"RULE_1_ESCALATION_OVERRIDE: not_applied (escalate={should_escalate}, pattern_score={pattern_result.score if pattern_result else 'N/A'})")
        
        # Rule 2: If content type is 'code' AND pattern analysis says simple → Set complexity='medium'
        if (content_result and 'code_detected' in content_result.signals and
            pattern_result and pattern_result.score < 0.3):
            old_score = consensus_result.score
            old_level = consensus_result.level
            consensus_result.score = max(consensus_result.score, 0.5)
            consensus_result.level = ComplexityLevel.MEDIUM
            consensus_result.signals.append("code_complexity_boost")
            conflict_steps.append(f"RULE_2_CODE_BOOST: code_detected=True, pattern_score={pattern_result.score:.3f} < 0.3 → score {old_score:.3f} → {consensus_result.score:.3f}, level {old_level.value} → {consensus_result.level.value}")
        else:
            code_detected = content_result and 'code_detected' in content_result.signals if content_result else False
            conflict_steps.append(f"RULE_2_CODE_BOOST: not_applied (code_detected={code_detected}, pattern_score={pattern_result.score if pattern_result else 'N/A'})")
        
        # Rule 3: If all components agree (within 0.2 range) → Boost confidence
        if not consensus_result.conflicting_signals_detected and len(scores) >= 3:
            old_confidence = consensus_result.confidence
            consensus_result.confidence = min(1.0, consensus_result.confidence * (1 + self.config.confidence_boost_agreement))
            consensus_result.signals.append("high_agreement")
            conflict_steps.append(f"RULE_3_AGREEMENT_BOOST: {len(scores)} components agree → confidence boosted {old_confidence:.3f} → {consensus_result.confidence:.3f}")
        else:
            conflict_steps.append(f"RULE_3_AGREEMENT_BOOST: not_applied (conflicts={consensus_result.conflicting_signals_detected}, components={len(scores)})")
        
        # Add conflict resolution details to reasoning
        if conflict_steps:
            conflict_reasoning = " | ".join(conflict_steps)
            if hasattr(consensus_result, 'reasoning') and consensus_result.reasoning:
                consensus_result.reasoning += f" | CONFLICT_RESOLUTION: {conflict_reasoning}"
            else:
                consensus_result.reasoning = f"CONFLICT_RESOLUTION: {conflict_reasoning}"
        
        return consensus_result
    
    async def _escalate_to_llm(
        self, 
        text: str, 
        context: RequestContext, 
        preliminary_result: ComplexityResult
    ) -> ComplexityResult:
        """Escalate to LLM for final analysis"""
        try:
            logger.info("Escalating to LLM for complexity analysis")
            llm_result = await self.llm_analyzer.analyze_with_llm(text, context)
            
            # Merge LLM result with preliminary result
            llm_result.analysis_components_completed = preliminary_result.analysis_components_completed
            llm_result.component_scores = preliminary_result.component_scores
            llm_result.analysis_time_breakdown = preliminary_result.analysis_time_breakdown
            llm_result.analysis_path = AnalysisPath.LLM_ESCALATION
            
            return llm_result
            
        except Exception as e:
            logger.error("LLM escalation failed: %s", str(e))
            # Return preliminary result with escalation failure noted
            preliminary_result.signals.append("llm_escalation_failed")
            return preliminary_result
    
    def _create_fast_path_result(self, fast_result: FastPathResult, start_time: float) -> ComplexityResult:
        """Create ComplexityResult from fast-path optimization"""
        level = ComplexityLevel.SIMPLE if fast_result.score < 0.3 else ComplexityLevel.MEDIUM
        
        # Create detailed reasoning for fast-path analysis
        reasoning_steps = []
        reasoning_steps.append(f"FAST_PATH_ANALYSIS: pattern_type={fast_result.pattern_type}")
        reasoning_steps.append(f"FAST_PATH_SCORE: {fast_result.score:.3f}")
        reasoning_steps.append(f"FAST_PATH_CONFIDENCE: {fast_result.confidence:.3f}")
        
        if fast_result.score < 0.3:
            level_reasoning = f"LEVEL_DETERMINATION: score={fast_result.score:.3f} < 0.3 → SIMPLE"
        else:
            level_reasoning = f"LEVEL_DETERMINATION: score={fast_result.score:.3f} ≥ 0.3 → MEDIUM"
        reasoning_steps.append(level_reasoning)
        
        reasoning_steps.append(f"ORIGINAL_REASON: {fast_result.reason}")
        reasoning_steps.append("EARLY_RETURN: fast-path optimization applied")
        
        detailed_reasoning = " | ".join(reasoning_steps)
        
        return ComplexityResult(
            score=fast_result.score,
            confidence=fast_result.confidence,
            level=level,
            reasoning=detailed_reasoning,
            analysis_path=AnalysisPath.FAST_PATH,
            analysis_time_ms=(time.time() - start_time) * 1000,
            content_type=ContentType.GENERAL,
            signals=[fast_result.pattern_type],
            analysis_components_completed=["fast_path"],
            early_return_triggered=True
        )
    
    def _create_fallback_result(self, text: str, start_time: float, error: str) -> ComplexityResult:
        """Create fallback result when analysis fails"""
        # Simple heuristic based on text length
        score = min(0.8, len(text) / 1000.0)
        level = ComplexityLevel.MEDIUM
        
        return ComplexityResult(
            score=score,
            confidence=0.3,  # Low confidence due to error
            level=level,
            reasoning="Fallback analysis due to error",
            analysis_path=AnalysisPath.RULE_BASED,
            analysis_time_ms=(time.time() - start_time) * 1000,
            content_type=ContentType.GENERAL,
            signals=["fallback_analysis", "analysis_error"],
            error_message=error
        )
    
    def _create_error_component_result(self, component_name: str, error: str) -> ComponentResult:
        """Create error result for failed component"""
        return ComponentResult(
            score=0.5,  # Default medium complexity
            confidence=0.2,  # Low confidence due to error
            signals=["component_error"],
            execution_time_ms=0.0,
            component_name=component_name
        )
    
    def _create_timeout_component_result(self, component_name: str) -> ComponentResult:
        """Create timeout result for component that didn't complete"""
        return ComponentResult(
            score=0.5,  # Default medium complexity
            confidence=0.3,  # Low confidence due to timeout
            signals=["component_timeout"],
            execution_time_ms=self.config.max_analysis_time_ms,
            component_name=component_name
        )
    
    async def _check_cache(self, text: str, context: RequestContext) -> Optional[ComplexityResult]:
        """Check cache for existing results"""
        try:
            # Make cache service call synchronous since it's not actually async
            cached_result = self.cache_service.get_cached_result(text, context)
            return cached_result
        except Exception as e:
            logger.debug("Cache check failed: %s", str(e))
            return None
    
    async def _cache_result(self, text: str, context: RequestContext, result: ComplexityResult):
        """Cache the analysis result"""
        try:
            # Make cache service call synchronous since it's not actually async
            self.cache_service.cache_result(text, context, result)
        except Exception as e:
            logger.debug("Cache storage failed: %s", str(e))
    
    def __del__(self):
        """Cleanup thread pool on destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
