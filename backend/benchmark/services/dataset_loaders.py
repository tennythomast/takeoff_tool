"""
Dataset loaders for benchmark app.

This module provides utilities for loading and sampling datasets for benchmarking.
Supported datasets:
- Banking77: Banking customer service queries
- HWU64: Human-robot dialogue dataset
- Enron: Email dataset
- AdText: Advertisement text dataset
- GitHub Issues: GitHub issue dataset
"""

import random
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np

# Try to import datasets, but don't fail if it's not installed
try:
    import datasets
    from datasets import load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    datasets = None
    DATASETS_AVAILABLE = False

logger = logging.getLogger(__name__)

class DatasetLoader:
    """Base class for dataset loaders."""
    
    def __init__(self, random_seed: int = 42):
        """Initialize the dataset loader.
        
        Args:
            random_seed: Random seed for reproducibility
        """
        self.random_seed = random_seed
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        if not DATASETS_AVAILABLE:
            logger.warning("HuggingFace datasets library not available. Please install it with: pip install datasets")
    
    def load_and_sample(self, sample_size: int) -> List[Dict[str, Any]]:
        """Load and sample the dataset.
        
        Args:
            sample_size: Number of samples to return
            
        Returns:
            List of samples
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def _convert_to_benchmark_format(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert samples to the benchmark format.
        
        Args:
            samples: List of samples
            
        Returns:
            List of samples in benchmark format
        """
        raise NotImplementedError("Subclasses must implement this method")


class Banking77Loader(DatasetLoader):
    """Loader for Banking77 dataset."""
    
    def load_and_sample(self, sample_size: int = 1000) -> List[Dict[str, Any]]:
        """Load and sample the Banking77 dataset.
        
        Args:
            sample_size: Number of samples to return
            
        Returns:
            List of samples
        """
        if not DATASETS_AVAILABLE:
            raise ImportError("HuggingFace datasets library not available. Please install it with: pip install datasets")
        
        # Load the dataset
        dataset = load_dataset("banking77")
        
        # Get the test split
        test_data = dataset["test"]
        
        # Sample from the test data
        if sample_size >= len(test_data):
            samples = test_data
            logger.warning(f"Requested sample size {sample_size} is larger than test set size {len(test_data)}. Using entire test set.")
        else:
            indices = random.sample(range(len(test_data)), sample_size)
            samples = [test_data[i] for i in indices]
        
        # Convert to benchmark format
        return self._convert_to_benchmark_format(samples)
    
    def _convert_to_benchmark_format(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Banking77 samples to the benchmark format.
        
        Args:
            samples: List of Banking77 samples
            
        Returns:
            List of samples in benchmark format
        """
        benchmark_samples = []
        
        for i, sample in enumerate(samples):
            benchmark_sample = {
                "sample_id": f"banking77_{i:04d}",
                "input_text": sample["text"],
                "expected_output": str(sample["label"]),  # Convert label to string
                "metadata": {
                    "dataset": "Banking77",
                    "intent_label": sample["label"],
                    "original_id": i
                }
            }
            benchmark_samples.append(benchmark_sample)
        
        return benchmark_samples


class HWU64Loader(DatasetLoader):
    """Loader for HWU64 dataset."""
    
    def load_and_sample(self, sample_size: int = 1000) -> List[Dict[str, Any]]:
        """Load and sample the HWU64 dataset.
        
        Args:
            sample_size: Number of samples to return
            
        Returns:
            List of samples
        """
        if not DATASETS_AVAILABLE:
            raise ImportError("HuggingFace datasets library not available. Please install it with: pip install datasets")
        
        # Load the dataset
        dataset = load_dataset("PolyAI/hwu64")
        
        # Get the test split
        test_data = dataset["test"]
        
        # Sample from the test data
        if sample_size >= len(test_data):
            samples = test_data
            logger.warning(f"Requested sample size {sample_size} is larger than test set size {len(test_data)}. Using entire test set.")
        else:
            indices = random.sample(range(len(test_data)), sample_size)
            samples = [test_data[i] for i in indices]
        
        # Convert to benchmark format
        return self._convert_to_benchmark_format(samples)
    
    def _convert_to_benchmark_format(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert HWU64 samples to the benchmark format.
        
        Args:
            samples: List of HWU64 samples
            
        Returns:
            List of samples in benchmark format
        """
        benchmark_samples = []
        
        for i, sample in enumerate(samples):
            benchmark_sample = {
                "sample_id": f"hwu64_{i:04d}",
                "input_text": sample["text"],
                "expected_output": sample["scenario"],  # Use scenario as expected output
                "metadata": {
                    "dataset": "HWU64",
                    "intent": sample["intent"],
                    "scenario": sample["scenario"],
                    "original_id": i
                }
            }
            benchmark_samples.append(benchmark_sample)
        
        return benchmark_samples


class EnronEmailLoader(DatasetLoader):
    """Loader for Enron Email dataset."""
    
    def load_and_sample(self, sample_size: int = 500) -> List[Dict[str, Any]]:
        """Load and sample the Enron Email dataset.
        
        Args:
            sample_size: Number of samples to return
            
        Returns:
            List of samples
        """
        if not DATASETS_AVAILABLE:
            raise ImportError("HuggingFace datasets library not available. Please install it with: pip install datasets")
        
        # Load the dataset
        dataset = load_dataset("enron_emails")
        
        # Get the train split (no test split available)
        data = dataset["train"]
        
        # Sample from the data
        if sample_size >= len(data):
            samples = data
            logger.warning(f"Requested sample size {sample_size} is larger than dataset size {len(data)}. Using entire dataset.")
        else:
            indices = random.sample(range(len(data)), sample_size)
            samples = [data[i] for i in indices]
        
        # Convert to benchmark format
        return self._convert_to_benchmark_format(samples)
    
    def _convert_to_benchmark_format(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Enron Email samples to the benchmark format.
        
        Args:
            samples: List of Enron Email samples
            
        Returns:
            List of samples in benchmark format
        """
        benchmark_samples = []
        
        for i, sample in enumerate(samples):
            # Use message body as input text, truncate if too long
            message_body = sample.get("message", "")
            if len(message_body) > 1000:  # Truncate long emails
                message_body = message_body[:1000] + "..."
            
            benchmark_sample = {
                "sample_id": f"enron_{i:04d}",
                "input_text": message_body,
                "expected_output": None,  # No expected output for this dataset
                "metadata": {
                    "dataset": "EnronEmail",
                    "subject": sample.get("subject", ""),
                    "sender": sample.get("sender", ""),
                    "date": sample.get("date", ""),
                    "original_id": i
                }
            }
            benchmark_samples.append(benchmark_sample)
        
        return benchmark_samples


class AdTextLoader(DatasetLoader):
    """Loader for Advertisement Text dataset."""
    
    def load_and_sample(self, sample_size: int = 500) -> List[Dict[str, Any]]:
        """Load and sample the Advertisement Text dataset.
        
        Args:
            sample_size: Number of samples to return
            
        Returns:
            List of samples
        """
        if not DATASETS_AVAILABLE:
            raise ImportError("HuggingFace datasets library not available. Please install it with: pip install datasets")
        
        # Load the dataset
        try:
            dataset = load_dataset("csv", data_files={"train": "https://raw.githubusercontent.com/quankiquanki/skytrax-reviews-dataset/master/data/airline.csv"})
            data_source = "airline_reviews"
        except Exception:
            # Fallback to another dataset if airline reviews not available
            dataset = load_dataset("ought/raft", "banking_77")
            data_source = "banking_77_fallback"
        
        # Get the train split
        data = dataset["train"]
        
        # Sample from the data
        if sample_size >= len(data):
            samples = data
            logger.warning(f"Requested sample size {sample_size} is larger than dataset size {len(data)}. Using entire dataset.")
        else:
            indices = random.sample(range(len(data)), sample_size)
            samples = [data[i] for i in indices]
        
        # Convert to benchmark format
        return self._convert_to_benchmark_format(samples, data_source)
    
    def _convert_to_benchmark_format(self, samples: List[Dict[str, Any]], data_source: str) -> List[Dict[str, Any]]:
        """Convert Advertisement Text samples to the benchmark format.
        
        Args:
            samples: List of Advertisement Text samples
            data_source: Source of the data
            
        Returns:
            List of samples in benchmark format
        """
        benchmark_samples = []
        
        for i, sample in enumerate(samples):
            if data_source == "airline_reviews":
                input_text = sample.get("content", "")
                metadata = {
                    "dataset": "AdText",
                    "source": "airline_reviews",
                    "airline": sample.get("airline", ""),
                    "rating": sample.get("rating", ""),
                    "original_id": i
                }
            else:  # banking_77_fallback
                input_text = sample.get("text", "")
                metadata = {
                    "dataset": "AdText",
                    "source": "banking_77_fallback",
                    "label": sample.get("label", ""),
                    "original_id": i
                }
            
            benchmark_sample = {
                "sample_id": f"adtext_{i:04d}",
                "input_text": input_text,
                "expected_output": None,  # No expected output for this dataset
                "metadata": metadata
            }
            benchmark_samples.append(benchmark_sample)
        
        return benchmark_samples


class GitHubIssuesLoader(DatasetLoader):
    """Loader for GitHub Issues dataset."""
    
    def load_and_sample(self, sample_size: int = 500) -> List[Dict[str, Any]]:
        """Load and sample the GitHub Issues dataset.
        
        Args:
            sample_size: Number of samples to return
            
        Returns:
            List of samples
        """
        if not DATASETS_AVAILABLE:
            raise ImportError("HuggingFace datasets library not available. Please install it with: pip install datasets")
        
        # Load the dataset
        try:
            dataset = load_dataset("scikit-learn/github-issues")
            data_source = "github_issues"
            # Get the train split
            data = dataset["train"]
        except Exception:
            # Fallback to another dataset - using banking_77 which we know works
            try:
                dataset = load_dataset("banking77")
                data_source = "banking77_fallback"
                logger.warning("GitHub Issues dataset not available. Using Banking77 dataset as fallback.")
                # Get the train split
                data = dataset["train"]
            except Exception:
                # Second fallback option
                dataset = load_dataset("csv", data_files={"train": "https://raw.githubusercontent.com/quankiquanki/skytrax-reviews-dataset/master/data/airline.csv"})
                data_source = "airline_reviews_fallback"
                logger.warning("GitHub Issues and Banking77 datasets not available. Using Airline Reviews dataset as fallback.")
                # Get the train split
                data = dataset["train"]
        
        # Sample from the data
        if sample_size >= len(data):
            samples = data
            logger.warning(f"Requested sample size {sample_size} is larger than dataset size {len(data)}. Using entire dataset.")
        else:
            indices = random.sample(range(len(data)), sample_size)
            samples = [data[i] for i in indices]
        
        # Convert to benchmark format
        return self._convert_to_benchmark_format(samples, data_source)
    
    def _convert_to_benchmark_format(self, samples: List[Dict[str, Any]], data_source: str) -> List[Dict[str, Any]]:
        """Convert GitHub Issues samples to the benchmark format.
        
        Args:
            samples: List of GitHub Issues samples
            data_source: Source of the data
            
        Returns:
            List of samples in benchmark format
        """
        benchmark_samples = []
        
        for i, sample in enumerate(samples):
            if data_source == "github_issues":
                # Extract title and body
                title = sample.get("title", "")
                body = sample.get("body", "")
                
                # Combine title and body
                input_text = f"{title}\n\n{body}"
                
                # Truncate if too long
                if len(input_text) > 1000:
                    input_text = input_text[:1000] + "..."
                
                metadata = {
                    "dataset": "GitHubIssues",
                    "source": "github_issues",
                    "repo": sample.get("repository", ""),
                    "labels": sample.get("labels", []),
                    "original_id": i
                }
            elif data_source == "banking77_fallback":
                input_text = sample.get("text", "")
                metadata = {
                    "dataset": "GitHubIssues",
                    "source": "banking77_fallback",
                    "label": sample.get("label", ""),
                    "original_id": i
                }
            else:  # airline_reviews_fallback
                input_text = sample.get("text", "")
                metadata = {
                    "dataset": "GitHubIssues",
                    "source": "airline_reviews_fallback",
                    "rating": sample.get("airline_sentiment", ""),
                    "original_id": i
                }
            
            benchmark_sample = {
                "sample_id": f"github_{i:04d}",
                "input_text": input_text,
                "expected_output": None,  # No expected output for this dataset
                "metadata": metadata
            }
            benchmark_samples.append(benchmark_sample)
        
        return benchmark_samples


def get_dataset_loader(dataset_name: str) -> DatasetLoader:
    """Get a dataset loader by name.
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        DatasetLoader instance
        
    Raises:
        ValueError: If dataset_name is not supported
    """
    dataset_loaders = {
        "banking77": Banking77Loader,
        "hwu64": HWU64Loader,
        "enron_email": EnronEmailLoader,
        "ad_text": AdTextLoader,
        "github_issues": GitHubIssuesLoader,
    }
    
    dataset_name_lower = dataset_name.lower()
    if dataset_name_lower not in dataset_loaders:
        raise ValueError(f"Dataset {dataset_name} not supported. Supported datasets: {', '.join(dataset_loaders.keys())}")
    
    return dataset_loaders[dataset_name_lower]()


def list_available_datasets() -> List[str]:
    """List all available datasets.
    
    Returns:
        List of dataset names
    """
    return ["banking77", "hwu64", "enron_email", "ad_text", "github_issues"]
