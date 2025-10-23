# Document Extraction Service

This module provides functionality to extract text and structured information from various document formats for use in RAG (Retrieval-Augmented Generation) pipelines.

**New Features:**
- [Unified Extraction Architecture](./UNIFIED_ARCHITECTURE.md) that combines multiple extraction tasks into a single LLM call for improved efficiency
- [Multi-Task Prompts System](./PROMPT_GUIDE.md) for flexible prompt management and domain-specific extraction

## Directory Structure

```
extraction/
├── __init__.py        # Package exports
├── text.py            # Core TextExtractor implementation
├── document_processor.py # Higher-level document processing
├── base.py            # Base extraction classes
├── vision.py          # Vision-based extraction
├── image_processor.py # Image processing utilities
├── layout_analyzer.py # Document layout analysis
├── table_extractor.py # Table extraction
├── unified_extractor.py # Unified extraction service (NEW)
├── hybrid_extractor.py # Intelligent hybrid extraction
├── cli.py             # Command-line interface
├── README.md          # This file
├── IMPLEMENTATION.md  # Detailed implementation documentation
├── UNIFIED_ARCHITECTURE.md # Unified architecture documentation (NEW)
└── tests/             # Test modules
    ├── __init__.py
    ├── test_text_extractor.py  # Basic tests
    ├── test_vision_extraction.py # Vision extraction tests
    ├── test_layout_analyzer.py # Layout analysis tests
    ├── test_table_extractor.py # Table extraction tests
    ├── test_unified_extractor.py # Unified extraction tests (NEW)
    ├── test_hybrid_extractor.py # Hybrid extraction tests
    ├── integration_test.py     # Integration with RAG pipeline
    └── example_usage.py        # Example usage scenarios
```

## Supported Formats

- **PDF** (digital and scanned)
- **DOCX** (Word documents)
- **TXT** (plain text)
- **MD** (Markdown)
- **CSV** (structured data)
- **Images** (JPG, PNG, TIFF, etc.)
- **XLSX** (Excel) - planned for future implementation

## Features

### Text Extraction

#### PDF Text Extractor
- Opens PDF with PyMuPDF (fitz)
- Extracts text page by page
- Preserves page boundaries
- Captures basic formatting (bold, italic if possible)
- Extracts tables (if structured)
- Gets metadata (author, creation date, title)
- Detects if PDF is scanned (low text density)
- Calculates text confidence score
- Identifies problematic pages

#### DOCX Extractor
- Uses python-docx library
- Extracts paragraphs in order
- Preserves heading hierarchy (H1, H2, H3)
- Extracts tables with structure
- Gets document properties (author, title)
- Preserves lists (bulleted, numbered)

#### Plain Text Extractor
- Reads TXT/MD files directly
- Detects encoding (UTF-8, Latin-1, etc.)
- Preserves line breaks
- For Markdown: Parses structure (headers, lists, code blocks)

#### CSV Extractor
- Parses CSV structure
- Detects delimiter (comma, tab, semicolon)
- Extracts headers
- Converts to text or structured format

### Vision Extraction

- Uses vision LLMs for image and scanned document text extraction
- Integrates with ModelHub for model selection
- Supports multiple image formats (JPG, PNG, TIFF, etc.)
- Optimizes images for vision models
- Tracks cost and usage metrics
- Provides confidence scores and warnings

### Layout Analysis

- Analyzes document structure and layout
- Identifies titles, headings, paragraphs, lists, tables, etc.
- Uses rule-based analysis for digital documents (fast, free)
- Falls back to vision-based analysis for complex documents
- Preserves reading order and hierarchy
- Extracts metadata like fonts and positions

### Table Extraction

- Multi-method table extraction with fallback strategy
- Uses Camelot for structured tables (best for bordered tables)
- Uses pdfplumber for simple tables
- Falls back to vision LLMs for complex or scanned tables
- Converts tables to pandas DataFrames
- Provides markdown and text representations
- Calculates confidence scores
- Tracks cost and usage metrics

### Unified Extraction (NEW)

- Combines multiple extraction tasks into a single LLM call
- Eliminates duplicate API calls across components
- Supports multiple extraction tasks:
  - Text extraction
  - Layout analysis
  - Table extraction
  - Entity recognition
  - Document summarization
- Provides comprehensive prompt engineering
- Tracks costs and usage metrics properly
- Significantly improves efficiency and reduces costs

### Hybrid Extraction

- Intelligently combines text and vision extraction methods
- Automatically selects optimal strategy based on document analysis
- Supports multiple strategies:
  - Fast: Text-only extraction for simple documents
  - Parallel: Simultaneous text and vision extraction
  - Vision-only: For scanned documents and images
- Analyzes document characteristics to determine best approach
- Provides quality assessment scores
- Merges results from different extraction methods
- Optimizes for both cost and quality

## Usage

### Basic Text Extraction

```python
from rag_service.services.extraction import TextExtractor, TextExtractorConfig

# Create a configuration
config = TextExtractorConfig(
    preserve_formatting=True,
    extract_tables=True,
    remove_headers_footers=False,
    min_text_density=0.1
)

# Create an extractor
extractor = TextExtractor(config)

# Extract text from a file
result = extractor.extract('/path/to/document.pdf')

# Access the extracted text
text = result['text']

# Access metadata (for PDF)
if 'metadata' in result:
    author = result['metadata'].get('author', 'Unknown')
    title = result['metadata'].get('title', 'Unknown')
    
# Check if PDF is scanned
if result.get('is_scanned', False):
    print("This PDF appears to be scanned. OCR might be needed.")
    print(f"Problematic pages: {result.get('problematic_pages', [])}")
```

### Vision-Based Extraction

```python
from rag_service.services.extraction import VisionExtractor, VisionConfig

# Create a configuration
config = VisionConfig(
    priority='balanced',  # 'cost', 'quality', or 'balanced'
    max_cost_per_document=1.0,
    structured_output=True
)

# Create an extractor
extractor = VisionExtractor(config)

# Extract text from an image or scanned document
result = extractor.extract('/path/to/image.jpg')

# Access the extracted text and metadata
text = result.extracted_text
model = result.model_used
cost = result.cost_usd
confidence = result.confidence_score
```

### Layout Analysis

```python
import asyncio
from rag_service.services.extraction import LayoutAnalyzer

async def analyze_document():
    # Create analyzer
    analyzer = LayoutAnalyzer()
    
    # Analyze document layout
    blocks = await analyzer.analyze_layout(
        '/path/to/document.pdf',
        method='auto'  # 'rule_based', 'vision', or 'auto'
    )
    
    # Process blocks
    for block in blocks:
        print(f"Type: {block.type.value}, Page: {block.page}")
        print(f"Text: {block.text[:100]}...")

# Run the async function
asyncio.run(analyze_document())
```

### Table Extraction

```python
import asyncio
from rag_service.services.extraction import TableExtractor

async def extract_tables():
    # Create extractor
    extractor = TableExtractor()
    
    # Extract tables
    tables = await extractor.extract_tables(
        '/path/to/document.pdf',
        pages=[1, 2, 3]  # Optional: specific pages to process
    )
    
    # Process tables
    for i, table in enumerate(tables):
        print(f"Table {i+1} on page {table['page']}:")
        print(f"Method: {table['method']}")
        print(f"Confidence: {table['confidence']:.2f}")
        print(table['data'])  # pandas DataFrame
        print(table['markdown'])  # Markdown representation

# Run the async function
asyncio.run(extract_tables())
```

### Unified Extraction (NEW)

```python
import asyncio
from rag_service.services.extraction import UnifiedExtractor, ExtractionRequest, ExtractionTask

async def extract_document():
    # Create extractor
    extractor = UnifiedExtractor()
    
    # Create extraction request
    request = ExtractionRequest(
        file_path='/path/to/document.pdf',
        tasks=[ExtractionTask.TEXT, ExtractionTask.LAYOUT, ExtractionTask.TABLES],
        organization=organization,  # For ModelHub routing
        quality_priority='balanced'
    )
    
    # Perform extraction
    response = await extractor.extract(request)
    
    # Access extraction results
    text = response.text
    layout_blocks = response.layout_blocks
    tables = response.tables
    
    # Access cost and model info
    print(f"Model: {response.model_used} ({response.provider_used})")
    print(f"Cost: ${response.cost_usd:.4f}")
    
    # Process tables
    for i, table in enumerate(tables):
        print(f"Table {i+1} on page {table['page']}:")
        print(table['markdown'])

# Run the async function
asyncio.run(extract_document())
```

### Hybrid Extraction

```python
import asyncio
from rag_service.services.extraction import HybridExtractor

async def extract_document():
    # Create extractor
    extractor = HybridExtractor()
    
    # Extract document with automatic strategy selection
    result = await extractor.extract(
        '/path/to/document.pdf',
        strategy='auto'  # 'auto', 'fast', 'parallel', or 'vision_only'
    )
    
    # Access extraction results
    print(f"Method used: {result['method']}")
    if 'primary_method' in result:
        print(f"Primary method: {result['primary_method']}")
    
    # Access extracted text
    text = result['text']
    
    # Access quality scores
    quality = result['quality']
    print(f"Overall quality: {quality['overall_score']:.2f}")
    
    # Access tables if available
    if 'tables' in result and result['tables']:
        print(f"Found {len(result['tables'])} tables")

# Run the async function
asyncio.run(extract_document())
```

## Testing

You can test the extractor with the included test scripts:

```bash
# Text extraction test
python -m rag_service.services.extraction.tests.test_text_extractor /path/to/document.pdf

# Vision extraction test
python -m rag_service.services.extraction.tests.test_vision_extraction /path/to/document.pdf

# Layout analysis test
python -m rag_service.services.extraction.tests.test_layout_analyzer /path/to/document.pdf

# Table extraction test
python -m rag_service.services.extraction.tests.test_table_extractor /path/to/document.pdf

# Unified extraction test (NEW)
python -m rag_service.services.extraction.tests.test_unified_extractor /path/to/document.pdf -t text,layout,tables

# Hybrid extraction test
python -m rag_service.services.extraction.tests.test_hybrid_extractor /path/to/document.pdf -s auto

# Example usage
python -m rag_service.services.extraction.tests.example_usage /path/to/document.pdf

# Integration test with RAG pipeline
python -m rag_service.services.extraction.tests.integration_test /path/to/document.pdf
```

## Command-Line Interface

The service includes a command-line interface for easy text extraction:

```bash
python -m rag_service.services.extraction.cli /path/to/document.pdf -o output.txt

# Process for RAG
python -m rag_service.services.extraction.cli /path/to/document.pdf --rag -f json -o output.json

# Process a directory
python -m rag_service.services.extraction.cli /path/to/documents/ -r -o extracted/

# Use vision extraction
python -m rag_service.services.extraction.cli /path/to/scanned.pdf -m vision -f summary

# Extract tables
python -m rag_service.services.extraction.cli /path/to/tables.pdf --extract-tables -f json -o tables.json

# Use unified extraction (NEW)
python -m rag_service.services.extraction.cli /path/to/document.pdf -m unified -f json -o output.json

# Use hybrid extraction
python -m rag_service.services.extraction.cli /path/to/document.pdf -m hybrid -f json -o output.json

# Use specific hybrid strategy
python -m rag_service.services.extraction.cli /path/to/document.pdf -m hybrid --hybrid-strategy parallel -f json
```

## Configuration Options

The `TextExtractorConfig` class provides the following options:

- `preserve_formatting`: Whether to preserve formatting (default: True)
- `extract_tables`: Whether to extract tables (default: True)
- `remove_headers_footers`: Whether to remove headers and footers (default: False)
- `min_text_density`: Minimum text density threshold for scanned PDF detection (default: 0.1)
- `max_page_size_mb`: Maximum page size in MB (default: 10)
- `strip_page_numbers`: Whether to strip page numbers (default: False)
- `detect_sections`: Whether to detect document sections (default: True)

## Error Handling

The extractor handles various error cases:
- Corrupted PDF: Attempts repair, then fails gracefully
- Encrypted PDF: Detects and rejects (or requests password)
- Scanned PDF: Detects and automatically uses vision extractor
- Malformed DOCX: Extracts what's possible, warns user
- Encoding issues: Tries multiple encodings, logs detected encoding
- API failures: Implements retry logic with exponential backoff
- Rate limiting: Handles rate limiting from vision API providers

## Performance Optimization

The extractor uses several strategies for performance optimization:
- Streams large files (doesn't load entirely in memory)
- Processes PDFs page-by-page
- Early exits on errors
- Caches extracted text per file hash

## Documentation

For more detailed implementation documentation, see:

- [UNIFIED_ARCHITECTURE.md](./UNIFIED_ARCHITECTURE.md) - Unified extraction architecture
- [PROMPT_GUIDE.md](./PROMPT_GUIDE.md) - Multi-task prompts guide
