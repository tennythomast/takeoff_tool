'use client'

import * as React from 'react'
import { Agent, agentCategories } from '@/lib/api/agent-service'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { EmojiPicker } from '@/components/ui/emoji-picker'

interface AgentBasicInfoSectionProps {
  agent: Agent
  updateAgent: (updates: Partial<Agent>) => void
}

export function AgentBasicInfoSection({ agent, updateAgent }: AgentBasicInfoSectionProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">Basic Information</h2>
        <p className="text-muted-foreground">
          Provide the basic details about your agent.
        </p>
      </div>

      <div className="space-y-4">
        {/* Agent Icon */}
        <div className="space-y-2">
          <Label htmlFor="icon">Agent Icon</Label>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center text-3xl">
              {agent.icon || '🤖'}
            </div>
            <EmojiPicker
              onEmojiSelect={(emoji) => updateAgent({ icon: emoji })}
              currentEmoji={agent.icon}
            />
          </div>
          <p className="text-sm text-muted-foreground">
            Choose an emoji that represents your agent's purpose.
          </p>
        </div>

        {/* Agent Name */}
        <div className="space-y-2">
          <Label htmlFor="name" className="required">Agent Name</Label>
          <Input
            id="name"
            placeholder="Enter a name for your agent"
            value={agent.name}
            onChange={(e) => updateAgent({ name: e.target.value })}
            className="max-w-md"
            required
          />
          <p className="text-sm text-muted-foreground">
            Choose a clear, descriptive name for your agent.
          </p>
        </div>

        {/* Agent Description */}
        <div className="space-y-2">
          <Label htmlFor="description" className="required">Description</Label>
          <Textarea
            id="description"
            placeholder="Describe what your agent does and how it can help users"
            value={agent.description}
            onChange={(e) => updateAgent({ description: e.target.value })}
            rows={4}
            required
          />
          <p className="text-sm text-muted-foreground">
            Provide a clear description of your agent's purpose and capabilities.
          </p>
        </div>

        {/* Agent Category */}
        <div className="space-y-2">
          <Label htmlFor="category">Category</Label>
          <Select
            value={agent.category}
            onValueChange={(value) => updateAgent({ category: value })}
          >
            <SelectTrigger className="max-w-md">
              <SelectValue placeholder="Select a category" />
            </SelectTrigger>
            <SelectContent>
              {agentCategories.map((category) => (
                <SelectItem key={category} value={category}>
                  {category}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-sm text-muted-foreground">
            Choose a category that best describes your agent's primary function.
          </p>
        </div>
      </div>
    </div>
  )
}
