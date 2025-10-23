"use client";

import React, { useState } from "react";
import { MessageContainer } from "./message-container";
import { ChatInput } from "./chat-input";
import { ChatHistorySidebar } from "./chat-history-sidebar";
import { useWorkspaceChat } from "@/context/workspace-chat-context";

export function WorkspaceChatLayout() {
  const {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    workspaceData,
    connectionStatus,
    sendMessage,
    suggestions
  } = useWorkspaceChat();

  const [activeSessionId, setActiveSessionId] = useState<string>("1");
  const [showSidebar, setShowSidebar] = useState(true);

  const handleSendMessage = (content: string) => {
    sendMessage(content);
  };

  const handleSessionSelect = (sessionId: string) => {
    setActiveSessionId(sessionId);
    // In a real implementation, load the selected session's messages
  };

  const handleNewChat = () => {
    // In a real implementation, create a new chat session
  };

  return (
    <div className="flex h-full w-full bg-gradient-to-br from-slate-50 to-white">
      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Minimal connection status and sidebar toggle */}
        <div className="flex-shrink-0 p-2 flex justify-between items-center">
          <div className="flex items-center gap-2">
            {connectionStatus === "connected" && (
              <div className="flex items-center text-xs text-green-600">
                <span className="h-2 w-2 rounded-full bg-green-600 mr-1"></span>
                Connected
              </div>
            )}
            {connectionStatus === "connecting" && (
              <div className="flex items-center text-xs text-amber-500">
                <span className="h-2 w-2 rounded-full bg-amber-500 mr-1 animate-pulse"></span>
                Connecting
              </div>
            )}
            {connectionStatus === "disconnected" && (
              <div className="flex items-center text-xs text-gray-500">
                <span className="h-2 w-2 rounded-full bg-gray-500 mr-1"></span>
                Disconnected
              </div>
            )}
            {connectionStatus === "error" && (
              <div className="flex items-center text-xs text-red-600">
                <span className="h-2 w-2 rounded-full bg-red-600 mr-1"></span>
                Error
              </div>
            )}
          </div>
          
          {/* Sidebar toggle */}
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className={`p-1 rounded hover:bg-gray-100 ${showSidebar ? 'text-blue-600' : 'text-gray-400'}`}
            title={showSidebar ? 'Hide chat history' : 'Show chat history'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </div>
        
        {/* Messages container with scrolling - stretched height */}
        <div className="flex-1 overflow-y-auto relative min-h-0">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-50/20 to-transparent pointer-events-none" />
          <MessageContainer 
            messages={messages}
            isLoading={isLoading}
            suggestions={[]}
          />
        </div>
        
        {/* Fixed bottom section with suggestions and input */}
        <div className="flex-shrink-0 bg-white/95 backdrop-blur-sm border-t border-slate-200 sticky bottom-0">
          {/* Suggestions row */}
          {messages.length === 0 && suggestions.length > 0 && (
            <div className="px-4 pt-3 pb-2">
              <div className="flex flex-wrap gap-2">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSendMessage(suggestion)}
                    className="px-3 py-2 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors border border-slate-200 hover:border-slate-300"
                  >
                    <span className="mr-2">✨</span>
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {/* Chat input */}
          <div className="p-2">
            <ChatInput
              value={inputValue}
              onChange={setInputValue}
              onSend={handleSendMessage}
              isLoading={isLoading}
              disabled={connectionStatus !== "connected"}
              placeholder="Ask about your workspace, agents, workflows, costs, or optimizations..."
            />
          </div>
        </div>
      </div>
      
      {/* Chat History Sidebar */}
      {showSidebar && (
        <ChatHistorySidebar
          sessions={[]}
          activeSessionId={activeSessionId}
          onSessionSelect={handleSessionSelect}
          onNewChat={handleNewChat}
        />
      )}
    </div>
  );
}
