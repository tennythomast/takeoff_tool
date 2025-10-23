"use client";

import React from "react";
import { WorkspaceData } from "@/context/workspace-chat-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Users, Activity, Zap, AlertCircle, History, HistoryIcon } from "lucide-react";

interface WorkspaceChatHeaderProps {
  workspaceData: WorkspaceData | null;
  connectionStatus: "connecting" | "connected" | "disconnected" | "error";
  isSidebarVisible?: boolean;
  onToggleSidebar?: () => void;
}

export function WorkspaceChatHeader({ 
  workspaceData, 
  connectionStatus, 
  isSidebarVisible = false, 
  onToggleSidebar 
}: WorkspaceChatHeaderProps) {
  if (!workspaceData) {
    return (
      <div className="border-b border-gray-200 bg-white p-4 flex items-center justify-between">
        <div className="animate-pulse h-6 w-48 bg-gray-200 rounded"></div>
        <div className="animate-pulse h-6 w-24 bg-gray-200 rounded"></div>
      </div>
    );
  }

  return (
    <div className="border-b border-gray-200 bg-white p-4 flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <h2 className="text-lg font-semibold text-gray-900">{workspaceData.name}</h2>
        <Badge variant={workspaceData.status === "ACTIVE" ? "default" : "secondary"}>
          {workspaceData.status}
        </Badge>
      </div>

      <div className="flex items-center space-x-4">
        {/* Connection status indicator */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center">
                {connectionStatus === "connected" && (
                  <span className="flex items-center text-sm text-green-600">
                    <span className="h-2 w-2 rounded-full bg-green-600 mr-2"></span>
                    Connected
                  </span>
                )}
                {connectionStatus === "connecting" && (
                  <span className="flex items-center text-sm text-amber-500">
                    <span className="h-2 w-2 rounded-full bg-amber-500 mr-2 animate-pulse"></span>
                    Connecting
                  </span>
                )}
                {connectionStatus === "disconnected" && (
                  <span className="flex items-center text-sm text-gray-500">
                    <span className="h-2 w-2 rounded-full bg-gray-500 mr-2"></span>
                    Disconnected
                  </span>
                )}
                {connectionStatus === "error" && (
                  <span className="flex items-center text-sm text-red-600">
                    <AlertCircle className="h-4 w-4 mr-1" />
                    Connection Error
                  </span>
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>WebSocket connection status</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Workspace stats */}
        <div className="flex items-center space-x-3">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center text-sm text-gray-600">
                  <Users className="h-4 w-4 mr-1" />
                  <span>{workspaceData.collaboratorsCount}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{workspaceData.collaboratorsCount} collaborators</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center text-sm text-gray-600">
                  <Activity className="h-4 w-4 mr-1" />
                  <span>{workspaceData.totalExecutions}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{workspaceData.totalExecutions} total executions</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center text-sm text-gray-600">
                  <Zap className="h-4 w-4 mr-1" />
                  <span>{workspaceData.agentsCount}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{workspaceData.agentsCount} active agents</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        {/* Chat History Sidebar Toggle */}
        {onToggleSidebar && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onToggleSidebar}
                  className={`ml-2 ${isSidebarVisible ? 'bg-gray-100 text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}
                >
                  <History className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isSidebarVisible ? 'Hide' : 'Show'} chat history</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
}
