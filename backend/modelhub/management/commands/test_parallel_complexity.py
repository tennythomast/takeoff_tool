# backend/modelhub/management/commands/test_parallel_complexity.py
"""
Management command to test and benchmark the parallel complexity analyzer.
"""
import asyncio
import time
from django.core.management.base import BaseCommand
from django.conf import settings

from modelhub.services.complexity import (
    get_complexity_analyzer, 
    EnhancedComplexityAnalyzer,
    ParallelComplexityAnalyzer
)
from modelhub.services.complexity.types import RequestContext


class Command(BaseCommand):
    help = 'Test and benchmark the parallel complexity analyzer'

    def add_arguments(self, parser):
        parser.add_argument(
            '--benchmark',
            action='store_true',
            help='Run performance benchmark comparing serial vs parallel analyzers'
        )
        parser.add_argument(
            '--test-cases',
            type=int,
            default=10,
            help='Number of test cases to run for benchmarking'
        )
        parser.add_argument(
            '--enable-parallel',
            action='store_true',
            help='Test with parallel analyzer enabled'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write("🧪 Testing Parallel Complexity Analyzer")
        self.stdout.write("=" * 50)
        
        if options['benchmark']:
            asyncio.run(self.run_benchmark(options['test_cases']))
        else:
            asyncio.run(self.run_basic_tests(options['enable_parallel']))

    async def run_basic_tests(self, enable_parallel=False):
        """Run basic functionality tests"""
        self.stdout.write("\n📋 Running Basic Tests...")
        
        # Test cases covering different complexity scenarios
        test_cases = [
            ("hello", "Fast-path: Single word"),
            ("Hi there!", "Fast-path: Greeting"),
            ("2 + 3", "Fast-path: Basic math"),
            ("What is AI?", "Simple: Basic question"),
            ("Please analyze this data and explain the trends", "Medium: Analysis request"),
            ("def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)", "Medium: Code"),
            ("Write a comprehensive analysis of the market trends, considering economic factors, consumer behavior, and competitive landscape", "Complex: Multi-faceted analysis"),
            ("x" * 5001, "Fast-path: Very long text"),
        ]
        
        # Get analyzer
        if enable_parallel:
            analyzer = ParallelComplexityAnalyzer()
            self.stdout.write("Using: ParallelComplexityAnalyzer")
        else:
            analyzer = get_complexity_analyzer()
            self.stdout.write(f"Using: {type(analyzer).__name__}")
        
        context = RequestContext(
            session_id="test-session",
            user_id="test-user",
            organization_id="test-org"
        )
        
        total_time = 0
        results = []
        
        for text, description in test_cases:
            start_time = time.time()
            
            try:
                result = await analyzer.analyze_complexity(text, context)
                execution_time = (time.time() - start_time) * 1000
                total_time += execution_time
                
                results.append({
                    'description': description,
                    'text': text[:50] + "..." if len(text) > 50 else text,
                    'score': result.score,
                    'confidence': result.confidence,
                    'level': result.level.value,
                    'path': result.analysis_path.value,
                    'time_ms': execution_time,
                    'components': len(result.analysis_components_completed) if hasattr(result, 'analysis_components_completed') else 0,
                    'fast_path': getattr(result, 'early_return_triggered', False)
                })
                
                self.stdout.write(
                    f"✅ {description}: {result.level.value} "
                    f"(score={result.score:.2f}, conf={result.confidence:.2f}, "
                    f"time={execution_time:.1f}ms, path={result.analysis_path.value})"
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ {description}: Error - {str(e)}")
                )
        
        # Summary
        avg_time = total_time / len(test_cases)
        fast_path_count = sum(1 for r in results if r['fast_path'])
        
        self.stdout.write("\n📊 Test Summary:")
        self.stdout.write(f"Total tests: {len(test_cases)}")
        self.stdout.write(f"Average time: {avg_time:.2f}ms")
        self.stdout.write(f"Total time: {total_time:.2f}ms")
        self.stdout.write(f"Fast-path hits: {fast_path_count}/{len(test_cases)}")
        
        # Performance assessment
        if avg_time < 12:
            self.stdout.write(self.style.SUCCESS("🎯 Performance: EXCELLENT (< 12ms avg)"))
        elif avg_time < 20:
            self.stdout.write(self.style.SUCCESS("✅ Performance: GOOD (< 20ms avg)"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ Performance: NEEDS IMPROVEMENT (> 20ms avg)"))

    async def run_benchmark(self, test_cases_count):
        """Run performance benchmark comparing serial vs parallel analyzers"""
        self.stdout.write(f"\n🏁 Running Performance Benchmark ({test_cases_count} iterations)")
        
        # Test cases for benchmarking
        benchmark_texts = [
            "hello",
            "What is artificial intelligence?",
            "Please analyze this complex technical architecture and provide detailed insights about scalability, performance, and maintainability",
            "def quicksort(arr): return arr if len(arr) <= 1 else quicksort([x for x in arr[1:] if x < arr[0]]) + [arr[0]] + quicksort([x for x in arr[1:] if x >= arr[0]])",
            "Write a comprehensive business strategy document covering market analysis, competitive landscape, financial projections, and risk assessment",
        ]
        
        context = RequestContext(
            session_id="benchmark-session",
            user_id="benchmark-user",
            organization_id="benchmark-org"
        )
        
        # Test serial analyzer
        self.stdout.write("\n🔄 Testing Serial Analyzer...")
        serial_analyzer = EnhancedComplexityAnalyzer()
        serial_times = []
        serial_results = []
        
        for i in range(test_cases_count):
            text = benchmark_texts[i % len(benchmark_texts)]
            start_time = time.time()
            
            try:
                result = await serial_analyzer.analyze_complexity(text, context)
                execution_time = (time.time() - start_time) * 1000
                serial_times.append(execution_time)
                serial_results.append(result)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Serial analyzer error: {str(e)}"))
        
        # Test parallel analyzer
        self.stdout.write("🚀 Testing Parallel Analyzer...")
        parallel_analyzer = ParallelComplexityAnalyzer()
        parallel_times = []
        parallel_results = []
        
        for i in range(test_cases_count):
            text = benchmark_texts[i % len(benchmark_texts)]
            start_time = time.time()
            
            try:
                result = await parallel_analyzer.analyze_complexity(text, context)
                execution_time = (time.time() - start_time) * 1000
                parallel_times.append(execution_time)
                parallel_results.append(result)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Parallel analyzer error: {str(e)}"))
        
        # Calculate statistics
        if serial_times and parallel_times:
            serial_avg = sum(serial_times) / len(serial_times)
            serial_p95 = sorted(serial_times)[int(len(serial_times) * 0.95)]
            
            parallel_avg = sum(parallel_times) / len(parallel_times)
            parallel_p95 = sorted(parallel_times)[int(len(parallel_times) * 0.95)]
            
            improvement = ((serial_avg - parallel_avg) / serial_avg) * 100
            
            # Results comparison
            score_diffs = []
            for i in range(min(len(serial_results), len(parallel_results))):
                score_diff = abs(serial_results[i].score - parallel_results[i].score)
                score_diffs.append(score_diff)
            
            avg_score_diff = sum(score_diffs) / len(score_diffs) if score_diffs else 0
            
            # Display results
            self.stdout.write("\n📈 Benchmark Results:")
            self.stdout.write("=" * 50)
            self.stdout.write(f"Serial Analyzer:")
            self.stdout.write(f"  Average time: {serial_avg:.2f}ms")
            self.stdout.write(f"  P95 time: {serial_p95:.2f}ms")
            self.stdout.write(f"  Min time: {min(serial_times):.2f}ms")
            self.stdout.write(f"  Max time: {max(serial_times):.2f}ms")
            
            self.stdout.write(f"\nParallel Analyzer:")
            self.stdout.write(f"  Average time: {parallel_avg:.2f}ms")
            self.stdout.write(f"  P95 time: {parallel_p95:.2f}ms")
            self.stdout.write(f"  Min time: {min(parallel_times):.2f}ms")
            self.stdout.write(f"  Max time: {max(parallel_times):.2f}ms")
            
            self.stdout.write(f"\nPerformance Improvement:")
            if improvement > 0:
                self.stdout.write(self.style.SUCCESS(f"  🚀 {improvement:.1f}% faster on average"))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠️ {abs(improvement):.1f}% slower on average"))
            
            self.stdout.write(f"\nAccuracy Comparison:")
            self.stdout.write(f"  Average score difference: {avg_score_diff:.3f}")
            if avg_score_diff < 0.1:
                self.stdout.write(self.style.SUCCESS("  ✅ Results are very similar"))
            elif avg_score_diff < 0.2:
                self.stdout.write(self.style.SUCCESS("  ✅ Results are reasonably similar"))
            else:
                self.stdout.write(self.style.WARNING("  ⚠️ Results show significant differences"))
            
            # Performance targets assessment
            self.stdout.write(f"\nTarget Assessment:")
            if parallel_avg <= 12:
                self.stdout.write(self.style.SUCCESS("  🎯 Average latency target MET (≤12ms)"))
            else:
                self.stdout.write(self.style.WARNING(f"  ❌ Average latency target MISSED ({parallel_avg:.1f}ms > 12ms)"))
            
            if parallel_p95 <= 15:
                self.stdout.write(self.style.SUCCESS("  🎯 P95 latency target MET (≤15ms)"))
            else:
                self.stdout.write(self.style.WARNING(f"  ❌ P95 latency target MISSED ({parallel_p95:.1f}ms > 15ms)"))
            
            # Fast-path analysis for parallel analyzer
            fast_path_count = sum(1 for r in parallel_results if getattr(r, 'early_return_triggered', False))
            fast_path_rate = (fast_path_count / len(parallel_results)) * 100
            self.stdout.write(f"  📊 Fast-path usage: {fast_path_rate:.1f}% ({fast_path_count}/{len(parallel_results)})")
            
        else:
            self.stdout.write(self.style.ERROR("❌ Benchmark failed - no timing data collected"))

    def test_feature_flag(self):
        """Test the feature flag functionality"""
        self.stdout.write("\n🏁 Testing Feature Flag...")
        
        # Test default (should be serial)
        analyzer = get_complexity_analyzer()
        self.stdout.write(f"Default analyzer: {type(analyzer).__name__}")
        
        # Test with environment variable (would need to be set externally)
        import os
        current_flag = os.environ.get('USE_PARALLEL_COMPLEXITY_ANALYZER', 'false')
        self.stdout.write(f"Current flag value: {current_flag}")
        
        if current_flag.lower() == 'true':
            self.stdout.write("✅ Parallel analyzer is ENABLED")
        else:
            self.stdout.write("ℹ️ Parallel analyzer is DISABLED (using serial)")
            self.stdout.write("   To enable: export USE_PARALLEL_COMPLEXITY_ANALYZER=true")
