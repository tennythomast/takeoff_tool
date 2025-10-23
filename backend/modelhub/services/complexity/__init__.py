# backend/modelhub/services/complexity/__init__.py
"""
Complexity analysis system for intelligent model routing.

This module provides both serial and parallel complexity analyzers:
- EnhancedComplexityAnalyzer: Original serial implementation (15-20ms)
- ParallelComplexityAnalyzer: New parallel implementation (8-12ms)

Use the get_complexity_analyzer() function to get the appropriate analyzer
based on the feature flag configuration.
"""
import os
from typing import Union

from .analyzer import EnhancedComplexityAnalyzer
from .parallel_analyzer import ParallelComplexityAnalyzer
from .types import (
    ComplexityResult, 
    RequestContext, 
    ComplexityLevel,
    AnalysisPath,
    ContentType,
    EscalationReason,
    ComponentResult,
    ParallelAnalysisConfig,
    FastPathResult
)
from .cache import ComplexityCacheService
from .escalation import QwenComplexityAnalyzer, LLMEscalationCriteria
from .rule_analyzer import RuleBasedComplexityAnalyzer

# Feature flag for parallel analyzer (can be set via environment variable)
USE_PARALLEL_ANALYZER = os.environ.get('USE_PARALLEL_COMPLEXITY_ANALYZER', 'false').lower() == 'true'


def get_complexity_analyzer() -> Union[EnhancedComplexityAnalyzer, ParallelComplexityAnalyzer]:
    """
    Get the appropriate complexity analyzer based on feature flag.
    
    Returns:
        EnhancedComplexityAnalyzer: Serial implementation (default)
        ParallelComplexityAnalyzer: Parallel implementation (if enabled)
    """
    return ParallelComplexityAnalyzer()



# Backward compatibility function
async def analyze_complexity(text: str, context: RequestContext) -> ComplexityResult:
    """
    Backward-compatible complexity analysis function.
    
    This maintains the original signature for existing code while
    automatically using the appropriate analyzer based on feature flags.
    """
    analyzer = get_complexity_analyzer()
    return await analyzer.analyze_complexity(text, context)


# Export all public classes and functions
__all__ = [
    # Main analyzers
    'EnhancedComplexityAnalyzer',
    'ParallelComplexityAnalyzer',
    'get_complexity_analyzer',
    'analyze_complexity',
    
    # Supporting classes
    'ComplexityCacheService',
    'QwenComplexityAnalyzer',
    'LLMEscalationCriteria',
    'RuleBasedComplexityAnalyzer',
    
    # Types and enums
    'ComplexityResult',
    'RequestContext',
    'ComplexityLevel',
    'AnalysisPath',
    'ContentType',
    'EscalationReason',
    'ComponentResult',
    'ParallelAnalysisConfig',
    'FastPathResult',
    
    # Feature flag
    'USE_PARALLEL_ANALYZER',
]

# Version info
__version__ = '2.0.0'
__author__ = 'AI Cost Optimizer Team'

# Package level configuration
import logging
logger = logging.getLogger(__name__)

def get_version_info():
    """Get version and capability information"""
    return {
        'version': __version__,
        'features': [
            'rule_based_analysis',
            'llm_escalation_framework', 
            'intelligent_caching',
            'multi_entity_support',
            'performance_monitoring',
            'confidence_scoring',
            'parallel_complexity_analysis'
        ],
        'entity_types_supported': [
            'platform_chat',
            'agent_session', 
            'workflow_execution',
            'workspace_chat',
            'rag_query'
        ],
        'performance_targets': {
            'rule_based_time_ms': '5-15',
            'llm_escalation_time_ms': '150-300',
            'cache_hit_time_ms': '1-2',
            'rule_based_accuracy': '85-90%',
            'llm_escalation_accuracy': '95%+',
            'escalation_rate': '15%',
            'parallel_analysis_time_ms': '8-12'
        }
    }