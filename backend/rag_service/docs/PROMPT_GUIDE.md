# Multi-Task Prompts Guide

## Overview

The multi-task prompts system provides a flexible way to create and manage prompts for different extraction tasks. This guide explains how to use the system effectively.

## Basic Usage

The `multi_task_prompts.py` module contains two main classes:

1. `MultiTaskPrompts` - Core prompts for standard extraction tasks
2. `SpecializedPrompts` - Domain-specific prompts for specialized document types

### Standard Extraction Tasks

To use standard extraction tasks:

```python
from rag_service.services.extraction import UnifiedExtractor, ExtractionRequest, ExtractionTask

# Create extractor
extractor = UnifiedExtractor()

# Create request with specific tasks
request = ExtractionRequest(
    file_path='/path/to/document.pdf',
    tasks=[ExtractionTask.TEXT, ExtractionTask.TABLES],
    organization=organization
)

# Extract content
response = await extractor.extract(request)
```

Available tasks:
- `ExtractionTask.TEXT` - Basic text extraction
- `ExtractionTask.LAYOUT` - Document layout analysis
- `ExtractionTask.TABLES` - Table extraction
- `ExtractionTask.ENTITIES` - Named entity extraction
- `ExtractionTask.SUMMARY` - Document summarization
- `ExtractionTask.ALL` - Perform all extraction tasks

### Specialized Document Types

For domain-specific documents:

```python
from rag_service.services.extraction import UnifiedExtractor, ExtractionRequest, ExtractionTask, SpecializedPrompts

# Get specialized prompt
financial_prompt = SpecializedPrompts.get_financial_document_prompt()

# Create request with specialized prompt
request = ExtractionRequest(
    file_path='/path/to/financial_report.pdf',
    tasks=[ExtractionTask.ALL],
    specialized_prompt=financial_prompt
)

# Extract content
response = await extractor.extract(request)
```

Available specialized prompts:
- `SpecializedPrompts.get_financial_document_prompt()` - For financial documents
- `SpecializedPrompts.get_scientific_document_prompt()` - For scientific papers
- `SpecializedPrompts.get_legal_document_prompt()` - For legal documents

## Creating Custom Prompts

You can create custom prompts for specific document types:

```python
# Create a custom prompt
custom_prompt = """
Analyze this medical document with special attention to:
- Patient information and medical history
- Diagnosis and treatment plans
- Medication details and dosages
- Lab results and vital signs
- Follow-up instructions

Extract any tables containing lab results or medication schedules.
Identify medical entities such as conditions, medications, procedures, and healthcare providers.
"""

# Use the custom prompt
request = ExtractionRequest(
    file_path='/path/to/medical_record.pdf',
    tasks=[ExtractionTask.TEXT, ExtractionTask.TABLES, ExtractionTask.ENTITIES],
    specialized_prompt=custom_prompt
)
```

## Adding New Specialized Prompts

To add new specialized prompts:

1. Open `multi_task_prompts.py`
2. Add a new static method to the `SpecializedPrompts` class:

```python
@staticmethod
def get_medical_document_prompt() -> str:
    """Get prompt specialized for medical documents"""
    return """
Analyze this medical document with special attention to:
- Patient information and medical history
- Diagnosis and treatment plans
- Medication details and dosages
- Lab results and vital signs
- Follow-up instructions

Extract any tables containing lab results or medication schedules.
Identify medical entities such as conditions, medications, procedures, and healthcare providers.
"""
```

## Best Practices

1. **Task Selection**: Only include the tasks you need to reduce token usage and processing time
2. **Specialized Prompts**: Use specialized prompts for domain-specific documents to improve extraction quality
3. **Quality Priority**: Set `quality_priority='quality'` for complex documents where accuracy is critical
4. **Page Limits**: Use `max_pages` to limit processing for large documents
5. **Cost Control**: Set `max_cost_usd` to prevent unexpected charges

## Testing Prompts

Use the provided test scripts to test your prompts:

```bash
# Test standard extraction
python -m rag_service.services.extraction.tests.test_unified_extractor /path/to/document.pdf -t text,tables

# Test specialized extraction
python -m rag_service.services.extraction.tests.test_specialized_prompts /path/to/document.pdf --type financial
```

## Prompt Design Tips

1. **Be Specific**: Clearly specify what information to extract
2. **Provide Examples**: Include examples of expected output format
3. **Domain Knowledge**: Include domain-specific terminology and concepts
4. **Structure**: Organize prompts with clear sections and bullet points
5. **Output Format**: Clearly specify the expected output format (JSON structure)

## Advanced Usage

For advanced use cases, you can combine specialized prompts with specific tasks:

```python
# Get specialized prompt
legal_prompt = SpecializedPrompts.get_legal_document_prompt()

# Create request with specialized prompt and specific tasks
request = ExtractionRequest(
    file_path='/path/to/contract.pdf',
    tasks=[ExtractionTask.TEXT, ExtractionTask.ENTITIES],  # Only extract text and entities
    specialized_prompt=legal_prompt,
    quality_priority='quality'  # Use high quality for legal documents
)
```

This approach allows for fine-grained control over the extraction process while still benefiting from domain-specific prompts.
