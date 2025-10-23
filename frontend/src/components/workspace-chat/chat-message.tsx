"use client";

import React from "react";
import { Message, RichContent } from "@/context/workspace-chat-context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { User, Bot, Sparkles, Clock, CheckCircle2, AlertCircle, Zap, DollarSign } from "lucide-react";

interface ChatMessageProps {
  message: Message;
  isSequential: boolean;
  metadata?: {
    model_used?: string;
    total_cost?: number;
    tokens_used?: number;
    provider?: string;
  };
}

export function ChatMessage({ message, isSequential, metadata }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const isStreaming = message.status === "streaming";
  const isError = message.status === "error";
  const isSent = message.status === "sent";
  
  // Format timestamp
  const formattedTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });
  
  // System messages are centered and styled differently
  if (isSystem) {
    return (
      <div className="flex justify-center my-3">
        <Badge variant="secondary" className="bg-slate-100 text-slate-600 border-slate-200 text-xs px-3 py-1">
          <Sparkles className="w-3 h-3 mr-1" />
          {message.content}
        </Badge>
      </div>
    );
  }
  
  return (
    <div
      className={cn(
        "group py-4 px-4 hover:bg-slate-50/50 transition-colors duration-200",
        isSequential && "py-1"
      )}
    >
      <div className="max-w-4xl mx-auto">
        <div className="flex gap-4">
          {/* Avatar - only show if not sequential */}
          {!isSequential && (
            <div className="flex-shrink-0">
              <Avatar className={cn(
                "h-7 w-7",
                isUser 
                  ? "bg-blue-500" 
                  : "bg-slate-700"
              )}>
                <AvatarFallback className="bg-transparent text-white text-xs">
                  {isUser ? (
                    <User className="h-3 w-3" />
                  ) : (
                    <Bot className="h-3 w-3" />
                  )}
                </AvatarFallback>
              </Avatar>
            </div>
          )}
          
          {/* Message content */}
          <div className="flex-1 min-w-0">
            {/* Header with name and status */}
            {!isSequential && (
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-slate-900">
                  {isUser ? "You" : "Assistant"}
                </span>
                {isStreaming && !isUser && (
                  <div className="flex items-center gap-1 text-xs text-slate-500">
                    <div className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
                    <span>Thinking...</span>
                  </div>
                )}
                {isSent && !isUser && (
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                )}
                {isError && (
                  <AlertCircle className="w-3 h-3 text-red-500" />
                )}
              </div>
            )}
            
            {/* Text content */}
            <div className={cn(
              "prose prose-sm max-w-none",
              "text-slate-800 leading-relaxed",
              isSequential && "ml-11"
            )}>
              <div className="whitespace-pre-wrap">{message.content}</div>
            </div>
            
            {/* Rich content if available */}
            {message.richContent && message.richContent.length > 0 && (
              <div className={cn("mt-3 space-y-2", isSequential && "ml-11")}>
                {message.richContent.map((item, index) => (
                  <div key={index} className="bg-slate-50 border border-slate-200 rounded-md p-3">
                    <Badge variant="outline" className="text-xs mb-2">
                      {item.type}
                    </Badge>
                    <pre className="text-xs text-slate-600 overflow-auto bg-white p-2 rounded border">
                      {JSON.stringify(item.data, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
            
            {/* Model info and metadata - only for AI responses */}
            {!isUser && !isSequential && isSent && (
              <div className={cn(
                "mt-3 flex items-center gap-4 text-xs text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
              )}>
                {/* Model used */}
                {(metadata?.model_used || metadata?.provider) && (
                  <div className="flex items-center gap-1">
                    <Zap className="w-3 h-3" />
                    <span>{metadata.model_used || metadata.provider || 'Unknown'}</span>
                  </div>
                )}
                
                {/* Token count */}
                {metadata?.tokens_used && (
                  <div className="flex items-center gap-1">
                    <span>Tokens: {metadata.tokens_used}</span>
                  </div>
                )}
                
                {/* Cost */}
                {metadata?.total_cost && (
                  <div className="flex items-center gap-1">
                    <DollarSign className="w-3 h-3" />
                    <span>${metadata.total_cost.toFixed(4)}</span>
                  </div>
                )}
                
                {/* Timestamp */}
                <div className="flex items-center gap-1 ml-auto">
                  <Clock className="w-3 h-3" />
                  <span>{formattedTime}</span>
                </div>
              </div>
            )}
            
            {/* Error state */}
            {isError && (
              <div className={cn(
                "mt-2 flex items-center gap-2 text-xs text-red-600",
                isSequential && "ml-11"
              )}>
                <AlertCircle className="w-3 h-3" />
                <span>Failed to send message</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
