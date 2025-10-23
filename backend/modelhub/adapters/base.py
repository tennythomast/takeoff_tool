from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional, List


class LLMResponse:
    """Container for LLM response data"""
    def __init__(
        self,
        content: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: int,
        cost: Decimal,
        raw_response: Optional[Dict[str, Any]] = None,
        is_streaming: bool = False,
        stream_id: Optional[str] = None
    ):
        self.content = content
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.latency_ms = latency_ms
        self.cost = cost
        self.raw_response = raw_response or {}
        self.is_streaming = is_streaming
        self.stream_id = stream_id
        
    @property
    def text(self) -> str:
        """Alias for content to maintain compatibility with consumer code"""
        return self.content


class BaseLLMAdapter(ABC):
    """Base class for LLM provider adapters"""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Complete a text prompt"""
        pass

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Complete a chat conversation"""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        pass

    @abstractmethod
    def validate_response(self, response: Any) -> None:
        """Validate provider response"""
        pass
