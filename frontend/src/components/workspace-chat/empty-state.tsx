"use client";

import React from "react";
import { Bot } from "lucide-react";

interface EmptyStateProps {
  suggestions: string[];
}

export function EmptyState({ suggestions }: EmptyStateProps) {
  return (
    <div className="h-full flex flex-col items-center justify-center p-6">
      <div className="max-w-4xl w-full">
        {/* Simple Welcome Message */}
        <div className="text-center mb-8">
          {/* Simple AI Avatar */}
          <div className="mx-auto mb-6">
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
              <Bot className="h-8 w-8 text-white" />
            </div>
          </div>
          
          {/* Simple greeting */}
          <h1 className="text-2xl font-semibold text-slate-900 mb-3">
            Hi there! 👋
          </h1>
          <p className="text-slate-600 max-w-md mx-auto">
            I'm your AI assistant. Ask me anything to get started!
          </p>
        </div>
      </div>
    </div>
  );
}
