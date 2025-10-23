"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { 
  MessageCircle, 
  Plus
} from "lucide-react";

interface ChatSession {
  id: string;
  title: string;
  messageCount: number;
  isActive?: boolean;
}

interface ChatHistorySidebarProps {
  sessions: ChatSession[];
  activeSessionId?: string;
  onSessionSelect: (sessionId: string) => void;
  onNewChat: () => void;
}

export function ChatHistorySidebar({
  sessions,
  activeSessionId,
  onSessionSelect,
  onNewChat
}: ChatHistorySidebarProps) {
  // Mock data for demonstration
  const mockSessions: ChatSession[] = [
    {
      id: "1",
      title: "Workspace Performance Analysis",
      messageCount: 8,
      isActive: activeSessionId === "1"
    },
    {
      id: "2", 
      title: "Cost Optimization Discussion",
      messageCount: 12,
      isActive: activeSessionId === "2"
    },
    {
      id: "3",
      title: "Agent Configuration Help",
      messageCount: 5,
      isActive: activeSessionId === "3"
    },
    {
      id: "4",
      title: "Workflow Debugging",
      messageCount: 15,
      isActive: activeSessionId === "4"
    },
    {
      id: "5",
      title: "Quick Question",
      messageCount: 3,
      isActive: activeSessionId === "5"
    }
  ];

  const displaySessions = sessions.length > 0 ? sessions : mockSessions;

  return (
    <div className="w-80 h-full bg-white border-l border-slate-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Chat History</h2>
          <Button
            size="sm"
            onClick={onNewChat}
            className="bg-blue-500 hover:bg-blue-600 text-white"
          >
            <Plus className="w-4 h-4 mr-1" />
            New
          </Button>
        </div>
      </div>

      {/* Sessions List */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {displaySessions.map((session) => (
            <div
              key={session.id}
              className={cn(
                "cursor-pointer transition-all duration-200 p-3 rounded-lg border",
                session.isActive || activeSessionId === session.id
                  ? "border-blue-200 bg-blue-50/50"
                  : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
              )}
              onClick={() => onSessionSelect(session.id)}
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-sm text-slate-900 truncate flex-1 mr-2">
                  {session.title}
                </h3>
                <div className="flex items-center gap-1 text-xs text-slate-500 flex-shrink-0">
                  <MessageCircle className="w-3 h-3" />
                  <span>{session.messageCount}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
