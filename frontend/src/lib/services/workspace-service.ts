import { API_BASE_URL } from '../constants';
import { getStoredTokens } from "@/lib/auth/auth-service";
import { Agent } from '@/lib/api/agent-service';

// Activity type for recent activities
export interface WorkspaceActivity {
  type: 'create' | 'update' | 'analyze';
  description: string;
  time: string;
}

// Workspace types
export interface Workspace {
  id: string;
  name: string;
  description: string;
  status: 'ACTIVE' | 'ARCHIVED' | 'COMPLETED';
  organization: string;
  owner: string;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  type?: 'ANALYSIS' | 'CONTENT' | 'SUPPORT';
  metadata: {
    collaboratorCount?: number;
    maxCollaborators?: number;
    savingsPercentage?: number;
    healthScore?: number;
    fileCount?: number;
    toolCount?: number;
    chatCount?: number;
    recentActivities?: WorkspaceActivity[];
    [key: string]: any;
  };
}

export interface WorkspaceCollaborator {
  id: string;
  workspace: string;
  user: string;
  user_name?: string;
  user_email?: string;
  role: 'ADMIN' | 'EDITOR' | 'VIEWER';
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

export interface CreateWorkspaceRequest {
  name: string;
  description?: string;
}

// Session types (reused from project service)
export interface Session {
  id: string;
  title: string;
  description: string;
  workspace: string;
  creator: string;
  model_type: 'TEXT' | 'CODE' | 'IMAGE' | 'VOICE' | 'VIDEO';
  status: 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'FAILED';
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  cost: number;
  metadata: Record<string, any>;
}

export interface CreateSessionRequest {
  title: string;
  description?: string;
  workspace: string;
  model_type: 'TEXT' | 'CODE' | 'IMAGE' | 'VOICE' | 'VIDEO';
  initial_prompt?: string;
}

// Define the ChatMessage interface
export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  content_type?: string;
  timestamp: string;
  model_used?: string;
  execution_metadata?: Record<string, any>;
}

export interface SessionMessagesResponse {
  session_id: string;
  context_session_id: string;
  messages: ChatMessage[];
}

class WorkspaceService {
  private baseUrl = `${API_BASE_URL}`;
  
  // Workspaces
  async getWorkspaces(filters?: Record<string, any>): Promise<Workspace[]> {
    // Convert filters to proper query parameters
    let queryParams = '';
    if (filters && Object.keys(filters).length > 0) {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          // Make sure status is uppercase as the backend expects
          if (key === 'status') {
            const upperCaseValue = String(value).toUpperCase();
            params.append(key, upperCaseValue);
          } else {
            params.append(key, String(value));
          }
        }
      });
      queryParams = params.toString();
    }
    
    const url = `${this.baseUrl}/api/v1/workspaces/${queryParams ? `?${queryParams}` : ''}`;
    
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
      console.error('API request failed:', response.status, response.statusText);
      throw new Error(`Failed to fetch workspaces: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Check if the response has a results property (common in Django REST Framework)
    if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
      return data.results;
    }
    
    // Check if the response has a workspaces property
    if (data && typeof data === 'object' && 'workspaces' in data && Array.isArray(data.workspaces)) {
      return data.workspaces;
    }
    
    // If the response is already an array
    if (Array.isArray(data)) {
      return data;
    }
    
    console.error('Unexpected API response format:', data);
    return [];
  }
  
  async getWorkspace(id: string): Promise<Workspace> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/workspaces/${id}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch workspace: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async createWorkspace(data: CreateWorkspaceRequest): Promise<Workspace> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/workspaces/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create workspace: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async updateWorkspace(id: string, data: Partial<Workspace>): Promise<Workspace> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/workspaces/${id}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update workspace: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async archiveWorkspace(id: string): Promise<Workspace> {
    return this.updateWorkspace(id, { status: 'ARCHIVED' });
  }
  
  async completeWorkspace(id: string): Promise<Workspace> {
    return this.updateWorkspace(id, { status: 'COMPLETED' });
  }
  
  // Collaborators
  async getCollaborators(workspaceId: string): Promise<WorkspaceCollaborator[]> {
    const url = `${this.baseUrl}/api/v1/workspaces/${workspaceId}/collaborators/`;
    
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
      throw new Error(`Failed to fetch collaborators: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async addCollaborator(workspaceId: string, userId: string, role: 'ADMIN' | 'EDITOR' | 'VIEWER'): Promise<WorkspaceCollaborator> {
    const url = `${this.baseUrl}/api/v1/workspaces/${workspaceId}/collaborators/`;
    
    const tokens = getStoredTokens();
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
      body: JSON.stringify({ user: userId, role }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to add collaborator: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async updateCollaborator(workspaceId: string, userId: string, role: 'ADMIN' | 'EDITOR' | 'VIEWER'): Promise<WorkspaceCollaborator> {
    const response = await fetch(`${this.baseUrl}/api/v1/workspaces/${workspaceId}/collaborators/${userId}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ role }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update collaborator: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async removeCollaborator(workspaceId: string, userId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/workspaces/${workspaceId}/collaborators/${userId}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to remove collaborator: ${response.statusText}`);
    }
  }
  
  // Sessions
  async getSessions(workspaceId?: string, filters?: Record<string, string | number>): Promise<Session[]> {
    // Check if workspaceId is provided
    if (!workspaceId) {
      console.error('Workspace ID is required to fetch sessions');
      return [];
    }
    
    const queryParams = new URLSearchParams();
    
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        queryParams.append(key, String(value));
      });
    }
    
    // Based on the backend code structure:
    // - The API base URL is now just ${API_BASE_URL} (http://localhost:8000)
    // - The API endpoints are under /api/v1/ as seen in dataelan/urls.py
    // - The prompt app's URLs are included in api_v1_patterns
    // - In prompt/urls.py, we have a nested router structure for prompt sessions under workspaces
    const url = `${this.baseUrl}/api/v1/workspaces/${workspaceId}/prompt-sessions/`;
    
    const tokens = getStoredTokens();
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    console.log('Fetch sessions request:', {
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? 'Bearer [TOKEN]' : 'No token', // Don't log the actual token
      },
      method: 'GET',
    });
    
    console.log('Fetch sessions response:', {
      url,
      status: response.status,
      statusText: response.statusText,
    });
    
    if (!response.ok) {
      // Try to get more details about the error
      try {
        const errorText = await response.text(); // Get raw response text first
        console.error('Error response text:', errorText);
        
        try {
          const errorData = JSON.parse(errorText);
          console.error('Error details:', errorData);
          throw new Error(`Failed to fetch sessions: ${response.statusText} - ${JSON.stringify(errorData)}`);
        } catch (jsonError) {
          // If we can't parse as JSON, use the raw text
          throw new Error(`Failed to fetch sessions: ${response.statusText} - ${errorText}`);
        }
      } catch (parseError) {
        // If we can't get the response text at all
        console.error('Error parsing response:', parseError);
        throw new Error(`Failed to fetch sessions: ${response.statusText} (Status: ${response.status})`);
      }
    }
    
    // Parse the response and ensure we return an array
    const data = await response.json();
    console.log('Sessions API response data:', data);
    
    // Check if the response is an object with a 'results' property (common DRF pagination format)
    if (data && typeof data === 'object') {
      if (Array.isArray(data)) {
        return data; // Already an array
      } else if (data.results && Array.isArray(data.results)) {
        return data.results; // DRF paginated response
      } else {
        console.warn('Unexpected API response format for sessions, converting to array:', data);
        return [data]; // Convert single object to array with one item
      }
    }
    
    console.warn('Invalid API response for sessions, returning empty array');
    return []; // Return empty array as fallback
  }
  
  async getSession(id: string): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/prompt-sessions/${id}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch session: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async createSession(data: CreateSessionRequest): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/prompt-sessions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async updateSession(id: string, data: Partial<Session>): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/prompt-sessions/${id}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update session: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async reassignSession(sessionId: string, workspaceId: string): Promise<Session> {
    return this.updateSession(sessionId, { workspace: workspaceId });
  }
  
  // Get messages for a specific session
  async getSessionMessages(workspaceId: string, sessionId: string): Promise<SessionMessagesResponse> {
    const tokens = getStoredTokens();
    
    const url = `${this.baseUrl}/api/v1/workspaces/${workspaceId}/prompt-sessions/${sessionId}/messages/`;
    
    console.log('Fetching session messages from:', url);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.error('Error fetching session messages:', response.status, response.statusText);
      throw new Error(`Failed to fetch session messages: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data;
  }
  
  // Agents
  async getWorkspaceAgents(workspaceId: string): Promise<Agent[]> {
    const tokens = getStoredTokens();
    
    // Use the workspace ID to filter agents that belong to this workspace
    const response = await fetch(`${this.baseUrl}/api/v1/agents/?workspace=${workspaceId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.error(`Failed to fetch workspace agents: ${response.statusText}`);
      return [];
    }
    
    const data = await response.json();
    
    // Handle both paginated and non-paginated responses
    if (data && typeof data === 'object') {
      if (Array.isArray(data)) {
        return data;
      } else if (data.results && Array.isArray(data.results)) {
        return data.results;
      }
    }
    
    return [];
  }

  // Workflows
  async getWorkflows(workspaceId: string): Promise<any[]> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/workflows/?workspace=${workspaceId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.error(`Failed to fetch workflows: ${response.statusText}`);
      return [];
    }
    
    const data = await response.json();
    
    // Handle both paginated and non-paginated responses
    if (data && typeof data === 'object') {
      if (Array.isArray(data)) {
        return data;
      } else if (data.results && Array.isArray(data.results)) {
        return data.results;
      }
    }
    
    return [];
  }

  async runWorkflow(workflowId: string): Promise<any> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/workflows/${workflowId}/run/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to run workflow: ${response.statusText}`);
    }
    
    return response.json();
  }

  async deleteWorkflow(workflowId: string): Promise<void> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/workflows/${workflowId}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete workflow: ${response.statusText}`);
    }
  }

  async duplicateWorkflow(workflowId: string): Promise<any> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/workflows/${workflowId}/duplicate/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to duplicate workflow: ${response.statusText}`);
    }
    
    return response.json();
  }

  // Files
  async getFiles(workspaceId: string): Promise<any[]> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/files/?workspace=${workspaceId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.error(`Failed to fetch files: ${response.statusText}`);
      return [];
    }
    
    const data = await response.json();
    
    // Handle both paginated and non-paginated responses
    if (data && typeof data === 'object') {
      if (Array.isArray(data)) {
        return data;
      } else if (data.results && Array.isArray(data.results)) {
        return data.results;
      }
    }
    
    return [];
  }
}

// Export as singleton
export const workspaceService = new WorkspaceService();
