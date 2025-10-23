"""
Cost calculator service for benchmark results.

This service is responsible for:
1. Calculating costs for different models
2. Comparing costs between platform and baseline models
3. Calculating cost savings
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import json

logger = logging.getLogger(__name__)

# Default cost per token for different models (in USD)
# These are approximate and should be updated with actual values
DEFAULT_COST_PER_TOKEN = {
    # OpenAI models
    "gpt-4": {
        "input": 0.00003,  # $0.03 per 1K input tokens
        "output": 0.00006,  # $0.06 per 1K output tokens
    },
    "gpt-4-turbo": {
        "input": 0.00001,  # $0.01 per 1K input tokens
        "output": 0.00003,  # $0.03 per 1K output tokens
    },
    "gpt-3.5-turbo": {
        "input": 0.000001,  # $0.001 per 1K input tokens
        "output": 0.000002,  # $0.002 per 1K output tokens
    },
    # Anthropic models
    "claude-3-opus": {
        "input": 0.00001,  # $0.01 per 1K input tokens
        "output": 0.00003,  # $0.03 per 1K output tokens
    },
    "claude-3-sonnet": {
        "input": 0.000003,  # $0.003 per 1K input tokens
        "output": 0.000015,  # $0.015 per 1K output tokens
    },
    "claude-3-haiku": {
        "input": 0.000000125,  # $0.00125 per 1K input tokens
        "output": 0.000000375,  # $0.00375 per 1K output tokens
    },
    # Open source models (hosted)
    "mixtral-8x7b": {
        "input": 0.0000006,  # $0.0006 per 1K input tokens
        "output": 0.0000006,  # $0.0006 per 1K output tokens
    },
    "llama-3-70b": {
        "input": 0.0000009,  # $0.0009 per 1K input tokens
        "output": 0.0000009,  # $0.0009 per 1K output tokens
    },
    # Default fallback
    "default": {
        "input": 0.000001,  # $0.001 per 1K input tokens
        "output": 0.000002,  # $0.002 per 1K output tokens
    }
}


class CostCalculator:
    """Service for calculating and comparing costs."""
    
    def __init__(self, custom_cost_config: Optional[Dict[str, Any]] = None):
        """Initialize the cost calculator.
        
        Args:
            custom_cost_config: Optional custom cost configuration
        """
        self.cost_per_token = DEFAULT_COST_PER_TOKEN.copy()
        
        # Update with custom cost config if provided
        if custom_cost_config:
            self._update_cost_config(custom_cost_config)
    
    def _update_cost_config(self, custom_config: Dict[str, Any]) -> None:
        """Update the cost configuration with custom values.
        
        Args:
            custom_config: Custom cost configuration
        """
        for model, costs in custom_config.items():
            if model not in self.cost_per_token:
                self.cost_per_token[model] = {"input": 0, "output": 0}
            
            for cost_type, value in costs.items():
                if cost_type in ["input", "output"]:
                    self.cost_per_token[model][cost_type] = value
    
    def calculate_cost(
        self, 
        model_name: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> float:
        """Calculate the cost for a specific model and token counts.
        
        Args:
            model_name: Name of the model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        # Get cost per token for the model, or use default if not found
        model_costs = self.cost_per_token.get(model_name, self.cost_per_token["default"])
        
        # Calculate total cost
        input_cost = model_costs["input"] * input_tokens
        output_cost = model_costs["output"] * output_tokens
        total_cost = input_cost + output_cost
        
        return total_cost
    
    def estimate_tokens_from_text(self, text: str) -> int:
        """Estimate the number of tokens in a text.
        
        This is a simple estimation. For production, consider using tiktoken or similar.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated number of tokens
        """
        if not text:
            return 0
        
        # Simple estimation: ~4 characters per token for English text
        return max(1, len(text) // 4)
    
    def calculate_cost_from_text(
        self, 
        model_name: str, 
        input_text: str, 
        output_text: str
    ) -> Dict[str, Any]:
        """Calculate the cost for a specific model based on input and output text.
        
        Args:
            model_name: Name of the model
            input_text: Input text
            output_text: Output text
            
        Returns:
            Dictionary with cost details
        """
        # Estimate token counts
        input_tokens = self.estimate_tokens_from_text(input_text)
        output_tokens = self.estimate_tokens_from_text(output_text)
        
        # Calculate cost
        total_cost = self.calculate_cost(model_name, input_tokens, output_tokens)
        
        return {
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": self.cost_per_token.get(model_name, self.cost_per_token["default"])["input"] * input_tokens,
            "output_cost": self.cost_per_token.get(model_name, self.cost_per_token["default"])["output"] * output_tokens,
            "total_cost": total_cost
        }
    
    def calculate_cost_savings(
        self, 
        platform_model: str, 
        platform_input: str, 
        platform_output: str,
        baseline_model: str,
        baseline_input: str,
        baseline_output: str
    ) -> Dict[str, Any]:
        """Calculate cost savings between platform and baseline.
        
        Args:
            platform_model: Platform model name
            platform_input: Platform input text
            platform_output: Platform output text
            baseline_model: Baseline model name
            baseline_input: Baseline input text
            baseline_output: Baseline output text
            
        Returns:
            Dictionary with cost savings details
        """
        # Calculate costs
        platform_cost_details = self.calculate_cost_from_text(
            platform_model, platform_input, platform_output
        )
        baseline_cost_details = self.calculate_cost_from_text(
            baseline_model, baseline_input, baseline_output
        )
        
        # Calculate savings
        absolute_savings = baseline_cost_details["total_cost"] - platform_cost_details["total_cost"]
        
        # Calculate percentage savings (avoid division by zero)
        if baseline_cost_details["total_cost"] > 0:
            percentage_savings = (absolute_savings / baseline_cost_details["total_cost"]) * 100
        else:
            percentage_savings = 0
        
        return {
            "platform_model": platform_model,
            "baseline_model": baseline_model,
            "platform_cost": platform_cost_details["total_cost"],
            "baseline_cost": baseline_cost_details["total_cost"],
            "absolute_savings": absolute_savings,
            "percentage_savings": percentage_savings,
            "platform_details": platform_cost_details,
            "baseline_details": baseline_cost_details
        }
    
    def calculate_aggregate_savings(
        self, 
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate aggregate cost savings across multiple results.
        
        Args:
            results: List of cost savings results
            
        Returns:
            Dictionary with aggregate savings details
        """
        if not results:
            return {
                "total_platform_cost": 0.0,
                "total_baseline_cost": 0.0,
                "total_absolute_savings": 0.0,
                "average_percentage_savings": 0.0,
                "sample_count": 0
            }
        
        # Sum up costs and savings
        total_platform_cost = sum(r["platform_cost"] for r in results)
        total_baseline_cost = sum(r["baseline_cost"] for r in results)
        total_absolute_savings = sum(r["absolute_savings"] for r in results)
        
        # Calculate average percentage savings
        percentage_savings = [r["percentage_savings"] for r in results]
        average_percentage_savings = sum(percentage_savings) / len(percentage_savings)
        
        return {
            "total_platform_cost": total_platform_cost,
            "total_baseline_cost": total_baseline_cost,
            "total_absolute_savings": total_absolute_savings,
            "average_percentage_savings": average_percentage_savings,
            "sample_count": len(results)
        }
