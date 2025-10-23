"use client"

import * as React from "react"
import { Agent } from "./types"
import { 
  BarChart3, 
  Clock,
  CheckCircle2
} from "lucide-react"

// Map categories to colors
const categoryColors = {
  'PRODUCTIVITY': 'from-blue-400 to-blue-600',
  'ANALYSIS': 'from-purple-400 to-purple-600',
  'COMPLIANCE': 'from-green-400 to-green-600',
  'RESEARCH': 'from-amber-400 to-amber-600'
}

// Map status to colors and labels
const statusConfig = {
  'ACTIVE': { color: 'bg-green-500', label: 'Active' },
  'DRAFT': { color: 'bg-gray-400', label: 'Draft' },
  'PAUSED': { color: 'bg-amber-500', label: 'Paused' },
  'ARCHIVED': { color: 'bg-red-500', label: 'Archived' }
}

interface CompactAgentCardProps {
  agent: Agent;
  isSelected: boolean;
  onClick: () => void;
  isCompact: boolean;
}

export function CompactAgentCard({ 
  agent, 
  isSelected, 
  onClick,
  isCompact
}: CompactAgentCardProps) {
  // Get the gradient color based on category
  const gradient = categoryColors[agent.category] || 'from-gray-400 to-gray-600';
  const status = statusConfig[agent.status];
  
  return (
    <div 
      className={`
        bg-white rounded-2xl p-5 border transition-all cursor-pointer
        ${isSelected 
          ? 'border-blue-500 shadow-md bg-blue-50/30' 
          : 'border-gray-100 shadow-sm hover:shadow-md hover:translate-y-[-2px]'
        }
      `}
      onClick={onClick}
    >
      <div className="flex items-center gap-4">
        {/* Icon */}
        <div className={`h-12 w-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-white shadow-sm flex-shrink-0`}>
          {agent.icon}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title and Status */}
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-semibold text-[#0E1036] truncate pr-2">{agent.name}</h3>
            <div className="flex items-center">
              <span className={`inline-block w-2 h-2 rounded-full ${status.color} mr-1`}></span>
              <span className="text-xs text-gray-500">{status.label}</span>
            </div>
          </div>
          
          {/* Description - only show if not compact or truncate to 1 line if compact */}
          <p className={`text-gray-600 text-sm ${isCompact ? 'line-clamp-1' : 'line-clamp-2'} leading-relaxed`}>
            {agent.description}
          </p>
          
          {/* Metrics - only show if not compact */}
          {!isCompact && (
            <div className="flex items-center gap-3 mt-3 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <BarChart3 className="h-3 w-3" />
                <span>{agent.executionCount} runs</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{agent.avgResponseTime}</span>
              </div>
              <div className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                <span>{agent.successRate}%</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
