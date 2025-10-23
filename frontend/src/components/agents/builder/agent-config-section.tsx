'use client'

import * as React from 'react'
import { Agent, AgentConfiguration, AgentTool } from '@/lib/api/agent-service'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

interface AgentConfigSectionProps {
  agent: Agent
  updateAgentConfig: (updates: Partial<AgentConfiguration>) => void
}

export function AgentConfigSection({ agent, updateAgentConfig }: AgentConfigSectionProps) {
  const toggleTool = (toolId: string) => {
    const updatedTools = agent.configuration.tools.map(tool => {
      if (tool.id === toolId) {
        return { ...tool, enabled: !tool.enabled }
      }
      return tool
    })
    
    updateAgentConfig({ tools: updatedTools })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Agent Configuration</h2>
        <p className="text-muted-foreground">
          Configure how your agent behaves, responds, and processes information.
        </p>
      </div>

      <Tabs defaultValue="tools" className="w-full">
        <TabsList className="grid grid-cols-4 mb-4">
          <TabsTrigger value="tools">Tools</TabsTrigger>
          <TabsTrigger value="response">Response Style</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="instructions">Instructions</TabsTrigger>
        </TabsList>
        
        <TabsContent value="tools" className="space-y-4">
          <div className="space-y-1">
            <h3 className="text-lg font-medium">Available Tools</h3>
            <p className="text-sm text-muted-foreground">
              Enable the tools your agent can use to perform tasks.
            </p>
          </div>
          
          <div className="space-y-4">
            {agent.configuration.tools.map((tool) => (
              <ToolCard 
                key={tool.id} 
                tool={tool} 
                onToggle={() => toggleTool(tool.id)} 
              />
            ))}
          </div>
        </TabsContent>
        
        <TabsContent value="response" className="space-y-4">
          <div className="space-y-1">
            <h3 className="text-lg font-medium">Response Style</h3>
            <p className="text-sm text-muted-foreground">
              Configure how your agent communicates with users.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tone">Communication Tone</Label>
              <Select
                value={agent.configuration.responseStyle.tone}
                onValueChange={(value: 'professional' | 'friendly' | 'technical' | 'simple') => 
                  updateAgentConfig({ 
                    responseStyle: { 
                      ...agent.configuration.responseStyle, 
                      tone: value 
                    } 
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a tone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="friendly">Friendly</SelectItem>
                  <SelectItem value="technical">Technical</SelectItem>
                  <SelectItem value="simple">Simple</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                How formal or casual your agent should sound.
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="format">Response Format</Label>
              <Select
                value={agent.configuration.responseStyle.format}
                onValueChange={(value: 'concise' | 'detailed') => 
                  updateAgentConfig({ 
                    responseStyle: { 
                      ...agent.configuration.responseStyle, 
                      format: value 
                    } 
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a format" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="concise">Concise</SelectItem>
                  <SelectItem value="detailed">Detailed</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                How brief or detailed your agent's responses should be.
              </p>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between">
              <Label htmlFor="creativity">Creativity Level</Label>
              <span className="text-sm text-muted-foreground">
                {agent.configuration.responseStyle.creativity}%
              </span>
            </div>
            <Slider
              id="creativity"
              min={0}
              max={100}
              step={10}
              value={[agent.configuration.responseStyle.creativity]}
              onValueChange={(value) => 
                updateAgentConfig({ 
                  responseStyle: { 
                    ...agent.configuration.responseStyle, 
                    creativity: value[0] 
                  } 
                })
              }
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Conservative</span>
              <span>Balanced</span>
              <span>Creative</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              How creative or conservative your agent should be in its responses.
            </p>
          </div>
        </TabsContent>
        
        <TabsContent value="memory" className="space-y-4">
          <div className="space-y-1">
            <h3 className="text-lg font-medium">Memory Settings</h3>
            <p className="text-sm text-muted-foreground">
              Configure how your agent remembers and uses conversation history.
            </p>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="memory-enabled">Enable Memory</Label>
              <p className="text-sm text-muted-foreground">
                Allow the agent to remember previous conversations.
              </p>
            </div>
            <Switch
              id="memory-enabled"
              checked={agent.configuration.memory.enabled}
              onCheckedChange={(checked) => 
                updateAgentConfig({ 
                  memory: { 
                    ...agent.configuration.memory, 
                    enabled: checked 
                  } 
                })
              }
            />
          </div>
          
          {agent.configuration.memory.enabled && (
            <div className="space-y-4 pt-2">
              <div className="space-y-2">
                <Label htmlFor="max-tokens">Memory Size (tokens)</Label>
                <Input
                  id="max-tokens"
                  type="number"
                  min={500}
                  max={10000}
                  step={500}
                  value={agent.configuration.memory.maxTokens}
                  onChange={(e) => 
                    updateAgentConfig({ 
                      memory: { 
                        ...agent.configuration.memory, 
                        maxTokens: parseInt(e.target.value) || 2000 
                      } 
                    })
                  }
                  className="max-w-xs"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum amount of conversation history to remember (higher values use more resources).
                </p>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label htmlFor="relevance">Relevance Threshold</Label>
                  <span className="text-sm text-muted-foreground">
                    {agent.configuration.memory.relevanceThreshold}
                  </span>
                </div>
                <Slider
                  id="relevance"
                  min={0.1}
                  max={1.0}
                  step={0.1}
                  value={[agent.configuration.memory.relevanceThreshold]}
                  onValueChange={(value) => 
                    updateAgentConfig({ 
                      memory: { 
                        ...agent.configuration.memory, 
                        relevanceThreshold: value[0] 
                      } 
                    })
                  }
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>More Inclusive</span>
                  <span>Balanced</span>
                  <span>More Selective</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  How selective the agent should be when recalling relevant information.
                </p>
              </div>
            </div>
          )}
        </TabsContent>
        
        <TabsContent value="instructions" className="space-y-4">
          <div className="space-y-1">
            <h3 className="text-lg font-medium">Custom Instructions</h3>
            <p className="text-sm text-muted-foreground">
              Provide specific instructions for how your agent should behave.
            </p>
          </div>
          
          <div className="space-y-2">
            <Textarea
              placeholder="Enter custom instructions for your agent..."
              value={agent.configuration.customInstructions || ''}
              onChange={(e) => updateAgentConfig({ customInstructions: e.target.value })}
              rows={8}
            />
            <p className="text-sm text-muted-foreground">
              These instructions will guide how your agent responds and behaves. Be specific about
              what you want the agent to do, how it should respond, and any limitations it should have.
            </p>
          </div>
          
          <div className="bg-muted p-4 rounded-md">
            <h4 className="text-sm font-medium mb-2">Example Instructions:</h4>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li>"Always provide step-by-step explanations for technical questions."</li>
              <li>"Use simple language and avoid jargon when explaining concepts."</li>
              <li>"When answering questions about code, include examples."</li>
              <li>"Always verify information before providing it to the user."</li>
            </ul>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

interface ToolCardProps {
  tool: AgentTool
  onToggle: () => void
}

function ToolCard({ tool, onToggle }: ToolCardProps) {
  return (
    <Card className={`transition-all ${tool.enabled ? 'border-primary' : ''}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base">{tool.name}</CardTitle>
            <CardDescription>{tool.description}</CardDescription>
          </div>
          <Switch checked={tool.enabled} onCheckedChange={onToggle} />
        </div>
      </CardHeader>
      {tool.enabled && tool.config && (
        <CardContent>
          <div className="pt-2">
            {tool.id === 'api-connector' && (
              <div className="space-y-2">
                <Label className="text-sm">API Endpoints</Label>
                <div className="flex flex-wrap gap-2">
                  {tool.config.endpoints && tool.config.endpoints.length > 0 ? (
                    tool.config.endpoints.map((endpoint: string, index: number) => (
                      <Badge key={index} variant="secondary">{endpoint}</Badge>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No endpoints configured</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  )
}
