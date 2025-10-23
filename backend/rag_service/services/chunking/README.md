# Chunking Service

## Overview

The Chunking Service provides content-aware document chunking that preserves structure and coordinates. It works seamlessly with the Unified Extractor to create optimized chunks for RAG retrieval.

## Architecture

### Integration with Unified Extractor

The chunking service is designed to work with the `ExtractionResponse` format from the `UnifiedExtractor`:

```
Document File
    ↓
DocumentProcessor (uses UnifiedExtractor)
    ↓
ExtractionResponse {
    text: str
    tables: List[Dict]
    layout_blocks: List[Dict]
    entities: List[Dict]
    metadata: Dict
}
    ↓
ChunkingService
    ↓
List[Chunk] (saved to database)
```

### Complete Pipeline

Use the `DocumentChunkingService` for the complete pipeline:

```python
from rag_service.services.document_chunking_service import DocumentChunkingService

# Initialize service
service = DocumentChunkingService()

# Process document and create chunks
chunks = await service.process_and_chunk_document(
    document=document_instance,
    file_path="/path/to/file.pdf",
    organization=organization,
    save_chunks=True
)
```

## Chunk Types

The service creates different types of chunks based on content:

### 1. Table Chunks (`chunk_type='table'`)
- **Strategy**: Atomic (one table = one chunk)
- **Preserves**: Table structure, headers, rows
- **Metadata**: Table type, caption, column headers, row count, bounding box

### 2. Drawing Metadata Chunks (`chunk_type='drawing_metadata'`)
- **Strategy**: Atomic (all metadata = one chunk)
- **Preserves**: Drawing number, revision, title, scale, units, date, author
- **Metadata**: All drawing-specific fields

### 3. Visual Element Chunks (`chunk_type='visual_element_group'`)
- **Strategy**: Spatial grouping
- **Preserves**: Complete coordinate data for all elements
- **Metadata**: Element type, count, zone, spatial description, bounding boxes
- **Critical**: Stores ALL element coordinates for overlay visualization

### 4. Text Chunks (`chunk_type='text'`)
- **Strategy**: Sliding window with overlap
- **Parameters**: 
  - Chunk size: 1000 characters
  - Overlap: 200 characters
- **Metadata**: Position, start/end character indices

## Key Features

### 1. Structure Preservation
- Tables remain atomic units
- Visual elements maintain spatial relationships
- Metadata kept together for context

### 2. Coordinate Preservation
- All visual element coordinates stored in metadata
- Enables overlay visualization on original documents
- Supports spatial queries and filtering

### 3. Cross-Referencing
- Links schedule tables to visual element groups
- Validates quantities between schedules and actual elements
- Creates bidirectional relationships

### 4. Searchable Metadata
- Extracts searchable terms from each chunk type
- Enables hybrid search (semantic + keyword)
- Improves retrieval accuracy

## Usage Examples

### Basic Usage

```python
from rag_service.services.chunking.chunking_service import ChunkingService
from rag_service.services.extraction.document_processor import DocumentProcessor

# Extract content
processor = DocumentProcessor()
extraction_response = await processor.process_file(
    file_path="document.pdf",
    organization=org
)

# Create chunks
chunking_service = ChunkingService()
chunks = chunking_service.chunk_document(
    extraction_response=extraction_response,
    document=document_instance
)
```

### Complete Pipeline with Auto-Save

```python
from rag_service.services.document_chunking_service import DocumentChunkingService

service = DocumentChunkingService()

# Process and save chunks automatically
chunks = await service.process_and_chunk_document(
    document=document,
    file_path="document.pdf",
    organization=organization,
    save_chunks=True  # Automatically saves to database
)

# Get statistics
stats = service.get_chunk_statistics(chunks)
print(f"Created {stats['total_chunks']} chunks")
print(f"Chunk types: {stats['chunk_types']}")
```

### Processing File Uploads

```python
# For file uploads (e.g., from Django request.FILES)
chunks = await service.process_and_chunk_file_object(
    document=document,
    file_obj=request.FILES['file'],
    file_name="uploaded_file.pdf",
    organization=request.user.organization,
    save_chunks=True
)
```

## Extended Chunk Model

The service uses the extended `Chunk` model with these additional fields:

- `chunk_type`: Type of chunk (table, metadata, text, visual_element_group)
- `parent_chunk`: Reference to parent chunk (for hierarchical structures)
- `related_chunks`: Many-to-many relationships with other chunks
- `embedding_vector`: JSON field for storing embeddings
- `metadata`: Rich JSON metadata specific to chunk type

## Helper Methods

### Searchable Terms Extraction
- `_extract_searchable_terms()`: Extract terms from tables
- `_extract_metadata_searchable_terms()`: Extract terms from metadata
- `_extract_visual_searchable_terms()`: Extract terms from visual elements

### Spatial Analysis
- `_determine_quadrant()`: Determine element quadrant in document
- `_calculate_group_bounding_box()`: Calculate bounding box for element groups

### Content Formatting
- `_format_table_as_text()`: Convert tables to readable text
- `_format_metadata_as_text()`: Convert metadata to readable text
- `_format_visual_group_as_text()`: Convert visual elements to readable text

## Integration Points

### With Document Processor
- Receives `ExtractionResponse` from `DocumentProcessor`
- Handles both file paths and file objects
- Supports all extraction methods (text, vision, unified)

### With Chunk Model
- Creates `Chunk` instances with proper relationships
- Sets chunk type, metadata, and content
- Establishes parent-child and related chunk relationships

### With Knowledge Base
- Updates document statistics after chunking
- Tracks token counts and chunk counts
- Integrates with embedding pipeline

## Best Practices

1. **Always use DocumentChunkingService** for the complete pipeline
2. **Set save_chunks=True** to automatically persist chunks
3. **Check extraction success** before proceeding with chunking
4. **Use appropriate chunk types** for different content
5. **Preserve coordinates** for visual elements
6. **Link related chunks** for better retrieval

## Future Enhancements

- [ ] Adaptive chunk sizing based on content complexity
- [ ] Semantic chunking using embeddings
- [ ] Multi-level hierarchical chunking
- [ ] Custom chunking strategies per document type
- [ ] Chunk quality scoring
- [ ] Automatic chunk optimization based on retrieval performance
