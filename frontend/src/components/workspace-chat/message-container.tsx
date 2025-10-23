"use client";

import React, { useRef, useEffect } from "react";
import { Message } from "@/context/workspace-chat-context";
import { ChatMessage } from "@/components/workspace-chat/chat-message";
import { EmptyState } from "@/components/workspace-chat/empty-state";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Calendar, Loader2 } from "lucide-react";

interface MessageContainerProps {
  messages: Message[];
  isLoading: boolean;
  suggestions: string[];
}

export function MessageContainer({ messages, isLoading, suggestions }: MessageContainerProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Group messages by date for timestamp display
  const groupedMessages = messages.reduce<{
    date: string;
    messages: Message[];
  }[]>((groups, message) => {
    const messageDate = new Date(message.timestamp).toLocaleDateString();
    const existingGroup = groups.find(group => group.date === messageDate);

    if (existingGroup) {
      existingGroup.messages.push(message);
    } else {
      groups.push({
        date: messageDate,
        messages: [message]
      });
    }

    return groups;
  }, []);

  // If no messages, show empty state
  if (messages.length === 0) {
    return <EmptyState suggestions={suggestions} />;
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {groupedMessages.map((group, groupIndex) => (
          <div key={group.date} className="space-y-6">
            {/* Date separator */}
            <div className="flex justify-center">
              <Badge 
                variant="secondary" 
                className="bg-white/80 backdrop-blur-sm text-slate-600 border border-slate-200 shadow-sm px-4 py-2"
              >
                <Calendar className="w-3 h-3 mr-2" />
                {group.date === new Date().toLocaleDateString() ? "Today" : group.date}
              </Badge>
            </div>

            {/* Messages in this group */}
            <div className="space-y-4">
              {group.messages.map((message, messageIndex) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  metadata={message.metadata}
                  isSequential={
                    messageIndex > 0 &&
                    group.messages[messageIndex - 1].role === message.role
                  }
                />
              ))}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-center">
            <div className="flex items-center gap-3 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-full px-6 py-3 shadow-sm">
              <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
              <span className="text-sm text-slate-600 font-medium">AI is generating response...</span>
            </div>
          </div>
        )}

        {/* Invisible element to scroll to */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
