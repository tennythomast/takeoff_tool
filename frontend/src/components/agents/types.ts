"use client"

// Define the tool types
export type ToolType = 'WEBHOOK' | 'API' | 'FUNCTION';
export type WebhookMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
export type WebhookAuthType = 'NONE' | 'BASIC' | 'BEARER' | 'API_KEY';

// Define the tool interface
export interface AgentTool {
  id: string;
  name: string;
  description: string;
  tool_type: ToolType;
  config?: Record<string, any>;
  is_required: boolean;
  
  // Webhook fields
  webhook_url?: string;
  webhook_method?: WebhookMethod;
  webhook_headers?: Record<string, string>;
  webhook_auth_type?: WebhookAuthType;
  webhook_auth_config?: Record<string, string>;
  
  // Schema validation fields
  input_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
  
  // Smart recommendation fields
  match_percentage?: number;
  performance_impact?: number;
  recommendation_reason?: string;
}

// Define the tool execution interface
export interface AgentToolExecution {
  id: string;
  tool_name: string;
  tool_type: string;
  status: string;
  status_display: string;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  error_message?: string;
  execution_time: number;
  created_at: string;
}

// Define the types for our agent components
export interface Agent {
  id: string;
  name: string;
  description: string;
  category: 'PRODUCTIVITY' | 'ANALYSIS' | 'COMPLIANCE' | 'RESEARCH';
  status: 'ACTIVE' | 'DRAFT' | 'PAUSED' | 'ARCHIVED';
  icon: string; // emoji or icon identifier
  executionCount: number;
  avgResponseTime: string; // e.g., "0.8s"
  successRate: number; // percentage
  lastUsed: string; // relative time like "2 hours ago"
  tools?: AgentTool[];
}

export type TabType = 'overview' | 'configuration' | 'analytics' | 'integrations' | 'versions';

export interface AgentDetailState {
  selectedAgent: Agent | null;
  isDetailOpen: boolean;
  activeTab: TabType;
}
