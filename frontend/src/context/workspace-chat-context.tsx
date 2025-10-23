"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { getStoredTokens } from "@/lib/auth/auth-service";

// Global connection manager to prevent multiple connections for the same workspace
const globalConnections = new Map<string, WebSocket>();

// Types
export interface WorkspaceData {
  id: string;
  name: string;
  createdAt: string;
  collaboratorsCount: number;
  status: "ACTIVE" | "INACTIVE";
  totalExecutions: number;
  workflowsCount: number;
  agentsCount: number;
  filesCount: number;
  toolsCount: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  status?: "sending" | "sent" | "streaming" | "error";
  isWelcomeMessage?: boolean;
  richContent?: RichContent[];
  metadata?: {
    model_used?: string;
    total_cost?: number;
    tokens_used?: number;
    provider?: string;
    execution_time?: number;
  };
}

export interface RichContent {
  type: "cost-analysis" | "agent-card" | "workflow-visualization" | "file-preview" | "tool-usage";
  data: any;
}

export interface WorkspaceMessageMetadata {
  workspaceId: string;
  entityType: "workspace_chat"; // Future: supports 'platform_chat'
  contextData: {
    currentAgents: string[];
    recentExecutions: boolean;
    costFocus: boolean;
  };
}

export interface WorkspaceChatContextType {
  // State
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  isLoading: boolean;
  workspaceData: WorkspaceData | null;
  connectionStatus: "connecting" | "connected" | "disconnected" | "error";
  
  // Actions
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  
  // Suggestions
  suggestions: string[];
}

// Create context
const WorkspaceChatContext = createContext<WorkspaceChatContextType | null>(null);

// Hook for using the context
export function useWorkspaceChat() {
  const context = useContext(WorkspaceChatContext);
  if (!context) {
    throw new Error("useWorkspaceChat must be used within a WorkspaceChatProvider");
  }
  return context;
}

// Provider props
interface WorkspaceChatProviderProps {
  children: React.ReactNode;
  workspaceId: string;
}

// Mock workspace data for initial development
const MOCK_WORKSPACE_DATA: WorkspaceData = {
  id: "ws-123",
  name: "Data Assets - Institutional",
  createdAt: "2025-05-15T10:30:00Z",
  collaboratorsCount: 2,
  status: "ACTIVE",
  totalExecutions: 334,
  workflowsCount: 4,
  agentsCount: 2,
  filesCount: 3,
  toolsCount: 4
};

// Mock suggestions based on workspace data
function generateSuggestions(workspaceData: WorkspaceData): string[] {
  return [
    `Analyze costs for my ${workspaceData.agentsCount} active agents`,
    `Why do I have ${workspaceData.totalExecutions} executions but only ${workspaceData.agentsCount} agents?`,
    `Optimize my ${workspaceData.workflowsCount} workflows for better cost efficiency`,
    `Show me performance breakdown by agent`
  ];
}

// Provider component
export function WorkspaceChatProvider({ children, workspaceId }: WorkspaceChatProviderProps) {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [workspaceData, setWorkspaceData] = useState<WorkspaceData | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected" | "error">("disconnected");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  // WebSocket ref
  const socketRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string>(uuidv4());
  const isConnectingRef = useRef<boolean>(false);
  const componentIdRef = useRef<string>(uuidv4());
  
  // Load workspace data
  useEffect(() => {
    // In a real implementation, fetch from API
    // For now, use mock data
    setWorkspaceData(MOCK_WORKSPACE_DATA);
    setSuggestions(generateSuggestions(MOCK_WORKSPACE_DATA));
    
    // Add welcome message
    const welcomeMessage: Message = {
      id: "welcome-message",
      role: "assistant",
      content: "Hi there! 👋 I'm here to help. What can I assist you with today?",
      timestamp: new Date().toISOString(),
      isWelcomeMessage: true
    };
    
    setMessages([welcomeMessage]);
  }, [workspaceId]);
  
  // Connect to WebSocket
  useEffect(() => {
    console.log("🔄 WebSocket useEffect triggered, workspaceId:", workspaceId, "componentId:", componentIdRef.current);
    if (!workspaceId) {
      console.log("🔄 No workspaceId, skipping WebSocket connection");
      return;
    }
    
    // Add a small delay to prevent rapid remounting issues
    const connectionTimer = setTimeout(() => {
      connectWebSocket();
    }, 100);
    
    const connectWebSocket = () => {
      try {
        // Check if there's already a global connection for this workspace
        const existingConnection = globalConnections.get(workspaceId);
        if (existingConnection && existingConnection.readyState === WebSocket.OPEN) {
          console.log("🔌 Using existing WebSocket connection for workspace:", workspaceId);
          socketRef.current = existingConnection;
          setConnectionStatus("connected");
          return;
        }
        
        // Prevent multiple simultaneous connection attempts
        if (isConnectingRef.current || (socketRef.current && socketRef.current.readyState === WebSocket.CONNECTING)) {
          console.log("🔌 Connection attempt already in progress, skipping...");
          return;
        }
        
        // Close existing connection if any
        if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) {
          console.log("🔌 Closing existing connection before creating new one");
          socketRef.current.close();
          socketRef.current = null;
        }
        
        // Remove any stale connections from global map
        if (existingConnection && existingConnection.readyState === WebSocket.CLOSED) {
          globalConnections.delete(workspaceId);
        }
        
        isConnectingRef.current = true;
        setConnectionStatus("connecting");
        
        // Get authentication token
        const tokens = getStoredTokens();
        if (!tokens?.access) {
          console.error("No authentication token available for WebSocket connection");
          setConnectionStatus("error");
          isConnectingRef.current = false;
          return;
        }
        
        // Use the correct WebSocket endpoint that matches backend configuration
        // Based on the backend routing: ws/chat/{session_id}/
        const baseWsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
        
        // Create a clean session ID without combining with workspace ID
        const sessionId = uuidv4();
        sessionIdRef.current = sessionId;
        
        // Construct the WebSocket URL with workspaceId as a query parameter
        const wsUrl = new URL(`/ws/chat/${sessionId}/`, baseWsUrl.replace(/^https?/, 'ws'));
        wsUrl.searchParams.append('token', tokens.access);
        wsUrl.searchParams.append('workspace_id', workspaceId);
        
        console.log("🔌 Attempting WebSocket connection to:", wsUrl.toString().replace(/token=[^&]+/, 'token=***'));
        console.log("🔌 Creating new WebSocket instance for workspace:", workspaceId);
        socketRef.current = new WebSocket(wsUrl.toString());
        
        // Add to global connection map
        globalConnections.set(workspaceId, socketRef.current);
        
        // Add immediate state logging
        console.log("🔌 WebSocket created, initial readyState:", socketRef.current.readyState);
        
        socketRef.current.onopen = () => {
          console.log("🔌 WebSocket connected");
          setConnectionStatus("connected");
          isConnectingRef.current = false;
        };
        
        socketRef.current.onclose = (event) => {
          console.log(`🔌 WebSocket closed: ${event.code} ${event.reason} for workspace:`, workspaceId);
          setConnectionStatus("disconnected");
          isConnectingRef.current = false;
          
          // Remove from global connection map
          globalConnections.delete(workspaceId);
          
          // Log additional details for debugging
          if (event.code === 1006) {
            console.warn("🔌 WebSocket closed abnormally - this usually indicates a connection issue");
          } else if (event.code === 1008) {
            console.error("🔌 WebSocket closed due to policy violation - check authentication");
          } else if (event.code === 4001) {
            console.error("🔌 WebSocket closed due to authentication error");
          }
          
          // Only attempt to reconnect if we have valid tokens and it's not an auth error
          if (event.code !== 1008 && event.code !== 4001) { // 1008 = policy violation, 4001 = auth error
            const tokens = getStoredTokens();
            if (tokens?.access) {
              console.log("🔄 Attempting to reconnect in 3 seconds...");
              setTimeout(connectWebSocket, 3000);
            } else {
              console.error("🔌 No valid tokens available for reconnection");
            }
          }
        };
        
        socketRef.current.onerror = (event) => {
          console.error("🔌 WebSocket error occurred");
          
          // Get more detailed error information
          const ws = event.target as WebSocket | null;
          const type = event.type || 'unknown';
          const readyState = ws?.readyState !== undefined ? ws.readyState : -1;
          const readyStateText = ws?.readyState !== undefined ? 
            ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState] || 'UNKNOWN' : 'unavailable';
          const url = ws?.url || 'unavailable';
          const timestamp = new Date().toISOString();
          
          // Log details as formatted string instead of object
          console.error(`🔌 Error Details:
            - Type: ${type}
            - ReadyState: ${readyState} (${readyStateText})
            - URL: ${url}
            - Timestamp: ${timestamp}`);
          
          // Additional context
          if (ws?.readyState === WebSocket.CONNECTING) {
            console.error("🔌 Error occurred while connecting - check if backend WebSocket server is running");
          } else if (ws?.readyState === WebSocket.CLOSED) {
            console.error("🔌 Error occurred on closed connection - connection was terminated");
          }
          
          setConnectionStatus("error");
          isConnectingRef.current = false;
        };
        
        socketRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log("📩 WebSocket message:", data);
            
            handleWebSocketMessage(data);
          } catch (error) {
            console.error("Error parsing WebSocket message:", error);
          }
        };
      } catch (error) {
        console.error("Error connecting to WebSocket:", error);
        setConnectionStatus("error");
        isConnectingRef.current = false;
      }
    };
    
    // Cleanup on unmount
    return () => {
      clearTimeout(connectionTimer);
      
      if (socketRef.current) {
        console.log("🔌 Cleaning up WebSocket connection on component unmount for workspace:", workspaceId);
        console.log("🔌 WebSocket readyState before cleanup:", socketRef.current.readyState);
        console.log("🔌 Component ID:", componentIdRef.current);
        
        // Only close if this component owns the connection
        const globalConnection = globalConnections.get(workspaceId);
        if (globalConnection === socketRef.current) {
          console.log("🔌 This component owns the global connection, closing it");
          socketRef.current.close();
          globalConnections.delete(workspaceId);
        } else {
          console.log("🔌 Another component owns the global connection, not closing");
        }
        
        socketRef.current = null;
      }
    };
  }, [workspaceId]);
  
  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((data: any) => {
    switch (data.type) {
      case "connection_established":
        console.log("Connection established with session ID:", data.session_id);
        break;
        
      case "stream_chunk":
        // Handle streaming message chunk
        setMessages(prev => {
          const existingMessageIndex = prev.findIndex(msg => msg.id === data.message_id);
          
          if (existingMessageIndex >= 0) {
            // Update existing message
            const updatedMessages = [...prev];
            updatedMessages[existingMessageIndex] = {
              ...updatedMessages[existingMessageIndex],
              content: updatedMessages[existingMessageIndex].content + data.content,
              status: "streaming"
            };
            return updatedMessages;
          } else {
            // Create new message
            return [...prev, {
              id: data.message_id,
              role: "assistant",
              content: data.content,
              timestamp: new Date().toISOString(),
              status: "streaming"
            }];
          }
        });
        break;
        
      case "complete":
      case "stream_complete":
        // Handle stream completion (backend sends 'complete', keeping 'stream_complete' for compatibility)
        console.log("🏁 Stream completed for message:", data.message_id);
        setMessages(prev => {
          const existingMessageIndex = prev.findIndex(msg => msg.id === data.message_id);
          
          // Extract metadata from completion message
          const metadata = {
            model_used: data.model_used,
            total_cost: data.total_cost,
            tokens_used: data.tokens_used,
            provider: data.metadata?.provider,
            execution_time: data.metadata?.execution_time
          };
          
          if (existingMessageIndex >= 0) {
            // Update existing message
            const updatedMessages = [...prev];
            updatedMessages[existingMessageIndex] = {
              ...updatedMessages[existingMessageIndex],
              status: "sent",
              richContent: data.rich_content || undefined,
              metadata: metadata
            };
            return updatedMessages;
          } else {
            // If no existing message found, create a new one with the complete response
            return [...prev, {
              id: data.message_id,
              role: "assistant",
              content: data.content || "Response received",
              timestamp: new Date().toISOString(),
              status: "sent",
              richContent: data.rich_content || undefined,
              metadata: metadata
            }];
          }
        });
        setIsLoading(false);
        break;
        
      case "workspace_update":
        // Handle workspace updates (executions, agent status, etc.)
        if (data.workspace_data) {
          setWorkspaceData(prev => ({
            ...prev,
            ...data.workspace_data
          }));
        }
        break;
        
      default:
        console.log("Unknown message type:", data.type);
    }
  }, []);
  
  // Send message
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;
    
    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
      status: "sending"
    };
    
    // Remove welcome message and add user message to state
    setMessages(prev => [...prev.filter(msg => !msg.isWelcomeMessage), userMessage]);
    setIsLoading(true);
    setInputValue("");
    
    try {
      // In a real implementation, send to WebSocket
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        const messagePayload = {
          type: "message",
          content,
          context: workspaceId || "workspace_chat",
          metadata: {
            workspaceId,
            entityType: "workspace_chat",
            contextData: {
              currentAgents: workspaceData?.agentsCount ? Array(workspaceData.agentsCount).fill("").map((_, i) => `agent-${i+1}`) : [],
              recentExecutions: true,
              costFocus: content.toLowerCase().includes("cost")
            }
          }
        };
        
        socketRef.current.send(JSON.stringify(messagePayload));
        
        // Update user message status
        setMessages(prev => 
          prev.map(msg => 
            msg.id === userMessage.id ? { ...msg, status: "sent" } : msg
          )
        );
      } else {
        // For development/demo, simulate response
        setTimeout(() => {
          const assistantMessage: Message = {
            id: uuidv4(),
            role: "assistant",
            content: `I'm simulating a response to: "${content}"`,
            timestamp: new Date().toISOString(),
            status: "sent"
          };
          
          setMessages(prev => [...prev, assistantMessage]);
          setIsLoading(false);
        }, 1000);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      
      // Update user message status to error
      setMessages(prev => 
        prev.map(msg => 
          msg.id === userMessage.id ? { ...msg, status: "error" } : msg
        )
      );
      
      setIsLoading(false);
    }
  }, [isLoading, workspaceId, workspaceData]);
  
  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);
  
  // Context value
  const contextValue: WorkspaceChatContextType = {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    workspaceData,
    connectionStatus,
    sendMessage,
    clearMessages,
    suggestions
  };
  
  return (
    <WorkspaceChatContext.Provider value={contextValue}>
      {children}
    </WorkspaceChatContext.Provider>
  );
}
