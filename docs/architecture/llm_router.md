# LLMRouter Technical Architecture

This document provides a detailed technical overview of the LLMRouter implementation, focusing on its async architecture, error handling, and database interaction patterns.

## Overview

The LLMRouter is the central execution component in Dataelan's Model Hub, responsible for:

1. Routing requests to appropriate LLM models based on defined rules
2. Managing fallback mechanisms when models fail
3. Recording comprehensive metrics for all executions
4. Providing a consistent interface for all LLM operations

## Async Implementation

### Core Design Principles

The LLMRouter is built with asynchronous programming at its core:

1. **Async/Await Pattern**: All external operations (API calls, database operations) use async/await
2. **Non-Blocking Execution**: Long-running operations don't block the event loop
3. **Isolation of Synchronous Code**: Django ORM operations are isolated and wrapped appropriately
4. **Proper Error Propagation**: Errors are handled and propagated correctly in async contexts

### Database Operations

Django ORM operations are synchronous by nature but need to be used in an async context. We use a decorator pattern to handle this:

```python
def db_operation(func):
    """Decorator to wrap database operations in sync_to_async"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await sync_to_async(func)(*args, **kwargs)
    return wrapper
```

This decorator is applied to methods that interact with the database:

```python
@db_operation
def _create_metrics(self, model_id: int, api_key_id: Optional[str] = None,
                 response: Optional[LLMResponse] = None,
                 error: Optional[Exception] = None) -> None:
    """Create metrics record in the database"""
    # Implementation details...
```

### Execution Flow

The main execution method is fully async and orchestrates the entire process:

```python
async def execute(
    self,
    model_type: str,
    request_context: Dict[str, Any],
    prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    **kwargs
):
    """
    Execute an LLM request with fallback support
    """
    # Implementation details...
```

The execution flow follows these steps:

1. Get matching routing rules (async)
2. Select models based on rules (in-memory operation)
3. For each model:
   a. Get API key from APIKeyManager (async)
   b. Get appropriate adapter (in-memory operation)
   c. Execute request via adapter (async)
   d. Record metrics (async via decorator)
   e. Return response if successful
   f. Handle errors and try next model if appropriate

## Error Handling

### Error Classification

Errors are classified into two categories:

1. **Fallback Errors**: Errors that should trigger fallback to another model
   - `QuotaExceededError`: API quota exceeded
   - `AuthenticationError`: Invalid API key
   - `InvalidRequestError`: Malformed request

2. **Non-Fallback Errors**: Errors that should be propagated immediately
   - `ContextLengthError`: Input is too long for the model
   - `NoValidModelError`: No suitable models found
   - `NoValidAdapterError`: No adapter found for provider

### Error Type Standardization

Error types are standardized for consistent metrics recording:

```python
# Map error types to consistent format with underscores
if error:
    error_class = error.__class__.__name__.upper()
    error_mapping = {
        'CONTEXTLENGTHERROR': 'CONTEXT_LENGTH_ERROR',
        'QUOTAEXCEEDEDERROR': 'QUOTA_EXCEEDED',
        'AUTHENTICATIONERROR': 'AUTHENTICATION_ERROR',
        'INVALIDREQUESTERROR': 'INVALID_REQUEST',
        'NOVALIDMODELERROR': 'NO_VALID_MODEL',
        'NOVALIDADAPTERERROR': 'NO_VALID_ADAPTER'
    }
    error_type = error_mapping.get(error_class, error_class)
    error_message = str(error)
else:
    error_type = 'NONE'
    error_message = ''
```

### Fallback Mechanism

The fallback mechanism is implemented in the main execution loop:

```python
# Simplified example
tried_models = []
errors = []

for model in prioritized_models:
    try:
        # Execute request
        return response
    except (QuotaExceededError, AuthenticationError, InvalidRequestError) as e:
        # Record error and try next model
        tried_models.append(model)
        errors.append(e)
        continue
    except (ContextLengthError) as e:
        # Record error and propagate immediately
        await self._create_metrics(model.id, api_key_id, error=e)
        raise
```

## Metrics Recording

### Metrics Data Model

Metrics are recorded in the `ModelMetrics` table with these key fields:

- `model_id`: The model used
- `organization`: The organization making the request
- `api_key_id`: The API key used (optional)
- `latency_ms`: Request latency in milliseconds
- `tokens_input`: Number of input tokens
- `tokens_output`: Number of output tokens
- `cost`: Calculated cost of the request
- `status`: SUCCESS or ERROR
- `error_type`: Type of error if status is ERROR
- `error_message`: Detailed error message

### Metrics Recording Implementation

```python
# Create metrics record with optional API key
metrics_data = {
    'model_id': model_id,
    'organization': self.organization,
    'latency_ms': response.latency_ms if response else 0,
    'tokens_input': response.tokens_input if response else 0,
    'tokens_output': response.tokens_output if response else 0,
    'cost': response.cost if response else Decimal('0.00'),
    'status': status,
    'error_type': error_type,
    'error_message': error_message
}

# Only include api_key_id if it's provided and valid
if api_key_id:
    metrics_data['api_key_id'] = api_key_id
    
ModelMetrics.objects.create(**metrics_data)
```

## Provider Adapter Pattern

### Base Adapter Interface

All provider adapters implement a common interface:

```python
class BaseLLMAdapter:
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Execute a completion request"""
        raise NotImplementedError
        
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Execute a chat request"""
        raise NotImplementedError
```

### Adapter Registration

Adapters are registered in the `PROVIDER_ADAPTERS` dictionary:

```python
class LLMRouter:
    PROVIDER_ADAPTERS: Dict[str, Type[BaseLLMAdapter]] = {
        # Will be populated by provider adapters
    }
```

Provider adapters register themselves:

```python
# In the OpenAI adapter module
LLMRouter.PROVIDER_ADAPTERS['openai'] = OpenAIAdapter
```

### Adapter Selection

The appropriate adapter is selected based on the provider:

```python
def _get_adapter(self, model: Model, api_key: str):
    """Get the appropriate adapter for the model"""
    adapter_class = self.PROVIDER_ADAPTERS.get(model.provider.slug)
    if not adapter_class:
        raise NoValidAdapterError(f'No adapter found for provider {model.provider.slug}')

    return adapter_class(
        api_key=api_key,
        model_config=model.config,
        provider_config=model.provider.config
    )
```

## Testing Strategy

### Mock Adapters

Tests use mock adapters to simulate different provider behaviors:

```python
class MockAdapter:
    """Mock adapter for testing"""
    def __init__(self, api_key=None, model_name=None, should_fail=False, error_type=None):
        self.api_key = api_key
        self.model_name = model_name
        self.should_fail = should_fail
        self.error_type = error_type

    async def complete(self, prompt, **kwargs):
        if self.should_fail:
            if self.error_type == 'quota':
                raise QuotaExceededError('Quota exceeded', 'mock_provider')
            # Other error types...
        return LLMResponse(
            content='mock response',
            tokens_input=10,
            tokens_output=20,
            latency_ms=100,
            cost=Decimal('0.001')
        )
```

### Async Test Methods

Tests are implemented as async methods to properly test async behavior:

```python
@patch('modelhub.services.llm_router.APIKeyManager')
async def test_quota_exceeded_fallback(self, mock_key_manager_class):
    # Test implementation...
```

### Database Operation Testing

Database operations in tests use `sync_to_async` to properly handle async context:

```python
count = await sync_to_async(ModelMetrics.objects.count)()
self.assertEqual(count, 2)  # Both models tried
```

## Performance Considerations

### Async Efficiency

The async implementation provides several performance benefits:

1. **Non-Blocking I/O**: External API calls don't block the event loop
2. **Concurrent Execution**: Multiple requests can be processed concurrently
3. **Efficient Resource Usage**: Server resources are used more efficiently

### Database Optimization

Database operations are optimized to minimize overhead:

1. **Batched Operations**: Related operations are batched where possible
2. **Minimal Queries**: Database queries are minimized
3. **Proper Transaction Handling**: Transactions are used appropriately

### Error Handling Efficiency

The error handling system is designed to be efficient:

1. **Early Failure Detection**: Errors that can't be recovered from are detected early
2. **Smart Fallback**: Only attempt fallback when it makes sense
3. **Comprehensive Metrics**: All attempts are recorded for analysis

## Future Improvements

1. **Distributed Tracing**: Add distributed tracing for better observability
2. **Circuit Breakers**: Implement circuit breakers to prevent cascading failures
3. **Caching Layer**: Add caching for frequently used data
4. **Rate Limiting**: Implement rate limiting to prevent quota exhaustion
5. **Parallel Execution**: Allow parallel execution of requests to multiple providers
