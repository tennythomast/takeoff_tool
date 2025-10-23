import { API_BASE_URL } from '@/lib/config'
import { getAuthHeaders } from '@/lib/auth/auth-api'

// Base API URL for agent endpoints
const API_URL = `${API_BASE_URL}/api/v1/agents/`

/**
 * Agent interface defining the structure of an agent
 */
export interface Agent {
  id?: string
  name: string
  description: string
  icon: string
  category: string
  capabilities: string[]
  configuration: AgentConfiguration & {
    generationMethod?: string;
    generationQuality?: string;
    canEnhance?: boolean;
    generationMetadata?: any;
  }
  createdAt?: string
  createdBy?: string
  isPublished?: boolean
  version?: string
  model?: string
}

/**
 * Agent configuration interface
 */
export interface AgentConfiguration {
  tools: AgentTool[]
  memory: AgentMemorySettings
  responseStyle: AgentResponseStyle
  customInstructions?: string
  knowledgeBases?: string[]
  webBrowsingEnabled?: boolean
  codeExecutionEnabled?: boolean
  mcpConnections?: string[] // IDs of MCP connections
}

/**
 * Agent tool interface
 */
export interface AgentTool {
  id: string
  name: string
  description: string
  enabled: boolean
  config?: Record<string, any>
}

/**
 * Agent memory settings
 */
export interface AgentMemorySettings {
  enabled: boolean
  maxTokens: number
  relevanceThreshold: number
}

/**
 * Agent response style configuration
 */
export interface AgentResponseStyle {
  tone: 'professional' | 'friendly' | 'technical' | 'simple'
  format: 'concise' | 'detailed'
  creativity: number // 0-100
}

/**
 * Available agent categories
 */
export const agentCategories = [
  'PRODUCTIVITY',
  'ANALYSIS',
  'COMPLIANCE',
  'RESEARCH',
  'CUSTOMER_SERVICE',
  'DEVELOPMENT',
  'GENERAL'
]

/**
 * Available agent capabilities
 */
export const agentCapabilities = [
  'Text Generation',
  'Code Generation',
  'Data Analysis',
  'Image Recognition',
  'Document Processing',
  'Web Browsing',
  'API Integration',
  'Knowledge Base Access'
]

/**
 * Available agent tools
 */
export const availableAgentTools: AgentTool[] = [
  {
    id: 'web-search',
    name: 'Web Search',
    description: 'Search the web for information',
    enabled: false
  },
  {
    id: 'code-interpreter',
    name: 'Code Interpreter',
    description: 'Execute and analyze code',
    enabled: false
  },
  {
    id: 'document-analysis',
    name: 'Document Analysis',
    description: 'Extract and analyze information from documents',
    enabled: false
  },
  {
    id: 'data-visualization',
    name: 'Data Visualization',
    description: 'Create charts and visualizations from data',
    enabled: false
  },
  {
    id: 'api-connector',
    name: 'API Connector',
    description: 'Connect to external APIs',
    enabled: false,
    config: {
      endpoints: []
    }
  }
]

import { refreshToken } from '@/lib/auth/token-refresh'

/**
 * Create a new agent
 */
export async function createAgent(agentData: any): Promise<Agent | null> {
  try {
    console.log('Creating agent with data:', JSON.stringify(agentData, null, 2))
    
    // First attempt
    let response = await fetch(`${API_URL}`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(agentData)
    })

    // If we get a 401 Unauthorized, try to refresh the token and retry
    if (response.status === 401) {
      console.log('Authentication failed, attempting to refresh token...')
      const refreshed = await refreshToken()
      
      if (refreshed) {
        console.log('Token refreshed, retrying request...')
        // Retry the request with new token
        response = await fetch(`${API_URL}`, {
          method: 'POST',
          headers: {
            ...getAuthHeaders(), // This will now use the refreshed token
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(agentData)
        })
      } else {
        console.error('Token refresh failed')
        throw new Error('Authentication failed and token refresh was unsuccessful')
      }
    }

    if (!response.ok) {
      const errorText = await response.text()
      let errorDetail = 'Unknown error'
      
      try {
        const errorData = JSON.parse(errorText)
        errorDetail = JSON.stringify(errorData, null, 2)
        console.error('API error response:', errorDetail)
        
        // Throw a detailed error that includes the response data
        throw new Error(`API error ${response.status}: ${errorDetail}`)
      } catch (e) {
        if (e instanceof SyntaxError) {
          // This is a JSON parse error, the response wasn't JSON
          console.error('API error response (not JSON):', errorText)
          errorDetail = errorText
          throw new Error(`API error ${response.status}: ${errorDetail}`)
        } else {
          // This is the error we threw above with the parsed JSON
          throw e
        }
      }
    }

    const data = await response.json()
    console.log('Agent created successfully:', data)
    return data
  } catch (error) {
    console.error('Error creating agent:', error)
    // Re-throw the error so it can be handled by the component
    throw error
  }
}

/**
 * Get agent by ID
 */
export async function getAgentById(id: string): Promise<Agent | null> {
  try {
    const response = await fetch(`${API_URL}/${id}`, {
      method: 'GET',
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      return null
    }

    return await response.json()
  } catch (error) {
    console.error(`Error fetching agent:`, error)
    return null
  }
}

/**
 * Update an existing agent
 */
export async function updateAgent(id: string, agentData: Partial<Agent>): Promise<Agent | null> {
  try {
    const response = await fetch(`${API_URL}/${id}`, {
      method: 'PATCH',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(agentData)
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new Error(errorData?.detail || `API error: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error(`Error updating agent ${id}:`, error)
    return null
  }
}

/**
 * Fetch all agents
 */
export async function fetchAgents(filters: {
  category?: string[]
  search?: string
  page?: number
  limit?: number
}): Promise<{ agents: Agent[]; total: number }> {
  try {
    // Construct query parameters
    const params = new URLSearchParams()
    
    if (filters.category && filters.category.length > 0) {
      filters.category.forEach(cat => {
        params.append('category', cat)
      })
    }
    
    if (filters.search) {
      params.append('search', filters.search)
    }
    
    if (filters.page) {
      params.append('page', filters.page.toString())
    }
    
    if (filters.limit) {
      params.append('limit', filters.limit.toString())
    }
    
    const queryString = params.toString()
    const url = queryString ? `${API_URL}?${queryString}` : API_URL
    
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: getAuthHeaders()
      })
      
      if (!response.ok) {
        console.warn(`API returned status: ${response.status}. Using empty results.`)
        return { agents: [], total: 0 }
      }
      
      const data = await response.json()
      
      return {
        agents: data.results || [],
        total: data.count || 0
      }
    } catch (fetchError) {
      console.error('Network error fetching agents:', fetchError)
      return { agents: [], total: 0 }
    }
  } catch (error) {
    console.error('Error in fetchAgents:', error)
    return { agents: [], total: 0 }
  }
}

/**
 * Delete an agent
 */
export async function deleteAgent(id: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    })

    return response.ok
  } catch (error) {
    console.error(`Error deleting agent ${id}:`, error)
    return false
  }
}

/**
 * Publish an agent to the marketplace
 */
export async function publishAgent(id: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/${id}/publish`, {
      method: 'POST',
      headers: getAuthHeaders()
    })

    return response.ok
  } catch (error) {
    console.error(`Error publishing agent ${id}:`, error)
    return false
  }
}

/**
 * Get default agent configuration
 */
export function getDefaultAgentConfiguration(): AgentConfiguration {
  return {
    tools: JSON.parse(JSON.stringify(availableAgentTools)),
    memory: {
      enabled: true,
      maxTokens: 2000,
      relevanceThreshold: 0.7
    },
    responseStyle: {
      tone: 'professional',
      format: 'concise',
      creativity: 50
    },
    customInstructions: '',
    knowledgeBases: []
  }
}

/**
 * Interface for agent generation request
 */
export interface AgentGenerationRequest {
  name?: string;
  primaryRole: string;
  problemStatement: string;
  targetUsers: string[];
  communicationStyle: string;
  outputFormat: string;
  qualityPreference: number;
  capabilities: string[];
}

/**
 * Interface for agent generation response
 */
export interface AgentGenerationResponse {
  instructions: string;
  generation_method: 'primary_llm' | 'alternative_llm' | 'smart_template' | 'basic_fallback' | 'emergency_fallback';
  quality_score: 'high' | 'medium-high' | 'medium' | 'basic' | 'minimal';
  can_enhance: boolean;
  suggestedConfiguration: {
    tools: string[];
    memory: Partial<AgentMemorySettings>;
    responseStyle: Partial<AgentResponseStyle>;
  };
  metadata?: {
    is_fallback?: boolean;
    is_emergency_fallback?: boolean;
    note?: string;
    enhancement_suggestion?: string;
    provider?: string;
    model_used?: string;
    character_count?: number;
    template_used?: string;
  };
}

/**
 * Generate agent instructions and configuration using AI
 */
export async function generateAgentInstructions(request: AgentGenerationRequest): Promise<AgentGenerationResponse> {
  try {
    // Import the agent instruction service
    const { agentInstructionService, ModelRoutingRule } = await import('@/lib/services/agent-instruction-service');
    
    // Determine routing rule based on quality preference
    let routingRule = ModelRoutingRule.BALANCED;
    if (request.qualityPreference === 3) {
      routingRule = ModelRoutingRule.QUALITY;
    } else if (request.qualityPreference === 1) {
      routingRule = ModelRoutingRule.SPEED;
    }
    
    // Use the enhanced service to generate instructions with routing rule
    console.log('Using enhanced agent instruction service with routing rule:', routingRule);
    return await agentInstructionService.generateInstructions({
      ...request,
      routingRule,
      additionalContext: `This agent is being created through the API. The user wants an agent that specializes in ${request.primaryRole} and can help with ${request.problemStatement}.`
    });
  } catch (error) {
    console.error('Error in generateAgentInstructions:', error);
    
    // Check if error is related to the service not being available
    if (error instanceof Error && 
        (error.message.includes('404') || 
         error.message.includes('not found') || 
         error.message.includes('JSON'))) {
      console.warn('Service endpoint not available or returned invalid response, using local generation');
      
      // Import the service again to use local generation
      try {
        const { agentInstructionService } = await import('@/lib/services/agent-instruction-service');
        return agentInstructionService.generateLocalInstructions(request);
      } catch (localGenError) {
        console.error('Error in local generation fallback:', localGenError);
        // Continue to API fallback
      }
    }
    
    // Fall back to the original API call if the service fails
    console.warn('Falling back to direct API call');
    
    const response = await fetch(`${API_URL}generate-instructions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...await getAuthHeaders(),
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('Error generating agent instructions:', errorData);
      throw new Error(errorData.message || 'Failed to generate agent instructions');
    }

    return await response.json();
  }
}
