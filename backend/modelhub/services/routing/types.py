# backend/modelhub/services/routing/types.py
"""
Types and data structures for the intelligent routing system.
Supports multiple entity types: platform_chat, agent_session, workflow_execution, workspace_chat
"""
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal


class OptimizationStrategy(Enum):
    """Optimization strategies for model selection"""
    COST_FIRST = "cost_first"
    BALANCED = "balanced" 
    QUALITY_FIRST = "quality_first"
    PERFORMANCE_FIRST = "performance_first"


class EntityType(Enum):
    """Supported entity types for routing"""
    PLATFORM_CHAT = "platform_chat"        # General platform conversations
    AGENT_SESSION = "agent_session"        # Agent-based interactions
    WORKFLOW_EXECUTION = "workflow_execution"  # Agentic workflow processing  
    WORKSPACE_CHAT = "workspace_chat"      # Workspace-specific conversations
    RAG_QUERY = "rag_query"               # RAG-enhanced queries
    PROMPT_SESSION = "prompt_session"      # Legacy prompt sessions


@dataclass
class RoutingDecision:
    """Represents a routing decision with full metadata"""
    selected_model: str
    selected_provider: str
    api_type: str
    confidence_score: float
    reasoning: str
    estimated_cost: Decimal
    estimated_tokens: int
    complexity_score: float
    content_type: str
    fallback_chain: List[Tuple[str, str]]  # [(provider, model), ...]
    decision_time_ms: int
    session_sticky: bool = False
    api_key_source: Optional[str] = None  # 'org' or 'dataelan'
    cost_protection_applied: bool = False
    entity_type: Optional[str] = None
    organization_strategy: Optional[str] = None


@dataclass
class RequestContext:
    """Enhanced context for routing decisions across all entity types"""
    
    # Core identification
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    
    # Entity-specific context
    entity_type: str = EntityType.PLATFORM_CHAT.value
    entity_id: Optional[str] = None  # Could be agent_id, workflow_id, etc.
    
    # BACKWARD COMPATIBILITY: Keep prompt_id for existing code
    prompt_id: Optional[str] = None  # ✅ Keep this for prompt-related functionality
    
    # Request specifics
    max_tokens: int = 1000
    model_type: str = 'TEXT'
    
    # Context data (entity-agnostic)
    conversation_history: Optional[List[Dict]] = None
    rag_documents: Optional[List[Dict]] = None
    user_preferences: Optional[Dict] = None
    
    # Performance and cost hints
    require_fast_response: bool = False
    cost_sensitive: bool = False  
    quality_critical: bool = False
    
    # Entity-specific metadata
    metadata: Optional[Dict] = None
    
    # BACKWARD COMPATIBILITY PROPERTIES
    @property
    def complexity(self) -> str:
        """Legacy property for backward compatibility"""
        return "medium"  # Default value for existing code


@dataclass
class ModelCandidate:
    """Represents a candidate model for routing"""
    provider: str
    model: str
    api_type: str
    cost_input: float
    cost_output: float
    context_window: int
    capabilities: List[str]
    api_key: str
    api_key_source: str
    config: Dict
    cost_protection: Dict
    
    def calculate_estimated_cost(self, estimated_tokens: int) -> Decimal:
        """Calculate estimated cost for this model"""
        input_tokens = estimated_tokens * 0.7  # Rough estimate
        output_tokens = estimated_tokens * 0.3
        
        cost = (
            (input_tokens / 1000 * self.cost_input) +
            (output_tokens / 1000 * self.cost_output)
        )
        return Decimal(str(cost))
    
    def can_handle_request(self, context: RequestContext, complexity_score: float) -> bool:
        """Check if this model can handle the request"""
        
        # Check context window
        if context.max_tokens > self.context_window:
            return False
        
        # Check complexity capabilities
        if complexity_score > 0.8 and 'advanced_reasoning' not in self.capabilities:
            return False
        
        # Entity-specific capability checks
        if context.entity_type == EntityType.WORKFLOW_EXECUTION.value:
            if 'function_calling' not in self.capabilities:
                return False
        
        return True


@dataclass
class SessionState:
    """Session state for stickiness decisions"""
    current_provider: Optional[str] = None
    current_model: Optional[str] = None
    message_count: int = 0
    avg_complexity: float = 0.5
    last_switch_time: float = 0
    entity_type: str = EntityType.PLATFORM_CHAT.value
    total_cost: Decimal = Decimal('0')
    performance_score: float = 1.0


@dataclass
class RoutingMetrics:
    """Metrics for routing decisions"""
    total_requests: int = 0
    rule_based_decisions: int = 0
    fallback_decisions: int = 0
    session_sticky_decisions: int = 0
    cost_protection_triggers: int = 0
    avg_decision_time_ms: float = 0.0
    
    # Entity-specific metrics
    entity_type_breakdown: Dict[str, int] = None
    
    def __post_init__(self):
        if self.entity_type_breakdown is None:
            self.entity_type_breakdown = {}
    
    @property
    def rule_based_rate(self) -> float:
        """Percentage of rule-based decisions"""
        if self.total_requests == 0:
            return 0.0
        return (self.rule_based_decisions / self.total_requests) * 100
    
    @property
    def stickiness_rate(self) -> float:
        """Percentage of session sticky decisions"""
        if self.total_requests == 0:
            return 0.0
        return (self.session_sticky_decisions / self.total_requests) * 100