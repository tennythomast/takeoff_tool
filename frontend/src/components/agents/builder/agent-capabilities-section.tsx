'use client'

import * as React from 'react'
import { Agent, agentCapabilities } from '@/lib/api/agent-service'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { InfoCircledIcon } from '@radix-ui/react-icons'

interface AgentCapabilitiesSectionProps {
  agent: Agent
  updateAgent: (updates: Partial<Agent>) => void
}

export function AgentCapabilitiesSection({ agent, updateAgent }: AgentCapabilitiesSectionProps) {
  const toggleCapability = (capability: string) => {
    const updatedCapabilities = agent.capabilities.includes(capability)
      ? agent.capabilities.filter((c) => c !== capability)
      : [...agent.capabilities, capability]
    
    updateAgent({ capabilities: updatedCapabilities })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Agent Capabilities</h2>
        <p className="text-muted-foreground">
          Select the capabilities your agent will have. These determine what tasks your agent can perform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agentCapabilities.map((capability) => {
          const isSelected = agent.capabilities.includes(capability)
          return (
            <Card 
              key={capability} 
              className={`cursor-pointer transition-all ${isSelected ? 'border-primary ring-1 ring-primary' : ''}`}
              onClick={() => toggleCapability(capability)}
            >
              <CardContent className="p-4 flex items-start space-x-4">
                <Checkbox 
                  checked={isSelected} 
                  onCheckedChange={() => toggleCapability(capability)}
                  className="mt-1"
                />
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <Label className="text-base font-medium cursor-pointer">{capability}</Label>
                    {getCapabilityBadge(capability)}
                  </div>
                  <p className="text-sm text-muted-foreground">{getCapabilityDescription(capability)}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {agent.capabilities.length === 0 && (
        <div className="flex items-center p-4 bg-muted/50 rounded-md">
          <InfoCircledIcon className="h-5 w-5 mr-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Select at least one capability for your agent.
          </p>
        </div>
      )}
    </div>
  )
}

function getCapabilityBadge(capability: string) {
  switch (capability) {
    case 'Web Browsing':
    case 'API Integration':
      return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">External Access</Badge>
    case 'Code Generation':
      return <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">Advanced</Badge>
    case 'Knowledge Base Access':
      return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Data Access</Badge>
    default:
      return null
  }
}

function getCapabilityDescription(capability: string): string {
  switch (capability) {
    case 'Text Generation':
      return 'Generate human-like text responses for various queries and tasks.'
    case 'Code Generation':
      return 'Write, explain, and debug code in multiple programming languages.'
    case 'Data Analysis':
      return 'Analyze and interpret data, generate insights, and create reports.'
    case 'Image Recognition':
      return 'Identify and describe the content of images.'
    case 'Document Processing':
      return 'Extract, summarize, and analyze information from documents.'
    case 'Web Browsing':
      return 'Search and retrieve information from the internet.'
    case 'API Integration':
      return 'Connect to external services and APIs to access or manipulate data.'
    case 'Knowledge Base Access':
      return 'Access and utilize information from your organization\'s knowledge base.'
    default:
      return 'Enable this capability for your agent.'
  }
}
