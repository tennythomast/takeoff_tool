import { Agent, AgentTool, AgentToolExecution } from "@/components/agents/types";

// Base API URL
const API_BASE_URL = '/api/agents';

// Agent Tool API
export const AgentToolAPI = {
  // Get all tools for an agent
  async getAgentTools(agentId: string): Promise<AgentTool[]> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/tools/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch agent tools: ${response.statusText}`);
    }
    return response.json();
  },

  // Create a new tool for an agent
  async createAgentTool(agentId: string, tool: Partial<AgentTool>): Promise<AgentTool> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/tools/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(tool),
    });
    if (!response.ok) {
      throw new Error(`Failed to create agent tool: ${response.statusText}`);
    }
    return response.json();
  },

  // Update an existing tool
  async updateAgentTool(agentId: string, toolId: string, tool: Partial<AgentTool>): Promise<AgentTool> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/tools/${toolId}/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(tool),
    });
    if (!response.ok) {
      throw new Error(`Failed to update agent tool: ${response.statusText}`);
    }
    return response.json();
  },

  // Delete a tool
  async deleteAgentTool(agentId: string, toolId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/tools/${toolId}/`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete agent tool: ${response.statusText}`);
    }
  }
};

// Agent Tool Execution API
export const AgentToolExecutionAPI = {
  // Get all tool executions for an agent execution
  async getToolExecutions(executionId: string): Promise<AgentToolExecution[]> {
    const response = await fetch(`${API_BASE_URL}/executions/${executionId}/tool-executions/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch tool executions: ${response.statusText}`);
    }
    return response.json();
  },

  // Get a specific tool execution
  async getToolExecution(executionId: string, toolExecutionId: string): Promise<AgentToolExecution> {
    const response = await fetch(`${API_BASE_URL}/executions/${executionId}/tool-executions/${toolExecutionId}/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch tool execution: ${response.statusText}`);
    }
    return response.json();
  }
};

// Agent Execution API
export const AgentExecutionAPI = {
  // Execute an agent with tools enabled
  async executeAgent(agentId: string, inputData: any, enableTools: boolean = true): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/execute/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input_data: inputData,
        enable_tools: enableTools
      }),
    });
    if (!response.ok) {
      throw new Error(`Failed to execute agent: ${response.statusText}`);
    }
    return response.json();
  },

  // Get execution details
  async getExecution(executionId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/executions/${executionId}/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch execution: ${response.statusText}`);
    }
    return response.json();
  }
};

// Export a default service object with all APIs
const AgentService = {
  tools: AgentToolAPI,
  executions: AgentExecutionAPI,
  toolExecutions: AgentToolExecutionAPI
};

export default AgentService;
