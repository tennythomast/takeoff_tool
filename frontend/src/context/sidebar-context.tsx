"use client"

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface SidebarContextType {
  isCompressed: boolean;
  setIsCompressed: (value: boolean) => void;
  toggleSidebar: () => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isCompressed, setIsCompressed] = useState(() => {
    // Check if we have a stored value in localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('sidebarCompressed');
      return stored ? JSON.parse(stored) : false;
    }
    return false;
  });

  // Toggle sidebar function
  const toggleSidebar = () => {
    const newValue = !isCompressed;
    setIsCompressed(newValue);
    // Store in localStorage for persistence
    if (typeof window !== 'undefined') {
      localStorage.setItem('sidebarCompressed', JSON.stringify(newValue));
    }
  };

  return (
    <SidebarContext.Provider value={{ isCompressed, setIsCompressed, toggleSidebar }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebarContext() {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error('useSidebarContext must be used within a SidebarProvider');
  }
  return context;
}
