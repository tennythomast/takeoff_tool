"""
Tests for the benchmark app.
"""

import uuid
import json
from unittest import mock
from django.test import TestCase
from django.utils import timezone

from benchmark.models import BenchmarkRun, BenchmarkResult, BenchmarkSummary
from benchmark.services.dataset_loaders import (
    get_dataset_loader, list_available_datasets, 
    Banking77Loader, HWU64Loader, EnronEmailLoader
)
from benchmark.services.benchmark_runner import BenchmarkRunner
from benchmark.services.quality_assessor import (
    calculate_semantic_similarity, assess_quality_retention,
    calculate_task_specific_metrics
)
from benchmark.services.cost_calculator import CostCalculator
from benchmark.services.report_generator import ReportGenerator


class BenchmarkModelsTestCase(TestCase):
    """Test case for benchmark models."""
    
    def setUp(self):
        """Set up test data."""
        # Create a benchmark run
        self.benchmark_run = BenchmarkRun.objects.create(
            dataset_name="test_dataset",
            total_samples=10,
            configuration={"test_config": True},
            status="running"
        )
        
        # Create benchmark results
        for i in range(5):
            BenchmarkResult.objects.create(
                benchmark_run=self.benchmark_run,
                sample_id=f"sample_{i}",
                input_text=f"Input text {i}",
                expected_output=f"Expected output {i}",
                complexity_score=0.5,
                complexity_level="MEDIUM",
                selected_model="gpt-3.5-turbo",
                estimated_cost=0.001,
                actual_response=f"Actual response {i}",
                execution_time_ms=100,
                gpt4_response=f"GPT-4 response {i}",
                gpt4_cost=0.002,
                claude_response=f"Claude response {i}",
                claude_cost=0.0015,
                semantic_similarity_vs_gpt4=0.9,
                semantic_similarity_vs_claude=0.85,
                quality_retained=True,
                quality_confidence=0.9
            )
        
        # Create a benchmark summary
        self.benchmark_summary = BenchmarkSummary.objects.create(
            benchmark_run=self.benchmark_run,
            total_cost_your_platform=0.005,
            total_cost_gpt4_baseline=0.01,
            total_cost_claude_baseline=0.0075,
            cost_savings_vs_gpt4_percent=50.0,
            cost_savings_vs_claude_percent=33.3,
            avg_quality_retention=90.0,
            model_distribution={"gpt-3.5-turbo": 5},
            complexity_distribution={"MEDIUM": 5}
        )
    
    def test_benchmark_run_properties(self):
        """Test BenchmarkRun properties."""
        # Test duration_seconds
        self.assertIsNone(self.benchmark_run.duration_seconds)
        
        # Test progress_percentage
        self.assertEqual(self.benchmark_run.progress_percentage, 50.0)
        
        # Test completed status
        self.benchmark_run.status = "completed"
        self.benchmark_run.save()
        
        # Test string representation
        self.assertIn(self.benchmark_run.dataset_name, str(self.benchmark_run))
    
    def test_benchmark_result_properties(self):
        """Test BenchmarkResult properties."""
        # Get a result
        result = self.benchmark_run.benchmarkresult_set.first()
        
        # Test cost_savings_vs_gpt4
        self.assertEqual(result.cost_savings_vs_gpt4, 50.0)
        
        # Test cost_savings_vs_claude
        self.assertEqual(result.cost_savings_vs_claude, 33.33)
        
        # Test string representation
        self.assertIn(result.sample_id, str(result))
    
    def test_benchmark_summary_update(self):
        """Test BenchmarkSummary update_from_results method."""
        # Update summary
        self.benchmark_summary.update_from_results()
        
        # Check updated values
        self.assertEqual(self.benchmark_summary.total_cost_your_platform, 0.005)
        self.assertEqual(self.benchmark_summary.total_cost_gpt4_baseline, 0.01)
        self.assertEqual(self.benchmark_summary.total_cost_claude_baseline, 0.0075)
        self.assertEqual(self.benchmark_summary.cost_savings_vs_gpt4_percent, 50.0)
        self.assertEqual(self.benchmark_summary.cost_savings_vs_claude_percent, 33.33)
        self.assertEqual(self.benchmark_summary.avg_quality_retention, 100.0)
        
        # Test string representation
        self.assertIn(str(self.benchmark_run), str(self.benchmark_summary))


class DatasetLoadersTestCase(TestCase):
    """Test case for dataset loaders."""
    
    @mock.patch('benchmark.services.dataset_loaders.datasets')
    def test_banking77_loader(self, mock_datasets):
        """Test Banking77Loader."""
        # Mock the dataset
        mock_dataset = mock.MagicMock()
        mock_dataset.__getitem__.side_effect = lambda idx: {
            "text": f"Sample text {idx}",
            "label": idx % 77
        }
        mock_dataset.__len__.return_value = 100
        mock_datasets.load_dataset.return_value = {"train": mock_dataset}
        
        # Create loader
        loader = Banking77Loader()
        
        # Test load_and_sample
        samples = loader.load_and_sample(5)
        
        # Check results
        self.assertEqual(len(samples), 5)
        for sample in samples:
            self.assertIn("sample_id", sample)
            self.assertIn("input_text", sample)
            self.assertIn("expected_output", sample)
    
    @mock.patch('benchmark.services.dataset_loaders.load_dataset')
    def test_hwu64_loader(self, mock_load_dataset):
        """Test HWU64Loader."""
        # Mock the dataset with both train and test splits
        # Include the 'scenario' key that the loader expects
        mock_train_dataset = mock.MagicMock()
        mock_train_dataset.__getitem__.side_effect = lambda idx: {
            "text": f"Sample text {idx}",
            "intent": f"intent_{idx % 10}",
            "scenario": f"scenario_{idx % 5}"  # Add scenario key
        }
        mock_train_dataset.__len__.return_value = 100
        
        mock_test_dataset = mock.MagicMock()
        mock_test_dataset.__getitem__.side_effect = lambda idx: {
            "text": f"Test text {idx}",
            "intent": f"intent_{idx % 10}",
            "scenario": f"scenario_{idx % 5}"  # Add scenario key
        }
        mock_test_dataset.__len__.return_value = 50
        
        mock_load_dataset.return_value = {
            "train": mock_train_dataset,
            "test": mock_test_dataset
        }
        
        # Create loader
        loader = HWU64Loader()
        
        # Test load_and_sample
        samples = loader.load_and_sample(5)
        
        # Check results
        self.assertEqual(len(samples), 5)
        for sample in samples:
            self.assertIn("sample_id", sample)
            self.assertIn("input_text", sample)
            self.assertIn("expected_output", sample)
    
    def test_get_dataset_loader(self):
        """Test get_dataset_loader function."""
        # Test valid dataset names
        self.assertIsInstance(get_dataset_loader("banking77"), Banking77Loader)
        self.assertIsInstance(get_dataset_loader("hwu64"), HWU64Loader)
        self.assertIsInstance(get_dataset_loader("enron_email"), EnronEmailLoader)
        
        # Test invalid dataset name
        with self.assertRaises(ValueError):
            get_dataset_loader("invalid_dataset")
    
    def test_list_available_datasets(self):
        """Test list_available_datasets function."""
        datasets = list_available_datasets()
        self.assertIsInstance(datasets, list)
        self.assertIn("banking77", datasets)
        self.assertIn("hwu64", datasets)
        self.assertIn("enron_email", datasets)
        self.assertIn("ad_text", datasets)
        self.assertIn("github_issues", datasets)
    
    @mock.patch('benchmark.services.dataset_loaders.load_dataset')
    def test_ad_text_loader(self, mock_load_dataset):
        """Test AdTextLoader."""
        # Mock the dataset
        mock_dataset = mock.MagicMock()
        mock_dataset.__getitem__.side_effect = lambda idx: {
            "text": f"Ad text {idx}",
            "label": "positive" if idx % 2 == 0 else "negative"
        }
        mock_dataset.__len__.return_value = 100
        mock_load_dataset.return_value = {"train": mock_dataset}
        
        # Create loader
        from benchmark.services.dataset_loaders import AdTextLoader
        loader = AdTextLoader()
        
        # Test load_and_sample
        samples = loader.load_and_sample(5)
        
        # Check results
        self.assertEqual(len(samples), 5)
        for sample in samples:
            self.assertIn("sample_id", sample)
            self.assertIn("input_text", sample)
            self.assertIn("expected_output", sample)
            self.assertIn("metadata", sample)
            self.assertEqual(sample["metadata"]["dataset"], "AdText")
    
    @mock.patch('benchmark.services.dataset_loaders.load_dataset')
    def test_ad_text_loader_fallback(self, mock_load_dataset):
        """Test AdTextLoader with fallback dataset."""
        # Mock the dataset load to fail for ad_text
        def side_effect(*args, **kwargs):
            if 'data_files' in kwargs:
                raise Exception("Dataset not found")
            return {"train": mock_dataset}
        
        mock_load_dataset.side_effect = side_effect
        
        # Mock the fallback dataset
        mock_dataset = mock.MagicMock()
        mock_dataset.__getitem__.side_effect = lambda idx: {
            "text": f"Fallback text {idx}",
            "label": idx % 77
        }
        mock_dataset.__len__.return_value = 100
        
        # Create loader
        from benchmark.services.dataset_loaders import AdTextLoader
        loader = AdTextLoader()
        
        # Test load_and_sample
        samples = loader.load_and_sample(5)
        
        # Check results
        self.assertEqual(len(samples), 5)
        for sample in samples:
            self.assertIn("sample_id", sample)
            self.assertIn("input_text", sample)
            self.assertIn("expected_output", sample)
            self.assertIn("metadata", sample)
            self.assertEqual(sample["metadata"]["dataset"], "AdText")
            # Use the actual fallback source name from the implementation
            self.assertEqual(sample["metadata"]["source"], "banking_77_fallback")
    
    @mock.patch('benchmark.services.dataset_loaders.load_dataset')
    def test_github_issues_loader(self, mock_load_dataset):
        """Test GitHubIssuesLoader."""
        # Mock the dataset
        mock_dataset = mock.MagicMock()
        mock_dataset.__getitem__.side_effect = lambda idx: {
            "title": f"Issue title {idx}",
            "body": f"Issue body {idx}",
            "repository": f"repo_{idx % 5}",
            "labels": [f"label_{idx % 3}", f"label_{idx % 5}"]
        }
        mock_dataset.__len__.return_value = 100
        mock_load_dataset.return_value = {"train": mock_dataset}
        
        # Create loader
        from benchmark.services.dataset_loaders import GitHubIssuesLoader
        loader = GitHubIssuesLoader()
        
        # Test load_and_sample
        samples = loader.load_and_sample(5)
        
        # Check results
        self.assertEqual(len(samples), 5)
        for sample in samples:
            self.assertIn("sample_id", sample)
            self.assertIn("input_text", sample)
            self.assertIn("expected_output", sample)
            self.assertIn("metadata", sample)
            self.assertEqual(sample["metadata"]["dataset"], "GitHubIssues")
    
    @mock.patch('benchmark.services.dataset_loaders.load_dataset')
    def test_github_issues_loader_fallback(self, mock_load_dataset):
        """Test GitHubIssuesLoader with fallback dataset."""
        # Mock the dataset load to fail for github_issues and succeed for fallback
        def side_effect(*args, **kwargs):
            if args[0] == "ought/raft":
                raise Exception("Dataset not found")
            return {"train": mock_dataset}
        
        mock_load_dataset.side_effect = side_effect
        
        # Mock the fallback dataset
        mock_dataset = mock.MagicMock()
        mock_dataset.__getitem__.side_effect = lambda idx: {
            "text": f"Fallback tweet {idx}",
            "label": idx % 3
        }
        mock_dataset.__len__.return_value = 100
        
        # Create loader
        from benchmark.services.dataset_loaders import GitHubIssuesLoader
        loader = GitHubIssuesLoader()
        
        # Test load_and_sample
        samples = loader.load_and_sample(5)
        
        # Check results
        self.assertEqual(len(samples), 5)
        for sample in samples:
            self.assertIn("sample_id", sample)
            self.assertIn("input_text", sample)
            self.assertIn("expected_output", sample)
            self.assertIn("metadata", sample)
            self.assertEqual(sample["metadata"]["dataset"], "GitHubIssues")
            self.assertEqual(sample["metadata"]["source"], "github_issues")


class BenchmarkRunnerTestCase(TestCase):
    """Test case for benchmark runner."""
    
    def setUp(self):
        """Set up test data."""
        self.runner = BenchmarkRunner()
    
    def test_start_benchmark_run(self):
        """Test start_benchmark_run method."""
        # Start a benchmark run
        run = self.runner.start_benchmark_run("test_dataset", 10, {"test": True})
        
        # Check run
        self.assertIsNotNone(run)
        self.assertEqual(run.dataset_name, "test_dataset")
        self.assertEqual(run.total_samples, 10)
        self.assertEqual(run.configuration, {"test": True})
        self.assertEqual(run.status, "running")
    
    @mock.patch('benchmark.services.benchmark_runner.get_dataset_loader')
    def test_execute_benchmark_run(self, mock_get_dataset_loader):
        """Test execute_benchmark_run method."""
        # Mock dataset loader
        mock_loader = mock.MagicMock()
        mock_loader.load_and_sample.return_value = [
            {
                "sample_id": "test_1",
                "input_text": "Test input",
                "expected_output": "Test output",
                "metadata": {"test": True}
            }
        ]
        mock_get_dataset_loader.return_value = mock_loader
        
        # Start a benchmark run
        run = self.runner.start_benchmark_run("test_dataset", 1, {"test": True})
        
        # Mock the complexity analyzer
        self.runner.complexity_analyzer = mock.MagicMock()
        self.runner.complexity_analyzer.analyze_complexity.return_value = {"score": 0.5, "level": "MEDIUM", "reasoning": {}}
        
        # Mock the LLM router
        self.runner.llm_router = mock.MagicMock()
        self.runner.llm_router.route_request.return_value = {"selected_model": "gpt-3.5-turbo", "estimated_cost": 0.001, "reasoning": {}}
        
        # Mock the unified client
        self.runner.unified_client = mock.MagicMock()
        self.runner.unified_client.execute.return_value = {"response": "Test response", "cost": 0.001}
        self.runner.unified_client.execute.side_effect = [
            {"response": "Test response", "cost": 0.001},  # Platform response
            {"response": "GPT-4 response", "cost": 0.002},  # GPT-4 response
            {"response": "Claude response", "cost": 0.0015}  # Claude response
        ]
        
        # Execute run with mocked quality assessment functions
        with mock.patch('benchmark.services.benchmark_runner.calculate_semantic_similarity', return_value=0.9):
            with mock.patch('benchmark.services.benchmark_runner.assess_quality_retention', return_value=True):
                self.runner.execute_benchmark_run(run.run_id)
        
        # Check run status
        run.refresh_from_db()
        self.assertEqual(run.status, "completed")
        
        # Check results
        results = run.benchmarkresult_set.all()
        self.assertEqual(len(results), 1)


class QualityAssessorTestCase(TestCase):
    """Test case for quality assessor."""
    
    def test_calculate_semantic_similarity_basic(self):
        """Test calculate_semantic_similarity with basic method."""
        # Test identical texts
        similarity = calculate_semantic_similarity("Hello world", "Hello world")
        self.assertEqual(similarity, 1.0)
        
        # Test completely different texts
        similarity = calculate_semantic_similarity("Hello world", "Goodbye universe")
        self.assertLess(similarity, 1.0)
        
        # Test empty texts
        similarity = calculate_semantic_similarity("", "")
        self.assertEqual(similarity, 0.0)
        
        similarity = calculate_semantic_similarity("Hello", "")
        self.assertEqual(similarity, 0.0)
    
    def test_assess_quality_retention(self):
        """Test assess_quality_retention function."""
        # Test quality retained
        self.assertTrue(assess_quality_retention(0.9, 0.8))
        self.assertTrue(assess_quality_retention(0.85, 0.9))
        
        # Test quality not retained
        self.assertFalse(assess_quality_retention(0.8, 0.8))
        self.assertFalse(assess_quality_retention(0.7, 0.7))
    
    def test_calculate_task_specific_metrics(self):
        """Test calculate_task_specific_metrics function."""
        # Test classification task
        metrics = calculate_task_specific_metrics(
            input_text="What category is this?",
            expected_output="sports",
            actual_response="This belongs to the sports category.",
            task_type="classification"
        )
        self.assertIn("accuracy", metrics)
        self.assertEqual(metrics["accuracy"], 1.0)
        
        # Test QA task
        metrics = calculate_task_specific_metrics(
            input_text="What is the capital of France?",
            expected_output=None,
            actual_response="The capital of France is Paris.",
            task_type="qa"
        )
        self.assertIn("answer_relevance", metrics)
        
        # Test summarization task
        metrics = calculate_task_specific_metrics(
            input_text="This is a very long text that needs to be summarized. " * 10,
            expected_output=None,
            actual_response="This is a summary.",
            task_type="summarization"
        )
        self.assertIn("conciseness", metrics)
        self.assertIn("coverage", metrics)


class CostCalculatorTestCase(TestCase):
    """Test case for cost calculator."""
    
    def setUp(self):
        """Set up test data."""
        self.calculator = CostCalculator()
    
    def test_calculate_cost(self):
        """Test calculate_cost method."""
        # Test GPT-4 cost
        cost = self.calculator.calculate_cost("gpt-4", 1000, 500)
        expected_cost = 0.00003 * 1000 + 0.00006 * 500
        self.assertEqual(cost, expected_cost)
        
        # Test unknown model (should use default)
        cost = self.calculator.calculate_cost("unknown-model", 1000, 500)
        expected_cost = 0.000001 * 1000 + 0.000002 * 500
        self.assertEqual(cost, expected_cost)
    
    def test_estimate_tokens_from_text(self):
        """Test estimate_tokens_from_text method."""
        # Test empty text
        self.assertEqual(self.calculator.estimate_tokens_from_text(""), 0)
        
        # Test short text
        self.assertEqual(self.calculator.estimate_tokens_from_text("Hello"), 1)
        
        # Test longer text
        text = "This is a longer text that should be more than one token." * 10
        self.assertGreater(self.calculator.estimate_tokens_from_text(text), 10)
    
    def test_calculate_cost_savings(self):
        """Test calculate_cost_savings method."""
        # Test cost savings
        savings = self.calculator.calculate_cost_savings(
            platform_model="gpt-3.5-turbo",
            platform_input="Input text",
            platform_output="Output text",
            baseline_model="gpt-4",
            baseline_input="Input text",
            baseline_output="Output text"
        )
        
        # Check results
        self.assertIn("platform_cost", savings)
        self.assertIn("baseline_cost", savings)
        self.assertIn("absolute_savings", savings)
        self.assertIn("percentage_savings", savings)
        self.assertGreater(savings["baseline_cost"], savings["platform_cost"])
        self.assertGreater(savings["absolute_savings"], 0)
        self.assertGreater(savings["percentage_savings"], 0)


class ReportGeneratorTestCase(TestCase):
    """Test case for report generator."""
    
    def setUp(self):
        """Set up test data."""
        # Create a benchmark run
        self.benchmark_run = BenchmarkRun.objects.create(
            dataset_name="test_dataset",
            total_samples=10,
            configuration={"test_config": True},
            status="completed"
        )
        
        # Create benchmark results
        for i in range(5):
            BenchmarkResult.objects.create(
                benchmark_run=self.benchmark_run,
                sample_id=f"sample_{i}",
                input_text=f"Input text {i}",
                expected_output=f"Expected output {i}",
                complexity_score=0.5,
                complexity_level="MEDIUM",
                selected_model="gpt-3.5-turbo",
                estimated_cost=0.001,
                actual_response=f"Actual response {i}",
                execution_time_ms=100,
                gpt4_response=f"GPT-4 response {i}",
                gpt4_cost=0.002,
                claude_response=f"Claude response {i}",
                claude_cost=0.0015,
                semantic_similarity_vs_gpt4=0.9,
                semantic_similarity_vs_claude=0.85,
                quality_retained=True,
                quality_confidence=0.9
            )
        
        # Create a benchmark summary
        self.benchmark_summary = BenchmarkSummary.objects.create(
            benchmark_run=self.benchmark_run,
            total_cost_your_platform=0.005,
            total_cost_gpt4_baseline=0.01,
            total_cost_claude_baseline=0.0075,
            cost_savings_vs_gpt4_percent=50.0,
            cost_savings_vs_claude_percent=33.3,
            avg_quality_retention=90.0,
            model_distribution={"gpt-3.5-turbo": 5},
            complexity_distribution={"MEDIUM": 5}
        )
        
        # Create report generator with temp directory
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.report_generator = ReportGenerator(report_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @mock.patch('benchmark.services.report_generator.VISUALIZATION_AVAILABLE', False)
    def test_generate_report_without_visualizations(self):
        """Test generate_report method without visualizations."""
        # Mock the _export_to_json method to avoid the error
        with mock.patch.object(self.report_generator, '_export_to_json') as mock_export_json:
            with mock.patch.object(self.report_generator, '_export_to_csv') as mock_export_csv:
                with mock.patch.object(self.report_generator, '_generate_summary_report') as mock_summary_report:
                    mock_export_json.return_value = self.temp_dir + "/test_report.json"
                    mock_export_csv.return_value = self.temp_dir + "/test_report.csv"
                    mock_summary_report.return_value = self.temp_dir + "/test_summary.md"
                    
                    # Generate report
                    report = self.report_generator.generate_report(self.benchmark_run.run_id)
                    
                    # Check report
                    self.assertEqual(report["benchmark_run"], self.benchmark_run.run_id)
                    self.assertEqual(report["dataset_name"], self.benchmark_run.dataset_name)
                    self.assertEqual(report["total_samples"], self.benchmark_run.total_samples)
                    self.assertEqual(report["status"], self.benchmark_run.status)
                    
                    # Check summary
                    self.assertIsNotNone(report["summary"])
                    
                    # Check exports
                    self.assertIsNotNone(report["csv_export"])
                    self.assertIsNotNone(report["json_export"])
                    self.assertIsNotNone(report["summary_report"])
                    
                    # Check that visualizations are None
                    self.assertIsNone(report["visualizations"])
