# Model Hub

The Model Hub is a core component of Dataelan that provides centralized management for AI model providers, intelligent routing, and comprehensive metrics tracking.

## Overview

The Model Hub enables organizations to:

- Connect to multiple LLM providers (OpenAI, Anthropic, etc.) through a unified interface
- Manage API keys with flexible strategies (Dataelan-managed, BYOK, or Hybrid)
- Define intelligent routing rules based on request context
- Track usage, costs, and performance metrics
- Handle errors and implement fallback strategies

## Architecture

### Core Components

1. **LLMRouter**: Central execution logic for routing LLM requests
2. **Provider Adapters**: Standardized interfaces for different LLM providers
3. **API Key Manager**: Handles API key selection and rotation
4. **Routing Rules**: Define how requests are routed to models
5. **Metrics**: Track usage, performance, and errors

### Data Models

- **Provider**: Represents an LLM provider (e.g., OpenAI, Anthropic)
- **Model**: Represents a specific model from a provider
- **APIKey**: Stores API keys for providers
- **RoutingRule**: Defines conditions for model selection
- **RoutingRuleModel**: Maps models to rules with weights
- **ModelMetrics**: Records usage and performance data

## LLMRouter

The LLMRouter is the central component responsible for executing LLM requests according to routing rules and handling fallbacks.

### Execution Flow

1. Match routing rules based on model type and request context
2. Select a model using weighted random selection
3. Get an API key via the APIKeyManager
4. Execute the request via the appropriate provider adapter
5. Record metrics and handle errors

### Async Implementation

The LLMRouter uses async/await patterns for non-blocking execution:

```python
async def execute(
    self,
    model_type: str,
    request_context: Dict[str, Any],
    prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    **kwargs
):
    # Implementation details...
```

Database operations are isolated using a decorator pattern:

```python
@db_operation
def _create_metrics(self, model_id: int, api_key_id: Optional[str] = None,
                 response: Optional[LLMResponse] = None,
                 error: Optional[Exception] = None) -> None:
    # Implementation details...
```

### Error Handling

The LLMRouter implements sophisticated error handling:

1. **Fallback Support**: For certain error types (e.g., quota exceeded), the router will try alternative models
2. **No Fallback Errors**: Some errors (e.g., context length) are passed through without fallback
3. **Standardized Error Types**: Error types are normalized for consistent metrics tracking
4. **Comprehensive Metrics**: All attempts (successful or failed) are recorded

Error type mapping example:
```python
error_mapping = {
    'CONTEXTLENGTHERROR': 'CONTEXT_LENGTH_ERROR',
    'QUOTAEXCEEDEDERROR': 'QUOTA_EXCEEDED',
    'AUTHENTICATIONERROR': 'AUTHENTICATION_ERROR',
    'INVALIDREQUESTERROR': 'INVALID_REQUEST',
    'NOVALIDMODELERROR': 'NO_VALID_MODEL',
    'NOVALIDADAPTERERROR': 'NO_VALID_ADAPTER'
}
```

## Routing Rules

Routing rules determine which models are eligible for a given request based on conditions.

### Rule Conditions

Conditions are defined as JSON and can include:
- Input length
- Model capabilities
- Cost constraints
- Organization preferences

Example:
```json
{
  "conditions": [
    {"field": "length", "operator": "lt", "value": 1000},
    {"field": "cost_sensitivity", "operator": "eq", "value": "low"}
  ]
}
```

### Model Selection

Models are selected from matching rules using weighted random selection:

1. All matching rules are identified based on conditions
2. Models from these rules are collected with their weights
3. A model is randomly selected with probability proportional to its weight

## API Key Management

The APIKeyManager handles API key selection with three strategies:

1. **Dataelan Keys**: Use Dataelan's managed keys (default)
2. **Organization Keys**: Use organization's own keys (BYOK)
3. **Hybrid**: Intelligently switch between Dataelan and organization keys based on usage patterns

### Hybrid Strategy

The hybrid strategy switches between Dataelan and organization keys based on:

1. For high-cost requests (over $5), always use organization keys
2. For low-cost requests:
   - Use Dataelan keys by default
   - Switch to organization keys if total Dataelan usage across ALL organizations exceeds 80% of total quota
   - Switch back to Dataelan keys if organization's own keys are near their quota (>80%)

## Metrics and Analytics

All LLM executions are tracked in the ModelMetrics table:

- Model used
- Organization
- API key
- Tokens (input and output)
- Latency
- Cost
- Status (success or error)
- Error type and message

These metrics enable:
- Cost tracking and allocation
- Performance monitoring
- Error analysis
- Usage patterns identification

## Provider Adapters

Each LLM provider has a dedicated adapter that implements the BaseLLMAdapter interface:

```python
class BaseLLMAdapter:
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Execute a completion request"""
        pass
        
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Execute a chat request"""
        pass
```

This adapter pattern allows for:
- Standardized response format
- Consistent error handling
- Easy addition of new providers
- Provider-specific optimizations

## Usage Example

```python
# Initialize the router with an organization
router = LLMRouter(organization)

# Execute a completion request
response = await router.execute(
    model_type="TEXT",
    request_context={"length": 500, "importance": "high"},
    prompt="Explain quantum computing in simple terms."
)

# Execute a chat request
response = await router.execute(
    model_type="CHAT",
    request_context={"length": 300},
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is machine learning?"}
    ]
)
```

## Best Practices

1. **Error Handling**: Always handle potential exceptions from the router
2. **Async/Await**: Use proper async patterns when working with the router
3. **Request Context**: Provide detailed request context for optimal routing
4. **Metrics Analysis**: Regularly review metrics to optimize routing rules
5. **Fallback Configuration**: Configure appropriate fallback behavior for your use case
