import { API_BASE_URL } from '@/lib/config'
import { getAuthHeaders } from '@/lib/auth/auth-api'

// Base API URL for MCP endpoints
const MCP_API_URL = `${API_BASE_URL}/api/v1/mcp/`

/**
 * MCP Server Registry interface
 */
export interface MCPServerRegistry {
  id: string
  qualified_name: string
  display_name: string
  description: string
  category: string
  icon: string
  server_type: 'stdio' | 'http' | 'websocket'
  capabilities: string[]
  is_verified: boolean
  is_active: boolean
}

/**
 * MCP Server Connection interface
 */
export interface MCPServerConnection {
  id: string
  organization: string
  server: MCPServerRegistry
  connection_name: string
  description: string
  is_active: boolean
  is_connected: boolean
  health_status: 'healthy' | 'warning' | 'error' | 'unknown'
  created_at: string
  updated_at: string
}

/**
 * MCP Resource interface
 */
export interface MCPResource {
  id: string
  connection: string
  resource_uri: string
  resource_name: string
  resource_type: string
  description: string
  operations: string[]
  is_available: boolean
  schema?: Record<string, any>
  external_id?: string
}

/**
 * MCP Workspace Access interface
 */
export interface MCPWorkspaceAccess {
  id: string
  workspace: string
  connection: string
  connection_name?: string
  access_type: 'full' | 'read_only' | 'custom'
  resource_filters?: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string
}

/**
 * Fetch all MCP server connections for the current organization
 */
export async function fetchMCPConnections(): Promise<MCPServerConnection[]> {
  const headers = getAuthHeaders()
  const response = await fetch(`${MCP_API_URL}connections/`, {
    method: 'GET',
    headers
  })

  if (!response.ok) {
    try {
      const error = await response.json()
      throw new Error(error.detail || `Failed to fetch MCP connections: ${response.statusText}`)
    } catch (jsonError) {
      // If response is not valid JSON (e.g., HTML error page)
      console.error('Non-JSON error response:', response.status, response.statusText)
      throw new Error(`Failed to fetch MCP connections: ${response.status} ${response.statusText}`)
    }
  }

  return response.json()
}

/**
 * Fetch resources for a specific MCP connection
 */
export async function fetchMCPResources(connectionId: string): Promise<MCPResource[]> {
  const headers = getAuthHeaders()
  const response = await fetch(`${MCP_API_URL}resources/?connection=${connectionId}`, {
    method: 'GET',
    headers
  })

  if (!response.ok) {
    try {
      const error = await response.json()
      throw new Error(error.detail || `Failed to fetch MCP resources: ${response.statusText}`)
    } catch (jsonError) {
      // If response is not valid JSON (e.g., HTML error page)
      console.error('Non-JSON error response:', response.status, response.statusText)
      throw new Error(`Failed to fetch MCP resources: ${response.status} ${response.statusText}`)
    }
  }

  return response.json()
}

/**
 * Fetch available MCP server registries
 */
export async function fetchMCPServerRegistries(): Promise<MCPServerRegistry[]> {
  const headers = getAuthHeaders()
  const response = await fetch(`${MCP_API_URL}registry/`, {
    method: 'GET',
    headers
  })

  if (!response.ok) {
    try {
      const error = await response.json()
      throw new Error(error.detail || `Failed to fetch MCP server registries: ${response.statusText}`)
    } catch (jsonError) {
      // If response is not valid JSON (e.g., HTML error page)
      console.error('Non-JSON error response:', response.status, response.statusText)
      throw new Error(`Failed to fetch MCP server registries: ${response.status} ${response.statusText}`)
    }
  }

  return response.json()
}

/**
 * Fetch MCP connections accessible to a specific workspace
 */
export async function fetchWorkspaceMCPConnections(workspaceId: string): Promise<MCPWorkspaceAccess[]> {
  const headers = getAuthHeaders()
  const response = await fetch(`${MCP_API_URL}workspace-access/?workspace=${workspaceId}`, {
    method: 'GET',
    headers
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch workspace MCP connections: ${response.statusText}`)
  }

  const data = await response.json()
  
  // Handle both paginated responses (with results key) and direct arrays
  return data.results ? data.results : (Array.isArray(data) ? data : [])
}

/**
 * Fetch resources accessible to a specific workspace
 */
export async function fetchWorkspaceAccessibleResources(workspaceId: string): Promise<MCPResource[]> {
  const headers = getAuthHeaders()
  const response = await fetch(`${MCP_API_URL}resources/accessible/?workspace=${workspaceId}`, {
    method: 'GET',
    headers
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch workspace accessible resources: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Add a resource to a workspace access configuration
 */
export async function addResourceToWorkspaceAccess(
  accessId: string,
  resourceId: string
): Promise<any> {
  const headers = getAuthHeaders()
  const response = await fetch(`${MCP_API_URL}workspace-access/${accessId}/add-resource/`, {
    method: 'POST',
    headers: {
      ...headers,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ resource_id: resourceId })
  })

  if (!response.ok) {
    throw new Error(`Failed to add resource to workspace access: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Remove a resource from a workspace access configuration
 */
export async function removeResourceFromWorkspaceAccess(
  accessId: string,
  resourceId: string
): Promise<any> {
  const headers = getAuthHeaders()
  const response = await fetch(`${MCP_API_URL}workspace-access/${accessId}/remove-resource/`, {
    method: 'POST',
    headers: {
      ...headers,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ resource_id: resourceId })
  })

  if (!response.ok) {
    throw new Error(`Failed to remove resource from workspace access: ${response.statusText}`)
  }

  return response.json()
}
