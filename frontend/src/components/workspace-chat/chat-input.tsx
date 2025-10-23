"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Send, Loader2, Sparkles, Zap, MessageCircle } from "lucide-react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (content: string) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  isLoading,
  disabled = false,
  placeholder = "Ask about your workspace, agents, or optimizations...",
  maxLength = 4000
}: ChatInputProps) {
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Suggested prompts for AI-native experience
  const suggestedPrompts = [
    "Analyze my workspace performance",
    "Show recent executions",
    "Help me improve workflows"
  ];
  
  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to get the correct scrollHeight
      textareaRef.current.style.height = "auto";
      
      // Set height based on scrollHeight (with min and max)
      const newHeight = Math.min(
        Math.max(textareaRef.current.scrollHeight, 40), // Min height: 40px
        200 // Max height: 200px
      );
      
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [value]);
  
  // Handle key press (Enter to send, Shift+Enter for new line)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isLoading && !disabled) {
        onSend(value);
      }
    }
  };
  
  // Handle send button click
  const handleSend = () => {
    if (value.trim() && !isLoading && !disabled) {
      onSend(value.trim());
      onChange("");
    }
  };
  
  // Handle suggested prompt click
  const handleSuggestedPrompt = (prompt: string) => {
    onChange(prompt);
    onSend(prompt);
  };
  
  const remainingChars = maxLength - value.length;
  const isNearLimit = remainingChars < 100;
  const isAtLimit = remainingChars <= 0;
  
  return (
    <div className="space-y-4">
      {/* Suggested prompts - show when input is empty and not loading */}
      {!value.trim() && !isLoading && (
        <div className="flex flex-wrap gap-2">
          {suggestedPrompts.map((prompt, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="cursor-pointer hover:bg-blue-100 hover:text-blue-700 transition-colors duration-200 px-3 py-1.5 text-xs bg-slate-50 text-slate-600 border border-slate-200 hover:border-blue-200"
              onClick={() => handleSuggestedPrompt(prompt)}
            >
              <Sparkles className="w-3 h-3 mr-1" />
              {prompt}
            </Badge>
          ))}
        </div>
      )}
      
      {/* Enhanced Input card */}
      <Card className={cn(
        "transition-all duration-300 border-2 bg-gradient-to-br from-white to-slate-50/50 backdrop-blur-sm",
        isFocused 
          ? "border-blue-400 shadow-xl ring-4 ring-blue-100/50 bg-gradient-to-br from-white to-blue-50/30" 
          : "border-slate-200 hover:border-slate-300 hover:shadow-md",
        disabled && "opacity-50 cursor-not-allowed"
      )}>
        <CardContent className="p-0">
          <div className="flex items-end">
            <div className="flex-1 relative">
              <Textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder={placeholder}
                disabled={disabled || isLoading}
                maxLength={maxLength}
                className={cn(
                  "resize-none min-h-[50px] max-h-[200px] border-0 focus:ring-0 focus-visible:ring-0 shadow-none bg-transparent px-1 py-1 text-slate-900 placeholder:text-slate-500 transition-all duration-200 w-full",
                  isFocused && "placeholder:text-slate-400"
                )}
                style={{ height: "50px" }}
              />
              
              {/* Character count and status */}
              <div className="flex items-center justify-between px-2 pb-1">
                <div className="flex items-center gap-2">
                  {isLoading && (
                    <div className="flex items-center gap-2 text-xs text-blue-600">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      <span>AI is thinking...</span>
                    </div>
                  )}
                  {disabled && !isLoading && (
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span>Connection required</span>
                    </div>
                  )}
                </div>
                
                {(isFocused || isNearLimit) && (
                  <div className={cn(
                    "text-xs transition-colors duration-200",
                    isAtLimit ? "text-red-500" : isNearLimit ? "text-amber-500" : "text-slate-400"
                  )}>
                    {remainingChars} characters left
                  </div>
                )}
              </div>
            </div>
            
            {/* Enhanced Send button */}
            <div className="p-2">
              <Button
                onClick={handleSend}
                disabled={!value.trim() || isLoading || disabled || isAtLimit}
                size="sm"
                className={cn(
                  "h-10 w-10 p-0 shrink-0 transition-all duration-300 rounded-lg",
                  value.trim() && !isLoading && !disabled && !isAtLimit
                    ? "bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 shadow-lg hover:shadow-xl hover:scale-105 ring-2 ring-blue-200/50"
                    : "bg-slate-300 hover:bg-slate-400 text-slate-600"
                )}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
