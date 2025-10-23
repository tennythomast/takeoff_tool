"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function AgentCreationPlaceholder() {
  const router = useRouter()
  
  const handleBack = () => {
    router.push("/agents")
  }
  
  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-6">
          <button 
            onClick={handleBack}
            className="p-2 rounded-full hover:bg-gray-100 transition-colors"
            aria-label="Go back"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </button>
          <h1 className="text-2xl font-bold text-gray-800">Create New Agent</h1>
        </div>
      </div>
      
      {/* Main content */}
      <Card className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <CardHeader>
          <CardTitle>Agent Creation Coming Soon</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-12 text-center">
            <div className="bg-blue-50 text-blue-700 p-6 rounded-lg inline-block mb-6">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mx-auto">
                <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path>
                <path d="M12 16v-4"></path>
                <path d="M12 8h.01"></path>
              </svg>
            </div>
            <h2 className="text-xl font-semibold mb-2">New Agent Creation Interface Coming Soon</h2>
            <p className="text-gray-600 max-w-md mx-auto mb-8">
              We're redesigning the agent creation experience to better integrate with our new agent template library.
              The new interface will be available soon.
            </p>
            <Button onClick={handleBack} className="bg-gradient-to-r from-[#17B2FF] to-[#0E1036] text-white">
              Return to Agents
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
