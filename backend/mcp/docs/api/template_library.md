# Template Library API Documentation

## Overview

The Template Library API provides endpoints for managing workflow templates, including template categories, template instantiation, validation, and feedback.

## Authentication

All API endpoints require JWT authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_token>
```

## Rate Limiting

Standard rate limiting applies to all endpoints:
- 100 requests per minute for authenticated users
- 20 requests per minute for unauthenticated users

## API Endpoints

### Template Categories

#### List Categories

```
GET /api/v1/template-library/categories/
```

Returns a list of all template categories.

**Response**

```json
[
  {
    "id": "uuid",
    "name": "Data Processing",
    "description": "Templates for data processing workflows",
    "icon": "code",
    "order": 1,
    "is_active": true,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

#### Create Category

```
POST /api/v1/template-library/categories/
```

Creates a new template category.

**Request Body**

```json
{
  "name": "Data Processing",
  "description": "Templates for data processing workflows",
  "icon": "code",
  "order": 1
}
```

**Response**

```json
{
  "id": "uuid",
  "name": "Data Processing",
  "description": "Templates for data processing workflows",
  "icon": "code",
  "order": 1,
  "is_active": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Templates

#### List Templates

```
GET /api/v1/template-library/templates/
```

Returns a list of all templates. Supports filtering by category, status, and search terms.

**Query Parameters**

- `category`: Filter by category ID
- `status`: Filter by lifecycle status (draft, published, deprecated)
- `search`: Search in name and description
- `ordering`: Order by field (e.g., `-created_at` for newest first)

**Response**

```json
[
  {
    "id": "uuid",
    "name": "Data Cleaning Template",
    "description": "A template for data cleaning workflows",
    "category": {
      "id": "uuid",
      "name": "Data Processing"
    },
    "version": "1.0.0",
    "lifecycle_status": "published",
    "workflow_id": "uuid",
    "configuration_schema": {
      "type": "object",
      "properties": {
        "input_file": {
          "type": "string",
          "description": "Path to input file"
        },
        "output_file": {
          "type": "string",
          "description": "Path to output file"
        }
      },
      "required": ["input_file", "output_file"]
    },
    "created_by": {
      "id": "uuid",
      "email": "user@example.com"
    },
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z",
    "tags": ["data", "cleaning"],
    "is_active": true,
    "usage_count": 10,
    "average_rating": 4.5
  }
]
```

#### Create Template

```
POST /api/v1/template-library/templates/
```

Creates a new template.

**Request Body**

```json
{
  "name": "Data Cleaning Template",
  "description": "A template for data cleaning workflows",
  "category": "uuid",
  "version": "1.0.0",
  "workflow_id": "uuid",
  "configuration_schema": {
    "type": "object",
    "properties": {
      "input_file": {
        "type": "string",
        "description": "Path to input file"
      },
      "output_file": {
        "type": "string",
        "description": "Path to output file"
      }
    },
    "required": ["input_file", "output_file"]
  },
  "lifecycle_status": "draft",
  "tags": ["data", "cleaning"]
}
```

**Response**

```json
{
  "id": "uuid",
  "name": "Data Cleaning Template",
  "description": "A template for data cleaning workflows",
  "category": {
    "id": "uuid",
    "name": "Data Processing"
  },
  "version": "1.0.0",
  "workflow_id": "uuid",
  "configuration_schema": {
    "type": "object",
    "properties": {
      "input_file": {
        "type": "string",
        "description": "Path to input file"
      },
      "output_file": {
        "type": "string",
        "description": "Path to output file"
      }
    },
    "required": ["input_file", "output_file"]
  },
  "lifecycle_status": "draft",
  "created_by": {
    "id": "uuid",
    "email": "user@example.com"
  },
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z",
  "tags": ["data", "cleaning"],
  "is_active": true,
  "usage_count": 0,
  "average_rating": null
}
```

#### Get Template Details

```
GET /api/v1/template-library/templates/{id}/
```

Returns details for a specific template.

**Response**

Same as the create template response.

#### Update Template

```
PUT /api/v1/template-library/templates/{id}/
```

Updates a template.

**Request Body**

Same as the create template request.

**Response**

Same as the create template response.

#### Instantiate Template

```
POST /api/v1/template-library/templates/{id}/instantiate/
```

Creates a new workflow from a template.

**Request Body**

```json
{
  "configuration": {
    "input_file": "/path/to/input.csv",
    "output_file": "/path/to/output.csv"
  }
}
```

**Response**

```json
{
  "id": "uuid",
  "template": {
    "id": "uuid",
    "name": "Data Cleaning Template"
  },
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  },
  "created_workflow_id": "uuid",
  "configuration_used": {
    "input_file": "/path/to/input.csv",
    "output_file": "/path/to/output.csv"
  },
  "created_at": "2023-01-01T00:00:00Z"
}
```

### Template Validations

#### List Validations

```
GET /api/v1/template-library/validations/
```

Returns a list of all template validations.

**Query Parameters**

- `template`: Filter by template ID
- `status`: Filter by validation status (pending, running, passed, failed)

**Response**

```json
[
  {
    "id": "uuid",
    "template": {
      "id": "uuid",
      "name": "Data Cleaning Template"
    },
    "status": "passed",
    "validation_results": {
      "tests_run": 5,
      "tests_passed": 5,
      "details": [...]
    },
    "notes": "All tests passed successfully",
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

#### Create Validation

```
POST /api/v1/template-library/validations/
```

Creates a new template validation.

**Request Body**

```json
{
  "template": "uuid",
  "notes": "Initial validation"
}
```

**Response**

```json
{
  "id": "uuid",
  "template": {
    "id": "uuid",
    "name": "Data Cleaning Template"
  },
  "status": "pending",
  "validation_results": null,
  "notes": "Initial validation",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Template Feedback

#### List Feedback

```
GET /api/v1/template-library/feedback/
```

Returns a list of all template feedback.

**Query Parameters**

- `template`: Filter by template ID
- `rating`: Filter by rating (1-5)

**Response**

```json
[
  {
    "id": "uuid",
    "template": {
      "id": "uuid",
      "name": "Data Cleaning Template"
    },
    "user": {
      "id": "uuid",
      "email": "user@example.com"
    },
    "rating": 5,
    "comments": "Works great!",
    "created_at": "2023-01-01T00:00:00Z"
  }
]
```

#### Create Feedback

```
POST /api/v1/template-library/feedback/
```

Creates new template feedback.

**Request Body**

```json
{
  "template": "uuid",
  "rating": 5,
  "comments": "Works great!"
}
```

**Response**

```json
{
  "id": "uuid",
  "template": {
    "id": "uuid",
    "name": "Data Cleaning Template"
  },
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  },
  "rating": 5,
  "comments": "Works great!",
  "created_at": "2023-01-01T00:00:00Z"
}
```

### Template Events

#### List Events

```
GET /api/v1/template-library/events/
```

Returns a list of all template events.

**Query Parameters**

- `template`: Filter by template ID
- `event_type`: Filter by event type (view, instantiate, etc.)
- `user`: Filter by user ID

**Response**

```json
[
  {
    "id": "uuid",
    "template": {
      "id": "uuid",
      "name": "Data Cleaning Template"
    },
    "user": {
      "id": "uuid",
      "email": "user@example.com"
    },
    "event_type": "view",
    "metadata": {
      "source": "search_results"
    },
    "created_at": "2023-01-01T00:00:00Z"
  }
]
```

## WebSocket Integration

The Template Library app supports real-time updates via WebSockets for template events and validations.

### Template Events Channel

```
ws://example.com/ws/template-events/{template_id}/
```

Broadcasts events related to a specific template, such as instantiations, validations, and feedback.

**Message Format**

```json
{
  "type": "template_event",
  "data": {
    "event_type": "instantiation",
    "template_id": "uuid",
    "user": "user@example.com",
    "timestamp": "2023-01-01T00:00:00Z",
    "details": {...}
  }
}
```

### Template Validation Channel

```
ws://example.com/ws/template-validations/{validation_id}/
```

Broadcasts updates about a specific template validation process.

**Message Format**

```json
{
  "type": "validation_update",
  "data": {
    "validation_id": "uuid",
    "template_id": "uuid",
    "status": "running",
    "progress": 75,
    "current_step": "Running test case 3/4",
    "timestamp": "2023-01-01T00:00:00Z"
  }
}
```

## Error Responses

All endpoints follow standard HTTP status codes and return detailed error messages:

```json
{
  "error": "validation_error",
  "detail": "Invalid template configuration",
  "fields": {
    "configuration_schema": ["This field is required"]
  }
}
```

Common error codes:
- 400: Bad Request - Invalid input
- 401: Unauthorized - Authentication required
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource not found
- 409: Conflict - Resource conflict
- 500: Internal Server Error - Server-side error

## Pagination

List endpoints support standard pagination with the following query parameters:
- `page`: Page number (default: 1)
- `page_size`: Number of items per page (default: 10, max: 100)

Paginated responses include:

```json
{
  "count": 100,
  "next": "http://example.com/api/v1/template-library/templates/?page=2",
  "previous": null,
  "results": [...]
}
```
