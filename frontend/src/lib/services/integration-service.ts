import { API_BASE_URL } from '../constants';
import { getStoredTokens, authenticatedFetch } from "@/lib/auth/auth-service";

// MCP Server Registry types
export interface MCPServerRegistry {
  id: string;
  qualified_name: string;
  display_name: string;
  description: string;
  category: string;
  server_type: 'stdio' | 'http' | 'websocket';
  capabilities: string[];
  supported_operations: string[];
  supports_workspace_scoping: boolean;
  version: string;
  is_verified: boolean;
  is_active: boolean;
  documentation_url?: string;
  source_url?: string;
  rating: number;
  icon?: string;
}

// MCP Server Connection types
export interface MCPServerConnection {
  id: string;
  organization: string;
  user: string;
  server: string;
  server_name: string;
  server_type: string;
  connection_name: string;
  description: string;
  config: Record<string, any>;
  is_active: boolean;
  is_connected: boolean;
  health_status: 'healthy' | 'warning' | 'error' | 'unknown';
  last_health_check: string | null;
  total_requests: number;
  failed_requests: number;
  avg_response_time: number;
  created_at: string;
  updated_at: string;
}

export interface CreateConnectionRequest {
  organization: string;
  server: string;
  connection_name: string;
  description?: string;
  config: Record<string, any>;
  auth_data: Record<string, any>;
}

export interface UpdateConnectionRequest {
  connection_name?: string;
  description?: string;
  config?: Record<string, any>;
  auth_data?: Record<string, any>;
  is_active?: boolean;
}

// MCP Resource types
export interface MCPResource {
  id: string;
  connection: string;
  connection_name: string;
  server_name: string;
  resource_uri: string;
  resource_name: string;
  resource_type: string;
  description: string;
  schema: Record<string, any>;
  operations: string[];
  external_id: string;
  parent_resource?: string;
  parent_name?: string;
  discovered_at: string;
  last_verified: string;
  is_available: boolean;
}

// Workspace Access types
export interface MCPWorkspaceAccess {
  id: string;
  workspace: string;
  workspace_name: string;
  connection: string;
  connection_name: string;
  access_name: string;
  description: string;
  allowed_resources: string[];
  allowed_resource_count: number;
  resource_filters: Record<string, any>;
  permission_level: 'read' | 'write' | 'admin';
  is_active: boolean;
  auto_sync: boolean;
  last_used: string | null;
  usage_count: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  created_by_username: string;
}

class IntegrationService {
  private baseUrl = `${API_BASE_URL}`;
  
  // MCP Server Registry
  async getAvailableMCPServers(filters?: Record<string, any>): Promise<MCPServerRegistry[]> {
    // Convert filters to query parameters
    let queryParams = '';
    if (filters && Object.keys(filters).length > 0) {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
      queryParams = params.toString();
    }
    
    const url = `${this.baseUrl}/api/v1/mcp/registry/${queryParams ? `?${queryParams}` : ''}`;
    const tokens = getStoredTokens();
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch MCP servers: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Handle pagination
    if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
      return data.results;
    }
    
    return Array.isArray(data) ? data : [];
  }
  
  async getMCPServerDetails(id: string): Promise<MCPServerRegistry> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/registry/${id}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch MCP server details: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async getServerConfigSchema(id: string): Promise<Record<string, any>> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/registry/${id}/config_schema/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch config schema: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  // MCP Server Connections
  async getMCPConnections(): Promise<MCPServerConnection[]> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/connections/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch MCP connections: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Handle pagination
    if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
      return data.results;
    }
    
    return Array.isArray(data) ? data : [];
  }
  
  async getConnectionDetails(id: string): Promise<MCPServerConnection> {
    try {
      console.log(`Fetching connection details for ID: ${id}`);
      const tokens = getStoredTokens();
      console.log(`Using API URL: ${this.baseUrl}`);
      
      const url = `${this.baseUrl}/api/v1/mcp/connections/${id}/`;
      console.log(`Full request URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
        },
        credentials: 'include',
      });
      
      if (!response.ok) {
        console.error(`API error: ${response.status} ${response.statusText}`);
        throw new Error(`Failed to fetch connection details: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Connection details fetched successfully');
      return data;
    } catch (error) {
      console.error('Error in getConnectionDetails:', error);
      throw error;
    }
  }
  
  async createConnection(data: CreateConnectionRequest): Promise<MCPServerConnection> {
    const tokens = getStoredTokens();
    
    console.log('Creating connection with data:', JSON.stringify(data, null, 2));
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/connections/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      // Try to get detailed error information from response
      try {
        const errorText = await response.text();
        console.error('Connection creation error raw response:', errorText);
        
        let errorData;
        try {
          // Try to parse as JSON
          errorData = JSON.parse(errorText);
          console.error('Connection creation error details:', errorData);
        } catch (jsonError) {
          console.error('Response is not valid JSON:', jsonError);
          throw new Error(`Failed to create connection: ${response.status} ${response.statusText}`);
        }
        
        // Format error message with details if available
        if (typeof errorData === 'object') {
          const errorMessages = Object.entries(errorData)
            .map(([field, errors]) => {
              if (Array.isArray(errors)) {
                return `${field}: ${errors.join(', ')}`;
              } else if (typeof errors === 'object' && errors !== null) {
                return `${field}: ${JSON.stringify(errors)}`;
              } else {
                return `${field}: ${errors}`;
              }
            })
            .join('; ');
          
          throw new Error(`Failed to create connection: ${errorMessages || response.statusText}`);
        }
      } catch (parseError) {
        // If we can't parse the error response, throw with the status text
        console.error('Could not parse error response:', parseError);
        throw new Error(`Failed to create connection: ${response.status} ${response.statusText}`);
      }
    }
    
    return response.json();
  }
  
  async updateConnection(id: string, data: UpdateConnectionRequest): Promise<MCPServerConnection> {
    console.log(`Updating connection ${id} with data:`, JSON.stringify(data, null, 2));
    console.log(`Using API URL: ${this.baseUrl}`);
    
    const url = `${this.baseUrl}/api/v1/mcp/connections/${id}/`;
    console.log(`Full request URL: ${url}`);
    
    try {
      // Use authenticatedFetch with forceSignOut set to false to prevent aggressive sign-outs
      const response = await authenticatedFetch(url, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }, false); // false means don't force sign-out on auth errors
      
      if (!response.ok) {
        // Try to get detailed error information from response
        try {
          const errorText = await response.text();
          console.error('Connection update error raw response:', errorText);
          
          let errorData;
          try {
            // Try to parse as JSON
            errorData = JSON.parse(errorText);
            console.error('Connection update error details:', errorData);
          } catch (jsonError) {
            console.error('Response is not valid JSON:', jsonError);
            throw new Error(`Failed to update connection: ${response.status} ${response.statusText}`);
          }
          
          // Format error message with details if available
          if (typeof errorData === 'object') {
            const errorMessages = Object.entries(errorData)
              .map(([field, errors]) => {
                if (Array.isArray(errors)) {
                  return `${field}: ${errors.join(', ')}`;
                } else if (typeof errors === 'object' && errors !== null) {
                  return `${field}: ${JSON.stringify(errors)}`;
                } else {
                  return `${field}: ${errors}`;
                }
              })
              .join('; ');
            
            throw new Error(`Failed to update connection: ${errorMessages || response.statusText}`);
          }
        } catch (parseError) {
          // If we can't parse the error response, throw with the status text
          console.error('Could not parse error response:', parseError);
          throw new Error(`Failed to update connection: ${response.status} ${response.statusText}`);
        }
      }
      
      const updatedConnection = await response.json();
      console.log('Connection updated successfully:', updatedConnection);
      return updatedConnection;
    } catch (error) {
      console.error('Error in updateConnection:', error);
      throw error;
    }
  }
  
  async testConnection(id: string): Promise<Record<string, any>> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/connections/${id}/test_connection/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Connection test failed: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async deleteConnection(id: string): Promise<void> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/connections/${id}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete connection: ${response.statusText}`);
    }
  }
  
  // MCP Resources
  async getResources(connectionId?: string): Promise<MCPResource[]> {
    const tokens = getStoredTokens();
    const url = connectionId 
      ? `${this.baseUrl}/api/v1/mcp/resources/?connection=${connectionId}` 
      : `${this.baseUrl}/api/v1/mcp/resources/`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${tokens?.access}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch resources: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.results || [];
  }
  
  async discoverResources(connectionId: string): Promise<{ status: string; message: string; resource_count?: number }> {
    const tokens = getStoredTokens();
    const url = `${this.baseUrl}/api/v1/mcp/connections/${connectionId}/discover_resources/`;
    
    console.log(`Discovering resources for connection ID: ${connectionId}`);
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens?.access}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        console.error(`Resource discovery failed with status: ${response.status} ${response.statusText}`);
        
        // Try to get detailed error information
        try {
          const errorText = await response.text();
          console.error('Error response raw text:', errorText);
          
          let errorData;
          try {
            errorData = JSON.parse(errorText);
            console.error('Parsed error data:', errorData);
            throw new Error(errorData.message || `Failed to discover resources: ${response.statusText}`);
          } catch (jsonError) {
            console.error('Response is not valid JSON:', jsonError);
            throw new Error(`Failed to discover resources: ${response.statusText}`);
          }
        } catch (textError) {
          console.error('Failed to read error response:', textError);
          throw new Error(`Failed to discover resources: ${response.statusText}`);
        }
      }
      
      const data = await response.json();
      console.log('Resource discovery successful:', data);
      return data;
    } catch (error) {
      console.error('Error in discoverResources:', error);
      throw error;
    }
  }
  
  // Workspace Access Management
  
  async getWorkspaceAccesses(connectionId: string): Promise<MCPWorkspaceAccess[]> {
    const tokens = getStoredTokens();
    
    const url = `${this.baseUrl}/api/v1/mcp/workspace-access/?connection=${connectionId}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch workspace accesses: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Handle pagination
    if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
      return data.results;
    }
    
    return Array.isArray(data) ? data : [];
  }
  
  async createWorkspaceAccess(workspaceAccess: {
    workspace: string;
    connection: string;
    access_name: string;
    description?: string;
    permission_level: 'read' | 'write' | 'admin';
    is_active: boolean;
    auto_sync: boolean;
    allowed_resources?: string[];
    resource_filters?: Record<string, any>;
  }): Promise<MCPWorkspaceAccess> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/workspace-access/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
      body: JSON.stringify(workspaceAccess),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || 
        JSON.stringify(errorData) || 
        `Failed to create workspace access: ${response.statusText}`
      );
    }
    
    return await response.json();
  }
  
  async updateWorkspaceAccess(id: string, data: Partial<MCPWorkspaceAccess>): Promise<MCPWorkspaceAccess> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/workspace-access/${id}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update workspace access: ${response.statusText}`);
    }
    
    return await response.json();
  }
  
  async deleteWorkspaceAccess(id: string): Promise<void> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/workspace-access/${id}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete workspace access: ${response.statusText}`);
    }
  }
  
  async getWorkspaceAccessResources(accessId: string): Promise<MCPResource[]> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/workspace-access/${accessId}/resources/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch workspace access resources: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    return Array.isArray(data) ? data : [];
  }
  
  async updateWorkspaceResources(accessId: string, resourceIds: string[]): Promise<{
    status: string;
    message: string;
    resources: MCPResource[];
  }> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/workspace-access/${accessId}/update_resources/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
      body: JSON.stringify({ resource_ids: resourceIds }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update workspace resources: ${response.statusText}`);
    }
    
    return await response.json();
  }
  
  // Workspace Access
  async getWorkspaceAccess(workspaceId: string): Promise<MCPWorkspaceAccess[]> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/mcp/workspace-access/?workspace=${workspaceId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch workspace access: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Handle pagination
    if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
      return data.results;
    }
    
    return Array.isArray(data) ? data : [];
  }
  
  async debugConnectionAuth(id: string): Promise<Record<string, any>> {
    try {
      console.log(`Debugging auth for connection ID: ${id}`);
      const tokens = getStoredTokens();
      console.log(`Using API URL: ${this.baseUrl}`);
      
      const url = `${this.baseUrl}/api/v1/mcp/connections/${id}/debug_auth/`;
      console.log(`Full request URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
        },
        credentials: 'include',
      });
      
      if (!response.ok) {
        console.error(`Debug API error: ${response.status} ${response.statusText}`);
        throw new Error(`Failed to debug connection auth: ${response.statusText}`);
      }
      
      const debugData = await response.json();
      console.log('Auth debug data:', debugData);
      return debugData;
    } catch (error) {
      console.error('Error in debugConnectionAuth:', error);
      throw error;
    }
  }
}



// Export as singleton
export const integrationService = new IntegrationService();

