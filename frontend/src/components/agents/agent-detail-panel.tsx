"use client"

import * as React from "react"
import { Agent, TabType, AgentTool } from "./types"
import { 
  X, 
  BarChart3, 
  Settings, 
  Zap,
  Link2,
  History,
  Play,
  Copy,
  Share2
} from "lucide-react"

interface AgentDetailPanelProps {
  agent: Agent;
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  onClose: () => void;
}

export function AgentDetailPanel({ 
  agent, 
  activeTab, 
  onTabChange,
  onClose 
}: AgentDetailPanelProps) {
  // Map categories to colors
  const categoryColors = {
    'PRODUCTIVITY': 'from-blue-400 to-blue-600',
    'ANALYSIS': 'from-purple-400 to-purple-600',
    'COMPLIANCE': 'from-green-400 to-green-600',
    'RESEARCH': 'from-amber-400 to-amber-600'
  }
  
  // Get the gradient color based on category
  const gradient = categoryColors[agent.category] || 'from-gray-400 to-gray-600';
  
  // Define tabs
  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: Zap },
    { id: 'configuration' as TabType, label: 'Configuration', icon: Settings },
    { id: 'analytics' as TabType, label: 'Analytics', icon: BarChart3 },
    { id: 'integrations' as TabType, label: 'Integrations', icon: Link2 },
    { id: 'versions' as TabType, label: 'Versions', icon: History }
  ];
  
  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-100">
        <div className="flex items-center gap-4">
          <div className={`h-10 w-10 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center text-white shadow-sm flex-shrink-0`}>
            {agent.icon}
          </div>
          <h2 className="font-semibold text-lg text-[#0E1036]">{agent.name}</h2>
        </div>
        <button 
          onClick={onClose}
          className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          aria-label="Close panel"
        >
          <X className="h-5 w-5 text-gray-500" />
        </button>
      </div>
      
      {/* Tabs */}
      <div className="border-b border-gray-100">
        <div className="flex overflow-x-auto scrollbar-hide">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const Icon = tab.icon;
            
            return (
              <button
                key={tab.id}
                className={`
                  flex items-center gap-2 px-6 py-4 text-sm font-medium whitespace-nowrap
                  ${isActive 
                    ? 'text-blue-600 border-b-2 border-blue-600' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }
                `}
                onClick={() => onTabChange(tab.id)}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>
      
      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'overview' && (
          <OverviewTab agent={agent} />
        )}
        
        {activeTab === 'configuration' && (
          <ConfigurationTab agent={agent} />
        )}
        
        {activeTab === 'analytics' && (
          <AnalyticsTab agent={agent} />
        )}
        
        {activeTab === 'integrations' && (
          <IntegrationsTab agent={agent} />
        )}
        
        {activeTab === 'versions' && (
          <VersionsTab agent={agent} />
        )}
      </div>
    </div>
  )
}

// Tab Components
function OverviewTab({ agent }: { agent: Agent }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">About this agent</h3>
        <p className="text-gray-600">{agent.description}</p>
      </div>
      
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-2">Capabilities</h4>
        <div className="flex flex-wrap gap-2">
          {['Data Processing', 'Text Analysis', 'Summarization', 'Classification'].map((tag) => (
            <span 
              key={tag} 
              className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-sm font-medium text-gray-500 mb-1">Executions</div>
          <div className="text-2xl font-semibold text-gray-900">{agent.executionCount}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-sm font-medium text-gray-500 mb-1">Success Rate</div>
          <div className="text-2xl font-semibold text-gray-900">{agent.successRate}%</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-sm font-medium text-gray-500 mb-1">Avg. Response Time</div>
          <div className="text-2xl font-semibold text-gray-900">{agent.avgResponseTime}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-sm font-medium text-gray-500 mb-1">Last Used</div>
          <div className="text-2xl font-semibold text-gray-900">{agent.lastUsed}</div>
        </div>
      </div>
      
      <div className="flex gap-3">
        <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors">
          <Play className="h-4 w-4" />
          Test Run
        </button>
        <button className="flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-200 transition-colors">
          <Copy className="h-4 w-4" />
          Duplicate
        </button>
        <button className="flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-200 transition-colors">
          <Share2 className="h-4 w-4" />
          Share
        </button>
      </div>
    </div>
  );
}

import { AgentToolConfig } from "./agent-tool-config";

function ConfigurationTab({ agent }: { agent: Agent }) {
  const [activeSection, setActiveSection] = React.useState<string>("steps");
  const [tools, setTools] = React.useState<AgentTool[]>(agent.tools || []);
  
  const steps = [
    { id: 1, title: 'Basic Information', isComplete: true },
    { id: 2, title: 'Capabilities & Tools', isComplete: true },
    { id: 3, title: 'Prompt Engineering', isComplete: false },
    { id: 4, title: 'Testing & Validation', isComplete: false },
  ];
  
  const handleToolsChange = (updatedTools: AgentTool[]) => {
    setTools(updatedTools);
    // Here you would typically call an API to update the agent's tools
    console.log("Tools updated:", updatedTools);
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4 border-b pb-4">
        <button 
          onClick={() => setActiveSection("steps")} 
          className={`px-4 py-2 text-sm font-medium rounded-md ${activeSection === "steps" ? "bg-blue-50 text-blue-700" : "text-gray-600"}`}
        >
          Configuration Steps
        </button>
        <button 
          onClick={() => setActiveSection("tools")} 
          className={`px-4 py-2 text-sm font-medium rounded-md ${activeSection === "tools" ? "bg-blue-50 text-blue-700" : "text-gray-600"}`}
        >
          Tools
        </button>
        <button 
          onClick={() => setActiveSection("parameters")} 
          className={`px-4 py-2 text-sm font-medium rounded-md ${activeSection === "parameters" ? "bg-blue-50 text-blue-700" : "text-gray-600"}`}
        >
          Parameters
        </button>
      </div>
      
      {activeSection === "steps" && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Smart Configuration</h3>
          
          <div className="space-y-4">
            {steps.map((step) => (
              <div 
                key={step.id}
                className={`
                  border rounded-lg p-4 transition-all
                  ${step.isComplete ? 'border-green-200 bg-green-50' : 'border-gray-200'}
                `}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`
                      h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium
                      ${step.isComplete 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-gray-100 text-gray-700'}
                    `}>
                      {step.id}
                    </div>
                    <h4 className="font-medium text-gray-900">{step.title}</h4>
                  </div>
                  
                  {step.isComplete ? (
                    <span className="text-green-600 text-sm font-medium">Completed</span>
                  ) : (
                    <button className="text-blue-600 text-sm font-medium">
                      {step.id === 3 ? 'Continue' : 'Start'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {activeSection === "tools" && (
        <AgentToolConfig 
          tools={tools} 
          onToolsChange={handleToolsChange} 
        />
      )}
      
      {activeSection === "parameters" && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">Agent Parameters</h3>
          <p className="text-gray-500">Configure the parameters for this agent.</p>
          {/* Parameter configuration UI would go here */}
          <div className="text-center py-8 border border-dashed rounded-lg">
            <p className="text-gray-500">No parameters configured yet</p>
            <button className="mt-4 px-4 py-2 bg-blue-50 text-blue-700 rounded-md text-sm font-medium">
              Add Parameter
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function AnalyticsTab({ agent }: { agent: Agent }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Performance Analytics</h3>
      
      <div className="bg-gray-50 rounded-xl p-6 flex items-center justify-center">
        <div className="text-center">
          <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Analytics charts will appear here</p>
        </div>
      </div>
      
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Performance Metrics</h4>
        <div className="space-y-3">
          {[
            { label: 'Average Response Time', value: agent.avgResponseTime },
            { label: 'Success Rate', value: `${agent.successRate}%` },
            { label: 'Error Rate', value: `${100 - agent.successRate}%` },
            { label: 'Total Executions', value: agent.executionCount }
          ].map((metric) => (
            <div key={metric.label} className="flex justify-between items-center border-b border-gray-100 pb-2">
              <span className="text-gray-600">{metric.label}</span>
              <span className="font-medium text-gray-900">{metric.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function IntegrationsTab(_props: { agent: Agent }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Integrations</h3>
      
      <div className="bg-gray-50 rounded-xl p-6 flex items-center justify-center">
        <div className="text-center">
          <Link2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No integrations configured</p>
          <button className="mt-4 text-blue-600 font-medium">Add Integration</button>
        </div>
      </div>
    </div>
  );
}

function VersionsTab(_props: { agent: Agent }) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Version History</h3>
      
      <div className="space-y-4">
        {[
          { version: 'v1.2', date: '2 days ago', author: 'You', changes: 'Updated prompt template' },
          { version: 'v1.1', date: '1 week ago', author: 'You', changes: 'Added new tool integration' },
          { version: 'v1.0', date: '2 weeks ago', author: 'You', changes: 'Initial version' }
        ].map((version) => (
          <div key={version.version} className="border border-gray-200 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <div className="font-medium text-gray-900">{version.version}</div>
              <div className="text-sm text-gray-500">{version.date}</div>
            </div>
            <div className="text-sm text-gray-600">
              <span className="text-gray-500">By {version.author}</span>
              <p className="mt-1">{version.changes}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
