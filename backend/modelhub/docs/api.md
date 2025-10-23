# API Endpoints

The `modelhub` app exposes a comprehensive REST API for managing providers, models, API keys, routing rules, and model metrics. All endpoints require JWT authentication.

## Endpoints

### Providers
- `GET /api/modelhub/providers/` — List all providers
- `POST /api/modelhub/providers/` — Create a new provider
- `GET /api/modelhub/providers/{id}/` — Retrieve provider details
- `PUT/PATCH /api/modelhub/providers/{id}/` — Update provider
- `DELETE /api/modelhub/providers/{id}/` — Delete provider

### Models
- `GET /api/modelhub/models/` — List all registered models
- `POST /api/modelhub/models/` — Register a new model
- `GET /api/modelhub/models/{id}/` — Retrieve model details
- `PUT/PATCH /api/modelhub/models/{id}/` — Update model
- `DELETE /api/modelhub/models/{id}/` — Delete model
- `POST /api/modelhub/models/{id}/estimate_cost/` — Estimate cost for a given model and token counts

### API Keys
- `GET /api/modelhub/api-keys/` — List API keys
- `POST /api/modelhub/api-keys/` — Create API key
- `GET /api/modelhub/api-keys/{id}/` — Retrieve API key details
- `PUT/PATCH /api/modelhub/api-keys/{id}/` — Update API key
- `DELETE /api/modelhub/api-keys/{id}/` — Delete API key
- `GET /api/modelhub/api-keys/usage_summary/` — Get usage summary for all API keys
- `GET /api/modelhub/api-keys/health_status/` — Get health status of API keys
- `GET /api/modelhub/api-keys/{id}/quota_status/` — Get quota status for a specific API key

### Routing Rules
- `GET /api/modelhub/routing-rules/` — List routing rules
- `POST /api/modelhub/routing-rules/` — Create routing rule
- `GET /api/modelhub/routing-rules/{id}/` — Retrieve routing rule
- `PUT/PATCH /api/modelhub/routing-rules/{id}/` — Update routing rule
- `DELETE /api/modelhub/routing-rules/{id}/` — Delete routing rule
- `POST /api/modelhub/routing-rules/evaluate/` — Evaluate routing rules for a given model type and context

### Model Metrics
- `GET /api/modelhub/metrics/` — List model metrics
- `POST /api/modelhub/metrics/` — Create metric record
- `GET /api/modelhub/metrics/{id}/` — Retrieve metric details
- `GET /api/modelhub/metrics/cost_summary/` — Get cost summary for the organization
- `GET /api/modelhub/metrics/optimization_stats/` — Get optimization statistics
- `GET /api/modelhub/metrics/dashboard_summary/` — Get all dashboard data in one call

---

## Authentication
All endpoints require JWT authentication. Include your JWT token in the `Authorization` header:
```
Authorization: Bearer <your_token>
```

## Permissions
- Only authenticated users can access endpoints.
- Some actions (such as deleting or updating) may require admin or organization owner permissions.

## Pagination
- List endpoints are paginated. Use `?page=` and `?page_size=` query parameters.

## Error Handling
- Standard error responses include HTTP status codes and error messages.
- Validation errors return `400 Bad Request` with details.
- Permission errors return `403 Forbidden`.

## Example Request/Response
```http
# Request
POST /api/modelhub/models/1/estimate_cost/
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "input_tokens": 1000,
  "output_tokens": 500
}

# Response
{
  "estimated_cost": 0.0025
}
```

---

For additional details, see the OpenAPI/Swagger documentation or the `drf-spectacular` schema endpoint.
