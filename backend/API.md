# Dataelan API Documentation

## Overview

The Dataelan API is a RESTful API that follows standard REST conventions. All data is sent and received as JSON.

## Authentication

The API uses JWT (JSON Web Token) authentication. To authenticate, you need to:

1. Obtain a token pair (access + refresh tokens):
```http
POST /api/auth/token/
{
    "email": "user@example.com",
    "password": "your_password"
}
```

2. Use the access token in subsequent requests:
```http
Authorization: Bearer <your_access_token>
```

3. Refresh the access token when it expires:
```http
POST /api/auth/token/refresh/
{
    "refresh": "<your_refresh_token>"
}
```

## API Versioning

The API uses Accept header versioning. Current version is 1.0.

Example:
```http
Accept: application/json; version=1.0
```

## Common Response Format

All responses follow a consistent format:

Success Response:
```json
{
    "data": {
        // Response data here
    },
    "status_code": 200
}
```

Error Response:
```json
{
    "message": "Error description",
    "errors": {
        // Detailed error information
    },
    "status_code": 400
}
```

## Endpoints

### Projects

#### List Projects
```http
GET /api/v1/projects/
```

#### Create Project
```http
POST /api/v1/projects/
{
    "name": "Project Name",
    "description": "Project Description",
    "organization": "org_id",
    "status": "ACTIVE"
}
```

#### Project Collaborators
```http
GET /api/v1/projects/{project_id}/collaborators/
POST /api/v1/projects/{project_id}/collaborators/
{
    "user": "user_id",
    "role": "EDITOR"
}
```

### Prompt Sessions

#### List Prompt Sessions
```http
GET /api/v1/prompt-sessions/
```

#### Create Prompt Session
```http
POST /api/v1/prompt-sessions/
{
    "name": "Session Name",
    "project": "project_id"
}
```

#### Prompts
```http
GET /api/v1/prompt-sessions/{session_id}/prompts/
POST /api/v1/prompt-sessions/{session_id}/prompts/
{
    "content": "Prompt content",
    "model": "MODEL_NAME"
}
```

### Actionable Tasks

#### List Tasks
```http
GET /api/v1/tasks/
```

#### Create Task
```http
POST /api/v1/tasks/
{
    "title": "Task Title",
    "description": "Task Description",
    "project": "project_id",
    "priority": "HIGH",
    "status": "PENDING",
    "due_date": "2025-06-01T00:00:00Z"
}
```

#### Task Actions
```http
POST /api/v1/tasks/{task_id}/complete/
POST /api/v1/tasks/{task_id}/cancel/
POST /api/v1/tasks/{task_id}/reopen/
```

## Pagination

All list endpoints are paginated with 50 items per page. Use `page` query parameter to navigate:

```http
GET /api/v1/projects/?page=2
```

Response includes pagination metadata:
```json
{
    "count": 100,
    "next": "http://api.example.org/api/v1/projects/?page=3",
    "previous": "http://api.example.org/api/v1/projects/?page=1",
    "results": []
}
```

## Filtering and Ordering

Most list endpoints support filtering and ordering:

```http
GET /api/v1/tasks/?status=PENDING&ordering=-due_date
```

## Rate Limiting

The API implements rate limiting based on user tiers:
- Free: 100 requests per minute
- Pro: 1000 requests per minute
- Enterprise: Custom limits

## Error Codes

- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Best Practices

1. Always include API version in Accept header
2. Use HTTPS for all requests
3. Implement proper error handling
4. Cache responses when appropriate
5. Use pagination for large datasets
6. Include proper authentication headers
