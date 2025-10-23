'use client'

import * as React from 'react'
import { Agent } from '@/lib/api/agent-service'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
// @ts-ignore - Type definitions provided in src/types/radix-ui.d.ts
import { CheckCircledIcon, CrossCircledIcon } from '@radix-ui/react-icons'

interface AgentSummarySectionProps {
  agent: Agent
}

export function AgentSummarySection({ agent }: AgentSummarySectionProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Review & Create</h2>
        <p className="text-muted-foreground">
          Review your agent configuration before creating it.
        </p>
      </div>

      <div className="space-y-4">
        {/* Basic Information */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Basic Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-2xl">
                  {agent.icon || '🤖'}
                </div>
                <div>
                  <h3 className="font-semibold text-lg">{agent.name || 'Unnamed Agent'}</h3>
                  {agent.category && (
                    <Badge variant="outline" className="text-xs">
                      {agent.category}
                    </Badge>
                  )}
                </div>
              </div>
              
              <div>
                <h4 className="text-sm font-medium mb-1">Description</h4>
                <p className="text-sm text-muted-foreground">
                  {agent.description || 'No description provided.'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Capabilities */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Capabilities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {agent.capabilities.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {agent.capabilities.map((capability: string) => (
                    <Badge key={capability} variant="secondary">
                      {capability}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No capabilities selected. Please go back and select at least one capability.
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Tools */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Enabled Tools</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {agent.configuration.tools.some(tool => tool.enabled) ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {agent.configuration.tools.map((tool) => (
                    <div key={tool.id} className="flex items-center text-sm">
                      {tool.enabled ? (
                        <CheckCircledIcon className="h-4 w-4 mr-2 text-green-500" />
                      ) : (
                        <CrossCircledIcon className="h-4 w-4 mr-2 text-muted-foreground" />
                      )}
                      <span className={tool.enabled ? '' : 'text-muted-foreground'}>
                        {tool.name}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No tools enabled. Your agent will have limited functionality.
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-1">Response Style</h4>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
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
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">Memory</h4>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Status:</span>{' '}
                    <span>{agent.configuration.memory.enabled ? 'Enabled' : 'Disabled'}</span>
                  </div>
                  {agent.configuration.memory.enabled && (
                    <>
                      <div>
                        <span className="text-muted-foreground">Size:</span>{' '}
                        <span>{agent.configuration.memory.maxTokens} tokens</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Relevance Threshold:</span>{' '}
                        <span>{agent.configuration.memory.relevanceThreshold}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {agent.configuration.customInstructions && (
                <div>
                  <h4 className="text-sm font-medium mb-1">Custom Instructions</h4>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {agent.configuration.customInstructions}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
