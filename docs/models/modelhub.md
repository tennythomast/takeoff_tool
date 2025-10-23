# Model Hub Data Models

This document provides a detailed overview of the data models that power the Model Hub in Dataelan.

## Core Models

### Provider

The `Provider` model represents an LLM provider such as OpenAI, Anthropic, or Google.

```python
class Provider(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    status = models.CharField(choices=[
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('DEPRECATED', 'Deprecated')
    ])
    config = models.JSONField(default=dict)
```

**Key Fields:**
- `slug`: Unique identifier used in routing and adapter selection
- `config`: Provider-specific configuration (API version, base URL, etc.)
- `status`: Current status of the provider

**Usage:**
- Used by the LLMRouter to identify the appropriate adapter
- Referenced by Models to establish provider relationships
- Used in API key management for provider-specific keys

### Model

The `Model` model represents a specific model offered by a provider.

```python
class Model(BaseModel):
    provider = models.ForeignKey('Provider', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    model_type = models.CharField(choices=[
        ('TEXT', 'Text'),
        ('CODE', 'Code'),
        ('IMAGE', 'Image'),
        ('VOICE', 'Voice'),
        ('VIDEO', 'Video')
    ])
    capabilities = models.JSONField(default=list)
    config = models.JSONField(default=dict)
    cost_input = models.DecimalField(max_digits=10, decimal_places=6)
    cost_output = models.DecimalField(max_digits=10, decimal_places=6)
    context_window = models.IntegerField()
    status = models.CharField(choices=[
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('DEPRECATED', 'Deprecated')
    ])
```

**Key Fields:**
- `provider`: The provider that offers this model
- `model_type`: The type of content this model can process
- `capabilities`: Specific capabilities of the model (e.g., function calling, vision)
- `cost_input`/`cost_output`: Cost per token for input and output
- `context_window`: Maximum context length in tokens

**Usage:**
- Selected by the LLMRouter based on routing rules
- Used to calculate costs for requests
- Referenced in metrics for tracking usage

### APIKey

The `APIKey` model stores API keys for different providers.

```python
class APIKey(BaseModel):
    organization = models.ForeignKey('Organization', null=True, blank=True)
    provider = models.ForeignKey('Provider', on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    key = EncryptedCharField(max_length=255)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    daily_quota = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    monthly_quota = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
```

**Key Fields:**
- `organization`: The organization that owns this key (null for Dataelan keys)
- `provider`: The provider this key is for
- `key`: The encrypted API key
- `is_active`: Whether the key is currently active
- `daily_quota`/`monthly_quota`: Spending limits for this key

**Usage:**
- Selected by the APIKeyManager based on the organization's strategy
- Used by provider adapters to authenticate requests
- Referenced in metrics for tracking usage by key

## Routing Models

### RoutingRule

The `RoutingRule` model defines conditions for routing requests to specific models.

```python
class RoutingRule(BaseModel):
    organization = models.ForeignKey('Organization', null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    model_type = models.CharField(choices=[
        ('TEXT', 'Text'),
        ('CODE', 'Code'),
        ('IMAGE', 'Image'),
        ('VOICE', 'Voice'),
        ('VIDEO', 'Video')
    ])
    conditions = models.JSONField()
    models = models.ManyToManyField('Model', through='RoutingRuleModel')
```

**Key Fields:**
- `organization`: The organization this rule belongs to (null for system-wide rules)
- `priority`: The priority of this rule (lower numbers = higher priority)
- `model_type`: The type of model this rule applies to
- `conditions`: JSON conditions for when this rule should apply

**Conditions Format:**
```json
[
  {
    "field": "length",
    "operator": "lt",
    "value": 1000
  },
  {
    "field": "importance",
    "operator": "eq",
    "value": "high"
  }
]
```

**Usage:**
- Evaluated by the LLMRouter to determine eligible models
- Used to implement complex routing logic
- Can be organization-specific or system-wide

### RoutingRuleModel

The `RoutingRuleModel` model connects routing rules to models with weights.

```python
class RoutingRuleModel(models.Model):
    rule = models.ForeignKey(RoutingRule, on_delete=models.CASCADE)
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    weight = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list)
```

**Key Fields:**
- `rule`: The routing rule
- `model`: The model this rule can route to
- `weight`: The weight for random selection (higher = more likely)

**Usage:**
- Used by the LLMRouter for weighted random selection
- Allows multiple models to be eligible for a single rule
- Enables load balancing across models

## Metrics Models

### ModelMetrics

The `ModelMetrics` model records metrics for all model executions.

```python
class ModelMetrics(BaseModel):
    model = models.ForeignKey('Model', on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', null=True, blank=True)
    api_key = models.ForeignKey('APIKey', null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    latency_ms = models.IntegerField()
    tokens_input = models.IntegerField()
    tokens_output = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=6)
    status = models.CharField(choices=[
        ('SUCCESS', 'Success'),
        ('ERROR', 'Error'),
        ('TIMEOUT', 'Timeout')
    ])
    error_type = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
```

**Key Fields:**
- `model`: The model used for this execution
- `organization`: The organization that made the request
- `api_key`: The API key used (optional)
- `latency_ms`: Request latency in milliseconds
- `tokens_input`/`tokens_output`: Token counts
- `cost`: Calculated cost of the request
- `status`: Outcome of the request
- `error_type`: Standardized error type if status is ERROR
- `error_message`: Detailed error message

**Standard Error Types:**
- `NONE`: No error occurred
- `QUOTA_EXCEEDED`: API quota exceeded
- `AUTHENTICATION_ERROR`: Invalid API key
- `CONTEXT_LENGTH_ERROR`: Input too long for model
- `INVALID_REQUEST`: Malformed request
- `NO_VALID_MODEL`: No suitable models found
- `NO_VALID_ADAPTER`: No adapter found for provider

**Usage:**
- Created by the LLMRouter for all execution attempts
- Used for cost tracking and billing
- Used for performance monitoring and analytics
- Used for error analysis and debugging

## Relationships

The Model Hub models are interconnected in the following ways:

1. **Provider → Model**: One-to-many relationship. A provider can offer multiple models.

2. **Provider → APIKey**: One-to-many relationship. A provider can have multiple API keys.

3. **Organization → APIKey**: One-to-many relationship. An organization can have multiple API keys.

4. **Organization → RoutingRule**: One-to-many relationship. An organization can have multiple routing rules.

5. **RoutingRule → Model**: Many-to-many relationship through RoutingRuleModel. A rule can apply to multiple models, and a model can be referenced by multiple rules.

6. **Model → ModelMetrics**: One-to-many relationship. A model can have multiple metrics records.

7. **Organization → ModelMetrics**: One-to-many relationship. An organization can have multiple metrics records.

8. **APIKey → ModelMetrics**: One-to-many relationship. An API key can be used in multiple requests.

## Database Considerations

### Indexes

The following indexes are recommended for optimal performance:

1. `ModelMetrics.model_id, ModelMetrics.timestamp`: For efficient querying of metrics by model over time
2. `ModelMetrics.organization_id, ModelMetrics.timestamp`: For efficient querying of metrics by organization over time
3. `ModelMetrics.status, ModelMetrics.error_type`: For efficient querying of errors
4. `RoutingRule.organization_id, RoutingRule.model_type, RoutingRule.priority`: For efficient rule matching

### Foreign Keys

All foreign key relationships include appropriate `on_delete` behavior:

- `CASCADE`: When the parent record is deleted, all related records are also deleted
- `SET_NULL`: When the parent record is deleted, the foreign key is set to NULL (used for optional relationships)

### Data Integrity

The following constraints ensure data integrity:

1. Unique constraints on `Provider.slug` and `Provider.name`
2. Check constraints on `RoutingRule.priority` (1-100)
3. Check constraints on `RoutingRuleModel.weight` (1-100)
4. Encryption of sensitive data in `APIKey.key`

## Async Considerations

When working with these models in async contexts, special care must be taken:

1. Use `sync_to_async` for database operations
2. Isolate database operations in dedicated methods
3. Use the `db_operation` decorator for methods that interact with the database:

```python
def db_operation(func):
    """Decorator to wrap database operations in sync_to_async"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await sync_to_async(func)(*args, **kwargs)
    return wrapper
```

Example usage:

```python
@db_operation
def _create_metrics(self, model_id: int, api_key_id: Optional[str] = None,
                 response: Optional[LLMResponse] = None,
                 error: Optional[Exception] = None) -> None:
    """Create metrics record in the database"""
    # Database operations...
```
