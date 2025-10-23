'use client'

import * as React from 'react'
import { Agent } from '@/lib/api/agent-service'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
// @ts-ignore - Type definitions provided in src/types/radix-ui.d.ts
import { CheckCircledIcon } from '@radix-ui/react-icons'

interface AgentPreviewCardProps {
  agent: Agent
}

export function AgentPreviewCard({ agent }: AgentPreviewCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="bg-muted/50 pb-4">
        <CardTitle className="text-lg">Agent Preview</CardTitle>
        <CardDescription>
          This is how your agent will appear to users.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="p-6 space-y-4">
          {/* Agent Icon and Name */}
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-2xl">
              {agent.icon || '🤖'}
            </div>
            <div>
              <h3 className="font-semibold text-lg">
                {agent.name || 'Unnamed Agent'}
              </h3>
              {agent.category && (
                <Badge variant="outline" className="text-xs">
                  {agent.category}
                </Badge>
              )}
            </div>
          </div>

          {/* Description */}
          <div className="text-sm text-muted-foreground">
            {agent.description || 'No description provided.'}
          </div>

          {/* Capabilities */}
          {agent.capabilities.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Capabilities</h4>
              <div className="flex flex-wrap gap-1.5">
                {agent.capabilities.map((capability: string) => (
                  <Badge key={capability} variant="secondary" className="text-xs">
                    {capability}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Tools */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Tools</h4>
            <div className="space-y-1">
              {agent.configuration.tools
                .filter((tool) => tool.enabled)
                .map((tool) => (
                  <div key={tool.id} className="flex items-center text-sm">
                    <CheckCircledIcon className="h-4 w-4 mr-2 text-green-500" />
                    <span>{tool.name}</span>
                  </div>
                ))}
              {!agent.configuration.tools.some((tool) => tool.enabled) && (
                <div className="text-sm text-muted-foreground">
                  No tools enabled
                </div>
              )}
            </div>
          </div>

          {/* Response Style */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Communication Style</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Tone:</span>{' '}
                <span className="capitalize">{agent.configuration.responseStyle.tone}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Format:</span>{' '}
                <span className="capitalize">{agent.configuration.responseStyle.format}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Creativity:</span>{' '}
                <span>{agent.configuration.responseStyle.creativity}%</span>
              </div>
              <div>
                <span className="text-muted-foreground">Memory:</span>{' '}
                <span>{agent.configuration.memory.enabled ? 'Enabled' : 'Disabled'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Footer */}
        <div className="border-t p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Status</span>
            <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
              Draft
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
