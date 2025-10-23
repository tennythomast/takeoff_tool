"""
Benchmark runner service for orchestrating benchmark runs.

This service is responsible for:
1. Loading and sampling datasets
2. Running samples through the complexity analyzer
3. Running samples through the LLM router
4. Executing requests through the unified LLM client
5. Calculating quality metrics
6. Storing results in the database
"""

import time
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from django.utils import timezone
from django.db import transaction

from benchmark.models import BenchmarkRun, BenchmarkResult, BenchmarkSummary
from benchmark.services.dataset_loaders import get_dataset_loader
from benchmark.services.quality_assessor import calculate_semantic_similarity, assess_quality_retention

# Import the necessary services from your existing codebase
# These imports will need to be adjusted based on your actual project structure
try:
    from modelhub.services.complexity import EnhancedComplexityAnalyzer
    from modelhub.services.complexity.types import RequestContext
    from modelhub.services.llm_router import EnhancedLLMRouter
    from modelhub.services.unified_llm_client import UnifiedLLMClient
    from modelhub.services.routing.types import OptimizationStrategy
    MODELHUB_AVAILABLE = True
except ImportError:
    MODELHUB_AVAILABLE = False
    logging.warning("Modelhub services not available. Running in mock mode.")

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Main orchestrator for benchmark runs."""
    
    def __init__(self):
        """Initialize the benchmark runner."""
        if MODELHUB_AVAILABLE:
            self.complexity_analyzer = EnhancedComplexityAnalyzer()
            self.llm_router = EnhancedLLMRouter()
            self.unified_client = UnifiedLLMClient()
            # Default baseline models (can be overridden in configuration)
            self.baseline_models = {
                'openai': 'gpt-4',
                'anthropic': 'claude-3-5-sonnet-20240620'  # Updated to use requested model
            }
            # Cache for API keys
            self.api_key_cache = {}
        else:
            self.complexity_analyzer = None
            self.llm_router = None
            self.unified_client = None
            self.baseline_models = {}
            self.api_key_cache = {}
            logger.warning("Running in mock mode. Results will be simulated.")
            
    async def _get_api_key_for_provider(self, provider_slug: str) -> str:
        """Get API key for the specified provider.
        
        Args:
            provider_slug: Provider slug (e.g., 'openai', 'anthropic')
            
        Returns:
            API key string or empty string if not found
        """
        # Check cache first
        if provider_slug in self.api_key_cache:
            return self.api_key_cache[provider_slug]
            
        # Import here to avoid circular imports
        from channels.db import database_sync_to_async
        from modelhub.models import APIKey
        
        @database_sync_to_async
        def get_key():
            # Try Dataelan system-wide key (no organization)
            api_key = APIKey.objects.filter(
                organization__isnull=True,
                provider__slug=provider_slug,
                is_active=True
            ).first()
            
            if api_key and api_key.quota_status.get('status') != 'exceeded':
                return api_key.key
            return ""
            
        # Get key and cache it
        key = await get_key()
        self.api_key_cache[provider_slug] = key
        return key
    
    async def start_benchmark_run(
        self, 
        dataset_name: str, 
        sample_size: int, 
        complexity_only: bool = False,
        configuration: Dict[str, Any] = None
    ) -> BenchmarkRun:
        """Start a new benchmark run.
        
        Args:
            dataset_name: Name of the dataset to benchmark
            sample_size: Number of samples to use
            complexity_only: If True, only run complexity analysis
            configuration: Additional configuration for the benchmark run
            
        Returns:
            BenchmarkRun instance
        """
        from asgiref.sync import sync_to_async
        
        # Create a new benchmark run
        benchmark_run = await sync_to_async(BenchmarkRun.objects.create)(
            dataset_name=dataset_name,
            total_samples=sample_size,
            configuration={
                "complexity_only": complexity_only,
                **(configuration or {})
            },
            status="running"
        )
        
        mode = "complexity-only" if complexity_only else "full"
        logger.info(f"Started {mode} benchmark run {benchmark_run.run_id} for dataset {dataset_name} with {sample_size} samples")
        
        return benchmark_run
    
    async def execute_benchmark_run(self, benchmark_run_id: uuid.UUID, complexity_only: bool = False) -> BenchmarkRun:
        """Execute a benchmark run.
        
        Args:
            benchmark_run_id: ID of the benchmark run to execute
            complexity_only: If True, only run complexity analysis and skip routing/execution
            
        Returns:
            Updated BenchmarkRun instance
        """
        from asgiref.sync import sync_to_async
        
        try:
            # Get the benchmark run
            benchmark_run = await sync_to_async(BenchmarkRun.objects.get)(run_id=benchmark_run_id)
            
            # Load the dataset
            dataset_loader = get_dataset_loader(benchmark_run.dataset_name)
            samples = dataset_loader.load_and_sample(benchmark_run.total_samples)
            
            mode = "complexity-only" if complexity_only else "full"
            logger.info(f"Starting {mode} benchmark run {benchmark_run_id} with {len(samples)} samples")
            
            # Process each sample
            results = []
            for i, sample in enumerate(samples):
                try:
                    # Log progress
                    if i % 10 == 0 or i == len(samples) - 1:
                        logger.info(f"Processing sample {i+1}/{len(samples)} for benchmark run {benchmark_run_id}")
                    
                    # Process the sample with complexity_only flag
                    result = await self._process_sample(sample, benchmark_run, complexity_only=complexity_only)
                    results.append(result)
                    
                except Exception as e:
                        logger.error(f"Error processing sample {sample['sample_id']}: {str(e)}")
            
            # Save all results - ensure each result has a unique ID
            for result in results:
                # Explicitly set a new UUID for each result before bulk create
                result.id = uuid.uuid4()
            await sync_to_async(BenchmarkResult.objects.bulk_create)(results)
            
            # Create summary - ensure it's properly awaited
            summary = await sync_to_async(self._create_or_update_summary)(benchmark_run)
            # Force a refresh of the summary from the database to ensure it's up to date
            await sync_to_async(lambda: summary.refresh_from_db())()
            
            # Mark the benchmark run as completed
            benchmark_run.status = "completed"
            await sync_to_async(benchmark_run.save)()
            
            logger.info(f"Completed {mode} benchmark run {benchmark_run_id}")
            
            return benchmark_run
            
        except Exception as e:
            logger.error(f"Error executing benchmark run {benchmark_run_id}: {str(e)}")
            
            # Mark the benchmark run as failed
            try:
                benchmark_run = await sync_to_async(BenchmarkRun.objects.get)(run_id=benchmark_run_id)
                benchmark_run.status = "failed"
                await sync_to_async(benchmark_run.save)()
            except Exception:
                pass
            
            raise
    
    async def _process_sample(self, sample: Dict[str, Any], benchmark_run: BenchmarkRun, complexity_only: bool = False) -> BenchmarkResult:
        """Process a single sample.
        
        Args:
            sample: Sample to process
            benchmark_run: BenchmarkRun instance
            complexity_only: If True, only run complexity analysis and skip routing/execution
            
        Returns:
            BenchmarkResult instance
        """
        # Create a new benchmark result with a fresh UUID
        result = BenchmarkResult(
            id=uuid.uuid4(),  # Explicitly generate a new UUID for each result
            benchmark_run=benchmark_run,
            sample_id=sample["sample_id"],
            input_text=sample["input_text"],
            expected_output=sample.get("expected_output", ""),
            created_at=timezone.now(),
        )
        
        try:
            # If running in mock mode, simulate results
            if not MODELHUB_AVAILABLE:
                self._simulate_results(result)
                return result
            
            # Step 1: Run through complexity analyzer
            complexity_start_time = time.time()
            
            # Create a default context for benchmark
            context = RequestContext(
                entity_type="benchmark_test",
                require_fast_response=True
            )
            
            # Await the async analyze_complexity call
            complexity_analysis = await self.complexity_analyzer.analyze_complexity(
                sample["input_text"], 
                context=context
            )
            complexity_time = time.time() - complexity_start_time
            
            # Update benchmark result with complexity analysis
            result.complexity_score = complexity_analysis.score
            result.complexity_level = complexity_analysis.level.value if hasattr(complexity_analysis.level, 'value') else str(complexity_analysis.level)
            result.complexity_reasoning = complexity_analysis.reasoning
            result.complexity_analysis_time = complexity_time
            
            if complexity_only:
                return result
                
            # Step 2: Run through LLM router (only if not in complexity-only mode)
            routing_start_time = time.time()
            
            # Create default organization for benchmark
            organization = None  # Using None for benchmark tests
            model_type = "TEXT"  # Default model type
            content_type = complexity_analysis.content_type.value if hasattr(complexity_analysis.content_type, 'value') else str(complexity_analysis.content_type)
            
            # Create a request context for the benchmark
            request_context = RequestContext(
                entity_type="benchmark_test",
                prompt_id=sample["sample_id"],
                session_id=str(benchmark_run.run_id)
            )
            # Set model_type after initialization
            request_context.model_type = model_type
            
            routing_decision = await self.llm_router.route_request(
                organization=organization,
                model_type=model_type,
                complexity_score=complexity_analysis.score,
                content_type=content_type,
                context=request_context,
                strategy=OptimizationStrategy.BALANCED
            )
            routing_time = time.time() - routing_start_time
            
            # Update benchmark result with routing decision (convert to dict for JSON serialization)
            # Convert Decimal to float for JSON serialization
            estimated_cost = routing_decision.estimated_cost if hasattr(routing_decision, 'estimated_cost') else 0.0
            if hasattr(estimated_cost, '__float__'):  # Check if it's a Decimal or similar
                estimated_cost = float(estimated_cost)
                
            result.routing_decision = {
                'provider_slug': routing_decision.selected_provider if hasattr(routing_decision, 'selected_provider') else 'unknown',
                'model_name': routing_decision.selected_model if hasattr(routing_decision, 'selected_model') else 'unknown',
                'estimated_cost': estimated_cost,
                'routing_time_ms': int(routing_time * 1000) if routing_time else 0
            }
            result.selected_model = routing_decision.selected_model if hasattr(routing_decision, 'selected_model') else "unknown"
            result.estimated_cost = routing_decision.estimated_cost if hasattr(routing_decision, 'estimated_cost') else 0.0
            
            # Step 3: Execute through unified client
            execution_start_time = time.time()
            try:
                # Get API key for the provider
                api_key = await self._get_api_key_for_provider(routing_decision.selected_provider)
                
                llm_response = await self.unified_client.call_llm(
                    provider_slug=routing_decision.selected_provider,
                    model_name=routing_decision.selected_model,
                    api_key=api_key,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": sample["input_text"]}
                    ],
                    stream=False
                )
                execution_time = (time.time() - execution_start_time) * 1000  # Convert to ms
                
                # Update benchmark result with platform response
                result.actual_response = llm_response.content if hasattr(llm_response, 'content') else ""
                result.execution_time_ms = int(execution_time)
                
            except Exception as e:
                logger.error(f"Error executing sample {sample['sample_id']}: {str(e)}")
            
            # Step 4: Execute through GPT-4 baseline
            gpt4_start_time = time.time()
            try:
                # Get API key for OpenAI
                openai_api_key = await self._get_api_key_for_provider("openai")
                
                gpt4_response = await self.unified_client.call_llm(
                    provider_slug="openai",
                    model_name=self.baseline_models.get('openai', 'gpt-4'),
                    api_key=openai_api_key,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": sample["input_text"]}
                    ],
                    stream=False
                )
                gpt4_time = (time.time() - gpt4_start_time) * 1000  # Convert to ms
            except Exception as e:
                logger.error(f"Error executing GPT-4 baseline for sample {sample['sample_id']}: {str(e)}")
                gpt4_response = {"response": ""}
                gpt4_time = 0     
            # Update benchmark result with GPT-4 response
            result.gpt4_response = gpt4_response.content if hasattr(gpt4_response, 'content') else ""
            result.gpt4_cost = gpt4_response.cost if hasattr(gpt4_response, 'cost') else 0.0
            
            # Step 5: Execute through Claude baseline
            claude_start_time = time.time()
            try:
                # Get API key for Anthropic
                anthropic_api_key = await self._get_api_key_for_provider("anthropic")
                
                claude_response = await self.unified_client.call_llm(
                    provider_slug="anthropic",
                    model_name=self.baseline_models.get('anthropic', 'claude-3-sonnet-20240229'),
                    api_key=anthropic_api_key,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": sample["input_text"]}
                    ],
                    stream=False
                )
                claude_time = (time.time() - claude_start_time) * 1000  # Convert to ms
            except Exception as e:
                logger.error(f"Error executing Claude baseline for sample {sample['sample_id']}: {str(e)}")
                claude_response = {"response": ""}
                claude_time = 0
            
            # Update benchmark result with Claude response
            result.claude_response = claude_response.content if hasattr(claude_response, 'content') else ""
            result.claude_cost = claude_response.cost if hasattr(claude_response, 'cost') else 0.0
            
            # Step 6: Calculate quality metrics
            result.semantic_similarity_vs_gpt4 = calculate_semantic_similarity(
                result.actual_response, result.gpt4_response
            )
            result.semantic_similarity_vs_claude = calculate_semantic_similarity(
                result.actual_response, result.claude_response
            )
            
            # Determine if quality is retained
            result.quality_retained = assess_quality_retention(
                result.semantic_similarity_vs_gpt4,
                result.semantic_similarity_vs_claude
            )
            
            # Set quality confidence
            result.quality_confidence = max(
                result.semantic_similarity_vs_gpt4,
                result.semantic_similarity_vs_claude
            )
            
            # Save the benchmark result using sync_to_async for async context
            from channels.db import sync_to_async
            await sync_to_async(result.save)()
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing sample {sample['sample_id']}: {str(e)}")
            raise
    
    async def _simulate_results(self, benchmark_result: BenchmarkResult) -> None:
        """Simulate results for a benchmark result when running in mock mode.
        
        Args:
            benchmark_result: BenchmarkResult instance to update
        """
        import random
        
        # Simulate complexity analysis
        complexity_levels = ["SIMPLE", "MEDIUM", "COMPLEX", "VERY_COMPLEX"]
        complexity_level = random.choice(complexity_levels)
        complexity_score = {
            "SIMPLE": random.uniform(0.0, 0.25),
            "MEDIUM": random.uniform(0.25, 0.5),
            "COMPLEX": random.uniform(0.5, 0.75),
            "VERY_COMPLEX": random.uniform(0.75, 1.0)
        }[complexity_level]
        
        benchmark_result.complexity_score = complexity_score
        benchmark_result.complexity_level = complexity_level
        benchmark_result.complexity_reasoning = {
            "score": complexity_score,
            "level": complexity_level,
            "confidence": random.uniform(0.7, 0.95),
            "reasoning": f"Mock reasoning for {complexity_level} complexity",
            "analysis_path": "MOCK_ANALYSIS"
        }
        
        # Simulate routing decision
        models = ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet", "mixtral-8x7b", "llama-3-70b"]
        selected_model = random.choice(models)
        
        # Cost estimates based on model
        cost_map = {
            "gpt-3.5-turbo": random.uniform(0.0001, 0.0005),
            "gpt-4": random.uniform(0.001, 0.003),
            "claude-3-sonnet": random.uniform(0.0008, 0.002),
            "mixtral-8x7b": random.uniform(0.0001, 0.0004),
            "llama-3-70b": random.uniform(0.0002, 0.0006)
        }
        
        estimated_cost = cost_map[selected_model]
        
        benchmark_result.routing_decision = {
            "selected_model": selected_model,
            "selected_provider": selected_model.split("-")[0],
            "confidence_score": random.uniform(0.7, 0.95),
            "reasoning": f"Mock routing decision for {complexity_level} complexity",
            "estimated_cost": estimated_cost,
            "decision_time_ms": random.randint(5, 20),
            "entity_type": "benchmark_test"
        }
        benchmark_result.selected_model = selected_model
        benchmark_result.estimated_cost = estimated_cost
        
        # Simulate responses
        benchmark_result.actual_response = f"Mock response from {selected_model} for input: {benchmark_result.input_text[:50]}..."
        benchmark_result.execution_time_ms = random.randint(200, 2000)
        
        # Ensure costs are properly set with non-zero values
        benchmark_result.gpt4_response = f"Mock GPT-4 response for input: {benchmark_result.input_text[:50]}..."
        benchmark_result.gpt4_cost = cost_map["gpt-4"] * random.uniform(1.0, 1.5)  # Add some randomness
        
        benchmark_result.claude_response = f"Mock Claude response for input: {benchmark_result.input_text[:50]}..."
        benchmark_result.claude_cost = cost_map["claude-3-sonnet"] * random.uniform(1.0, 1.5)  # Add some randomness
        
        # Simulate quality metrics
        benchmark_result.semantic_similarity_vs_gpt4 = random.uniform(0.7, 0.98)
        benchmark_result.semantic_similarity_vs_claude = random.uniform(0.7, 0.98)
        benchmark_result.quality_retained = random.random() > 0.2  # 80% chance of quality being retained
        benchmark_result.quality_confidence = max(
            benchmark_result.semantic_similarity_vs_gpt4,
            benchmark_result.semantic_similarity_vs_claude
        )
        
        # Save the benchmark result
        # Use sync_to_async for database operations in async context
        from channels.db import sync_to_async
        await sync_to_async(benchmark_result.save)()
    
    def _create_or_update_summary(self, benchmark_run: BenchmarkRun) -> BenchmarkSummary:
        """Create or update a summary for a benchmark run.
        
        Args:
            benchmark_run: BenchmarkRun instance
            
        Returns:
            BenchmarkSummary instance
        """
        # Get or create the summary
        summary, created = BenchmarkSummary.objects.get_or_create(benchmark_run=benchmark_run)
        
        # Update the summary
        summary.update_from_results()
        
        return summary
