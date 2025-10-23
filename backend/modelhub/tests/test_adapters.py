import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
import json
import asyncio

from modelhub.adapters.base import BaseLLMAdapter, LLMResponse


class TestLLMResponse(unittest.TestCase):
    """Test cases for the LLMResponse class."""

    def test_llm_response_initialization(self):
        """Test that LLMResponse can be initialized with proper attributes."""
        response = LLMResponse(
            content="This is a test response",
            tokens_input=10,
            tokens_output=20,
            latency_ms=150,
            cost=Decimal('0.001'),
            raw_response={"id": "test-id", "choices": [{"text": "This is a test response"}]}
        )
        
        self.assertEqual(response.content, "This is a test response")
        self.assertEqual(response.tokens_input, 10)
        self.assertEqual(response.tokens_output, 20)
        self.assertEqual(response.latency_ms, 150)
        self.assertEqual(response.cost, Decimal('0.001'))
        self.assertEqual(response.raw_response["id"], "test-id")
    
    def test_llm_response_without_raw_response(self):
        """Test that LLMResponse can be initialized without raw_response."""
        response = LLMResponse(
            content="This is a test response",
            tokens_input=10,
            tokens_output=20,
            latency_ms=150,
            cost=Decimal('0.001')
        )
        
        self.assertEqual(response.content, "This is a test response")
        self.assertEqual(response.raw_response, {})


class MockLLMAdapter(BaseLLMAdapter):
    """Mock implementation of BaseLLMAdapter for testing."""
    
    async def complete(self, prompt, **kwargs):
        """Mock implementation of complete method."""
        return LLMResponse(
            content=f"Completion for: {prompt}",
            tokens_input=len(prompt.split()),
            tokens_output=len(f"Completion for: {prompt}".split()),
            latency_ms=100,
            cost=Decimal('0.001')
        )
    
    async def chat(self, messages, **kwargs):
        """Mock implementation of chat method."""
        last_message = messages[-1]["content"] if messages else ""
        return LLMResponse(
            content=f"Response to: {last_message}",
            tokens_input=sum(len(m.get("content", "").split()) for m in messages),
            tokens_output=len(f"Response to: {last_message}".split()),
            latency_ms=120,
            cost=Decimal('0.002')
        )
    
    def count_tokens(self, text):
        """Mock implementation of count_tokens method."""
        return len(text.split())
    
    def validate_response(self, response):
        """Mock implementation of validate_response method."""
        if not response:
            raise ValueError("Response cannot be empty")


class TestBaseLLMAdapter(unittest.TestCase):
    """Test cases for the BaseLLMAdapter class."""

    def setUp(self):
        """Set up test data."""
        self.api_key = "test-api-key"
        self.model_config = {
            "name": "test-model",
            "temperature": 0.7,
            "max_tokens": 100
        }
        self.provider_config = {
            "base_url": "https://api.example.com/v1",
            "timeout": 30
        }
        self.adapter = MockLLMAdapter(
            api_key=self.api_key,
            model_config=self.model_config,
            provider_config=self.provider_config
        )

    def test_adapter_initialization(self):
        """Test that BaseLLMAdapter can be initialized with proper attributes."""
        self.assertEqual(self.adapter.api_key, self.api_key)
        self.assertEqual(self.adapter.model_config, self.model_config)
        self.assertEqual(self.adapter.provider_config, self.provider_config)

    def test_complete_method(self):
        """Test the complete method."""
        prompt = "This is a test prompt"
        
        # Run the async method in a synchronous context for testing
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.adapter.complete(prompt))
        
        self.assertEqual(response.content, "Completion for: This is a test prompt")
        self.assertEqual(response.tokens_input, 5)  # 5 words in the prompt
        self.assertEqual(response.tokens_output, 7)  # 7 words in the response
        self.assertEqual(response.latency_ms, 100)
        self.assertEqual(response.cost, Decimal('0.001'))

    def test_chat_method(self):
        """Test the chat method."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        # Run the async method in a synchronous context for testing
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.adapter.chat(messages))
        
        self.assertEqual(response.content, "Response to: Hello, how are you?")
        self.assertEqual(response.tokens_input, 8)  # 8 words total in messages
        self.assertEqual(response.tokens_output, 5)  # 5 words in the response
        self.assertEqual(response.latency_ms, 120)
        self.assertEqual(response.cost, Decimal('0.002'))

    def test_count_tokens_method(self):
        """Test the count_tokens method."""
        text = "This is a test text with multiple words"
        token_count = self.adapter.count_tokens(text)
        self.assertEqual(token_count, 8)  # 8 words in the text

    def test_validate_response_method(self):
        """Test the validate_response method."""
        # Valid response
        self.adapter.validate_response("Valid response")
        
        # Invalid response
        with self.assertRaises(ValueError):
            self.adapter.validate_response(None)


# Test with a more realistic adapter implementation
class TestOpenAIAdapter(unittest.TestCase):
    """Test cases for a hypothetical OpenAI adapter implementation."""
    
    @patch('modelhub.adapters.openai_adapter.OpenAIAdapter.complete')
    async def test_openai_complete(self, mock_complete):
        """Test the OpenAI adapter complete method with mocks."""
        # This test assumes there's an OpenAIAdapter class in modelhub.adapters.openai_adapter
        # If not, this is just an example of how you would test it
        
        # Set up the mock
        mock_response = LLMResponse(
            content="This is a mock OpenAI response",
            tokens_input=5,
            tokens_output=6,
            latency_ms=200,
            cost=Decimal('0.002'),
            raw_response={
                "id": "cmpl-123",
                "object": "text_completion",
                "model": "text-davinci-003",
                "choices": [{"text": "This is a mock OpenAI response"}]
            }
        )
        mock_complete.return_value = mock_response
        
        # Import the adapter (this would fail if the adapter doesn't exist)
        try:
            from modelhub.adapters.openai_adapter import OpenAIAdapter
            
            # Create the adapter
            adapter = OpenAIAdapter(
                api_key="sk-test",
                model_config={"name": "text-davinci-003"},
                provider_config={}
            )
            
            # Call the method
            response = await adapter.complete("Test prompt")
            
            # Check the response
            self.assertEqual(response.content, "This is a mock OpenAI response")
            self.assertEqual(response.tokens_input, 5)
            self.assertEqual(response.tokens_output, 6)
            self.assertEqual(response.latency_ms, 200)
            self.assertEqual(response.cost, Decimal('0.002'))
            
        except ImportError:
            # Skip the test if the adapter doesn't exist
            self.skipTest("OpenAIAdapter not implemented yet")


# Test adapter factory
class TestLLMAdapterFactory(unittest.TestCase):
    """Test cases for a hypothetical LLM adapter factory."""
    
    @patch('modelhub.adapters.factory.LLMAdapterFactory.get_adapter')
    def test_adapter_factory(self, mock_get_adapter):
        """Test the adapter factory with mocks."""
        # This test assumes there's an LLMAdapterFactory class in modelhub.adapters.factory
        # If not, this is just an example of how you would test it
        
        # Set up the mock
        mock_adapter = MockLLMAdapter(
            api_key="test-api-key",
            model_config={},
            provider_config={}
        )
        mock_get_adapter.return_value = mock_adapter
        
        # Import the factory (this would fail if the factory doesn't exist)
        try:
            from modelhub.adapters.factory import LLMAdapterFactory
            
            # Create the factory
            factory = LLMAdapterFactory()
            
            # Get an adapter
            adapter = factory.get_adapter(
                provider="openai",
                model="text-davinci-003",
                api_key="test-api-key"
            )
            
            # Check the adapter
            self.assertIsInstance(adapter, MockLLMAdapter)
            
        except ImportError:
            # Skip the test if the factory doesn't exist
            self.skipTest("LLMAdapterFactory not implemented yet")
