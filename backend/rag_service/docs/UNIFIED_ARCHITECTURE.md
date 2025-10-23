# Unified Extraction Architecture

## Overview

The unified extraction architecture provides a streamlined approach to document processing by combining multiple extraction tasks into a single LLM call. This eliminates duplicate API calls, reduces costs, and improves performance.

## Key Components

### UnifiedExtractor

The `UnifiedExtractor` class is the central component of the architecture. It:

- Handles multiple extraction tasks in a single LLM call
- Integrates with ModelHub for model selection and API key management
- Provides a comprehensive prompt that extracts all requested information
- Tracks costs and usage metrics properly
- Returns a structured response with all extracted data

### Extraction Tasks

The system supports the following extraction tasks:

- **TEXT**: Basic text extraction from documents
- **LAYOUT**: Document structure analysis (titles, paragraphs, etc.)
- **TABLES**: Table extraction with structure preservation
- **ENTITIES**: Named entity recognition
- **SUMMARY**: Document summarization
- **ALL**: Performs all extraction tasks in a single call

### Integration Points

The unified architecture integrates with:

1. **ModelHub**: For model selection, API key management, and usage tracking
2. **ImageProcessor**: For converting documents to images for vision models
3. **DocumentProcessor**: As a high-level interface for document processing
4. **Layout/Table Extractors**: As specialized extraction components

## Benefits

- **Cost Efficiency**: Single LLM call instead of multiple calls
- **Performance**: Reduced latency and overhead
- **Consistency**: Unified approach to extraction across components
- **Maintainability**: Centralized prompt engineering and response parsing
- **Flexibility**: Can request specific extraction tasks as needed

## Architecture Diagram

```
┌───────────────────┐     ┌───────────────────┐
│ DocumentProcessor │     │ Layout/Table      │
│                   │     │ Extractors        │
└─────────┬─────────┘     └─────────┬─────────┘
          │                         │
          ▼                         ▼
┌─────────────────────────────────────────────┐
│              UnifiedExtractor               │
├─────────────────────────────────────────────┤
│ - extract(request)                          │
│ - _build_unified_prompt(tasks)              │
│ - _build_vision_messages(prompt, image)     │
│ - _merge_page_results(response, results)    │
└─────────┬─────────────────────────┬─────────┘
          │                         │
┌─────────▼─────────┐     ┌─────────▼─────────┐
│   ImageProcessor  │     │     ModelHub      │
└───────────────────┘     └───────────────────┘
```

## Usage Examples

### Basic Usage

```python
from rag_service.services.extraction import UnifiedExtractor, ExtractionRequest, ExtractionTask

# Create extractor
extractor = UnifiedExtractor()

# Create request
request = ExtractionRequest(
    file_path='/path/to/document.pdf',
    tasks=[ExtractionTask.TEXT, ExtractionTask.TABLES],
    organization=organization,
    quality_priority='balanced'
)

# Extract content
response = await extractor.extract(request)

# Access results
text = response.text
tables = response.tables
cost = response.cost_usd
```

### Complete Document Analysis

```python
# Extract everything in one call
request = ExtractionRequest(
    file_path='/path/to/document.pdf',
    tasks=[ExtractionTask.ALL],
    organization=organization
)

response = await extractor.extract(request)

# Access all extracted information
text = response.text
layout_blocks = response.layout_blocks
tables = response.tables
entities = response.entities
summary = response.summary
```

## Implementation Details

### Prompt Engineering

The unified prompt is dynamically constructed based on the requested tasks. It includes:

1. Clear instructions for each extraction task
2. Specific output format requirements
3. Examples of expected output
4. Task-specific guidance

### Response Processing

The response from the LLM is:

1. Parsed from JSON format
2. Validated for required fields
3. Converted to appropriate data structures (e.g., pandas DataFrames for tables)
4. Merged across multiple pages if needed

### Error Handling

The system includes robust error handling for:

- LLM API failures
- JSON parsing errors
- Missing or malformed responses
- Rate limiting and quota issues

## Performance Considerations

- **Page Limits**: By default, processing is limited to 10 pages to manage costs
- **Image Optimization**: Images are resized and optimized before sending to vision models
- **Selective Tasks**: Only requested tasks are included in the prompt
- **Quality vs. Cost**: Configurable quality priority ('cost', 'quality', 'balanced')

## Future Improvements

- **Streaming Responses**: Support for streaming extraction results
- **Parallel Processing**: Process multiple pages in parallel
- **Caching**: Cache extraction results for frequently accessed documents
- **Custom Tasks**: Allow for custom extraction tasks with user-defined prompts
- **Fine-tuned Models**: Support for fine-tuned models specific to extraction tasks

## Migration Guide

### From Individual Extractors

If you were previously using individual extractors:

```python
# Old approach
layout_analyzer = LayoutAnalyzer()
blocks = await layout_analyzer.analyze_layout(file_path, organization)

table_extractor = TableExtractor()
tables = await table_extractor.extract_tables(file_path, organization)
```

New unified approach:

```python
# New approach
unified_extractor = UnifiedExtractor()
request = ExtractionRequest(
    file_path=file_path,
    tasks=[ExtractionTask.LAYOUT, ExtractionTask.TABLES],
    organization=organization
)
response = await unified_extractor.extract(request)

blocks = response.layout_blocks
tables = response.tables
```

### From DocumentProcessor

If you were using the DocumentProcessor:

```python
# Old approach
processor = DocumentProcessor()
result = processor.process_file(file_path, method=ExtractionMethod.VISION)
```

New unified approach:

```python
# New approach
processor = DocumentProcessor()
result = await processor.process_file(
    file_path, 
    method=ExtractionMethod.UNIFIED,
    organization=organization
)
```

## Conclusion

The unified extraction architecture represents a significant improvement in our document processing capabilities. By eliminating duplicate LLM calls and providing a comprehensive extraction approach, it delivers better performance, lower costs, and more consistent results across different extraction tasks.
