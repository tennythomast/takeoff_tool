# File: backend/modelhub/services/unified_llm_client.py

import time
import logging
import traceback
import importlib
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union, AsyncGenerator
from abc import ABC, abstractmethod

from channels.db import database_sync_to_async
from ..adapters.base import LLMResponse

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def call_api(
        self, 
        model_name: str, 
        api_key: str, 
        messages: Optional[List[Dict[str, str]]], 
        prompt: Optional[str], 
        api_type: str,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        """Call the provider's API
        
        Args:
            model_name: Name of the model to use
            api_key: API key for authentication
            messages: List of chat messages (for chat models)
            prompt: Text prompt (for completion models)
            api_type: Type of API to use (CHAT or COMPLETION)
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            If stream=False: A single LLMResponse with the complete response
            If stream=True: An AsyncGenerator yielding LLMResponse objects for each chunk
        """
        pass
    
    def get_required_modules(self) -> List[str]:
        """Return list of required module names for dynamic imports"""
        return []


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation (also handles OpenAI-compatible APIs)"""
    
    def get_required_modules(self) -> List[str]:
        return ['openai']
    
    async def call_api(
        self, 
        model_name: str, 
        api_key: str, 
        messages: Optional[List[Dict[str, str]]], 
        prompt: Optional[str], 
        api_type: str,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        try:
            # Dynamic import
            openai = importlib.import_module('openai')
            AsyncOpenAI = getattr(openai, 'AsyncOpenAI')
        except ImportError as e:
            raise ImportError(f"OpenAI library not installed: {e}")
        
        start_time = time.time()
        stream_id = None
        
        if stream:
            # Generate a unique stream ID if streaming
            stream_id = f"stream_{int(time.time())}_{model_name.replace('-', '_')}"
            
        # Get provider config to check for custom base URL
        provider_slug = kwargs.get('provider_slug', 'openai')
        base_url = None
        
        logger.info(f"OpenAIProvider.call_api - provider_slug: {provider_slug}")
        
        if provider_slug != 'openai':
            # Get custom base URL for OpenAI-compatible providers
            provider_config = await UnifiedLLMClient._get_provider_config(provider_slug)
            logger.info(f"Provider config for {provider_slug}: {provider_config}")
            if provider_config and provider_config.get('config'):
                base_url = provider_config['config'].get('base_url')
                logger.info(f"Extracted base_url: {base_url}")
        
        # Create client with optional custom base URL
        client_kwargs = {'api_key': api_key}
        if base_url:
            client_kwargs['base_url'] = base_url
            logger.info(f"Using custom base URL for {provider_slug}: {base_url}")
        else:
            logger.warning(f"No base_url set for {provider_slug}, will use default OpenAI endpoint")
        
        try:
            client = AsyncOpenAI(**client_kwargs)
            
            # Set default max_tokens if not provided
            if 'max_tokens' not in kwargs:
                kwargs['max_tokens'] = 1000
            
            if api_type == 'CHAT':
                if prompt and not messages:
                    messages = [{'role': 'user', 'content': prompt}]
                
                if not messages:
                    raise ValueError("Chat models require messages format")
                
                # Handle streaming mode
                if stream:
                    async def process_stream():
                        content_so_far = ""
                        tokens_output = 0
                        
                        # Create streaming response
                        openai_kwargs = {k: v for k, v in kwargs.items() 
                                        if k not in ['provider_slug']}

                        stream_response = await client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            stream=True,
                            **openai_kwargs
)
                        
                        # Process each chunk
                        async for chunk in stream_response:
                            if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                                content_delta = chunk.choices[0].delta.content or ""
                                content_so_far += content_delta
                                tokens_output += 1  # Approximate token count
                                
                                # Calculate elapsed time for each chunk
                                current_latency_ms = int((time.time() - start_time) * 1000)
                                
                                # Yield each chunk as an LLMResponse
                                yield LLMResponse(
                                    content=content_delta,
                                    tokens_input=len(messages),  # Approximate for streaming
                                    tokens_output=1,  # Each chunk is roughly one token
                                    latency_ms=current_latency_ms,
                                    cost=Decimal('0.00'),  # Cost calculated later
                                    raw_response={'chunk': chunk.model_dump() if hasattr(chunk, 'model_dump') else {'chunk': str(chunk)}},
                                    is_streaming=True,
                                    stream_id=stream_id
                                )
                        
                        # Final response with complete content
                        final_latency_ms = int((time.time() - start_time) * 1000)
                        yield LLMResponse(
                            content=content_so_far,
                            tokens_input=len(messages) * 4,  # Approximate
                            tokens_output=tokens_output,
                            latency_ms=final_latency_ms,
                            cost=Decimal('0.00'),  # Cost calculated later
                            raw_response={'complete': True},
                            is_streaming=True,
                            stream_id=stream_id
                        )
                    
                    return process_stream()
                else:
                    # Non-streaming mode (original behavior)
                    openai_kwargs = {k: v for k, v in kwargs.items() 
                                    if k not in ['provider_slug']}

                    response = await client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        **openai_kwargs
                    )
                    
                    # Add detailed logging of the raw response object
                    logger.debug(f"Raw OpenAI response object: {response}")
                    logger.debug(f"Response type: {type(response)}")
                    logger.debug(f"Response dir: {dir(response)}")
                    
                    # Check if response has choices attribute
                    if hasattr(response, 'choices') and response.choices:
                        logger.debug(f"Response has choices: {response.choices}")
                        if len(response.choices) > 0 and hasattr(response.choices[0], 'message'):
                            logger.debug(f"First choice message: {response.choices[0].message}")
                    else:
                        logger.error(f"Response missing choices attribute or empty choices: {response}")
                    
                    content = response.choices[0].message.content
                    tokens_input = response.usage.prompt_tokens
                    tokens_output = response.usage.completion_tokens
                
            elif api_type == 'COMPLETION':
                if messages and not prompt:
                    prompt_parts = []
                    for msg in messages:
                        if msg['role'] == 'system':
                            prompt_parts.append(f"System: {msg['content']}")
                        elif msg['role'] == 'user':
                            prompt_parts.append(f"Human: {msg['content']}")
                        elif msg['role'] == 'assistant':
                            prompt_parts.append(f"Assistant: {msg['content']}")
                    prompt = "\n".join(prompt_parts) + "\nAssistant:"
                
                if not prompt:
                    raise ValueError("Text completion models require prompt format")
                
                # Handle streaming for completions
                if stream:
                    async def process_completion_stream():
                        content_so_far = ""
                        tokens_output = 0
                                                
                        openai_kwargs = {k: v for k, v in kwargs.items() 
                                        if k not in ['provider_slug']}

                        stream_response = await client.completions.create(
                            model=model_name,
                            prompt=prompt,
                            stream=True,
                            **openai_kwargs
                        )
                        
                        # Process each chunk
                        async for chunk in stream_response:
                            if hasattr(chunk.choices[0], 'text'):
                                content_delta = chunk.choices[0].text or ""
                                content_so_far += content_delta
                                tokens_output += 1  # Approximate
                                
                                # Calculate elapsed time for each chunk
                                current_latency_ms = int((time.time() - start_time) * 1000)
                                
                                # Yield each chunk
                                yield LLMResponse(
                                    content=content_delta,
                                    tokens_input=len(prompt) // 4,  # Approximate
                                    tokens_output=1,
                                    latency_ms=current_latency_ms,
                                    cost=Decimal('0.00'),
                                    raw_response={'chunk': chunk.model_dump() if hasattr(chunk, 'model_dump') else {'chunk': str(chunk)}},
                                    is_streaming=True,
                                    stream_id=stream_id
                                )
                        
                        # Final response
                        final_latency_ms = int((time.time() - start_time) * 1000)
                        yield LLMResponse(
                            content=content_so_far,
                            tokens_input=len(prompt) // 4,
                            tokens_output=tokens_output,
                            latency_ms=final_latency_ms,
                            cost=Decimal('0.00'),
                            raw_response={'complete': True},
                            is_streaming=True,
                            stream_id=stream_id
                        )
                    
                    return process_completion_stream()
                else:
                    # Non-streaming mode
                    response = await client.completions.create(
                        model=model_name,
                        prompt=prompt,
                        **kwargs
                    )
                    content = response.choices[0].text
                    tokens_input = response.usage.prompt_tokens
                    tokens_output = response.usage.completion_tokens
                
            else:
                raise ValueError(f"Unsupported API type: {api_type}")
            
            # Only reached in non-streaming mode
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Calculate actual cost based on token usage
            calculated_cost = await UnifiedLLMClient._calculate_cost(
                provider_slug='openai',
                model_name=model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output
            )
            
            return LLMResponse(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                cost=calculated_cost,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else {'response': str(response)}
            )
            
        except Exception as e:
            error_type = type(e).__name__
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Enhanced error logging for debugging RunPod/OpenAI-compatible API issues
            logger.error(f"OpenAI API error: {e}")
            logger.error(f"Error type: {error_type}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            
            # For provider-specific debugging
            if provider_slug != 'openai':
                logger.error(f"Provider-specific error for {provider_slug} using OpenAI-compatible API")
                if base_url:
                    logger.error(f"Using custom base URL: {base_url}")
            
            return LLMResponse(
                content=f"Error: {str(e)}",
                tokens_input=0,
                tokens_output=0,
                latency_ms=latency_ms,
                cost=Decimal('0.00'),
                raw_response={"error": str(e), "type": error_type, "traceback": traceback.format_exc()}
            )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider implementation with proper max_tokens handling"""
    
    def get_required_modules(self) -> List[str]:
        return ['anthropic']
    
    async def call_api(
        self, 
        model_name: str, 
        api_key: str, 
        messages: Optional[List[Dict[str, str]]], 
        prompt: Optional[str], 
        api_type: str,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        try:
            # Dynamic import
            anthropic = importlib.import_module('anthropic')
            AsyncAnthropic = getattr(anthropic, 'AsyncAnthropic')
        except ImportError as e:
            raise ImportError(f"Anthropic library not installed: {e}")
        
        start_time = time.time()
        
        try:
            client = AsyncAnthropic(api_key=api_key)
            
            # Convert prompt to messages if needed
            if prompt and not messages:
                messages = [{'role': 'user', 'content': prompt}]
            
            if not messages:
                raise ValueError("Anthropic requires messages format")
            
            # Process messages for Anthropic format
            anthropic_messages = []
            system_content = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] in ["user", "assistant"]:
                    anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
            
            # CRITICAL FIX: Ensure max_tokens is always set for Anthropic
            # Anthropic API requires max_tokens parameter
            max_tokens = kwargs.get('max_tokens', 1000)  # Default to 1000 if not provided
            
            # Prepare API call with required parameters
            call_kwargs = {
                'model': model_name,
                'messages': anthropic_messages,
                'max_tokens': max_tokens,  # This is REQUIRED for Anthropic
            }
            
            # Add system message if present
            if system_content:
                call_kwargs['system'] = system_content
            
            # Add other parameters (excluding max_tokens to avoid duplication)
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['max_tokens', 'stream_callback']}
            call_kwargs.update(filtered_kwargs)
            
            logger.debug(f"Anthropic API call: model={model_name}, max_tokens={max_tokens}, messages_count={len(anthropic_messages)}")
            
            # Generate a unique stream ID if streaming
            stream_id = None
            if stream:
                stream_id = f"stream_{int(time.time())}_{model_name.replace('-', '_')}"
                call_kwargs['stream'] = True
                
                async def process_stream():
                    content_so_far = ""
                    tokens_input = 0
                    tokens_output = 0
                    chunk_count = 0
                    
                    try:
                        # Create streaming response
                        stream_response = await client.messages.create(**call_kwargs)
                        
                        # Process each chunk
                        async for chunk in stream_response:
                            chunk_count += 1
                            
                            # Extract token usage from message_start event
                            if hasattr(chunk, 'message') and hasattr(chunk.message, 'usage'):
                                usage = chunk.message.usage
                                if hasattr(usage, 'input_tokens'):
                                    tokens_input = usage.input_tokens
                                if hasattr(usage, 'output_tokens'):
                                    tokens_output = usage.output_tokens
                            
                            # Extract additional token usage from message_delta event
                            if hasattr(chunk, 'usage') and hasattr(chunk.usage, 'output_tokens'):
                                tokens_output = chunk.usage.output_tokens
                            
                            if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                                content_delta = chunk.delta.text or ""
                                content_so_far += content_delta
                                
                                # Calculate elapsed time for each chunk
                                current_latency_ms = int((time.time() - start_time) * 1000)
                                
                                # Yield each chunk
                                yield LLMResponse(
                                    content=content_delta,
                                    tokens_input=tokens_input,
                                    tokens_output=tokens_output,
                                    latency_ms=current_latency_ms,
                                    cost=Decimal('0.00'),
                                    raw_response={'chunk': chunk.model_dump() if hasattr(chunk, 'model_dump') else {'chunk': str(chunk)}},
                                    is_streaming=True,
                                    stream_id=stream_id
                                )

                            else:
                                # Skip chunks without text content (normal for streaming metadata events)
                                pass
                        
                        # Calculate cost using extracted token counts
                        await UnifiedLLMClient._calculate_cost(
                            provider_slug='anthropic',
                            model_name=model_name,
                            tokens_input=tokens_input,
                            tokens_output=tokens_output
                        )
                        
                        # Note: In streaming mode, we only yield individual chunks.
                        # The consumer will accumulate chunks and handle final metadata.
                        # This prevents duplication of the complete response.
                    except Exception as stream_error:
                        logger.error(f"Anthropic streaming error: {stream_error}")
                        # Yield an error response
                        yield LLMResponse(
                            content=f"Streaming error: {str(stream_error)}",
                            tokens_input=0,
                            tokens_output=0,
                            latency_ms=int((time.time() - start_time) * 1000),
                            cost=Decimal('0.00'),
                            raw_response={"error": str(stream_error)},
                            is_streaming=True,
                            stream_id=stream_id
                        )
                
                return process_stream()
            else:
                # Non-streaming mode (original behavior)
                response = await client.messages.create(**call_kwargs)
                
                # Extract content from response
                if hasattr(response, 'content') and len(response.content) > 0:
                    content = response.content[0].text
                else:
                    content = "No response content received"
                    logger.warning("Anthropic response had no content")
            
            # Estimate tokens (Anthropic doesn't provide exact counts in older versions)
            tokens_input = len(str(anthropic_messages)) // 4
            tokens_output = len(content) // 4
            
            # Try to get actual token usage if available
            if hasattr(response, 'usage'):
                if hasattr(response.usage, 'input_tokens'):
                    tokens_input = response.usage.input_tokens
                if hasattr(response.usage, 'output_tokens'):
                    tokens_output = response.usage.output_tokens
            
            # Calculate actual cost based on token usage
            calculated_cost = await UnifiedLLMClient._calculate_cost(
                provider_slug='anthropic',
                model_name=model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output
            )
            
            return LLMResponse(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=int((time.time() - start_time) * 1000),
                cost=calculated_cost,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else str(response)
            )
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Anthropic API error ({error_type}): {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Provide specific error messages for common issues
            if 'max_tokens' in str(e).lower():
                error_msg = f"Configuration error: max_tokens parameter issue. Value used: {kwargs.get('max_tokens', 'not provided')}"
            elif 'RateLimitError' in error_type:
                error_msg = "Rate limit exceeded. Please try again in a moment."
            elif 'AuthenticationError' in error_type:
                error_msg = "Authentication failed. Please check your API key."
            elif 'InvalidRequestError' in error_type:
                error_msg = f"Invalid request: {str(e)}"
            else:
                error_msg = f"Anthropic API error: {str(e)}"
                
            return LLMResponse(
                content=f"I'm having trouble with Anthropic services. {error_msg}",
                tokens_input=0,
                tokens_output=0,
                latency_ms=int((time.time() - start_time) * 1000),
                cost=Decimal('0.00'),
                raw_response={"error": str(e), "type": error_type}
            )


class GoogleProvider(BaseLLMProvider):
    """Provider for Google Gemini models"""
    
    def get_required_modules(self) -> List[str]:
        return ['google.generativeai']
    
    async def call_api(
        self, 
        model_name: str, 
        api_key: str, 
        messages: Optional[List[Dict[str, str]]], 
        prompt: Optional[str], 
        api_type: str,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Call Google Gemini API"""
        start_time = time.time()
        
        try:
            import google.generativeai as genai
            
            # Configure API key
            genai.configure(api_key=api_key)
            
            # Get the model
            model = genai.GenerativeModel(model_name)
            
            # Convert messages to Gemini format if needed
            if messages:
                # Combine messages into a single prompt
                prompt_parts = []
                for msg in messages:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role == 'system':
                        prompt_parts.append(f"System: {content}")
                    elif role == 'user':
                        prompt_parts.append(f"User: {content}")
                    elif role == 'assistant':
                        prompt_parts.append(f"Assistant: {content}")
                prompt = "\n\n".join(prompt_parts)
            
            # Set generation config
            generation_config = {
                'temperature': kwargs.get('temperature', 0.1),
                'max_output_tokens': kwargs.get('max_tokens', 8000),
            }
            
            # Generate content
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract content
            content = response.text if hasattr(response, 'text') else ''
            
            # Estimate tokens (Gemini provides usage metadata)
            tokens_input = 0
            tokens_output = 0
            
            if hasattr(response, 'usage_metadata'):
                tokens_input = getattr(response.usage_metadata, 'prompt_token_count', 0)
                tokens_output = getattr(response.usage_metadata, 'candidates_token_count', 0)
            else:
                # Fallback estimation
                tokens_input = len(prompt) // 4
                tokens_output = len(content) // 4
            
            # Calculate cost
            calculated_cost = await UnifiedLLMClient._calculate_cost(
                provider_slug='google',
                model_name=model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output
            )
            
            return LLMResponse(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=int((time.time() - start_time) * 1000),
                cost=calculated_cost,
                raw_response={'text': content, 'usage': {'input_tokens': tokens_input, 'output_tokens': tokens_output}}
            )
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Google API error ({error_type}): {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            return LLMResponse(
                content=f"I'm having trouble with Google Gemini services. {str(e)}",
                tokens_input=0,
                tokens_output=0,
                latency_ms=int((time.time() - start_time) * 1000),
                cost=Decimal('0.00'),
                raw_response={"error": str(e), "type": error_type}
            )


class UnifiedLLMClient:
    """Dynamic unified client for multiple LLM providers"""
    
    # Registry of available providers
    _provider_registry = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'qwen': OpenAIProvider,  # Qwen uses OpenAI-compatible API
        'google': GoogleProvider,  # Google Gemini with native API
    }
    
    @classmethod
    def register_provider(cls, slug: str, provider_class: type):
        """Register a new provider dynamically"""
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError("Provider must inherit from BaseLLMProvider")
        cls._provider_registry[slug] = provider_class
        logger.info(f"Registered new provider: {slug}")
    
    @staticmethod
    async def call_llm(
        provider_slug: str, 
        model_name: str, 
        api_key: str,
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMResponse, None]]:
        """Call the appropriate LLM based on provider slug"""
        
        # Validate inputs
        if not api_key or api_key.strip() == "" or api_key == "your-openai-key-here":
            logger.error(f"Invalid API key provided for {provider_slug} model {model_name}")
            return LLMResponse(
                content=f"I'm unable to access {provider_slug} services because no valid API key is configured. Please contact your administrator to set up API keys.",
                tokens_input=0,
                tokens_output=0,
                latency_ms=0,
                cost=Decimal('0.00'),
                raw_response={"error": f"Invalid API key for {provider_slug}"}
            )
            
        if not messages and not prompt:
            logger.error("No messages or prompt provided to LLM client")
            return LLMResponse(
                content="I encountered a technical issue. No prompt was provided to me.",
                tokens_input=0,
                tokens_output=0,
                latency_ms=0,
                cost=Decimal('0.00'),
                raw_response={"error": "No prompt or messages provided"}
            )
        
        start_time = time.time()
        try:
            logger.debug(f"Calling {provider_slug} model {model_name} with {'messages' if messages else 'prompt'}")
            
                # Set default max_tokens if not provided
            if 'max_tokens' not in kwargs:
                kwargs['max_tokens'] = 1000  # Default value for all providers
            
            provider_config = await UnifiedLLMClient._get_provider_config(provider_slug)

            if provider_config and provider_config.get('config', {}).get('api_type') == 'openai':
                # Use OpenAI provider for OpenAI-compatible APIs
                provider_class = UnifiedLLMClient._provider_registry.get('openai')
                kwargs['provider_slug'] = provider_slug  # Pass provider slug for custom base URL
            else:
                # Use the registered provider
                provider_class = UnifiedLLMClient._provider_registry.get(provider_slug)
            if not provider_class:
                # Try to get provider configuration from database
                provider_config = await UnifiedLLMClient._get_provider_config(provider_slug)
                
                if not provider_config:
                    logger.error(f"Unsupported provider: {provider_slug}")
                    return LLMResponse(
                        content=f"I'm unable to process your request because the provider '{provider_slug}' is not supported.",
                        tokens_input=0,
                        tokens_output=0,
                        latency_ms=int((time.time() - start_time) * 1000),
                        cost=Decimal('0.00'),
                        raw_response={"error": f"Unsupported provider: {provider_slug}"}
                    )
                
                # Try to load provider dynamically from config
                provider_class = await UnifiedLLMClient._load_provider_from_config(provider_config)
            
            # Get API type for the model
            api_type = await UnifiedLLMClient._get_api_type_for_model(provider_slug, model_name)
            
            # Instantiate and call provider
            provider = provider_class()
            response = await provider.call_api(
                model_name=model_name,
                api_key=api_key,
                messages=messages,
                prompt=prompt,
                api_type=api_type,
                stream=stream,
                **kwargs
            )
            
            # For streaming responses, return the generator directly
            if stream:
                # For streaming, we'll return the response generator directly
                # Cost will be calculated in the consumer for the final response
                return response
            else:
                # Calculate cost if response was successful (non-streaming)
                if response.content and not response.raw_response.get('error'):
                    cost = await UnifiedLLMClient._calculate_cost(
                        provider_slug, 
                        model_name, 
                        response.tokens_input, 
                        response.tokens_output
                    )
                    response.cost = cost
                
                return response
            
        except Exception as e:
            logger.error(f"Error calling {provider_slug} model {model_name}: {str(e)}")
            logger.error(traceback.format_exc())
            
            return LLMResponse(
                content=f"I'm currently having trouble connecting to {provider_slug} services. This might be due to API key issues, rate limits, or service availability. Please try again later or contact support if the issue persists.",
                tokens_input=0,
                tokens_output=0,
                latency_ms=int((time.time() - start_time) * 1000),
                cost=Decimal('0.00'),
                raw_response={"error": str(e)}
            )
    
    @staticmethod
    @database_sync_to_async
    def _get_provider_config(provider_slug: str) -> Optional[Dict]:
        """Get provider configuration from database"""
        try:
            from ..models import Provider
            provider = Provider.objects.get(slug=provider_slug, status='ACTIVE')
            return {
                'name': provider.name,
                'slug': provider.slug,
                'config': provider.config
            }
        except:
            return None
    
    @staticmethod
    @database_sync_to_async
    def _get_api_type_for_model(provider_slug: str, model_name: str) -> str:
        """Get API type for a specific model"""
        from ..models import Model
        return Model.get_api_type_for_model(provider_slug, model_name)
    
    @staticmethod
    @database_sync_to_async
    def _calculate_cost(provider_slug: str, model_name: str, tokens_input: int, tokens_output: int) -> Decimal:
        """Calculate cost based on token usage and model rates"""
        try:
            from ..models import Model
            model_obj = Model.objects.get(name=model_name, provider__slug=provider_slug)
            cost = (Decimal(str(tokens_input)) / 1000 * model_obj.cost_input + 
                   Decimal(str(tokens_output)) / 1000 * model_obj.cost_output)
            return cost
        except Model.DoesNotExist:
            logger.debug(f"Model {model_name} not found in database, using zero cost")
            return Decimal('0.00')
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return Decimal('0.00')
    
    @staticmethod
    async def _load_provider_from_config(provider_config: Dict) -> type:
        """Load provider class dynamically from configuration"""
        # This could be extended to load custom provider classes
        # For now, return None to indicate unsupported provider
        return None
    
    @staticmethod
    def get_supported_providers() -> List[str]:
        """Get list of supported provider slugs"""
        return list(UnifiedLLMClient._provider_registry.keys())
    
    @staticmethod
    async def validate_provider_setup(provider_slug: str) -> Dict[str, Any]:
        """Validate that a provider is properly set up"""
        try:
            provider_class = UnifiedLLMClient._provider_registry.get(provider_slug)
            if not provider_class:
                return {
                    'valid': False,
                    'error': f'Provider {provider_slug} not registered'
                }
            
            # Check required modules
            provider = provider_class()
            missing_modules = []
            
            for module_name in provider.get_required_modules():
                try:
                    importlib.import_module(module_name)
                except ImportError:
                    missing_modules.append(module_name)
            
            if missing_modules:
                return {
                    'valid': False,
                    'error': f'Missing required modules: {", ".join(missing_modules)}'
                }
            
            # Check database configuration
            provider_config = await UnifiedLLMClient._get_provider_config(provider_slug)
            if not provider_config:
                return {
                    'valid': False,
                    'error': f'Provider {provider_slug} not configured in database'
                }
            
            return {
                'valid': True,
                'config': provider_config
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }


# Example of how to add a new provider dynamically
class CustomProvider(BaseLLMProvider):
    """Example custom provider"""
    
    def get_required_modules(self) -> List[str]:
        return ['requests']  # or whatever modules your provider needs
    
    async def call_api(self, model_name: str, api_key: str, messages, prompt, api_type: str, **kwargs) -> LLMResponse:
        # Your custom implementation here
        # Make sure to handle max_tokens properly for your provider
        max_tokens = kwargs.get('max_tokens', 1000)
        
        return LLMResponse(
            content="Custom provider response",
            tokens_input=10,
            tokens_output=20,
            latency_ms=100,
            cost=Decimal('0.01'),
            raw_response={}
        )
