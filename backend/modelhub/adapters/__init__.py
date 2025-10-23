from .base import BaseLLMAdapter, LLMResponse

__all__ = ['BaseLLMAdapter', 'LLMResponse']

# We're using a unified client approach instead of separate adapters
# The PROVIDER_ADAPTERS dictionary is kept for backward compatibility
PROVIDER_ADAPTERS = {}

