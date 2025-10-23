# context_manager/utils.py

import hashlib
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


def count_tokens(text: str) -> int:
    """
    Simple token counting utility
    
    In production, replace with tiktoken or actual model tokenizer
    This is a reasonable approximation for planning purposes
    """
    if not text:
        return 0
    
    # Rough approximation: 1 token per 4 characters
    # This works reasonably well for English text
    return len(text) // 4


async def get_model_context_window(model: str) -> int:
    """
    Get context window size for a model from ModelHub
    
    Centralized model capability mapping using ModelHub as source of truth
    """
    try:
        # Import here to avoid circular imports
        from modelhub.models import Model
        
        # Parse provider and model from the model string
        provider_slug, model_name = _parse_model_string(model)
        
        # Get model from ModelHub
        try:
            model_obj = await Model.get_model_async(provider_slug, model_name)
            context_window = model_obj.context_window
            
            logger.debug(f"Got context window for {model}: {context_window} tokens from ModelHub")
            return context_window
            
        except Model.DoesNotExist:
            logger.warning(f"Model '{model}' not found in ModelHub, using fallback detection")
            return _get_fallback_context_window(model)
            
    except Exception as e:
        logger.warning(f"Failed to get context window from ModelHub for '{model}': {str(e)}")
        return _get_fallback_context_window(model)


def _parse_model_string(model: str) -> tuple[str, str]:
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


def _get_fallback_context_window(model: str) -> int:
    """
    Fallback context window detection when ModelHub lookup fails
    
    Uses hardcoded values as backup - should rarely be used
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


async def get_embedding_vector(content: str, organization_id: str) -> Optional[str]:
    """
    Generate embedding vector for content
    
    Placeholder for vector embedding integration
    In Phase 2, we'll use simple hashing, upgrade to real embeddings later
    """
    try:
        # For Phase 2: Simple content hash as vector ID
        # In production: Use actual embedding service (OpenAI, Sentence Transformers, etc.)
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]
        
        # TODO: Replace with actual vector embedding
        # Example:
        # from sentence_transformers import SentenceTransformer
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # embedding = model.encode(content)
        # vector_id = await store_vector_in_qdrant(embedding, organization_id)
        
        return f"vec_{content_hash}"
        
    except Exception as e:
        logger.warning(f"Failed to generate embedding: {str(e)}")
        return None


def clean_content_for_summary(content: str) -> str:
    """
    Clean and prepare content for summarization
    
    Removes noise and formatting that doesn't add value to summaries
    """
    if not content:
        return ""
    
    # Remove excessive whitespace
    cleaned = ' '.join(content.split())
    
    # Remove very short lines that are likely noise
    lines = cleaned.split('\n')
    meaningful_lines = [line.strip() for line in lines if len(line.strip()) > 5]
    
    if meaningful_lines:
        return '\n'.join(meaningful_lines)
    else:
        return cleaned  # Return original if no meaningful lines found


def calculate_cost_savings(cache_hits: int, average_generation_cost: Decimal) -> Decimal:
    """
    Calculate cost savings from caching
    
    Args:
        cache_hits: Number of cache hits
        average_generation_cost: Average cost to generate a summary
        
    Returns:
        Total cost savings from caching
    """
    return Decimal(str(cache_hits)) * average_generation_cost


def format_context_for_display(context_content: str, max_length: int = 500) -> str:
    """
    Format context content for display in admin/debugging
    
    Truncates long content and adds helpful formatting
    """
    if not context_content:
        return "No content"
    
    if len(context_content) <= max_length:
        return context_content
    
    truncated = context_content[:max_length]
    return "{0}... (truncated, total length: {1} chars)".format(truncated, len(context_content))


def validate_organization_access(organization_id: str, user_org_id: str) -> bool:
    """
    Validate that user has access to organization data
    
    Security utility for multi-tenant access control
    """
    # Simple validation - in production, implement proper RBAC
    return organization_id == user_org_id


def get_tier_limits(tier: str) -> Dict[str, Any]:
    """
    Get limits and capabilities for a subscription tier
    
    Centralized tier configuration
    """
    TIER_LIMITS = {
        'starter': {
            'session_retention_days': 7,
            'summary_cache_retention_days': 7,
            'max_summarization_cost_per_day': Decimal('1.00'),
            'max_context_tokens': 2000,
            'cleanup_threshold': 0.5,
            'features': ['basic_context', 'simple_cleanup']
        },
        'pro': {
            'session_retention_days': 30,
            'summary_cache_retention_days': 14,
            'max_summarization_cost_per_day': Decimal('5.00'),
            'max_context_tokens': 4000,
            'cleanup_threshold': 0.3,
            'features': ['advanced_context', 'smart_cleanup', 'analytics']
        },
        'team': {
            'session_retention_days': 90,
            'summary_cache_retention_days': 30,
            'max_summarization_cost_per_day': Decimal('25.00'),
            'max_context_tokens': 6000,
            'cleanup_threshold': 0.2,
            'features': ['premium_context', 'team_sharing', 'advanced_analytics']
        },
        'enterprise': {
            'session_retention_days': 365,
            'summary_cache_retention_days': 90,
            'max_summarization_cost_per_day': Decimal('100.00'),
            'max_context_tokens': 8000,
            'cleanup_threshold': 0.1,
            'features': ['unlimited_context', 'custom_retention', 'white_glove_support', 'audit_logs']
        }
    }
    
    return TIER_LIMITS.get(tier, TIER_LIMITS['starter'])


class PerformanceMonitor:
    """
    Simple performance monitoring utility
    
    Tracks key metrics for optimization
    """
    
    def __init__(self):
        self.metrics = {
            'context_preparations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'fresh_summaries': 0,
            'incremental_updates': 0,
            'full_context_uses': 0,
            'total_cost': Decimal('0.00'),
            'total_time_ms': 0
        }
    
    def record_context_preparation(self, 
                                 strategy: str,
                                 cost: Decimal,
                                 time_ms: int,
                                 cache_hit: bool = False):
        """Record a context preparation event"""
        self.metrics['context_preparations'] += 1
        self.metrics['total_cost'] += cost
        self.metrics['total_time_ms'] += time_ms
        
        if cache_hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
        
        if strategy == 'full_context':
            self.metrics['full_context_uses'] += 1
        elif strategy == 'fresh_summary':
            self.metrics['fresh_summaries'] += 1
        elif strategy == 'incremental_summary':
            self.metrics['incremental_updates'] += 1
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_cache_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        if total_cache_requests == 0:
            return 0.0
        return self.metrics['cache_hits'] / total_cache_requests
    
    def get_average_cost(self) -> Decimal:
        """Calculate average cost per preparation"""
        if self.metrics['context_preparations'] == 0:
            return Decimal('0.00')
        return self.metrics['total_cost'] / self.metrics['context_preparations']
    
    def get_average_time(self) -> float:
        """Calculate average time per preparation"""
        if self.metrics['context_preparations'] == 0:
            return 0.0
        return self.metrics['total_time_ms'] / self.metrics['context_preparations']
    
    def get_full_context_percentage(self) -> float:
        """Calculate percentage of requests using full context"""
        if self.metrics['context_preparations'] == 0:
            return 0.0
        return (self.metrics['full_context_uses'] / self.metrics['context_preparations']) * 100
    
    def reset(self):
        """Reset all metrics"""
        for key in self.metrics:
            if isinstance(self.metrics[key], Decimal):
                self.metrics[key] = Decimal('0.00')
            else:
                self.metrics[key] = 0


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def log_performance_metrics():
    """Log current performance metrics"""
    metrics = performance_monitor.metrics
    logger.info(f"Performance Metrics: "
               f"Preparations: {metrics['context_preparations']}, "
               f"Cache Hit Rate: {performance_monitor.get_cache_hit_rate():.2%}, "
               f"Full Context: {performance_monitor.get_full_context_percentage():.1f}%, "
               f"Avg Cost: ${performance_monitor.get_average_cost():.4f}, "
               f"Avg Time: {performance_monitor.get_average_time():.0f}ms")


class ContextValidator:
    """
    Validation utilities for context operations
    
    Ensures data integrity and proper formatting
    """
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """Validate session ID format"""
        if not session_id or not isinstance(session_id, str):
            return False
        
        # Must be reasonable length and contain valid characters
        if len(session_id) < 8 or len(session_id) > 128:
            return False
        
        return True
    
    @staticmethod
    def validate_entity_id(entity_id: str) -> bool:
        """Validate entity ID format"""
        if not entity_id or not isinstance(entity_id, str):
            return False
        
        # Must be reasonable length
        if len(entity_id) < 8 or len(entity_id) > 128:
            return False
        
        return True
    
    @staticmethod
    def validate_organization_id(organization_id: str) -> bool:
        """Validate organization ID format"""
        if not organization_id or not isinstance(organization_id, str):
            return False
        
        # Must be reasonable length
        if len(organization_id) < 8 or len(organization_id) > 128:
            return False
        
        return True
    
    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """Validate model name format"""
        if not model_name or not isinstance(model_name, str):
            return False
        
        # Must be reasonable length and contain valid characters
        if len(model_name) < 3 or len(model_name) > 100:
            return False
        
        # Allow alphanumeric, hyphens, underscores, dots, and slashes
        import re
        if not re.match(r'^[a-zA-Z0-9\-_./]+$', model_name):
            return False
        
        return True
    
    @staticmethod
    def validate_message_content(content: str) -> bool:
        """Validate message content"""
        if not content or not isinstance(content, str):
            return False
        
        # Must have reasonable length
        if len(content) > 100000:  # 100KB limit
            return False
        
        return True


# Create validator instance
validator = ContextValidator()