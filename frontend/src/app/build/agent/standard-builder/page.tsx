'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import { AgentBuilderForm } from '@/components/agents/builder/agent-builder-form'

export default function StandardBuilderPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const workspaceId = searchParams.get('workspace')
  
  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-gray-50">
      <div className="flex-1 overflow-auto">
        <AgentBuilderForm workspaceId={workspaceId} />
      </div> 
    </div>
  )
}
