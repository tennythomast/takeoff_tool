# Model Control Plane (MCP) API

The Model Control Plane (MCP) API provides endpoints for managing external service integrations, resource discovery, and workspace-level access control.

## Authentication

All MCP API endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Rate Limiting

API requests are subject to rate limiting:
- 100 requests per minute for authenticated users
- 5 requests per minute for unauthenticated users

## Server Registry

### List Available MCP Server Types

```
GET /api/v1/mcp/registry/
```

Returns a list of registered MCP server types that can be connected to.

**Query Parameters:**
- `supports_workspace_scoping` (boolean): Filter by workspace scoping support
- `provider_type` (string): Filter by provider type (e.g., "jira", "github")

**Response:**
```json
[
  {
    "id": "1",
    "qualified_name": "jira/mcp-server",
    "display_name": "Jira Server",
    "description": "Connect to Jira Cloud or Server instances",
    "provider_type": "jira",
    "supports_workspace_scoping": true,
    "scoping_config_schema": {
      "properties": {
        "project_keys": {
          "type": "array",
          "items": {"type": "string"},
          "description": "List of Jira project keys to allow access to"
        }
      }
    }
  }
]
```

### Get Server Registry Configuration Schema

```
GET /api/v1/mcp/registry/{id}/config-schema/
```

Returns the configuration schema for a specific MCP server type.

**Response:**
```json
{
  "auth": {
    "type": "object",
    "properties": {
      "api_token": {"type": "string", "format": "password"},
      "base_url": {"type": "string", "format": "uri"}
    },
    "required": ["api_token", "base_url"]
  },
  "options": {
    "type": "object",
    "properties": {
      "timeout": {"type": "integer", "default": 30}
    }
  }
}
```

## Server Connections

### List Server Connections

```
GET /api/v1/mcp/connections/
```

Returns a list of MCP server connections for the current user's organizations.

**Query Parameters:**
- `organization` (uuid): Filter by organization ID
- `server` (integer): Filter by server registry ID
- `is_active` (boolean): Filter by active status

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "server": {
      "id": "1",
      "qualified_name": "jira/mcp-server",
      "display_name": "Jira Server"
    },
    "organization": {
      "id": "123e4567-e89b-12d3-a456-426614174111",
      "name": "Acme Corp"
    },
    "connection_name": "Acme Jira",
    "description": "Jira connection for Acme Corp",
    "is_active": true,
    "last_connected": "2023-07-14T10:30:00Z",
    "created_at": "2023-07-01T12:00:00Z",
    "created_by": {
      "id": "123e4567-e89b-12d3-a456-426614174222",
      "username": "john.doe"
    }
  }
]
```

### Create Server Connection

```
POST /api/v1/mcp/connections/
```

Creates a new MCP server connection.

**Request Body:**
```json
{
  "server": 1,
  "organization": "123e4567-e89b-12d3-a456-426614174111",
  "connection_name": "Acme Jira",
  "description": "Jira connection for Acme Corp",
  "auth_data": {
    "api_token": "your-api-token",
    "base_url": "https://acme.atlassian.net"
  },
  "config_options": {
    "timeout": 60
  }
}
```

**Response:** Same as GET with 201 Created status

### Test Connection

```
POST /api/v1/mcp/connections/{id}/test/
```

Tests the connection to the MCP server.

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "details": {
    "version": "8.20.0",
    "server_time": "2023-07-14T10:35:00Z"
  }
}
```

### Discover Resources

```
POST /api/v1/mcp/connections/{id}/discover/
```

Discovers resources available through this connection.

**Request Body:**
```json
{
  "resource_types": ["project", "issue"],
  "max_results": 100
}
```

**Response:**
```json
{
  "success": true,
  "message": "Resource discovery completed",
  "resources_found": 42,
  "resources_created": 35,
  "resources_updated": 7
}
```

## Resource Discovery

### List Discovered Resources

```
GET /api/v1/mcp/resources/
```

Returns a list of discovered resources.

**Query Parameters:**
- `connection` (uuid): Filter by connection ID
- `resource_type` (string): Filter by resource type
- `parent` (integer): Filter by parent resource ID
- `search` (string): Search by name or description
- `is_available` (boolean): Filter by availability status

**Response:**
```json
[
  {
    "id": 1,
    "connection": "123e4567-e89b-12d3-a456-426614174000",
    "resource_uri": "jira://PROJ/issues",
    "resource_name": "Project Issues",
    "resource_type": "issue",
    "description": "Issues in the PROJ project",
    "schema": {
      "properties": {
        "key": {"type": "string"},
        "summary": {"type": "string"}
      }
    },
    "operations": ["read", "create", "update"],
    "external_id": "10000",
    "parent_resource": 2,
    "discovered_at": "2023-07-14T10:40:00Z",
    "last_verified": "2023-07-14T10:40:00Z",
    "is_available": true
  }
]
```

## Workspace Access

### List Workspace Access Configurations

```
GET /api/v1/mcp/workspace-access/
```

Returns a list of workspace access configurations.

**Query Parameters:**
- `workspace` (uuid): Filter by workspace ID
- `connection` (uuid): Filter by connection ID
- `is_active` (boolean): Filter by active status

**Response:**
```json
[
  {
    "id": 1,
    "workspace": {
      "id": "123e4567-e89b-12d3-a456-426614174333",
      "name": "Product Development"
    },
    "connection": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "connection_name": "Acme Jira"
    },
    "access_name": "Jira Development Access",
    "description": "Access to development projects in Jira",
    "allowed_resources": [
      {
        "id": 2,
        "resource_name": "DEV Project",
        "resource_type": "project"
      }
    ],
    "resource_filters": {
      "project_keys": ["DEV", "QA"],
      "issue_types": ["bug", "task", "story"]
    },
    "permission_level": "write",
    "is_active": true,
    "auto_sync": true,
    "last_used": "2023-07-14T11:00:00Z",
    "usage_count": 42,
    "created_at": "2023-07-01T12:30:00Z",
    "created_by": {
      "id": "123e4567-e89b-12d3-a456-426614174222",
      "username": "john.doe"
    }
  }
]
```

### Add Resource to Workspace Access

```
POST /api/v1/mcp/workspace-access/{id}/add-resource/
```

Adds a resource to the allowed resources for this workspace access.

**Request Body:**
```json
{
  "resource_id": 3
}
```

**Response:**
```json
{
  "success": true,
  "message": "Resource added to workspace access",
  "resource": {
    "id": 3,
    "resource_name": "QA Project",
    "resource_type": "project"
  }
}
```

### Remove Resource from Workspace Access

```
POST /api/v1/mcp/workspace-access/{id}/remove-resource/
```

Removes a resource from the allowed resources for this workspace access.

**Request Body:**
```json
{
  "resource_id": 3
}
```

**Response:**
```json
{
  "success": true,
  "message": "Resource removed from workspace access"
}
```

## Resource Usage

### List Resource Usage

```
GET /api/v1/mcp/usage/
```

Returns a list of resource usage records.

**Query Parameters:**
- `workspace_access` (integer): Filter by workspace access ID
- `resource` (integer): Filter by resource ID
- `date_from` (date): Filter by usage date (from)
- `date_to` (date): Filter by usage date (to)

**Response:**
```json
[
  {
    "id": 1,
    "workspace_access": 1,
    "resource": {
      "id": 1,
      "resource_name": "Project Issues",
      "resource_type": "issue"
    },
    "usage_date": "2023-07-14",
    "request_count": 150,
    "error_count": 2,
    "avg_response_time": 0.45,
    "data_transferred": 2048,
    "cost": 0.05
  }
]
```

### Get Usage Summary

```
GET /api/v1/mcp/usage/summary/
```

Returns a summary of resource usage.

**Query Parameters:**
- `workspace` (uuid): Filter by workspace ID
- `connection` (uuid): Filter by connection ID
- `period` (string): Time period for summary (day, week, month)

**Response:**
```json
{
  "total_requests": 1250,
  "total_errors": 15,
  "avg_response_time": 0.52,
  "total_data_transferred": 15360,
  "total_cost": 0.75,
  "by_resource_type": {
    "issue": {
      "requests": 800,
      "errors": 10,
      "avg_response_time": 0.48
    },
    "project": {
      "requests": 450,
      "errors": 5,
      "avg_response_time": 0.60
    }
  }
}
```

## Resource Mappings

### List Resource Mappings

```
GET /api/v1/mcp/mappings/
```

Returns a list of resource mappings.

**Query Parameters:**
- `workspace_access` (integer): Filter by workspace access ID
- `resource` (integer): Filter by resource ID
- `component_type` (string): Filter by component type
- `component_id` (string): Filter by component ID

**Response:**
```json
[
  {
    "id": 1,
    "workspace_access": 1,
    "resource": {
      "id": 1,
      "resource_name": "Project Issues",
      "resource_type": "issue"
    },
    "component_type": "workflow",
    "component_id": "123e4567-e89b-12d3-a456-426614174444",
    "mapping_config": {
      "field_mappings": {
        "issue_key": "{{context.issue_id}}",
        "summary": "{{context.title}}"
      }
    },
    "last_synced": "2023-07-14T11:30:00Z",
    "sync_frequency": 3600,
    "is_active": true,
    "created_at": "2023-07-01T13:00:00Z"
  }
]
```

### Sync Resource Mapping

```
POST /api/v1/mcp/mappings/{id}/sync/
```

Triggers a synchronization for this resource mapping.

**Response:**
```json
{
  "success": true,
  "message": "Synchronization triggered",
  "sync_id": "123e4567-e89b-12d3-a456-426614174555",
  "items_synced": 15,
  "items_failed": 0
}
```

## WebSocket Integration

The MCP API also supports real-time updates via WebSocket connections:

```
ws://your-server/ws/mcp/resources/{connection_id}/
```

### Message Types

#### Resource Updated
```json
{
  "type": "resource_updated",
  "resource": {
    "id": 1,
    "resource_name": "Project Issues",
    "resource_type": "issue",
    "is_available": true
  }
}
```

#### Connection Status
```json
{
  "type": "connection_status",
  "connection_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "connected",
  "timestamp": "2023-07-14T12:00:00Z"
}
```

## Error Responses

All API endpoints use standard HTTP status codes and return detailed error messages:

```json
{
  "error": "resource_not_found",
  "message": "The requested resource was not found",
  "details": {
    "resource_id": 999
  }
}
```

Common error codes:
- `400 Bad Request`: Invalid input parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
