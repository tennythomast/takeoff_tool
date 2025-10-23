"""
Management command to run a benchmark.
"""

import logging
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from benchmark.models import BenchmarkRun
from benchmark.services.benchmark_runner import BenchmarkRunner
from benchmark.services.dataset_loaders import get_dataset_loader, list_available_datasets

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run a benchmark on a dataset'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'dataset_name',
            type=str,
            help='Name of the dataset to benchmark'
        )
        parser.add_argument(
            '--samples',
            type=int,
            default=10,
            help='Number of samples to use (default: 10)'
        )
        parser.add_argument(
            '--config',
            type=str,
            default='{}',
            help='JSON configuration for the benchmark run (default: {})'
        )
        parser.add_argument(
            '--list-datasets',
            action='store_true',
            help='List available datasets and exit'
        )
        parser.add_argument(
            '--complexity-only',
            action='store_true',
            help='Only run complexity analysis and skip routing/execution'
        )
    
    def handle(self, *args, **options):
        """Handle the command."""
        dataset_name = options['dataset_name']
        samples = options['samples']
        complexity_only = options['complexity_only']
        
        # Initialize benchmark runner
        runner = BenchmarkRunner()
        
        try:
            # Run the benchmark asynchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Start the benchmark run
                benchmark_run = loop.run_until_complete(
                    runner.start_benchmark_run(
                        dataset_name=dataset_name,
                        sample_size=samples,
                        complexity_only=complexity_only
                    )
                )
                
                # Execute the benchmark run
                completed_run = loop.run_until_complete(
                    runner.execute_benchmark_run(benchmark_run.run_id, complexity_only=complexity_only)
                )
                
                # Output results
                mode = "Complexity-only" if complexity_only else "Full"
                self.stdout.write(self.style.SUCCESS(
                    f"{mode} benchmark run completed successfully!"
                ))
                self.stdout.write(f"Run ID: {completed_run.run_id}")
                self.stdout.write(f"Dataset: {completed_run.dataset_name}")
                self.stdout.write(f"Samples: {completed_run.total_samples}")
                self.stdout.write(f"Status: {completed_run.status}")
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error during benchmark execution: {str(e)}"))
                if hasattr(e, '__traceback__'):
                    import traceback
                    self.stderr.write(traceback.format_exc())
                
            finally:
                loop.close()
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error starting benchmark: {str(e)}"))
            if hasattr(e, '__traceback__'):
                import traceback
                self.stderr.write(traceback.format_exc())
            return 1
            
        return 0
