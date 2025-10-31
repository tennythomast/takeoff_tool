"""
Prompts module for takeoff extraction
"""

from .base import BasePrompt
from .trades.concrete_prompts import ConcreteExtractionPrompt
from .components.rules import get_combined_rules, UNIVERSAL_EXTRACTION_RULES

__all__ = [
    'BasePrompt',
    'ConcreteExtractionPrompt',
    'get_combined_rules',
    'UNIVERSAL_EXTRACTION_RULES',
]