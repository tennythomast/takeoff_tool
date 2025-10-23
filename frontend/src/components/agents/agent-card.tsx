"use client"

import * as React from "react"
import { useState, useRef, useEffect } from "react"
import { 
  MoreVertical, 
  Settings, 
  BarChart3, 
  Play, 
  Copy, 
  Trash2
} from "lucide-react"

interface AgentCardProps {
  id: string
  name: string
  description: string
  icon: React.ElementType
  iconGradient: string
  metrics: {
    executions: number
    avgTime: number
  }
  onClick?: () => void
  onAction?: (action: string) => void
}

export function AgentCard({
  name,
  description,
  icon: Icon,
  iconGradient,
  metrics,
  onClick,
  onAction
}: AgentCardProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  
  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [menuRef])

  const handleAction = (action: string) => {
    setMenuOpen(false)
    onAction?.(action)
  }

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't trigger card click if clicking on menu
    if (!e.target || !(e.target as Element).closest('.agent-menu')) {
      onClick?.()
    }
  }

  return (
    <div 
      className="bg-white bg-opacity-80 backdrop-blur-sm rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-md transition-all hover:translate-y-[-2px] relative group cursor-pointer"
      onClick={handleCardClick}
    >
      {/* Menu Button and Dropdown */}
      <div className="absolute top-4 right-4 z-10 agent-menu" ref={menuRef}>
        <button 
          className="p-1 hover:bg-gray-100 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" 
          onClick={(e) => {
            e.stopPropagation()
            setMenuOpen(!menuOpen)
          }}
          aria-label="Agent options"
        >
          <MoreVertical className="h-5 w-5 text-gray-500" />
        </button>
        
        {menuOpen && (
          <div className="absolute right-0 mt-1 w-48 bg-white rounded-xl shadow-lg py-1 border border-gray-100 z-20">
            <button 
              className="flex items-center w-full px-4 py-2 text-sm text-left text-gray-700 hover:bg-gray-50"
              onClick={() => handleAction('configure')}
            >
              <Settings className="mr-2 h-4 w-4" />
              Configure
            </button>
            <button 
              className="flex items-center w-full px-4 py-2 text-sm text-left text-gray-700 hover:bg-gray-50"
              onClick={() => handleAction('analytics')}
            >
              <BarChart3 className="mr-2 h-4 w-4" />
              Analytics
            </button>
            <button 
              className="flex items-center w-full px-4 py-2 text-sm text-left text-gray-700 hover:bg-gray-50"
              onClick={() => handleAction('test')}
            >
              <Play className="mr-2 h-4 w-4" />
              Test Run
            </button>
            <hr className="my-1 border-gray-100" />
            <button 
              className="flex items-center w-full px-4 py-2 text-sm text-left text-gray-700 hover:bg-gray-50"
              onClick={() => handleAction('duplicate')}
            >
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </button>
            <button 
              className="flex items-center w-full px-4 py-2 text-sm text-left text-red-600 hover:bg-red-50"
              onClick={() => handleAction('delete')}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </button>
          </div>
        )}
      </div>
      
      {/* Icon and Title Row */}
      <div className="flex items-center gap-4 mb-4">
        <div className={`h-14 w-14 rounded-2xl bg-gradient-to-br ${iconGradient} flex items-center justify-center text-white shadow-sm flex-shrink-0`}>
          <Icon className="h-7 w-7" />
        </div>
        <h3 className="font-semibold text-lg text-[#0E1036] leading-tight">{name}</h3>
      </div>
      
      {/* Content */}
      <p className="text-gray-600 text-sm mb-4 line-clamp-3 leading-relaxed">{description}</p>
      
      {/* Simplified Metrics - Single Line */}
      <div className="flex items-center gap-4 text-sm text-gray-500">
        <div className="flex flex-col">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Executions</span>
          <span className="font-semibold text-gray-700">{metrics.executions.toLocaleString()}</span>
        </div>
        <div className="w-px h-8 bg-gray-200"></div>
        <div className="flex flex-col">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">Avg Time</span>
          <span className="font-semibold text-gray-700">{metrics.avgTime}s</span>
        </div>
      </div>
    </div>
  )
}