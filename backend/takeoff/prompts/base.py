"""
Base prompt class for all extraction prompts
"""

from typing import Dict, Any
from abc import ABC, abstractmethod


class BasePrompt(ABC):
    """
    Base class for all extraction prompts
    
    Provides common functionality and enforces a consistent interface
    for all extraction prompts.
    """
    
    name = "base_prompt"
    version = "0.0.0"
    description = "Base prompt class"
    
    @abstractmethod
    def render(self, **kwargs) -> str:
        """
        Render the prompt with the given variables
        
        Args:
            **kwargs: Variables to use in the prompt template
            
        Returns:
            Rendered prompt string
        """
        pass
    
    @abstractmethod
    def get_default_variables(self) -> Dict[str, Any]:
        """
        Get default variables for the prompt template
        
        Returns:
            Dictionary of default variables
        """
        pass
