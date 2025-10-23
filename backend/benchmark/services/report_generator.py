"""
Report generator service for benchmark results.

This service is responsible for:
1. Generating visualizations from benchmark results
2. Creating summary reports
3. Exporting results to various formats
"""

import logging
import json
import os
import csv
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from django.conf import settings
from django.db.models import Avg, Count, Sum, F, Q
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from benchmark.models import BenchmarkRun, BenchmarkResult, BenchmarkSummary

logger = logging.getLogger(__name__)

# Try to import visualization libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    logger.warning("Visualization libraries not available. Install matplotlib, pandas, and numpy for visualizations.")


class ReportGenerator:
    """Service for generating reports and visualizations from benchmark results."""
    
    def __init__(self, report_dir: Optional[str] = None):
        """Initialize the report generator.
        
        Args:
            report_dir: Directory to store reports. Defaults to MEDIA_ROOT/benchmark_reports/
        """
        if report_dir:
            self.report_dir = report_dir
        else:
            # Use Django's MEDIA_ROOT if available, otherwise use a default
            media_root = getattr(settings, 'MEDIA_ROOT', '/tmp')
            self.report_dir = os.path.join(media_root, 'benchmark_reports')
        
        # Create report directory if it doesn't exist
        os.makedirs(self.report_dir, exist_ok=True)
        
        self.visualization_available = VISUALIZATION_AVAILABLE
    
    def generate_report(self, benchmark_run_id: uuid.UUID) -> Dict[str, Any]:
        """Generate a comprehensive report for a benchmark run.
        
        Args:
            benchmark_run_id: ID of the benchmark run
            
        Returns:
            Dictionary with report details and file paths
        """
        try:
            # Get the benchmark run
            benchmark_run = BenchmarkRun.objects.get(run_id=benchmark_run_id)
            
            # Create a report directory for this run
            run_report_dir = os.path.join(self.report_dir, str(benchmark_run_id))
            os.makedirs(run_report_dir, exist_ok=True)
            
            # Generate report components
            report = {
                "benchmark_run": benchmark_run.run_id,
                "dataset_name": benchmark_run.dataset_name,
                "timestamp": benchmark_run.run_timestamp,
                "total_samples": benchmark_run.total_samples,
                "status": benchmark_run.status,
                "duration_seconds": benchmark_run.duration_seconds,
            }
            
            # Get the summary
            try:
                summary = BenchmarkSummary.objects.get(benchmark_run=benchmark_run)
                report["summary"] = {
                    "total_cost": summary.total_cost_your_platform,
                    "total_gpt4_cost": summary.total_cost_gpt4_baseline,
                    "total_claude_cost": summary.total_cost_claude_baseline,
                    "cost_savings_vs_gpt4": summary.cost_savings_vs_gpt4_percent,
                    "cost_savings_vs_claude": summary.cost_savings_vs_claude_percent,
                    "avg_quality_retention": summary.avg_quality_retention,
                    "model_distribution": summary.model_distribution,
                    "complexity_distribution": summary.complexity_distribution,
                }
            except BenchmarkSummary.DoesNotExist:
                report["summary"] = None
            
            # Generate visualizations if available
            if self.visualization_available:
                visualization_paths = self._generate_visualizations(benchmark_run, run_report_dir)
                report["visualizations"] = visualization_paths
            else:
                report["visualizations"] = None
            
            # Export results to CSV
            csv_path = self._export_to_csv(benchmark_run, run_report_dir)
            report["csv_export"] = csv_path
            
            # Export results to JSON
            json_path = self._export_to_json(benchmark_run, run_report_dir)
            report["json_export"] = json_path
            
            # Generate summary report
            summary_path = self._generate_summary_report(benchmark_run, run_report_dir)
            report["summary_report"] = summary_path
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report for benchmark run {benchmark_run_id}: {str(e)}")
            raise
    
    def _generate_visualizations(self, benchmark_run: BenchmarkRun, report_dir: str) -> Dict[str, str]:
        """Generate visualizations for a benchmark run.
        
        Args:
            benchmark_run: BenchmarkRun instance
            report_dir: Directory to store visualizations
            
        Returns:
            Dictionary mapping visualization names to file paths
        """
        visualization_paths = {}
        
        # Get results
        results = BenchmarkResult.objects.filter(benchmark_run=benchmark_run)
        
        if not results.exists():
            return visualization_paths
        
        # Create a pandas DataFrame from results
        data = []
        for result in results:
            data.append({
                'sample_id': result.sample_id,
                'complexity_score': result.complexity_score,
                'complexity_level': result.complexity_level,
                'selected_model': result.selected_model,
                'estimated_cost': result.estimated_cost,
                'execution_time_ms': result.execution_time_ms,
                'semantic_similarity_vs_gpt4': result.semantic_similarity_vs_gpt4,
                'semantic_similarity_vs_claude': result.semantic_similarity_vs_claude,
                'quality_retained': result.quality_retained,
                'quality_confidence': result.quality_confidence,
            })
        
        df = pd.DataFrame(data)
        
        # 1. Model distribution pie chart
        try:
            plt.figure(figsize=(10, 6))
            model_counts = df['selected_model'].value_counts()
            plt.pie(model_counts, labels=model_counts.index, autopct='%1.1f%%')
            plt.title('Model Distribution')
            pie_chart_path = os.path.join(report_dir, 'model_distribution.png')
            plt.savefig(pie_chart_path)
            plt.close()
            visualization_paths['model_distribution'] = pie_chart_path
        except Exception as e:
            logger.error(f"Error generating model distribution chart: {str(e)}")
        
        # 2. Complexity distribution histogram
        try:
            plt.figure(figsize=(10, 6))
            plt.hist(df['complexity_score'], bins=10)
            plt.title('Complexity Score Distribution')
            plt.xlabel('Complexity Score')
            plt.ylabel('Count')
            complexity_hist_path = os.path.join(report_dir, 'complexity_distribution.png')
            plt.savefig(complexity_hist_path)
            plt.close()
            visualization_paths['complexity_distribution'] = complexity_hist_path
        except Exception as e:
            logger.error(f"Error generating complexity distribution chart: {str(e)}")
        
        # 3. Quality retention by complexity level
        try:
            plt.figure(figsize=(10, 6))
            quality_by_complexity = df.groupby('complexity_level')['quality_retained'].mean()
            quality_by_complexity.plot(kind='bar')
            plt.title('Quality Retention by Complexity Level')
            plt.xlabel('Complexity Level')
            plt.ylabel('Quality Retention Rate')
            quality_bar_path = os.path.join(report_dir, 'quality_by_complexity.png')
            plt.savefig(quality_bar_path)
            plt.close()
            visualization_paths['quality_by_complexity'] = quality_bar_path
        except Exception as e:
            logger.error(f"Error generating quality by complexity chart: {str(e)}")
        
        # 4. Execution time by model
        try:
            plt.figure(figsize=(10, 6))
            execution_time_by_model = df.groupby('selected_model')['execution_time_ms'].mean()
            execution_time_by_model.plot(kind='bar')
            plt.title('Average Execution Time by Model')
            plt.xlabel('Model')
            plt.ylabel('Execution Time (ms)')
            time_bar_path = os.path.join(report_dir, 'execution_time_by_model.png')
            plt.savefig(time_bar_path)
            plt.close()
            visualization_paths['execution_time_by_model'] = time_bar_path
        except Exception as e:
            logger.error(f"Error generating execution time chart: {str(e)}")
        
        # 5. Semantic similarity comparison
        try:
            plt.figure(figsize=(10, 6))
            similarity_data = {
                'vs GPT-4': df['semantic_similarity_vs_gpt4'].mean(),
                'vs Claude': df['semantic_similarity_vs_claude'].mean()
            }
            plt.bar(similarity_data.keys(), similarity_data.values())
            plt.title('Average Semantic Similarity')
            plt.xlabel('Baseline')
            plt.ylabel('Similarity Score')
            plt.ylim(0, 1)
            similarity_bar_path = os.path.join(report_dir, 'semantic_similarity.png')
            plt.savefig(similarity_bar_path)
            plt.close()
            visualization_paths['semantic_similarity'] = similarity_bar_path
        except Exception as e:
            logger.error(f"Error generating semantic similarity chart: {str(e)}")
        
        return visualization_paths
    
    def _export_to_csv(self, benchmark_run: BenchmarkRun, report_dir: str) -> str:
        """Export benchmark results to CSV.
        
        Args:
            benchmark_run: BenchmarkRun instance
            report_dir: Directory to store the CSV file
            
        Returns:
            Path to the CSV file
        """
        csv_path = os.path.join(report_dir, f"benchmark_results_{benchmark_run.run_id}.csv")
        
        # Get results
        results = BenchmarkResult.objects.filter(benchmark_run=benchmark_run)
        
        if not results.exists():
            return csv_path
        
        # Write to CSV
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'sample_id', 'input_text', 'expected_output', 'complexity_score', 
                'complexity_level', 'selected_model', 'estimated_cost', 
                'actual_response', 'execution_time_ms', 'gpt4_response', 
                'gpt4_cost', 'claude_response', 'claude_cost', 
                'semantic_similarity_vs_gpt4', 'semantic_similarity_vs_claude', 
                'quality_retained', 'quality_confidence'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'sample_id': result.sample_id,
                    'input_text': result.input_text[:100] + '...' if len(result.input_text) > 100 else result.input_text,
                    'expected_output': result.expected_output[:100] + '...' if result.expected_output and len(result.expected_output) > 100 else result.expected_output,
                    'complexity_score': result.complexity_score,
                    'complexity_level': result.complexity_level,
                    'selected_model': result.selected_model,
                    'estimated_cost': result.estimated_cost,
                    'actual_response': result.actual_response[:100] + '...' if len(result.actual_response) > 100 else result.actual_response,
                    'execution_time_ms': result.execution_time_ms,
                    'gpt4_response': result.gpt4_response[:100] + '...' if len(result.gpt4_response) > 100 else result.gpt4_response,
                    'gpt4_cost': result.gpt4_cost,
                    'claude_response': result.claude_response[:100] + '...' if len(result.claude_response) > 100 else result.claude_response,
                    'claude_cost': result.claude_cost,
                    'semantic_similarity_vs_gpt4': result.semantic_similarity_vs_gpt4,
                    'semantic_similarity_vs_claude': result.semantic_similarity_vs_claude,
                    'quality_retained': result.quality_retained,
                    'quality_confidence': result.quality_confidence
                })
        
        return csv_path
    
    def _export_to_json(self, benchmark_run: BenchmarkRun, report_dir: str) -> str:
        """Export benchmark results to JSON.
        
        Args:
            benchmark_run: BenchmarkRun instance
            report_dir: Directory to store the JSON file
            
        Returns:
            Path to the JSON file
        """
        json_path = os.path.join(report_dir, f"benchmark_results_{benchmark_run.run_id}.json")
        
        # Get results
        results = BenchmarkResult.objects.filter(benchmark_run=benchmark_run)
        
        if not results.exists():
            with open(json_path, 'w') as f:
                json.dump({"results": []}, f, cls=DjangoJSONEncoder)
            return json_path
        
        # Convert results to JSON-serializable format
        json_results = []
        for result in results:
            json_results.append({
                'sample_id': result.sample_id,
                'input_text': result.input_text,
                'expected_output': result.expected_output,
                'complexity_score': result.complexity_score,
                'complexity_level': result.complexity_level,
                'complexity_reasoning': result.complexity_reasoning,
                'routing_decision': result.routing_decision,
                'selected_model': result.selected_model,
                'estimated_cost': result.estimated_cost,
                'actual_response': result.actual_response,
                'execution_time_ms': result.execution_time_ms,
                'gpt4_response': result.gpt4_response,
                'gpt4_cost': result.gpt4_cost,
                'claude_response': result.claude_response,
                'claude_cost': result.claude_cost,
                'semantic_similarity_vs_gpt4': result.semantic_similarity_vs_gpt4,
                'semantic_similarity_vs_claude': result.semantic_similarity_vs_claude,
                'quality_retained': result.quality_retained,
                'quality_confidence': result.quality_confidence
            })
        
        # Get summary if available
        try:
            summary = BenchmarkSummary.objects.get(benchmark_run=benchmark_run)
            json_summary = {
                'total_cost': summary.total_cost_your_platform,
                'total_gpt4_cost': summary.total_cost_gpt4_baseline,
                'total_claude_cost': summary.total_cost_claude_baseline,
                'cost_savings_vs_gpt4': summary.cost_savings_vs_gpt4_percent,
                'cost_savings_vs_claude': summary.cost_savings_vs_claude_percent,
                'avg_quality_retention': summary.avg_quality_retention,
                'model_distribution': summary.model_distribution,
                'complexity_distribution': summary.complexity_distribution,
            }
        except BenchmarkSummary.DoesNotExist:
            json_summary = None
        
        # Write to JSON
        with open(json_path, 'w') as f:
            json.dump({
                "benchmark_run": str(benchmark_run.run_id),
                "dataset_name": benchmark_run.dataset_name,
                "timestamp": benchmark_run.timestamp.isoformat(),
                "total_samples": benchmark_run.total_samples,
                "status": benchmark_run.status,
                "duration_seconds": benchmark_run.duration_seconds,
                "summary": json_summary,
                "results": json_results
            }, f, cls=DjangoJSONEncoder)
        
        return json_path
    
    def _generate_summary_report(self, benchmark_run: BenchmarkRun, report_dir: str) -> str:
        """Generate a summary report in markdown format.
        
        Args:
            benchmark_run: BenchmarkRun instance
            report_dir: Directory to store the report
            
        Returns:
            Path to the summary report
        """
        report_path = os.path.join(report_dir, f"summary_report_{benchmark_run.run_id}.md")
        
        # Get summary if available
        try:
            summary = BenchmarkSummary.objects.get(benchmark_run=benchmark_run)
        except BenchmarkSummary.DoesNotExist:
            summary = None
        
        # Write the report
        with open(report_path, 'w') as f:
            f.write(f"# Benchmark Summary Report\n\n")
            f.write(f"## Run Information\n\n")
            f.write(f"- **Run ID**: {benchmark_run.run_id}\n")
            f.write(f"- **Dataset**: {benchmark_run.dataset_name}\n")
            f.write(f"- **Timestamp**: {benchmark_run.run_timestamp}\n")
            f.write(f"- **Total Samples**: {benchmark_run.total_samples}\n")
            f.write(f"- **Status**: {benchmark_run.status}\n")
            f.write(f"- **Duration**: {benchmark_run.duration_seconds} seconds\n\n")
            
            if summary:
                f.write(f"## Cost Analysis\n\n")
                f.write(f"- **Total Platform Cost**: ${summary.total_cost_your_platform:.6f}\n")
                f.write(f"- **Total GPT-4 Cost**: ${summary.total_cost_gpt4_baseline:.6f}\n")
                f.write(f"- **Total Claude Cost**: ${summary.total_cost_claude_baseline:.6f}\n")
                f.write(f"- **Cost Savings vs GPT-4**: {summary.cost_savings_vs_gpt4_percent:.2f}%\n")
                f.write(f"- **Cost Savings vs Claude**: {summary.cost_savings_vs_claude_percent:.2f}%\n\n")
                
                f.write(f"## Quality Analysis\n\n")
                f.write(f"- **Average Quality Retention**: {summary.avg_quality_retention:.2f}%\n\n")
                
                f.write(f"## Model Distribution\n\n")
                f.write("```\n")
                f.write(json.dumps(summary.model_distribution, indent=2))
                f.write("\n```\n\n")
                
                f.write(f"## Complexity Distribution\n\n")
                f.write("```\n")
                f.write(json.dumps(summary.complexity_distribution, indent=2))
                f.write("\n```\n\n")
            
            # Add links to exported files
            f.write(f"## Exported Files\n\n")
            f.write(f"- [CSV Export](./benchmark_results_{benchmark_run.run_id}.csv)\n")
            f.write(f"- [JSON Export](./benchmark_results_{benchmark_run.run_id}.json)\n\n")
            
            # Add links to visualizations if available
            if self.visualization_available:
                f.write(f"## Visualizations\n\n")
                f.write(f"- [Model Distribution](./model_distribution.png)\n")
                f.write(f"- [Complexity Distribution](./complexity_distribution.png)\n")
                f.write(f"- [Quality by Complexity](./quality_by_complexity.png)\n")
                f.write(f"- [Execution Time by Model](./execution_time_by_model.png)\n")
                f.write(f"- [Semantic Similarity](./semantic_similarity.png)\n\n")
        
        return report_path
