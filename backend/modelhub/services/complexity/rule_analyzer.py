# backend/modelhub/services/complexity/rule_analyzer.py
"""
High-performance rule-based complexity analyzer.
Handles 85% of requests with <15ms analysis time and >85% accuracy.
"""
import re
import time
import hashlib
from typing import Dict, List, Tuple, Optional
import logging

from .types import (
    ComplexityResult, ComplexityLevel, AnalysisPath, ContentType, 
    RequestContext, PatternCategory, CacheKey
)

logger = logging.getLogger(__name__)


class RuleBasedComplexityAnalyzer:
    """
    High-performance rule-based analyzer for 85% of requests.
    Target: 5-15ms analysis time, 85%+ confidence, 85-90% accuracy.
    """
    
    def __init__(self):
        # Pre-compile all regex patterns for performance
        self._compile_patterns()
        
        # Performance tracking
        self._analysis_count = 0
        self._total_time_ms = 0.0
    
    def _compile_patterns(self):
        """Compile all regex patterns for optimal performance"""
        
        # ============================================
        # HIGH CONFIDENCE SIMPLE PATTERNS (Score: 0.0-0.3)
        # ============================================
        self.SIMPLE_PATTERNS = {
            PatternCategory.GREETINGS: [
                re.compile(r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b', re.I),
                re.compile(r'\b(thanks|thank you|thx|appreciate|cheers)\b', re.I),
                re.compile(r'\b(yes|no|ok|okay|sure|alright|yep|nope)\b', re.I),
                re.compile(r'\b(bye|goodbye|see you|talk later|take care)\b', re.I),
                re.compile(r'\b(please|excuse me|sorry|pardon)\b', re.I)
            ],
            
            PatternCategory.SINGLE_WORD: [
                re.compile(r'^\w{1,15}$'),  # Single word queries
                re.compile(r'^\w+\?$'),     # Single word questions
                re.compile(r'^[a-zA-Z]{1,20}$')  # Single words, no numbers/symbols
            ],
            
            PatternCategory.BASIC_FACTS: [
                re.compile(r'^what is \w+\?$', re.I),
                re.compile(r'^who is \w+\?$', re.I), 
                re.compile(r'^when is \w+\?$', re.I),
                re.compile(r'^where is \w+\?$', re.I),
                re.compile(r'^how much \w+\?$', re.I),
                re.compile(r'^define \w+$', re.I),
                re.compile(r'^meaning of \w+$', re.I)
            ],
            
            PatternCategory.SIMPLE_REQUESTS: [
                re.compile(r'^(show me|give me|tell me) \w+$', re.I),
                re.compile(r'^list \w+$', re.I),
                re.compile(r'^find \w+$', re.I),
                re.compile(r'^help with \w+$', re.I),
                re.compile(r'^explain \w+$', re.I)
            ],
            
            PatternCategory.ACKNOWLEDGMENTS: [
                re.compile(r'\b(got it|understood|makes sense|clear|perfect)\b', re.I),
                re.compile(r'\b(that works|sounds good|looks good)\b', re.I)
            ]
        }
        
        # ============================================
        # HIGH CONFIDENCE COMPLEX PATTERNS (Score: 0.7-1.0)
        # ============================================
        self.COMPLEX_PATTERNS = {
            PatternCategory.ANALYSIS_TASKS: [
                re.compile(r'\b(analyze|analysis|evaluate|assessment|compare|comparison)\b.*\b(and|then|also|additionally)\b', re.I),
                re.compile(r'\b(step by step|step-by-step|walkthrough|break down)\b', re.I),
                re.compile(r'\b(comprehensive|detailed|thorough|in-depth)\b.*\b(analysis|review|report)\b', re.I),
                re.compile(r'\b(examine|investigate|study|research)\b.*\b(patterns|trends|relationships)\b', re.I)
            ],
            
            PatternCategory.CODE_GENERATION: [
                re.compile(r'\b(write|create|generate|build).*\b(code|function|class|script|program)\b', re.I),
                re.compile(r'\b(implement|develop).*\b(algorithm|solution|system)\b', re.I),
                re.compile(r'\b(debug|fix|refactor|optimize).*\b(code|function)\b', re.I),
                re.compile(r'\b(API|endpoint|database|backend|frontend)\b.*\b(implementation|integration)\b', re.I)
            ],
            
            PatternCategory.DOCUMENT_CREATION: [
                re.compile(r'\b(write|create|draft).*\b(essay|article|blog|report|proposal|plan)\b', re.I),
                re.compile(r'\b(documentation|manual|guide|tutorial|handbook)\b', re.I),
                re.compile(r'\bmultiple.*\b(pages|sections|chapters)\b', re.I),
                re.compile(r'\b(business plan|strategy document|requirements document)\b', re.I)
            ],
            
            PatternCategory.COMPLEX_REASONING: [
                re.compile(r'\b(strategy|strategic|planning)\b.*\b(considering|given|based on)\b', re.I),
                re.compile(r'\b(recommendation|suggest|advise).*\b(based on|considering|given)\b', re.I),
                re.compile(r'\b(pros and cons|advantages and disadvantages)\b', re.I),
                re.compile(r'\b(if.*then|assuming.*what|what if.*then)\b', re.I),
                re.compile(r'\b(trade.?offs?|implications|consequences)\b', re.I)
            ],
            
            PatternCategory.MULTI_STEP_PLANNING: [
                re.compile(r'\b(roadmap|timeline|phases|milestones)\b', re.I),
                re.compile(r'\b(first.*then.*finally|step 1.*step 2)\b', re.I),
                re.compile(r'\b(implementation plan|execution strategy)\b', re.I)
            ]
        }
        
        # ============================================
        # CONTEXT-AWARE PATTERNS
        # ============================================
        self.CONTEXT_PATTERNS = {
            PatternCategory.RAG_SIMPLE: [
                re.compile(r'\b(what|who|when|where)\b.*\b(in|from|about)\b', re.I),
                re.compile(r'\b(show|find|get).*\b(document|file|information)\b', re.I),
                re.compile(r'\b(search for|look up|retrieve)\b', re.I)
            ],
            
            PatternCategory.RAG_COMPLEX: [
                re.compile(r'\b(compare|contrast).*\b(across|between).*\b(documents|sources)\b', re.I),
                re.compile(r'\b(synthesize|combine|merge).*\b(information|data)\b', re.I),
                re.compile(r'\b(conflicting|contradictory|different).*\b(sources|documents)\b', re.I),
                re.compile(r'\b(patterns across|themes in|trends from)\b.*\b(documents|sources)\b', re.I)
            ],
            
            PatternCategory.SESSION_BUILDING: [
                re.compile(r'\b(previously|earlier|before|last time)\b', re.I),
                re.compile(r'\b(continue|follow up|building on)\b', re.I),
                re.compile(r'\b(this|that|these|those)\b.*\b(mentioned|discussed|said)\b', re.I),
                re.compile(r'\b(as we discussed|like I said|from our conversation)\b', re.I)
            ]
        }
        
        # ============================================
        # CONTENT TYPE DETECTION PATTERNS
        # ============================================
        self.CONTENT_TYPE_PATTERNS = {
            ContentType.CODE: [
                re.compile(r'```|`.*`', re.I),
                re.compile(r'\b(function|class|import|def|var|let|const|return)\b', re.I),
                re.compile(r'\b(javascript|python|java|c\+\+|html|css|sql|react|node)\b', re.I),
                re.compile(r'\b(api|endpoint|database|server|framework)\b', re.I),
                re.compile(r'\b(debug|error|exception|bug|compile)\b', re.I)
            ],
            
            ContentType.DATA_ANALYSIS: [
                re.compile(r'\b(data|dataset|csv|json|excel|table)\b', re.I),
                re.compile(r'\b(chart|graph|visualization|plot|dashboard)\b', re.I),
                re.compile(r'\b(statistics|analysis|metrics|kpi|analytics)\b', re.I),
                re.compile(r'\b(correlation|regression|trend|pattern)\b', re.I)
            ],
            
            ContentType.BUSINESS: [
                re.compile(r'\b(business|strategy|market|customer|sales|revenue)\b', re.I),
                re.compile(r'\b(plan|proposal|budget|forecast|roi)\b', re.I),
                re.compile(r'\b(meeting|presentation|stakeholder|client)\b', re.I),
                re.compile(r'\b(competitive|market share|growth|profit)\b', re.I)
            ],
            
            ContentType.CREATIVE: [
                re.compile(r'\b(creative|artistic|innovative|original|imaginative)\b', re.I),
                re.compile(r'\b(story|poem|script|novel|writing)\b', re.I),
                re.compile(r'\b(design|artwork|creative brief)\b', re.I),
                re.compile(r'\b(brainstorm|ideate|conceptualize)\b', re.I)
            ],
            
            ContentType.TECHNICAL: [
                re.compile(r'\b(technical|engineering|architecture|system)\b', re.I),
                re.compile(r'\b(specification|requirement|documentation)\b', re.I),
                re.compile(r'\b(infrastructure|deployment|scalability)\b', re.I),
                re.compile(r'\b(performance|optimization|security)\b', re.I)
            ]
        }
        
        # ============================================
        # ESCALATION TRIGGER PATTERNS
        # ============================================
        self.ESCALATION_PATTERNS = {
            'nuanced': [
                re.compile(r'\b(nuanced|subtle|complex relationship|depends on)\b', re.I),
                re.compile(r'\b(considering|taking into account|given that)\b.*\b(however|but|although)\b', re.I),
                re.compile(r'\b(on one hand|on the other hand|alternatively)\b', re.I)
            ],
            
            'multi_faceted': [
                re.compile(r'\b(multiple|several|various).*\b(aspects|factors|considerations)\b', re.I),
                re.compile(r'\b(from different perspectives|various angles)\b', re.I)
            ],
            
            'domain_expertise': [
                re.compile(r'\b(specialized|technical|expert|professional)\b.*\b(knowledge|understanding)\b', re.I),
                re.compile(r'\b(industry|domain|field).*\b(specific|dependent)\b', re.I)
            ],
            
            'contextual': [
                re.compile(r'\b(in this context|given the situation|under these circumstances)\b', re.I),
                re.compile(r'\b(interpretation|perspective|viewpoint)\b', re.I)
            ],
            
            'subjective': [
                re.compile(r'\b(opinion|perspective|subjective|personal)\b', re.I),
                re.compile(r'\b(feel|think|believe|prefer)\b', re.I)
            ]
        }
    
    def analyze_complexity(self, text: str, context: RequestContext) -> ComplexityResult:
        """
        Fast rule-based complexity analysis.
        
        Returns high-confidence results for 85% of cases.
        Low-confidence results should be escalated to LLM.
        """
        start_time = time.time()
        self._analysis_count += 1
        
        # Normalize text for analysis
        text = text.strip()
        text_lower = text.lower()
        char_count = len(text)
        word_count = len(text.split())
        
        # ===========================================
        # PHASE 1: HIGH-CONFIDENCE SIMPLE DETECTION
        # ===========================================
        
        # Very short queries - likely simple
        if char_count < 20:
            simple_score = self._check_pattern_matches(text_lower, self.SIMPLE_PATTERNS)
            if simple_score > 0:
                return self._create_result(
                    score=0.1, 
                    reasoning=f"very_short_simple:chars={char_count},patterns={simple_score}",
                    confidence=0.95,
                    content_type=self._detect_content_type(text_lower),
                    pattern_matches={'simple': simple_score},
                    start_time=start_time
                )
        
        # Basic factual patterns under 100 chars
        if char_count < 100:
            simple_matches = self._check_pattern_matches(text_lower, self.SIMPLE_PATTERNS)
            if simple_matches >= 2:  # Multiple simple indicators
                return self._create_result(
                    score=0.15,
                    reasoning=f"multiple_simple_patterns:{simple_matches}",
                    confidence=0.90,
                    content_type=self._detect_content_type(text_lower),
                    pattern_matches={'simple': simple_matches},
                    start_time=start_time
                )
        
        # ===========================================
        # PHASE 2: HIGH-CONFIDENCE COMPLEX DETECTION  
        # ===========================================
        
        # Long requests are likely complex
        if char_count > 1000:
            complex_matches = self._check_pattern_matches(text_lower, self.COMPLEX_PATTERNS)
            if complex_matches > 0:
                return self._create_result(
                    score=0.85,
                    reasoning=f"long_complex_request:chars={char_count},patterns={complex_matches}",
                    confidence=0.90,
                    content_type=self._detect_content_type(text_lower),
                    pattern_matches={'complex': complex_matches},
                    start_time=start_time
                )
        
        # Multiple complex indicators
        complex_score = self._check_pattern_matches(text_lower, self.COMPLEX_PATTERNS)
        if complex_score >= 3:  # Multiple complex patterns
            return self._create_result(
                score=0.80,
                reasoning=f"multiple_complex_patterns:{complex_score}",
                confidence=0.88,
                content_type=self._detect_content_type(text_lower),
                pattern_matches={'complex': complex_score},
                start_time=start_time
            )
        
        # ===========================================
        # PHASE 3: CONTENT TYPE ANALYSIS
        # ===========================================
        
        content_type = self._detect_content_type(text_lower)
        content_complexity = self._get_content_type_complexity(content_type, char_count, word_count)
        
        if content_complexity['confidence'] > 0.85:
            return self._create_result(
                score=content_complexity['score'],
                reasoning=f"content_type_{content_type.value}:chars={char_count}",
                confidence=content_complexity['confidence'],
                content_type=content_type,
                pattern_matches=content_complexity.get('matches', {}),
                start_time=start_time
            )
        
        # ===========================================
        # PHASE 4: CONTEXT-AWARE ANALYSIS
        # ===========================================
        
        context_complexity = self._analyze_context_complexity(text_lower, context)
        if context_complexity['confidence'] > 0.85:
            return self._create_result(
                score=context_complexity['score'],
                reasoning=f"context_{context_complexity['reason']}",
                confidence=context_complexity['confidence'],
                content_type=content_type,
                context_factors=context_complexity.get('factors', {}),
                start_time=start_time
            )
        
        # ===========================================
        # PHASE 5: LENGTH + PATTERN COMBINATION
        # ===========================================
        
        # Calculate base complexity from length
        if char_count < 50:
            base_score = 0.1
        elif char_count < 200:
            base_score = 0.3
        elif char_count < 500:
            base_score = 0.5
        else:
            base_score = 0.7
        
        # Adjust based on patterns
        simple_matches = self._check_pattern_matches(text_lower, self.SIMPLE_PATTERNS)
        complex_matches = self._check_pattern_matches(text_lower, self.COMPLEX_PATTERNS)
        escalation_matches = self._check_escalation_patterns(text_lower)
        
        final_score = base_score
        confidence = 0.70  # Medium confidence
        reasoning = f"length_based:{base_score:.1f}"
        
        # Strong simple indicators reduce complexity
        if simple_matches > complex_matches and simple_matches >= 1:
            final_score = max(0.1, base_score - 0.3)
            confidence = 0.80
            reasoning = f"simple_patterns_override:s={simple_matches},c={complex_matches}"
        
        # Strong complex indicators increase complexity  
        elif complex_matches > simple_matches and complex_matches >= 1:
            final_score = min(1.0, base_score + 0.3)
            confidence = 0.80
            reasoning = f"complex_patterns_override:c={complex_matches},s={simple_matches}"
        
        # Escalation patterns reduce confidence
        if escalation_matches >= 2:
            confidence = max(0.60, confidence - 0.2)
            reasoning += f",escalation_signals={escalation_matches}"
        
        return self._create_result(
            score=final_score,
            reasoning=reasoning,
            confidence=confidence,
            content_type=content_type,
            pattern_matches={'simple': simple_matches, 'complex': complex_matches, 'escalation': escalation_matches},
            start_time=start_time
        )
    
    def _check_pattern_matches(self, text: str, pattern_dict: Dict) -> int:
        """Count pattern matches across all categories"""
        total_matches = 0
        for category, patterns in pattern_dict.items():
            for pattern in patterns:
                if pattern.search(text):
                    total_matches += 1
        return total_matches
    
    def _check_escalation_patterns(self, text: str) -> int:
        """Count patterns that suggest LLM escalation needed"""
        total_matches = 0
        for category, patterns in self.ESCALATION_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(text):
                    total_matches += 1
        return total_matches
    
    def _detect_content_type(self, text: str) -> ContentType:
        """Detect the primary content type"""
        max_matches = 0
        detected_type = ContentType.GENERAL
        
        for content_type, patterns in self.CONTENT_TYPE_PATTERNS.items():
            matches = sum(1 for pattern in patterns if pattern.search(text))
            if matches > max_matches:
                max_matches = matches
                detected_type = content_type
        
        return detected_type
    
    def _get_content_type_complexity(self, content_type: ContentType, char_count: int, word_count: int) -> Dict:
        """Get complexity based on content type and characteristics"""
        
        # Content type complexity mappings
        type_complexity = {
            ContentType.CODE: {'base': 0.6, 'confidence': 0.85},
            ContentType.DATA_ANALYSIS: {'base': 0.5, 'confidence': 0.80},
            ContentType.BUSINESS: {'base': 0.4, 'confidence': 0.75},
            ContentType.TECHNICAL: {'base': 0.55, 'confidence': 0.80},
            ContentType.CREATIVE: {'base': 0.45, 'confidence': 0.75},
            ContentType.GENERAL: {'base': 0.3, 'confidence': 0.60}
        }
        
        base_info = type_complexity.get(content_type, type_complexity[ContentType.GENERAL])
        
        # Adjust for length and word density
        if char_count > 500:
            score = min(1.0, base_info['base'] + 0.2)
        elif char_count < 100:
            score = max(0.1, base_info['base'] - 0.2)
        else:
            score = base_info['base']
        
        # Adjust for word complexity (words per character ratio)
        if char_count > 0:
            word_density = word_count / char_count
            if word_density < 0.15:  # Very dense text, fewer spaces
                score += 0.1
        
        return {
            'score': score,
            'confidence': base_info['confidence']
        }
    
    def _analyze_context_complexity(self, text: str, context: RequestContext) -> Dict:
        """Analyze complexity based on conversation/RAG context"""
        
        # RAG context complexity
        if context.rag_documents:
            doc_count = len(context.rag_documents)
            rag_complex_matches = self._check_pattern_matches(text, {
                'rag_complex': self.CONTEXT_PATTERNS[PatternCategory.RAG_COMPLEX]
            })
            
            if doc_count > 5 and rag_complex_matches > 0:
                return {
                    'score': 0.75, 
                    'confidence': 0.88, 
                    'reason': 'multi_doc_synthesis',
                    'factors': {'doc_count': doc_count, 'rag_matches': rag_complex_matches}
                }
            elif doc_count > 1 and rag_complex_matches > 0:
                return {
                    'score': 0.60, 
                    'confidence': 0.85, 
                    'reason': 'multi_doc_analysis',
                    'factors': {'doc_count': doc_count, 'rag_matches': rag_complex_matches}
                }
            elif doc_count > 0:
                return {
                    'score': 0.35, 
                    'confidence': 0.80, 
                    'reason': 'single_doc_retrieval',
                    'factors': {'doc_count': doc_count}
                }
        
        # Session context complexity
        if context.conversation_history:
            history_length = len(context.conversation_history)
            session_matches = self._check_pattern_matches(text, {
                'session': self.CONTEXT_PATTERNS[PatternCategory.SESSION_BUILDING]
            })
            
            if history_length > 10 and session_matches > 0:
                return {
                    'score': 0.55, 
                    'confidence': 0.85, 
                    'reason': 'long_session_reference',
                    'factors': {'history_length': history_length, 'session_matches': session_matches}
                }
            elif history_length > 3 and session_matches > 0:
                return {
                    'score': 0.40, 
                    'confidence': 0.80, 
                    'reason': 'session_reference',
                    'factors': {'history_length': history_length, 'session_matches': session_matches}
                }
        
        return {
            'score': 0.3, 
            'confidence': 0.60, 
            'reason': 'insufficient_context'
        }
    
    def _create_result(
        self, 
        score: float, 
        reasoning: str, 
        confidence: float, 
        content_type: ContentType,
        pattern_matches: Optional[Dict] = None,
        context_factors: Optional[Dict] = None,
        start_time: float = None
    ) -> ComplexityResult:
        """Create standardized complexity result"""
        
        # Determine complexity level
        if score < 0.3:
            level = ComplexityLevel.SIMPLE
        elif score < 0.7:
            level = ComplexityLevel.MEDIUM
        else:
            level = ComplexityLevel.COMPLEX
        
        analysis_time = int((time.time() - start_time) * 1000) if start_time else 0
        self._total_time_ms += analysis_time
        
        return ComplexityResult(
            score=score,
            level=level,
            confidence=confidence,
            reasoning=reasoning,
            analysis_path=AnalysisPath.RULE_BASED,
            analysis_time_ms=analysis_time,
            content_type=content_type,
            pattern_matches=pattern_matches,
            context_factors=context_factors,
            cache_hit=False
        )
    
    def get_performance_stats(self) -> Dict:
        """Get analyzer performance statistics"""
        avg_time = self._total_time_ms / self._analysis_count if self._analysis_count > 0 else 0
        
        return {
            'total_analyses': self._analysis_count,
            'average_time_ms': round(avg_time, 2),
            'analyzer_type': 'rule_based'
        }