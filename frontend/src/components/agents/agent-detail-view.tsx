"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Agent, TabType } from "./types"
import { CompactAgentCard } from "./compact-agent-card"
import { AgentDetailPanel } from "./agent-detail-panel"
import { useSidebarContext } from "@/context/sidebar-context"
import { 
  Plus, 
  Zap, 
  BarChart3, 
  ShieldCheck,
  FileText,
  Search
} from "lucide-react"

// Sample data for demonstration
const sampleAgents: Agent[] = [
  {
    id: "1",
    name: "Jira Summarizer",
    description: "Automatically summarizes Jira tickets and provides actionable insights for sprint planning and backlog management.",
    category: "PRODUCTIVITY",
    status: "ACTIVE",
    icon: "📋",
    executionCount: 1247,
    avgResponseTime: "0.8s",
    successRate: 98.5,
    lastUsed: "2 hours ago"
  },
  {
    id: "2",
    name: "Email Classifier",
    description: "Smart email routing and priority classification for customer support teams with automated tagging and escalation rules.",
    category: "PRODUCTIVITY",
    status: "ACTIVE",
    icon: "📧",
    executionCount: 892,
    avgResponseTime: "1.2s",
    successRate: 95.2,
    lastUsed: "5 hours ago"
  },
  {
    id: "3",
    name: "Lead Scorer",
    description: "Sales qualification automation that scores leads based on engagement, fit, and conversion probability using advanced ML models.",
    category: "ANALYSIS",
    status: "ACTIVE",
    icon: "📊",
    executionCount: 1582,
    avgResponseTime: "1.8s",
    successRate: 92.7,
    lastUsed: "1 day ago"
  },
  {
    id: "4",
    name: "Document Processor",
    description: "Extracts key information from documents, identifies entities, and categorizes content for easy retrieval and analysis.",
    category: "ANALYSIS",
    status: "DRAFT",
    icon: "📄",
    executionCount: 0,
    avgResponseTime: "0s",
    successRate: 0,
    lastUsed: "Never"
  },
  {
    id: "5",
    name: "Code Reviewer",
    description: "Analyzes code for best practices, potential bugs, and security vulnerabilities with detailed explanations and fix suggestions.",
    category: "RESEARCH",
    status: "PAUSED",
    icon: "💻",
    executionCount: 347,
    avgResponseTime: "3.2s",
    successRate: 89.3,
    lastUsed: "1 week ago"
  },
  {
    id: "6",
    name: "Customer Support Bot",
    description: "Handles common customer inquiries, troubleshoots issues, and escalates complex problems to the appropriate team members.",
    category: "COMPLIANCE",
    status: "ACTIVE",
    icon: "🤖",
    executionCount: 2156,
    avgResponseTime: "0.5s",
    successRate: 97.1,
    lastUsed: "1 hour ago"
  }
];

// Filter tabs data
const filterTabs = [
  { id: "all", label: "All", count: 6, icon: null },
  { id: "productivity", label: "Productivity", count: 2, icon: Zap },
  { id: "analysis", label: "Analysis", count: 2, icon: BarChart3 },
  { id: "compliance", label: "Compliance", count: 1, icon: ShieldCheck },
  { id: "research", label: "Research", count: 1, icon: FileText }
];

export function AgentDetailView() {
  // State
  const router = useRouter();
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [activeFilter, setActiveFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  
  // Get sidebar context
  const { setIsCompressed } = useSidebarContext();
  
  // Filter agents based on active filter and search query
  const filteredAgents = sampleAgents.filter(agent => {
    const matchesFilter = activeFilter === "all" || 
                         activeFilter === agent.category.toLowerCase();
    
    const matchesSearch = searchQuery === "" || 
                         agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         agent.description.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesFilter && matchesSearch;
  });
  
  // Handle agent selection
  const handleAgentClick = (agent: Agent) => {
    setSelectedAgent(agent);
    setIsDetailOpen(true);
    // Compress sidebar when agent is selected
    setIsCompressed(true);
  };
  
  // Handle closing the detail panel
  const handleCloseDetail = () => {
    setIsDetailOpen(false);
    // Expand sidebar when detail panel is closed
    setIsCompressed(false);
    // Optional: Reset selected agent after animation completes
    // setTimeout(() => setSelectedAgent(null), 300);
  };
  
  // Handle tab change
  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
  };
  
  // Handle escape key to close detail panel
  useEffect(() => {
    const handleEscKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isDetailOpen) {
        handleCloseDetail();
      }
    };
    
    document.addEventListener('keydown', handleEscKey);
    return () => {
      document.removeEventListener('keydown', handleEscKey);
    };
  }, [isDetailOpen]);
  
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Filter and Action Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
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

            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search agents..."
                  className="pl-10 pr-4 py-2 bg-white rounded-xl border border-gray-300 text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              
              {/* Create Button */}
              <button 
                className="flex items-center gap-2 bg-gradient-to-r from-[#17B2FF] to-[#0E1036] text-white px-4 py-2 rounded-full font-medium hover:opacity-90 transition-opacity"
                aria-label="Create new agent"
                onClick={() => router.push('/agents/create')}
              >
                <Plus className="h-4 w-4" />
                Create Agent (New UI Coming Soon)
              </button>
            </div>
          </div>
        </div>

        {/* Main Content Area with Dynamic Layout */}
        <div className={`
          flex transition-all duration-300 ease-in-out h-[calc(100vh-180px)] overflow-hidden
          ${isDetailOpen ? 'gap-6' : 'gap-0'}
        `}>
          {/* Left Panel - Agent Grid */}
          <div className={`
            transition-all duration-300 ease-in-out overflow-y-auto
            ${isDetailOpen ? 'w-[40%]' : 'w-full'}
          `}>
            <div className={`
              grid gap-6 transition-all duration-300
              ${isDetailOpen 
                ? 'grid-cols-1 sm:grid-cols-2' 
                : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'}
            `}>
              {filteredAgents.map((agent) => (
                <CompactAgentCard
                  key={agent.id}
                  agent={agent}
                  isSelected={selectedAgent?.id === agent.id}
                  onClick={() => handleAgentClick(agent)}
                  isCompact={isDetailOpen}
                />
              ))}
            </div>
            
            {/* Empty State */}
            {filteredAgents.length === 0 && (
              <div className="text-center py-12">
                <div className="text-gray-400 mb-4">
                  <BarChart3 className="h-12 w-12 mx-auto" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No agents found</h3>
                <p className="text-gray-500 mb-4">
                  Try adjusting your search or filter to find what you&apos;re looking for.
                </p>
              </div>
            )}
          </div>
          
          {/* Right Panel - Detail View */}
          <div className={`
            transition-all duration-300 ease-in-out transform
            ${isDetailOpen ? 'w-[60%] translate-x-0' : 'w-0 translate-x-full'}
          `}>
            {selectedAgent && isDetailOpen && (
              <AgentDetailPanel
                agent={selectedAgent}
                activeTab={activeTab}
                onTabChange={handleTabChange}
                onClose={handleCloseDetail}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
