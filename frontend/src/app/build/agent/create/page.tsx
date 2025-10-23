"use client"

import { MainLayout } from "@/components/layout/main-layout"
import { AgentCreationPlaceholder } from "@/components/agents/agent-creation-placeholder"

export default function CreateAgentPage() {
  return (
    <MainLayout>
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
        <AgentCreationPlaceholder />
      </div>
    </MainLayout>
  )
}
