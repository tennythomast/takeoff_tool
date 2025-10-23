# Voyage AI Embedding Service

## Overview

The `VoyageEmbeddingService` is fully integrated with Dataelan's ModelHub architecture, providing enterprise-grade embedding capabilities with automatic API key management, cost tracking, and usage analytics.

## Architecture Integration

### ModelHub Integration

The embedding service integrates with ModelHub's existing infrastructure:

1. **Provider Management**: Uses the `voyage` provider configured in ModelHub
2. **API Key Management**: Retrieves API keys from `modelhub.APIKey` model
   - Supports organization-specific keys
   - Falls back to system-wide keys
   - Respects API key strategy (org_only, org_with_dataelan_fallback, dataelan_only)

3. **Model Configuration**: Retrieves model settings from `modelhub.Model`
   - Pricing information (cost_input, cost_output)
   - Model capabilities and dimensions
   - Context window and configuration

4. **Usage Tracking**: Logs all embedding operations to `modelhub.ModelMetrics`
   - Token usage
   - Cost tracking
   - Latency monitoring
   - API key attribution

## Setup

### 1. Install Dependencies

```bash
pip install voyageai>=0.2.0
```

Already added to `requirements.txt`.

### 2. Setup Voyage Provider and Models

Run the management command to create Voyage provider and models in ModelHub:

```bash
python manage.py setup_embedding_models
```

This creates:
- **Provider**: Voyage AI with embedding support
- **Models**: 
  - `voyage-3-lite` (512 dimensions, $0.00002/1k tokens)
  - `voyage-3.5-lite` (2048 dimensions, $0.00002/1k tokens)
  - `voyage-3.5` (2048 dimensions, $0.00012/1k tokens)

### 3. Configure API Keys

Add Voyage AI API keys through Django admin or API:

**System-wide key (for all organizations):**
```python
from modelhub.models import APIKey, Provider

voyage_provider = Provider.objects.get(slug='voyage')
APIKey.objects.create(
    provider=voyage_provider,
    label='Dataelan System Key',
    key='your-voyage-api-key',
    is_default=True,
    is_active=True,
    organization=None  # System-wide
)
```

**Organization-specific key:**
```python
APIKey.objects.create(
    provider=voyage_provider,
    label='Organization Key',
    key='org-voyage-api-key',
    is_default=True,
    is_active=True,
    organization=your_organization
)
```

## Usage

### Async Usage (Recommended)

```python
from rag_service.services.embedding.embedding_service import VoyageEmbeddingService

# Create service instance
service = VoyageEmbeddingService(
    organization=organization,
    model_name='voyage-3.5-lite'
)

# Embed document chunks
texts = ["This is a document chunk", "Another chunk"]
embeddings, cost, latency_ms = await service.embed_chunks(texts)

# Embed search query
query = "What is the meaning of life?"
embedding, cost, latency_ms = await service.embed_query(query)

# Get embedding dimensions
dimensions = service.dimensions  # 2048 for voyage-3.5-lite
```

### Knowledge Base Integration

```python
from rag_service.services.embedding.embedding_service import VoyageEmbeddingService

# Create service from knowledge base configuration
service = await VoyageEmbeddingService.create_for_knowledge_base(knowledge_base)

# Use the service
embeddings, cost, latency_ms = await service.embed_chunks(chunks)
```

### Synchronous Usage (Legacy)

For synchronous contexts or quick testing:

```python
from rag_service.services.embedding.embedding_service import SimpleVoyageEmbeddings

# Direct initialization with API key
embeddings = SimpleVoyageEmbeddings(api_key="your-key", model_name="voyage-3.5-lite")

# Embed chunks
vectors = embeddings.embed_chunks(["text1", "text2"])

# Embed query
vector = embeddings.embed_query("search query")
```

## Features

### 1. Automatic API Key Management
- Retrieves keys from ModelHub's APIKey model
- Supports organization hierarchy (org key → system key)
- Respects organization's API key strategy
- Automatic key rotation and fallback

### 2. Cost Tracking
- Calculates costs using ModelHub pricing
- Logs all usage to ModelMetrics
- Tracks per-organization spending
- Supports quota management

### 3. Performance Monitoring
- Tracks latency for each operation
- Logs tokens per second
- Records success/failure rates
- Integration with ModelHub analytics

### 4. Model Configuration
- Supports multiple Voyage models
- Automatic dimension detection
- Model-specific optimizations
- Configurable via KnowledgeBase

## Model Options

| Model | Dimensions | Cost/1k Tokens | Best For |
|-------|-----------|----------------|----------|
| voyage-3-lite | 512 | $0.00002 | Cost-sensitive applications |
| voyage-3.5-lite | 2048 | $0.00002 | Balanced performance/cost |
| voyage-3.5 | 2048 | $0.00012 | Premium quality |

## Error Handling

The service provides comprehensive error handling:

```python
try:
    embeddings, cost, latency = await service.embed_chunks(texts)
except ValueError as e:
    # API key not configured or model not found
    logger.error(f"Configuration error: {e}")
except Exception as e:
    # API errors, network issues, etc.
    logger.error(f"Embedding error: {e}")
```

## Analytics and Monitoring

All embedding operations are logged to `ModelMetrics` with:
- Operation type: 'embedding'
- Model name and provider
- Token usage and cost
- Latency and throughput
- API key source (org/system)

Query analytics:
```python
from modelhub.models import ModelMetrics

# Get embedding analytics
analytics = ModelMetrics.get_embedding_analytics(
    organization=org,
    days=30
)

# Returns:
# {
#     'total_embedding_cost': Decimal,
#     'total_tokens_processed': int,
#     'avg_embedding_latency': float,
#     'total_embedding_requests': int
# }
```

## Integration with RAG Pipeline

The embedding service integrates seamlessly with the RAG pipeline:

1. **Document Processing**: Embed chunks during document ingestion
2. **Query Processing**: Embed user queries for semantic search
3. **Cost Optimization**: Track and optimize embedding costs
4. **Quality Monitoring**: Monitor embedding quality and performance

## Best Practices

1. **Use async methods**: Always use async methods in production for better performance
2. **Batch embeddings**: Embed multiple chunks at once for efficiency
3. **Monitor costs**: Use ModelMetrics to track embedding costs
4. **Configure quotas**: Set monthly quotas on API keys to prevent overspending
5. **Choose appropriate model**: Use voyage-3.5-lite for most use cases

## Troubleshooting

### No API key available
```
ValueError: No Voyage AI API key available. Please configure an API key in ModelHub.
```
**Solution**: Add a Voyage API key through Django admin or create one programmatically.

### Model not found
```
ValueError: Model voyage-3.5-lite not found in ModelHub. Please run setup_embedding_models command.
```
**Solution**: Run `python manage.py setup_embedding_models`

### Import errors
```
ImportError: No module named 'voyageai'
```
**Solution**: Install dependencies: `pip install -r requirements.txt`
