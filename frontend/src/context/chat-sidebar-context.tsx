"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react'

export interface ChatMessage {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: Date
  model?: {
    name: string
    provider: string
  }
  tokens?: {
    total: number
    prompt: number
    completion: number
  }
  cost?: number
  isStreaming?: boolean
  metadata?: {
    error?: boolean
    errorType?: string
    errorCode?: string
    recoverable?: boolean
    [key: string]: any  // Allow for additional metadata properties
  }
}

interface ChatSidebarContextType {
  isOpen: boolean
  setIsOpen: (open: boolean) => void
  messages: ChatMessage[]
  addMessage: (message: ChatMessage) => void
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  clearMessages: () => void
  currentCost: number
  updateCost: (cost: number) => void
}

const ChatSidebarContext = createContext<ChatSidebarContextType | undefined>(undefined)

export function ChatSidebarProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentCost, setCurrentCost] = useState(0)

  const addMessage = (message: ChatMessage) => {
    console.log('➕ [CONTEXT] Adding message:', {
      id: message.id,
      role: message.role,
      contentLength: message.content?.length || 0,
      contentPreview: message.content?.substring(0, 100) + '...',
      isStreaming: message.isStreaming,
      hasModel: !!message.model,
      hasTokens: !!message.tokens,
      hasCost: message.cost !== undefined
    });
    
    // Check if message already exists to prevent duplicates
    const existingMessage = messages.find(m => m.id === message.id);
    if (existingMessage) {
      console.warn('⚠️ [CONTEXT] Message already exists, updating instead of adding:', message.id);
      updateMessage(message.id, message);
      return;
    }
    
    setMessages(prev => {
      const newMessages = [...prev, message];
      
      // Debug: Log the message array before and after addition
      console.log('💾 [CONTEXT] Messages before/after addition:', {
        beforeCount: prev.length,
        afterCount: newMessages.length,
        messageIds: newMessages.map(m => ({id: m.id, contentLength: m.content?.length || 0}))
      });
      
      return newMessages;
    });
    
    // Update cost if this is an assistant message with cost
    if (message.role === 'assistant' && message.cost) {
      console.log('💰 [CONTEXT] Updating cost:', {
        oldCost: currentCost,
        messageCost: message.cost,
        newCost: currentCost + message.cost
      });
      setCurrentCost(prev => prev + message.cost!)
    }
  }

  const updateMessage = (id: string, updates: Partial<ChatMessage>) => {
    console.log('🔄 [CONTEXT] Updating message:', {
      id,
      updates,
      updatesKeys: Object.keys(updates),
      hasContent: 'content' in updates,
      contentLength: updates.content?.length || 0,
      contentPreview: updates.content?.substring(0, 100) + '...',
      isStreaming: updates.isStreaming
    });
    
    // Find the old message before updating to get its cost and log details
    let oldCost = 0;
    const oldMessage = messages.find(m => m.id === id);
    
    if (oldMessage) {
      console.log('💾 [CONTEXT] Found existing message:', {
        id,
        oldContentLength: oldMessage.content?.length || 0,
        oldContentPreview: oldMessage.content?.substring(0, 100) + '...',
        oldIsStreaming: oldMessage.isStreaming,
        newContentLength: updates.content?.length || oldMessage.content?.length || 0,
        contentChanged: updates.content !== undefined && updates.content !== oldMessage.content
      });
      
      if (updates.cost !== undefined && updates.role === 'assistant') {
        oldCost = oldMessage?.cost || 0;
      }
    } else {
      console.warn('⚠️ [CONTEXT] Message not found for update:', id);
    }
    
    // Update the messages
    setMessages(prev => {
      const newMessages = prev.map(msg => 
        msg.id === id 
          ? { ...msg, ...updates }
          : msg
      );
      
      // Debug: Log the message array before and after update
      console.log('💾 [CONTEXT] Messages before/after update:', {
        beforeCount: prev.length,
        afterCount: newMessages.length,
        messageUpdated: newMessages.some(m => m.id === id),
        updatedMessage: newMessages.find(m => m.id === id),
        allMessageIds: newMessages.map(m => ({id: m.id, contentLength: m.content?.length || 0}))
      });
      
      return newMessages;
    });
    
    // Update cost if cost was updated
    if (updates.cost !== undefined && updates.role === 'assistant') {
      console.log('💰 [CONTEXT] Updating cost after message update:', {
        oldCost,
        newCost: updates.cost!,
        totalCost: currentCost - oldCost + updates.cost!
      });
      setCurrentCost(prev => prev - oldCost + updates.cost!);
    }
  }

  const clearMessages = () => {
    console.log('🧹 Clearing all messages from context')
    setMessages([])
    setCurrentCost(0)
  }

  const updateCost = (cost: number) => {
    setCurrentCost(prev => prev + cost)
  }

  return (
    <ChatSidebarContext.Provider value={{
      isOpen,
      setIsOpen,
      messages,
      addMessage,
      updateMessage,
      clearMessages,
      currentCost,
      updateCost,
    }}>
      {children}
    </ChatSidebarContext.Provider>
  )
}

export function useChatSidebar() {
  const context = useContext(ChatSidebarContext)
  if (context === undefined) {
    throw new Error('useChatSidebar must be used within a ChatSidebarProvider')
  }
  return context
}