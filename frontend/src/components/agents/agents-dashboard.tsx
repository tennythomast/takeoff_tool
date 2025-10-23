"use client"

import * as React from "react"
import { useState } from "react"
import { 
  Plus, 
  Zap, 
  BarChart3, 
  ShieldCheck,
  Users,
  Mail,
  Diamond
} from "lucide-react"
import { AgentCard } from "@/components/agents/agent-card"

// Agent type definition
interface Agent {
  id: string
  name: string
  description: string
  type: string
  icon: React.ElementType
  iconGradient: string
  metrics: {
    executions: number
    avgTime: number
  }
  category: "productivity" | "analysis" | "compliance"
}

// Filter tabs data
const filterTabs = [
  { id: "all", label: "All", count: 3, icon: null },
  { id: "productivity", label: "Productivity", count: 2, icon: Zap },
  { id: "analysis", label: "Analysis", count: 1, icon: BarChart3 },
  { id: "compliance", label: "Compliance", count: 0, icon: ShieldCheck }
]

// Sample agents data - Only 3 agents
const agents: Agent[] = [
  {
    id: "1",
    name: "Jira Summarizer",
    description: "Automatically summarizes Jira tickets and provides actionable insights for sprint planning and backlog management.",
    type: "jira",
    icon: Diamond,
    iconGradient: "from-blue-400 to-blue-600",
    metrics: {
      executions: 1247,
      avgTime: 0.8
    },
    category: "productivity"
  },
  {
    id: "2",
    name: "Email Classifier",
    description: "Smart email routing and priority classification for customer support teams with automated tagging and escalation rules.",
    type: "email",
    icon: Mail,
    iconGradient: "from-orange-400 to-red-500",
    metrics: {
      executions: 892,
      avgTime: 1.2
    },
    category: "productivity"
  },
  {
    id: "3",
    name: "Lead Scorer",
    description: "Sales qualification automation that scores leads based on engagement, fit, and conversion probability using advanced ML models.",
    type: "leads",
    icon: Users,
    iconGradient: "from-green-400 to-green-600",
    metrics: {
      executions: 1582,
      avgTime: 1.8
    },
    category: "analysis"
  }
]

export function AgentsDashboard() {
  const [activeFilter, setActiveFilter] = useState("all")

  // Filter agents based on active filter
  const filteredAgents = agents.filter(agent => {
    return activeFilter === "all" || activeFilter === agent.category
  })

  const handleAgentClick = (agentId: string) => {
    console.log('Opening agent:', agentId)
    // Navigate to agent details page
  }

  const handleAgentAction = (agentId: string, action: string) => {
    console.log(`Action ${action} for agent ${agentId}`)
    // Handle specific actions (configure, analytics, test, duplicate, delete)
  }

  return (
    <div className="w-full">
      {/* Action Bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {/* Filter Tabs */}
          <div className="bg-white bg-opacity-70 backdrop-blur-sm rounded-2xl p-1.5">
            <div className="flex space-x-2">
              {filterTabs.map((tab) => (
                <button
                  key={tab.id}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    activeFilter === tab.id
                      ? "bg-white text-[#0E1036] shadow-sm"
                      : "text-gray-600 hover:bg-white/50"
                  }`}
                  onClick={() => setActiveFilter(tab.id)}
                >
                  {tab.icon && <tab.icon className="h-4 w-4" />}
                  {tab.label}
                  <span className={`ml-1 px-1.5 py-0.5 rounded-full text-xs ${
                    activeFilter === tab.id 
                      ? "bg-[#17B2FF]/10 text-[#17B2FF]" 
                      : "bg-gray-100 text-gray-500"
                  }`}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Create Button */}
        <button 
          className="flex items-center gap-2 bg-gradient-to-r from-[#17B2FF] to-[#0E1036] text-white px-4 py-2 rounded-full font-medium hover:opacity-90 transition-opacity"
          aria-label="Create new agent"
        >
          <Plus className="h-4 w-4" />
          Create Agent
        </button>
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredAgents.map((agent) => (
          <AgentCard
            key={agent.id}
            id={agent.id}
            name={agent.name}
            description={agent.description}
            icon={agent.icon}
            iconGradient={agent.iconGradient}
            metrics={agent.metrics}
            onClick={() => handleAgentClick(agent.id)}
            onAction={(action) => handleAgentAction(agent.id, action)}
          />
        ))}
      </div>

      {/* Empty State */}
      {filteredAgents.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <BarChart3 className="h-12 w-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No agents in this category</h3>
          <p className="text-gray-500 mb-4">
            Try selecting a different filter to see more agents.
          </p>
        </div>
      )}
    </div>
  )
}