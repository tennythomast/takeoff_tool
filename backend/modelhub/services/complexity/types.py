# backend/modelhub/services/complexity/types.py
"""
Shared types and data structures for the complexity analysis system.
"""
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import time


class ComplexityLevel(Enum):
    """Complexity levels for routing decisions"""
    SIMPLE = "simple"
    MEDIUM = "medium" 
    COMPLEX = "complex"


class AnalysisPath(Enum):
    """Analysis path taken to determine complexity"""
    RULE_BASED = "rule_based"
    LLM_ESCALATION = "llm_escalation"
    CACHED = "cached"
    PARALLEL_CONSENSUS = "parallel_consensus"
    FAST_PATH = "fast_path"


class ContentType(Enum):
    """Content types for specialized analysis"""
    GENERAL = "general"
    CODE = "code"
    DATA_ANALYSIS = "data_analysis"
    IMAGE = "image"
    BUSINESS = "business"
    CREATIVE = "creative"
    TECHNICAL = "technical"


class EscalationReason(Enum):
    """Reasons for escalating to LLM analysis"""
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING_SIGNALS = "conflicting_signals"
    NUANCED_REQUEST = "nuanced_request"
    CONTEXT_DEPENDENT = "context_dependent"
    NOVEL_PATTERN = "novel_pattern"
    MULTI_DOMAIN = "multi_domain"


@dataclass
class ComponentResult:
    """Result from a single parallel analysis component"""
    score: float
    confidence: float
    signals: List[str]
    execution_time_ms: float
    component_name: str


@dataclass
class ComplexityResult:
    """Result of complexity analysis with full metadata"""
    score: float  # 0.0 - 1.0
    level: ComplexityLevel
    confidence: float  # 0.0 - 1.0
    reasoning: str
    analysis_path: AnalysisPath
    analysis_time_ms: int
    content_type: ContentType
    escalation_reason: Optional[EscalationReason] = None
    pattern_matches: Optional[Dict[str, int]] = None
    context_factors: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    signals: List[str] = field(default_factory=list)
    
    # New fields for parallel analysis
    analysis_components_completed: List[str] = field(default_factory=list)
    component_scores: Dict[str, ComponentResult] = field(default_factory=dict)
    consensus_confidence: float = 0.0
    analysis_time_breakdown: Dict[str, float] = field(default_factory=dict)
    conflicting_signals_detected: bool = False
    early_return_triggered: bool = False
    error_message: Optional[str] = None


@dataclass
class RequestContext:
    """Enhanced context for routing decisions"""
    # Core identification
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    
    # Request specifics
    max_tokens: int = 1000
    prompt_id: Optional[str] = None
    entity_type: str = 'prompt_session'  # 'prompt_session', 'agent_session', 'workflow_execution'
    
    # Context data
    conversation_history: Optional[List[Dict]] = None
    rag_documents: Optional[List[Dict]] = None
    user_preferences: Optional[Dict] = None
    
    # Performance hints
    require_fast_response: bool = False
    cost_sensitive: bool = False
    quality_critical: bool = False


@dataclass
class AnalysisMetrics:
    """Performance metrics for analysis operations"""
    total_requests: int = 0
    rule_based_count: int = 0
    llm_escalation_count: int = 0
    cache_hits: int = 0
    avg_analysis_time_ms: float = 0.0
    accuracy_score: float = 0.0
    
    @property
    def escalation_rate(self) -> float:
        """Percentage of requests escalated to LLM"""
        if self.total_requests == 0:
            return 0.0
        return (self.llm_escalation_count / self.total_requests) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Percentage of cache hits"""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100


class PatternCategory:
    """Categories for pattern-based analysis"""
    
    # High-confidence simple patterns
    GREETINGS = "greetings"
    SINGLE_WORD = "single_word"
    BASIC_FACTS = "basic_facts"
    SIMPLE_REQUESTS = "simple_requests"
    ACKNOWLEDGMENTS = "acknowledgments"
    
    # High-confidence complex patterns
    ANALYSIS_TASKS = "analysis_tasks"
    CODE_GENERATION = "code_generation"
    DOCUMENT_CREATION = "document_creation"
    COMPLEX_REASONING = "complex_reasoning"
    MULTI_STEP_PLANNING = "multi_step_planning"
    
    # Context-aware patterns
    RAG_SIMPLE = "rag_simple"
    RAG_COMPLEX = "rag_complex"
    SESSION_BUILDING = "session_building"
    DOMAIN_SPECIFIC = "domain_specific"
    
    # Escalation trigger patterns
    NUANCED_LANGUAGE = "nuanced_language"
    CONTRADICTORY_SIGNALS = "contradictory_signals"
    CREATIVE_SUBJECTIVE = "creative_subjective"
    EXPERT_KNOWLEDGE = "expert_knowledge"


@dataclass
class CacheKey:
    """Key for complexity caching"""
    text_hash: str
    context_hash: str
    organization_id: Optional[str] = None
    
    def __str__(self) -> str:
        if self.organization_id:
            return f"complexity:{self.organization_id}:{self.text_hash}:{self.context_hash}"
        return f"complexity:global:{self.text_hash}:{self.context_hash}"


@dataclass
class EscalationDecision:
    """Decision about whether to escalate to LLM"""
    should_escalate: bool
    reason: EscalationReason
    confidence_threshold: float
    actual_confidence: float
    organization_strategy: Optional[str] = None
    estimated_llm_cost: Optional[Decimal] = None
    
    @property
    def confidence_gap(self) -> float:
        """How far below threshold the confidence is"""
        return max(0.0, self.confidence_threshold - self.actual_confidence)


@dataclass
class ParallelAnalysisConfig:
    """Configuration for parallel complexity analysis"""
    max_analysis_time_ms: int = 5000
    early_return_threshold: float = 0.90
    consensus_weights: Dict[str, float] = field(default_factory=lambda: {
        'pattern_analysis': 0.30,
        'content_detection': 0.25,
        'context_factors': 0.20,
        'escalation_patterns': 0.15,
        'conflicting_signals': 0.10
    })
    universal_confidence_threshold: float = 0.75
    conflict_detection_threshold: float = 0.3
    confidence_boost_agreement: float = 0.10
    confidence_penalty_conflict: float = 0.20


@dataclass
class FastPathResult:
    """Result from fast-path optimization checks"""
    matched: bool
    pattern_type: str
    score: float
    confidence: float
    reason: str