'use client'

import * as React from 'react'
import { useSearchParams } from 'next/navigation'
import { SmartAgentBuilderFlow } from '@/components/agents/builder/smart-agent-builder-flow'

export default function SmartAgentBuilderPage() {
  const searchParams = useSearchParams()
  const workspaceId = searchParams.get('workspace')
  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-gray-50">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Create Smart Agent</h1>
              <p className="mt-1 text-sm text-gray-500">Build your AI agent with our guided setup</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="max-w-7xl mx-auto h-full">
          <SmartAgentBuilderFlow workspaceId={workspaceId} />
        </div>
      </div>
    </div>
  )
}
