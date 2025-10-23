# context_manager/services/decision_service.py

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextDecision:
    """Decision result from the context decision engine"""
    use_full_context: bool
    target_context_tokens: int
    buffer_tokens: int
    strategy_reason: str
    estimated_cost: Decimal
    quality_score: float


class ContextDecisionService:
    """
    PHASE 2 CORE: Smart Context Decision Engine
    Makes intelligent decisions about full context vs summarization
    
    This is the brain of the system - decides when to use full context
    vs when to summarize based on actual model capabilities from ModelHub
    """
    
    # Cost per 1K tokens for summarization (Mixtral pricing)
    SUMMARIZATION_COST_PER_1K = Decimal('0.0002')
    
    def __init__(self, buffer_percentage: float = 0.2):
        """
        Initialize decision service
        
        Args:
            buffer_percentage: Percentage of context window to reserve for responses
        """
        self.buffer_percentage = buffer_percentage
        
    async def make_context_decision(self, 
                                   conversation_tokens: int,
                                   target_model: str,
                                   preserve_quality: bool = True,
                                   cost_limit: Optional[Decimal] = None) -> ContextDecision:
        """
        PHASE 2 CORE: The revolutionary context decision algorithm
        
        Key Innovation: Always prefer full context when possible, only summarize when necessary
        This is what makes our system unique - we preserve 100% quality when feasible
        
        Args:
            conversation_tokens: Current conversation size in tokens
            target_model: Model we're preparing context for
            preserve_quality: Whether to prioritize quality over cost
            cost_limit: Maximum cost willing to spend on context preparation
            
        Returns:
            ContextDecision with strategy and parameters
        """
        
        # Get model capabilities from ModelHub
        model_context_window = await self.get_model_context_window(target_model)
        buffer_tokens = int(model_context_window * self.buffer_percentage)
        available_context_tokens = model_context_window - buffer_tokens
        
        # DECISION LOGIC: Full context vs Smart summarization
        
        if conversation_tokens <= available_context_tokens:
            # 🎯 OPTIMAL PATH: Full context fits perfectly
            # Zero cost, perfect quality - this is our target for 80%+ of requests
            return ContextDecision(
                use_full_context=True,
                target_context_tokens=conversation_tokens,
                buffer_tokens=buffer_tokens,
                strategy_reason=f"Full context ({conversation_tokens:,} tokens) fits in available space ({available_context_tokens:,} tokens)",
                estimated_cost=Decimal('0.00'),
                quality_score=1.0
            )
        
        # Conversation is too large - need smart summarization
        
        # Calculate estimated summarization cost
        estimated_cost = self._calculate_summarization_cost(conversation_tokens)
        
        # Check cost limits
        if cost_limit and estimated_cost > cost_limit:
            # Cost too high - use aggressive truncation
            truncation_tokens = min(available_context_tokens, int(conversation_tokens * 0.5))
            return ContextDecision(
                use_full_context=False,
                target_context_tokens=truncation_tokens,
                buffer_tokens=buffer_tokens,
                strategy_reason=f"Cost limit (${cost_limit}) exceeded, using truncation",
                estimated_cost=Decimal('0.00'),
                quality_score=0.6
            )
        
        # Smart summarization path
        return ContextDecision(
            use_full_context=False,
            target_context_tokens=available_context_tokens,
            buffer_tokens=buffer_tokens,
            strategy_reason=f"Conversation ({conversation_tokens:,} tokens) exceeds available space, using smart summarization",
            estimated_cost=estimated_cost,
            quality_score=0.85  # High quality with smart summarization
        )
    
    async def get_model_context_window(self, model: str) -> int:
        """
        Get context window for a specific model from ModelHub
        
        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            
        Returns:
            Context window size in tokens
        """
        try:
            # Import here to avoid circular imports
            from modelhub.models import Model
            
            # First, try to parse provider and model from the model string
            provider_slug, model_name = self._parse_model_string(model)
            
            # Get model from ModelHub
            try:
                model_obj = await Model.get_model_async(provider_slug, model_name)
                context_window = model_obj.context_window
                
                logger.debug(f"Got context window for {model}: {context_window} tokens from ModelHub")
                return context_window
                
            except Model.DoesNotExist:
                logger.warning(f"Model '{model}' not found in ModelHub, using fallback detection")
                return self._get_fallback_context_window(model)
                
        except Exception as e:
            logger.warning(f"Failed to get context window from ModelHub for '{model}': {str(e)}")
            return self._get_fallback_context_window(model)
    
    def _parse_model_string(self, model: str) -> tuple[str, str]:
        """
        Parse model string to extract provider and model name
        
        Args:
            model: Model string (e.g., "gpt-4", "claude-3-sonnet", "openai/gpt-4")
            
        Returns:
            (provider_slug, model_name)
        """
        # Handle explicit provider/model format
        if '/' in model:
            parts = model.split('/', 1)
            return parts[0], parts[1]
        
        # Infer provider from model name
        model_lower = model.lower()
        
        if any(prefix in model_lower for prefix in ['gpt-', 'chatgpt', 'text-davinci', 'text-curie']):
            return 'openai', model
        elif any(prefix in model_lower for prefix in ['claude-', 'claude']):
            return 'anthropic', model
        elif any(prefix in model_lower for prefix in ['gemini', 'palm']):
            return 'google', model
        elif any(prefix in model_lower for prefix in ['mixtral', 'mistral']):
            return 'mistral', model
        else:
            # Default to openai for unknown models
            logger.debug(f"Unknown model format '{model}', defaulting to openai provider")
            return 'openai', model
    
    def _get_fallback_context_window(self, model: str) -> int:
        """
        Fallback context window detection when ModelHub lookup fails
        
        Uses hardcoded values as backup
        """
        # Fallback mapping for common models
        FALLBACK_WINDOWS = {
            # OpenAI models
            'gpt-4': 32000,
            'gpt-4-turbo': 128000,
            'gpt-4-32k': 32000,
            'gpt-3.5-turbo': 16000,
            'gpt-3.5-turbo-16k': 16000,
            'gpt-3.5-turbo-instruct': 4000,
            
            # Anthropic models
            'claude-3-sonnet': 200000,
            'claude-3-haiku': 200000,
            'claude-3-opus': 200000,
            'claude-2': 100000,
            'claude-instant': 8000,
            'claude-instant-1': 8000,
            
            # Google models
            'gemini-pro': 32000,
            'palm-2': 8000,
            
            # Mistral models
            'mixtral-8x7b': 32000,
            'mistral-7b': 8000,
        }
        
        # Normalize model name
        normalized_model = model.lower().replace('_', '-')
        
        # Check exact match
        if model in FALLBACK_WINDOWS:
            return FALLBACK_WINDOWS[model]
        
        # Check normalized match
        for known_model, window_size in FALLBACK_WINDOWS.items():
            if normalized_model in known_model or known_model in normalized_model:
                return window_size
        
        # Pattern-based fallback
        if any(pattern in normalized_model for pattern in ['gpt-4', 'claude-3', 'mixtral']):
            return 32000  # Large models
        elif any(pattern in normalized_model for pattern in ['gpt-3.5', 'claude-2', 'gemini']):
            return 16000  # Medium models
        else:
            # Conservative default
            logger.warning(f"Unknown model '{model}', defaulting to 4K context window")
            return 4000
    
    def categorize_model_by_context_size(self, model: str) -> str:
        """
        Categorize model by context window size
        
        Returns:
            'large', 'medium', or 'small'
        """
        context_window = self.get_model_context_window(model)
        
        if context_window >= 32000:
            return 'large'
        elif context_window >= 8000:
            return 'medium'
        else:
            return 'small'
    
    def _calculate_summarization_cost(self, conversation_tokens: int) -> Decimal:
        """
        Calculate estimated cost for summarizing a conversation
        
        Uses Mixtral pricing as our cost-effective summarization model
        """
        # Estimate that we'll process ~1.5x the conversation tokens for summarization
        # (input + summary generation)
        processing_tokens = int(conversation_tokens * 1.5)
        cost_per_token = self.SUMMARIZATION_COST_PER_1K / 1000
        
        estimated_cost = Decimal(str(processing_tokens)) * cost_per_token
        
        # Add small buffer for safety
        return estimated_cost * Decimal('1.1')
    
    async def should_use_cache(self, 
                              conversation_tokens: int,
                              target_model: str,
                              cache_age_hours: int = 0) -> bool:
        """
        Decide whether to use cached summary or generate fresh
        
        Args:
            conversation_tokens: Size of conversation
            target_model: Target model
            cache_age_hours: Age of available cache in hours
            
        Returns:
            True if cache should be used
        """
        
        # Always use fresh cache (< 1 hour old)
        if cache_age_hours < 1:
            return True
        
        # For large conversations, prefer cached summaries even if older
        if conversation_tokens > 10000:
            return cache_age_hours < 24  # 24 hour tolerance for large conversations
        
        # For medium conversations, moderate tolerance
        if conversation_tokens > 5000:
            return cache_age_hours < 12  # 12 hour tolerance
        
        # For small conversations, prefer fresh generation
        return cache_age_hours < 6  # 6 hour tolerance
    
    def get_optimal_summary_allocation(self, target_tokens: int) -> tuple[int, int]:
        """
        Get optimal allocation of tokens between summary and recent messages
        
        Args:
            target_tokens: Total tokens available for context
            
        Returns:
            (summary_tokens, recent_messages_tokens)
        """
        
        # Our proven 40/60 split: 40% summary, 60% recent messages
        summary_tokens = int(target_tokens * 0.4)
        recent_tokens = target_tokens - summary_tokens
        
        # Ensure minimum allocations
        min_summary = 100
        min_recent = 200
        
        if summary_tokens < min_summary:
            summary_tokens = min_summary
            recent_tokens = target_tokens - summary_tokens
        
        if recent_tokens < min_recent:
            recent_tokens = min_recent
            summary_tokens = target_tokens - recent_tokens
        
        return summary_tokens, recent_tokens
    
    async def evaluate_context_quality(self, 
                                      original_tokens: int,
                                      final_tokens: int,
                                      strategy_used: str) -> float:
        """
        Evaluate the quality of context preparation
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        
        if strategy_used == 'full_context':
            return 1.0  # Perfect quality
        
        if strategy_used == 'cached_summary':
            return 0.9  # High quality cached
        
        if strategy_used in ['smart_summary', 'incremental_summary']:
            # Quality based on compression ratio
            compression_ratio = final_tokens / original_tokens if original_tokens > 0 else 0
            base_quality = 0.85
            
            # Adjust based on how much we had to compress
            if compression_ratio > 0.8:
                return base_quality + 0.1  # Light compression
            elif compression_ratio > 0.5:
                return base_quality  # Moderate compression  
            else:
                return base_quality - 0.1  # Heavy compression
        
        # Fallback strategies
        return 0.6