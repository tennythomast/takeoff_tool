"""
Management command to generate a report for a benchmark run.
"""

import logging
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from benchmark.models import BenchmarkRun
from benchmark.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate a report for a benchmark run'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'run_id',
            type=str,
            help='ID of the benchmark run to generate a report for'
        )
        parser.add_argument(
            '--list-runs',
            action='store_true',
            help='List recent benchmark runs and exit'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            help='Directory to store the report (default: MEDIA_ROOT/benchmark_reports/)'
        )
    
    def handle(self, *args, **options):
        # Check if we should list runs
        if options['list_runs']:
            self.stdout.write("Recent benchmark runs:")
            recent_runs = BenchmarkRun.objects.order_by('-timestamp')[:10]
            for run in recent_runs:
                self.stdout.write(f"  - {run.run_id}: {run.dataset_name} ({run.timestamp}) - {run.status}")
            return
        
        run_id_str = options['run_id']
        output_dir = options.get('output_dir')
        
        # Parse run ID
        try:
            run_id = uuid.UUID(run_id_str)
        except ValueError:
            raise CommandError(f"Invalid run ID: {run_id_str}")
        
        # Check if run exists
        try:
            benchmark_run = BenchmarkRun.objects.get(run_id=run_id)
        except BenchmarkRun.DoesNotExist:
            raise CommandError(f"Benchmark run not found: {run_id}")
        
        # Check if run is completed
        if benchmark_run.status != "completed":
            self.stdout.write(self.style.WARNING(
                f"Warning: Benchmark run {run_id} has status '{benchmark_run.status}', not 'completed'"
            ))
            
            # Ask for confirmation
            if not self._confirm(f"Generate report anyway? [y/N] "):
                self.stdout.write("Aborted.")
                return
        
        # Create report generator
        report_generator = ReportGenerator(report_dir=output_dir)
        
        # Generate report
        self.stdout.write(f"Generating report for benchmark run {run_id}...")
        start_time = timezone.now()
        
        try:
            report = report_generator.generate_report(run_id)
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(self.style.SUCCESS(
                f"Report generated successfully in {duration:.2f} seconds!"
            ))
            
            # Print report details
            if 'summary_report' in report:
                self.stdout.write(f"Summary report: {report['summary_report']}")
            if 'csv_export' in report:
                self.stdout.write(f"CSV export: {report['csv_export']}")
            if 'json_export' in report:
                self.stdout.write(f"JSON export: {report['json_export']}")
            if 'visualizations' in report and report['visualizations']:
                self.stdout.write("Visualizations:")
                for name, path in report['visualizations'].items():
                    self.stdout.write(f"  - {name}: {path}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error generating report: {str(e)}"))
            raise CommandError(str(e))
    
    def _confirm(self, message):
        """Ask for user confirmation."""
        answer = input(message)
        return answer.lower() in ('y', 'yes')
