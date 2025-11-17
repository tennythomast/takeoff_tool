# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dataelan is a comprehensive AI-powered platform with intelligent LLM routing, cost optimization, and multi-tenant workspace management. The platform consists of a Django backend with WebSocket support and a Next.js frontend, designed for enterprise-scale AI applications. A key feature is the **Takeoff** module for advanced PDF/engineering drawing extraction using vector analysis and LLM-based element detection.

## Quick Start Commands

### Backend (Django)
```bash
# Setup and run backend
cd backend
python -m venv ../dataelan_env
source ../dataelan_env/bin/activate  # On Windows: ../dataelan_env/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Run tests
python manage.py test

# Management commands
python manage.py setup_providers          # Setup LLM providers
python manage.py setup_intelligent_routing # Setup routing rules
python manage.py collectstatic --noinput  # Collect static files
```

### Frontend (Next.js)
```bash
# Setup and run frontend
cd frontend
npm install
npm run dev    # Development server (runs on 0.0.0.0:3000)
npm run build  # Production build
npm run start  # Production server
npm run lint   # Lint code
npm test       # Run Jest tests
npm run test:watch # Run tests in watch mode
```

### Docker (Full Stack)
```bash
# Run complete application with Docker
docker-compose up -d          # Start all services
docker-compose down           # Stop all services  
docker-compose build          # Rebuild images
docker-compose logs backend   # View backend logs
docker-compose logs frontend  # View frontend logs
```

## Architecture Overview

### Backend (Django)
The backend uses a modular Django architecture with the following key applications:

**Core Apps:**
- `core/` - Authentication, users, organizations, base models with soft delete
- `workspaces/` - Multi-tenant workspace management with role-based access
- `modelhub/` - Intelligent LLM provider management and cost-optimized routing
- `prompt/` - Chat sessions and WebSocket consumers for real-time messaging
- `context_manager/` - Universal context management across all AI interactions

**AI & Automation:**
- `agents/` - Configurable AI agents with custom instructions and tools
- `rag_service/` - Retrieval-Augmented Generation with Qdrant vector database
- `mcp/` - Model Control Plane for external service integrations

**Document Processing:**
- `takeoff/` - Engineering drawing extraction with vector text/shape extraction and LLM-based element detection
  - Vector text extractor for precise text positioning
  - Vector shape extractor for geometric element detection
  - Chunked LLM extraction service for large documents (handles 100+ elements)
  - Measurement and validation services
  - Schema-based validation for extracted data

**Supporting Services:**
- `file_storage/` - File upload and management system
- `benchmark/` - Platform evaluation and performance metrics

**Key Architectural Patterns:**
- WebSocket architecture with Django Channels for real-time features
- Intelligent LLM routing with complexity analysis (85% rule-based, 15% LLM escalation)
- Cost tracking and optimization across all AI operations
- Multi-tenancy with organization-based soft isolation
- UUID-based entities with soft delete patterns

### Frontend (Next.js)
Modern Next.js 15 application with App Router architecture:

**Key Features:**
- TypeScript with comprehensive type safety
- Tailwind CSS with custom design system using Radix UI and shadcn/ui
- Real-time WebSocket chat with streaming AI responses
- Multi-tenant workspace management with data isolation
- Cost optimization dashboard with analytics and visualizations
- JWT-based authentication with automatic token refresh

**State Management:**
- React Context for global state (auth, chat, sidebar)
- TanStack React Query for server state management
- Local/session storage for strategic persistence

## Database & Infrastructure

**Database:** PostgreSQL with atomic transactions and proper indexing
**Caching:** Redis for sessions, channel layers, and application caching
**WebSockets:** Django Channels with Redis backend for real-time communication
**Background Tasks:** Celery for asynchronous processing
**Vector Database:** Qdrant for RAG and semantic search capabilities

### Document Processing Stack

The Takeoff module uses specialized libraries for PDF and document processing:

**PDF Processing:**
- PyMuPDF (fitz) - Advanced PDF extraction with vector graphics support
- PyPDF2 - PDF processing (backward compatibility)
- pdf2image - PDF to image conversion

**Table Extraction:**
- camelot-py - Table extraction from PDFs
- pdfplumber - Alternative table extraction
- pandas - DataFrame handling for tabulated data

**Document Formats:**
- python-docx - Word document processing
- beautifulsoup4 - HTML processing
- markdown - Markdown parsing

**Text Processing:**
- chardet - Encoding detection
- sentence-transformers - Local embeddings for semantic search

**Image Processing:**
- Pillow (PIL) - Image manipulation and processing

## Environment Variables

### Backend (.env)
```bash
# Database
POSTGRES_NAME=takeoff
POSTGRES_USER=takeoff
POSTGRES_PASSWORD=takeoff
POSTGRES_HOST=localhost  # or 'db' for Docker
POSTGRES_PORT=5434       # Docker mapped port (internal: 5432)

# Redis
REDIS_HOST=localhost     # or 'redis' for Docker
REDIS_PORT=6379

# Django
DEBUG=1
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# CORS settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000

# API settings
API_HOST=0.0.0.0
API_PORT=8000

# Channel Layers (for WebSockets)
CHANNEL_LAYERS_BACKEND=channels_redis.core.RedisChannelLayer

# MCP encryption key (auto-generated if not provided)
MCP_ENCRYPTION_KEY=<your-fernet-key>

# AI Provider API Keys (add as needed)
ANTHROPIC_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>
COHERE_API_KEY=<your-key>
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/chat/
```

## Takeoff Module - Document Extraction

The Takeoff module provides advanced PDF and engineering drawing extraction capabilities:

### Extraction Services

1. **Vector Text Extractor** (`vector_text_extractor.py`)
   - Extracts text with precise positioning from PDF vector graphics
   - Handles fonts, encoding, and text transformations
   - Returns structured text with bounding boxes and page numbers

2. **Vector Shape Extractor** (`vector_shape_extractor.py`)
   - Detects geometric shapes (circles, rectangles, polygons, ellipses)
   - Analyzes line styles, colors, and fill patterns
   - Useful for detecting element symbols in engineering drawings

3. **LLM Extraction Service** (`llm_extraction.py`)
   - Uses LLMs to extract structured elements from documents
   - Supports single-pass extraction for smaller documents (<30 elements)

4. **Chunked LLM Extraction** (`llm_extraction_chunked.py`)
   - Solves output token limit issues for large documents
   - Processes documents in chunks while maintaining full context
   - Handles 100+ elements reliably
   - Automatic deduplication and continuation detection
   - Configuration:
     - `ELEMENTS_PER_CHUNK = 15` (safe for 8K token limits)
     - `MAX_CHUNKS = 20` (allows 300 total elements)
     - `MAX_OUTPUT_TOKENS = 8000` (conservative limit)

### When to Use Which Extraction Method

- **Vector extractors**: For raw text/shape data without semantic understanding
- **LLM extraction**: For documents with <30 structured elements
- **Chunked LLM extraction**: For large documents (50+ elements) or unknown size

### Extraction Models

The `takeoff/models.py` defines comprehensive data structures:
- `ShapeType`, `LineStyle`, `Point`, `BoundingBox`
- `ShapeStyle` with validation for element symbols
- Measurement and validation models

See `backend/takeoff/services/CHUNKED_EXTRACTION_README.md` for detailed documentation on the chunked extraction service.

## Development Workflow

### Adding New Features

1. **Backend Changes:**
   - Follow Django app structure with models, serializers, views, urls
   - Add migrations: `python manage.py makemigrations`
   - Apply migrations: `python manage.py migrate`
   - Add API documentation with drf-spectacular decorators
   - WebSocket consumers go in `consumers.py`, routing in `routing.py`

2. **Frontend Changes:**
   - Use TypeScript for all new code
   - Follow shadcn/ui component patterns
   - Add pages to `src/app/` directory (App Router)
   - Use React Query for API calls with proper error handling
   - Add tests in `__tests__/` or `.test.tsx` files

3. **Database Changes:**
   - Always create migrations for model changes
   - Follow UUID primary key pattern from BaseModel
   - Use soft delete via SoftDeletableMixin
   - Add proper indexes for query performance

### Key Development Patterns

**Backend:**
- Use `BaseModel` for all models (UUID, soft delete, timestamps)
- Implement proper DRF permissions and serializers
- Use `UnifiedLLMClient` for AI provider integrations
- Follow organization-based multi-tenancy patterns

**Frontend:**
- Use TypeScript interfaces for all API responses
- Implement proper loading and error states
- Follow responsive design with Tailwind CSS
- Use React Hook Form with Zod validation for forms

## API Documentation

When backend is running, API documentation is available at:
- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

## Testing

### Backend Testing
```bash
cd backend
python manage.py test                    # Run all tests
python manage.py test core              # Test specific app
python manage.py test --keepdb          # Keep test database
coverage run --source='.' manage.py test # Run with coverage
coverage report                         # View coverage report
```

### Frontend Testing
```bash
cd frontend
npm test                                # Run Jest tests
npm run test:watch                      # Watch mode
```

## Important Notes

### General Platform
- **Multi-tenancy**: All models use organization-based isolation - always filter by organization
- **Cost Tracking**: All AI operations track costs - use `ModelMetrics` for monitoring
- **WebSocket Auth**: WebSocket connections require JWT token authentication
- **Soft Delete**: Never use `.delete()` directly - models use soft delete patterns (where implemented)
- **LLM Routing**: Use `LLMRouter` service for intelligent model selection based on complexity
- **Context Management**: Leverage `UniversalContextService` for cross-domain context sharing

### Takeoff Module
- **Extraction Method Selection**: Use chunked extraction (`llm_extraction_chunked.py`) for documents with 50+ elements or unknown size
- **Token Limits**: The chunked service handles output token limits by processing in batches while maintaining full context
- **Cost Implications**: Chunked extraction costs ~3x more than single-pass but guarantees complete extraction
- **Vector Extraction**: Use vector extractors (`vector_text_extractor.py`, `vector_shape_extractor.py`) when you need raw geometric/text data without semantic understanding
- **Deduplication**: The chunked service automatically deduplicates elements across chunks
- **Testing Extraction**: Test scripts are in `backend/takeoff/tests/` - use Docker exec to run them

## Troubleshooting

**Database Connection Issues:**
- Check PostgreSQL is running on port 5434 (Docker host, mapped from container's 5432) or 5432 (local)
- Default database name is `takeoff` (not `dataelan`)
- Verify credentials in environment variables match `.env.example`
- Docker: `docker-compose ps` to check if db service is healthy

**WebSocket Connection Issues:**
- Ensure Redis is running and accessible
- Check CORS settings in Django settings
- Verify token authentication is working

**Frontend API Issues:**
- Check NEXT_PUBLIC_API_URL is correct
- Verify backend is running and accessible
- Check browser network tab for CORS errors

**Docker Issues:**
- Ensure all services are healthy: `docker-compose ps`
- Check service logs: `docker-compose logs <service>`
- Rebuild if needed: `docker-compose build --no-cache`
- Container names: `takeoff_tool-backend-1`, `takeoff_tool-frontend-1`, `takeoff_tool-db-1`, `takeoff_tool-redis-1`

**Takeoff Extraction Issues:**
- **Truncated Output**: Use chunked extraction service for documents with many elements
- **Missing Dependencies**: Ensure PyMuPDF, camelot-py, and other document processing libraries are installed
- **Token Limit Errors**: Reduce `ELEMENTS_PER_CHUNK` in chunked service (default: 15)
- **Incomplete Extraction**: Check raw response files in `backend/takeoff/tests/output/` directory
- **Shape Detection**: Vector shape extractor requires vector graphics in PDF (not rasterized images)
- **Text Positioning**: Vector text extractor provides more accurate positioning than PyMuPDF's built-in text extraction