# Chunked LLM Extraction Service

## Overview

This is an alternative implementation of the LLM extraction service that solves the **output token limit** problem by requesting output in chunks while maintaining full document context.

## Problem Statement

The original extraction service was hitting output token limits when extracting from large documents:
- Documents with 50+ elements would get truncated mid-extraction
- Even with `max_tokens=50000`, the LLM's actual output limit (typically ~8K tokens) was being hit
- This resulted in incomplete extractions and duplicate key errors

## Solution: Chunked Output with Full Context

### Key Strategy

1. **Full Context**: Send the ENTIRE document to the LLM (all pages, all text)
2. **Chunked Output**: Request output in batches (e.g., "extract first 25 elements")
3. **Automatic Continuation**: Detect when more elements remain and request the next batch
4. **Deduplication**: Filter out any duplicate elements across chunks
5. **Merge Results**: Combine all chunks into a single complete extraction

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    FULL DOCUMENT CONTEXT                    │
│  (All pages, all text - sent to LLM every time)            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CHUNK 1 REQUEST                          │
│  "Extract the FIRST 25 concrete elements"                  │
│  Output limit: 8000 tokens                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    [25 elements extracted]
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CHUNK 2 REQUEST                          │
│  "Extract the NEXT 25 elements (skip: PF1, PF2, ...)"     │
│  Output limit: 8000 tokens                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    [25 more elements extracted]
                            │
                            ▼
                    ... continues until complete
```

## Configuration

### Key Parameters

```python
ELEMENTS_PER_CHUNK = 15      # Request this many elements per chunk
MAX_CHUNKS = 20              # Maximum chunks to prevent infinite loops
MAX_OUTPUT_TOKENS = 8000     # Conservative output limit per chunk
```

### Why These Values?

- **15 elements per chunk**: Safely fits within 8K token limit even with detailed specs (reduced from 25 to prevent truncation)
- **8000 tokens**: Conservative limit that works across all major LLMs
- **20 max chunks**: Allows for 300 total elements (15 × 20)

## Files Created

### 1. `llm_extraction_chunked.py`
The main chunked extraction service with:
- Full context prompt generation
- Chunk-by-chunk extraction logic
- Duplicate detection and filtering
- Automatic continuation detection
- Complete table parsing (copied from original)

### 2. `test_chunked_extraction.py`
Test script to validate the chunked extraction:
- Uses real documents from the database
- Compares results with original extraction
- Saves detailed output for analysis

### 3. `CHUNKED_EXTRACTION_README.md`
This documentation file

## Usage

### Running the Test

```bash
docker exec takeoff_tool-backend-1 python /app/backend/takeoff/tests/test_chunked_extraction.py
```

### Using in Code

```python
from takeoff.services.extractors.llm_extraction_chunked import ChunkedLLMExtractionService

service = ChunkedLLMExtractionService()

result = await service.extract_elements(
    drawing_id="your-drawing-id",
    trade="concrete"
)

if result['success']:
    print(f"Extracted {result['element_count']} elements")
    print(f"Processed {result['chunks_processed']} chunks")
    print(f"Total cost: ${result['total_cost_usd']:.4f}")
```

## Advantages Over Original

### ✅ Solves Token Limit Issues
- No more truncated extractions
- Can handle documents with 100+ elements
- Each chunk stays within safe token limits

### ✅ Better Cost Tracking
- Tracks cost per chunk
- Reports total cost across all chunks
- Shows processing time per chunk

### ✅ More Reliable
- Automatic continuation until complete
- Duplicate detection prevents errors
- Graceful handling of edge cases

### ✅ Better Debugging
- Saves raw response for each chunk
- Detailed logging of chunk processing
- Clear visibility into extraction progress

## Continuation Detection

The service detects when to continue in multiple ways:

1. **Explicit Markers**: LLM adds "CONTINUE: YES" or "CONTINUE: NO"
2. **Chunk Size**: If we get a full chunk (25 elements), assume more remain
3. **Partial Chunk**: If we get fewer than requested, likely complete

## Deduplication Strategy

Elements are deduplicated based on `element_id`:
- Track all extracted element IDs
- Skip any element with an ID already seen
- Log duplicate attempts for debugging

## Prompt Strategy

### First Chunk
```
Extract the FIRST 25 concrete elements you find.
Start from the beginning of the document.
Stop after 25 elements (or when you reach the end).
```

### Continuation Chunks
```
You have already extracted 25 elements.
Previously extracted IDs: PF1, PF2, PF3, ...

Extract the NEXT 25 concrete elements (NOT in the list above).
Skip any elements you've already extracted.
```

## Comparison with Original

| Feature | Original | Chunked |
|---------|----------|---------|
| **Context** | Full document | Full document |
| **Output** | All at once | In chunks |
| **Token Limit** | 50K (often hit) | 8K per chunk (safe) |
| **Max Elements** | ~50 (before truncation) | 500+ (20 chunks × 25) |
| **Cost Tracking** | Single cost | Per-chunk + total |
| **Debugging** | Single response file | Multiple chunk files |
| **Reliability** | Fails on large docs | Handles any size |

## When to Use Which

### Use Original (`llm_extraction.py`)
- Small documents (<30 elements)
- Quick single-pass extraction
- When you know the document fits in output limits

### Use Chunked (`llm_extraction_chunked.py`)
- Large documents (50+ elements)
- Unknown document size
- When reliability is critical
- When you need detailed cost tracking

## Future Enhancements

### Potential Improvements
1. **Dynamic chunk sizing**: Adjust based on element complexity
2. **Parallel chunk processing**: Extract multiple chunks simultaneously
3. **Smart continuation**: Use element counts from document to predict chunks needed
4. **Streaming support**: Stream chunks as they're extracted
5. **Resume capability**: Resume from a failed chunk

## Testing Results

After implementation, test with:
- Small documents (verify no regression)
- Large documents (verify completion)
- Edge cases (empty documents, single element, etc.)

## Reverting to Original

If needed, simply use the original service:

```python
from takeoff.services.extractors.llm_extraction import LLMExtractionService
```

The original service remains unchanged and fully functional.

## Cost Implications

### Cost Comparison

For a document with 75 elements:

**Original Approach** (fails):
- 1 request with full context
- Truncated at ~50 elements
- Cost: ~$0.04
- Result: Incomplete ❌

**Chunked Approach** (succeeds):
- 3 requests with full context
- All 75 elements extracted
- Cost: ~$0.12 (3 × $0.04)
- Result: Complete ✅

**Trade-off**: ~3x cost for complete extraction vs incomplete extraction

## Monitoring

Watch for:
- Average chunks per document
- Duplicate detection frequency
- Continuation accuracy
- Cost per chunk trends

## Support

For issues or questions:
1. Check the raw chunk response files in `/app/backend/takeoff/tests/output/`
2. Review the detailed logs for each chunk
3. Compare with original extraction results
4. Verify continuation markers in responses
