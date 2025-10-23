# backend/modelhub/services/complexity/tests/test_parallel_analyzer.py
"""
Unit tests for the ParallelComplexityAnalyzer.

Tests cover:
- Fast-path optimizations
- Parallel component execution
- Weighted consensus
- Conflict resolution
- Performance benchmarks
- Error handling
"""
import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock

from ..parallel_analyzer import ParallelComplexityAnalyzer
from ..types import (
    RequestContext, ComplexityResult, ComponentResult,
    ParallelAnalysisConfig, FastPathResult, ComplexityLevel,
    AnalysisPath
)


class TestParallelComplexityAnalyzer:
    """Test suite for ParallelComplexityAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing"""
        config = ParallelAnalysisConfig(
            max_analysis_time_ms=50,  # Shorter timeout for tests
            universal_confidence_threshold=0.75
        )
        return ParallelComplexityAnalyzer(config)
    
    @pytest.fixture
    def context(self):
        """Create test context"""
        return RequestContext(
            session_id="test-session",
            user_id="test-user",
            organization_id="test-org"
        )
    
    def test_fast_path_single_word(self, analyzer):
        """Test fast-path optimization for single word queries"""
        result = analyzer._check_fast_path("hello")
        
        assert result.matched is True
        assert result.pattern_type == "single_word"
        assert result.score == 0.1
        assert result.confidence == 0.95
    
    def test_fast_path_greeting(self, analyzer):
        """Test fast-path optimization for greetings"""
        result = analyzer._check_fast_path("Hi there!")
        
        assert result.matched is True
        assert result.pattern_type == "greeting"
        assert result.score == 0.1
        assert result.confidence == 0.95
    
    def test_fast_path_basic_math(self, analyzer):
        """Test fast-path optimization for basic math"""
        result = analyzer._check_fast_path("2 + 3")
        
        assert result.matched is True
        assert result.pattern_type == "basic_math"
        assert result.score == 0.15
        assert result.confidence == 0.90
    
    def test_fast_path_long_text(self, analyzer):
        """Test fast-path optimization for very long text"""
        long_text = "x" * 5001
        result = analyzer._check_fast_path(long_text)
        
        assert result.matched is True
        assert result.pattern_type == "long_text"
        assert result.score == 0.8
        assert result.confidence == 0.85
    
    def test_fast_path_no_match(self, analyzer):
        """Test fast-path when no pattern matches"""
        result = analyzer._check_fast_path("Analyze the market trends")
        
        assert result.matched is False
        assert result.pattern_type == "none"
    
    def test_pattern_analysis_sync(self, analyzer):
        """Test synchronous pattern analysis logic"""
        # Short text
        result = analyzer._analyze_patterns_sync("Hi")
        assert result['score'] <= 0.2
        assert "very_short_text" in result['signals']
        
        # Medium text with analysis keywords
        result = analyzer._analyze_patterns_sync("Please analyze this data and explain the trends")
        assert result['score'] > 0.2
        assert "analysis_keywords" in result['signals']
        
        # Code-related text
        result = analyzer._analyze_patterns_sync("Write a function to sort an array")
        assert "code_keywords" in result['signals']
    
    def test_content_type_detection_sync(self, analyzer):
        """Test synchronous content type detection"""
        # Code detection
        result = analyzer._detect_content_type_sync("def hello(): return 'world'")
        assert result['score'] == 0.6
        assert "code_detected" in result['signals']
        
        # Data analysis detection
        result = analyzer._detect_content_type_sync("Analyze this CSV dataset")
        assert "data_analysis" in result['signals']
        
        # Creative content
        result = analyzer._detect_content_type_sync("Write a creative story about space")
        assert "creative_content" in result['signals']
        assert result['score'] == 0.7
    
    def test_context_analysis_sync(self, analyzer):
        """Test synchronous context analysis"""
        # Context with conversation history
        context = RequestContext(
            conversation_history=[{"role": "user", "content": "msg"}] * 15,
            rag_documents=[{"title": "doc1"}, {"title": "doc2"}],
            quality_critical=True
        )
        
        result = analyzer._analyze_context_sync(context, "test")
        
        assert "long_conversation_history" in result['signals']
        assert "some_rag_documents" in result['signals']
        assert "quality_critical" in result['signals']
        assert result['score'] > 0.3
    
    def test_escalation_patterns_sync(self, analyzer):
        """Test synchronous escalation pattern matching"""
        # Text with multiple escalation indicators
        text = "Please provide a nuanced analysis comparing expert opinions on this complex technical matter"
        result = analyzer._check_escalation_patterns_sync(text)
        
        assert result['escalation_score'] >= 2
        assert result['should_escalate'] is True
        assert "nuanced_language" in result['patterns_found']
        assert "expert_knowledge" in result['patterns_found']
        assert "multi_faceted_analysis" in result['patterns_found']
    
    @pytest.mark.asyncio
    async def test_parallel_component_execution(self, analyzer, context):
        """Test that all components execute in parallel"""
        text = "Analyze this code function and explain its complexity"
        
        start_time = time.time()
        results = await analyzer._run_parallel_analysis(text, context)
        execution_time = (time.time() - start_time) * 1000
        
        # Should complete within reasonable time (parallel execution)
        assert execution_time < 100  # 100ms should be plenty for parallel execution
        
        # All components should have results
        expected_components = ['pattern_analysis', 'content_detection', 'context_factors', 'escalation_patterns']
        for component in expected_components:
            assert component in results
    
    @pytest.mark.asyncio
    async def test_weighted_consensus(self, analyzer, context):
        """Test weighted consensus calculation"""
        # Mock component results
        component_results = {
            'pattern_analysis': ComponentResult(
                score=0.4, confidence=0.8, signals=['medium_text'], 
                execution_time_ms=5.0, component_name='pattern_analysis'
            ),
            'content_detection': ComponentResult(
                score=0.6, confidence=0.9, signals=['code_detected'], 
                execution_time_ms=3.0, component_name='content_detection'
            ),
            'context_factors': ComponentResult(
                score=0.2, confidence=0.7, signals=['some_context'], 
                execution_time_ms=2.0, component_name='context_factors'
            ),
            'escalation_patterns': {
                'escalation_score': 1, 'confidence': 0.6, 'patterns_found': ['technical'],
                'should_escalate': False
            }
        }
        
        result = analyzer._apply_weighted_consensus(component_results, time.time())
        
        # Check that weighted average is calculated
        assert 0.3 < result.score < 0.6  # Should be weighted average
        assert 0.6 < result.confidence < 0.9
        assert result.level in [ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM, ComplexityLevel.COMPLEX]
        assert result.analysis_path == AnalysisPath.PARALLEL_CONSENSUS
        assert len(result.analysis_components_completed) == 4
    
    def test_conflict_resolution(self, analyzer):
        """Test conflict resolution logic"""
        # Create consensus result
        consensus_result = ComplexityResult(
            score=0.3, confidence=0.8, level=ComplexityLevel.SIMPLE,
            analysis_path=AnalysisPath.PARALLEL_CONSENSUS,
            analysis_time_ms=10.0, signals=[]
        )
        
        # Component results with conflicts
        component_results = {
            'pattern_analysis': ComponentResult(
                score=0.2, confidence=0.8, signals=['short_text'], 
                execution_time_ms=5.0, component_name='pattern_analysis'
            ),
            'content_detection': ComponentResult(
                score=0.6, confidence=0.9, signals=['code_detected'], 
                execution_time_ms=3.0, component_name='content_detection'
            ),
            'escalation_patterns': {'should_escalate': True}
        }
        
        result = analyzer._resolve_conflicts(consensus_result, component_results)
        
        # Should detect conflicts and apply resolution rules
        assert result.conflicting_signals_detected is True
        assert result.confidence < consensus_result.confidence  # Penalty applied
        
        # Code complexity boost rule should apply
        assert "code_complexity_boost" in result.signals
        assert result.level == ComplexityLevel.MEDIUM
    
    @pytest.mark.asyncio
    async def test_full_analysis_fast_path(self, analyzer, context):
        """Test full analysis with fast-path optimization"""
        result = await analyzer.analyze_complexity("hello", context)
        
        assert result.analysis_path == AnalysisPath.FAST_PATH
        assert result.early_return_triggered is True
        assert result.analysis_time_ms < 5  # Should be very fast
        assert "fast_path" in result.analysis_components_completed
    
    @pytest.mark.asyncio
    async def test_full_analysis_parallel_path(self, analyzer, context):
        """Test full analysis with parallel execution"""
        text = "Please analyze this complex technical document and provide insights"
        
        with patch.object(analyzer.cache_service, 'get_cached_result', return_value=None):
            with patch.object(analyzer.cache_service, 'cache_result', new_callable=AsyncMock):
                result = await analyzer.analyze_complexity(text, context)
        
        assert result.analysis_path in [AnalysisPath.PARALLEL_CONSENSUS, AnalysisPath.LLM_ESCALATION]
        assert len(result.analysis_components_completed) >= 4
        assert result.analysis_time_ms > 0
        assert result.component_scores is not None
    
    @pytest.mark.asyncio
    async def test_error_handling(self, analyzer, context):
        """Test error handling in parallel execution"""
        # Mock one component to fail
        with patch.object(analyzer, '_analyze_patterns', side_effect=Exception("Test error")):
            result = await analyzer.analyze_complexity("test text", context)
            
            # Should still return a result (fallback)
            assert result is not None
            assert result.score >= 0
            assert result.confidence >= 0
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, analyzer, context):
        """Test timeout handling in parallel execution"""
        # Create analyzer with very short timeout
        config = ParallelAnalysisConfig(max_analysis_time_ms=1)  # 1ms timeout
        fast_analyzer = ParallelComplexityAnalyzer(config)
        
        # Mock slow component
        async def slow_component(*args):
            await asyncio.sleep(0.1)  # 100ms delay
            return ComponentResult(0.5, 0.5, [], 100.0, "slow_component")
        
        with patch.object(fast_analyzer, '_analyze_patterns', side_effect=slow_component):
            result = await fast_analyzer.analyze_complexity("test", context)
            
            # Should handle timeout gracefully
            assert result is not None
    
    def test_create_error_component_result(self, analyzer):
        """Test error component result creation"""
        result = analyzer._create_error_component_result("test_component", "test error")
        
        assert result.component_name == "test_component"
        assert result.score == 0.5  # Default medium complexity
        assert result.confidence == 0.2  # Low confidence
        assert "component_error" in result.signals
    
    def test_create_timeout_component_result(self, analyzer):
        """Test timeout component result creation"""
        result = analyzer._create_timeout_component_result("test_component")
        
        assert result.component_name == "test_component"
        assert result.score == 0.5
        assert result.confidence == 0.3
        assert "component_timeout" in result.signals
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, analyzer, context):
        """Test cache integration"""
        text = "test query"
        
        # Mock cache hit
        cached_result = ComplexityResult(
            score=0.5, confidence=0.8, level=ComplexityLevel.MEDIUM,
            analysis_path=AnalysisPath.CACHED, analysis_time_ms=1.0,
            signals=["cached"], cache_hit=True
        )
        
        with patch.object(analyzer.cache_service, 'get_cached_result', return_value=cached_result):
            result = await analyzer.analyze_complexity(text, context)
            
            assert result.cache_hit is True
            assert result.analysis_path == AnalysisPath.CACHED
            assert result.analysis_time_ms < 5  # Should be very fast
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = ParallelAnalysisConfig(
            max_analysis_time_ms=20,
            universal_confidence_threshold=0.8,
            conflict_detection_threshold=0.2
        )
        
        analyzer = ParallelComplexityAnalyzer(config)
        assert analyzer.config.max_analysis_time_ms == 20
        assert analyzer.config.universal_confidence_threshold == 0.8
        assert analyzer.config.conflict_detection_threshold == 0.2
    
    @pytest.mark.asyncio
    async def test_performance_benchmark(self, analyzer, context):
        """Benchmark parallel vs expected performance"""
        test_cases = [
            "hello",  # Fast-path
            "What is AI?",  # Simple analysis
            "Analyze this complex technical architecture and provide detailed insights",  # Complex
            "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",  # Code
        ]
        
        total_time = 0
        for text in test_cases:
            start_time = time.time()
            result = await analyzer.analyze_complexity(text, context)
            execution_time = (time.time() - start_time) * 1000
            total_time += execution_time
            
            # Individual request should be fast
            if result.analysis_path == AnalysisPath.FAST_PATH:
                assert execution_time < 5  # Fast-path should be <5ms
            else:
                assert execution_time < 50  # Parallel analysis should be <50ms
        
        # Average should meet target
        avg_time = total_time / len(test_cases)
        assert avg_time < 20  # Target: 8-12ms average, allowing some margin
    
    def test_thread_pool_cleanup(self):
        """Test that thread pool is properly cleaned up"""
        analyzer = ParallelComplexityAnalyzer()
        executor = analyzer.executor
        
        # Cleanup
        del analyzer
        
        # Executor should be shutdown (this is hard to test directly,
        # but we can at least verify the cleanup method exists)
        assert hasattr(ParallelComplexityAnalyzer, '__del__')


@pytest.mark.asyncio
async def test_integration_with_existing_system():
    """Integration test with existing complexity analysis system"""
    from ..analyzer import EnhancedComplexityAnalyzer
    
    # Test that both analyzers produce similar results for the same input
    text = "Analyze the performance characteristics of this algorithm"
    context = RequestContext(session_id="test", organization_id="test-org")
    
    # Serial analyzer
    serial_analyzer = EnhancedComplexityAnalyzer()
    
    # Parallel analyzer  
    parallel_analyzer = ParallelComplexityAnalyzer()
    
    # Get results from both
    with patch.object(serial_analyzer.cache_service, 'get_cached_result', return_value=None):
        with patch.object(parallel_analyzer.cache_service, 'get_cached_result', return_value=None):
            serial_result = await serial_analyzer.analyze_complexity(text, context)
            parallel_result = await parallel_analyzer.analyze_complexity(text, context)
    
    # Results should be reasonably similar
    score_diff = abs(serial_result.score - parallel_result.score)
    assert score_diff < 0.3  # Allow some variance
    
    # Both should identify similar complexity levels for obvious cases
    if serial_result.score < 0.3:
        assert parallel_result.score < 0.5  # Should also be relatively simple
    elif serial_result.score > 0.7:
        assert parallel_result.score > 0.5  # Should also be relatively complex
