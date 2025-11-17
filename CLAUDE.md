# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dataelan is a comprehensive AI-powered platform with intelligent LLM routing, cost optimization, and multi-tenant workspace management. The platform currently exposes a Django backend with WebSocket support; the previous React/Next.js frontend has been removed and is being rebuilt from scratch.

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

### Docker (Full Stack)
```bash
# Run complete application with Docker
docker-compose up -d          # Start all services
docker-compose down           # Stop all services  
docker-compose build          # Rebuild images
docker-compose logs backend   # View backend logs
```

> **Note:** Docker currently builds/runs only the backend, Postgres, and Redis services. Reintroduce a frontend service after scaffolding the new client application.
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
- `workflows/` - Node-based workflow automation system
- `rag_service/` - Retrieval-Augmented Generation with Qdrant vector database
- `mcp/` - Model Control Plane for external service integrations

**Supporting Services:**
- `template_library/` - Reusable templates for prompts and workflows
- `actionable_tasks/` - Task management and tracking
- `file_storage/` - File upload and management system

**Key Architectural Patterns:**
- WebSocket architecture with Django Channels for real-time features
- Intelligent LLM routing with complexity analysis (85% rule-based, 15% LLM escalation)
- Cost tracking and optimization across all AI operations
- Multi-tenancy with organization-based soft isolation
- UUID-based entities with soft delete patterns

### Frontend (Rebuild in Progress)
The previous Next.js client has been removed. When the new frontend is scaffolded, document its stack, commands, and integration points here so other contributors understand how to run it locally and inside Docker.

## Database & Infrastructure

**Database:** PostgreSQL with atomic transactions and proper indexing
**Caching:** Redis for sessions, channel layers, and application caching  
**WebSockets:** Django Channels with Redis backend for real-time communication
**Background Tasks:** Celery for asynchronous processing
**Vector Database:** Qdrant for RAG and semantic search capabilities

## Environment Variables

### Backend (.env)
```bash
# Database
POSTGRES_NAME=dataelan
POSTGRES_USER=dataelan
POSTGRES_PASSWORD=dataelan
POSTGRES_HOST=localhost  # or 'db' for Docker
POSTGRES_PORT=5434

# Redis
REDIS_HOST=localhost     # or 'redis' for Docker
REDIS_PORT=6379

# Django
DEBUG=True
SECRET_KEY=django-insecure-0kj$e7jk7@8s3pkn5v2eux*9f%g0uftkf&l6@l5(3c71w^4_ku
MCP_ENCRYPTION_KEY=<your-fernet-key>

# AI Provider API Keys (add as needed)
ANTHROPIC_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>
COHERE_API_KEY=<your-key>
```

### Frontend (.env.local)
Pending. Define the necessary environment variables once the new frontend stack is chosen and scaffolded.

## Development Workflow

### Adding New Features

1. **Backend Changes:**
   - Follow Django app structure with models, serializers, views, urls
   - Add migrations: `python manage.py makemigrations`
   - Apply migrations: `python manage.py migrate`
   - Add API documentation with drf-spectacular decorators
   - WebSocket consumers go in `consumers.py`, routing in `routing.py`

2. **Frontend Changes (Coming Soon):**
   - Document coding standards once the new framework is selected
   - Add run/build/test commands for the new client
   - Update Docker integration to include the frontend container

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
Pending until the new frontend is created. Document the testing workflow here once available.

## Important Notes

- **Multi-tenancy**: All models use organization-based isolation - always filter by organization
- **Cost Tracking**: All AI operations track costs - use `ModelMetrics` for monitoring
- **WebSocket Auth**: WebSocket connections require JWT token authentication
- **Soft Delete**: Never use `.delete()` directly - models use soft delete patterns
- **LLM Routing**: Use `LLMRouter` service for intelligent model selection based on complexity
- **Context Management**: Leverage `UniversalContextService` for cross-domain context sharing

## Troubleshooting

**Database Connection Issues:**
- Check PostgreSQL is running on port 5434 (Docker) or 5432 (local)
- Verify credentials in environment variables

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