"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Agent } from "./types"
import { 
  ArrowLeft,
  Check,
  ChevronRight,
  Sparkles,
  Zap,
  Settings,
  Wrench,
  MessageSquare
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardFooter, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { AgentToolConfig } from "./agent-tool-config"

// Agent categories with icons and descriptions
const agentCategories = [
  {
    id: "PRODUCTIVITY",
    name: "Productivity",
    icon: "⚡️",
    description: "Automate repetitive tasks and workflows",
    color: "bg-blue-100 text-blue-600 border-blue-200"
  },
  {
    id: "ANALYSIS",
    name: "Analysis",
    icon: "📊",
    description: "Process and analyze data for insights",
    color: "bg-purple-100 text-purple-600 border-purple-200"
  },
  {
    id: "COMPLIANCE",
    name: "Compliance",
    icon: "🛡️",
    description: "Ensure adherence to rules and regulations",
    color: "bg-green-100 text-green-600 border-green-200"
  },
  {
    id: "RESEARCH",
    name: "Research",
    icon: "🔍",
    description: "Gather and synthesize information",
    color: "bg-amber-100 text-amber-600 border-amber-200"
  }
]

export function AgentCreationView() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [progress, setProgress] = useState(0)
  const [activeTab, setActiveTab] = useState("basic")
  const [formComplete, setFormComplete] = useState(false)
  const [agentTools, setAgentTools] = useState<any[]>([])
  
  // Form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "",
    icon: "🤖",
    tools: [] as any[]
  })
  
  // Update progress based on form completion
  useEffect(() => {
    let completedFields = 0
    const totalFields = 3 // name, description, category
    
    if (formData.name) completedFields++
    if (formData.description) completedFields++
    if (formData.category) completedFields++
    
    const calculatedProgress = Math.floor((completedFields / totalFields) * 100)
    setProgress(calculatedProgress)
    
    // Check if basic form is complete
    setFormComplete(Boolean(formData.name && formData.description && formData.category))
  }, [formData])
  
  // Handle form input changes
  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }
  
  // Handle category selection
  const handleCategorySelect = (categoryId: string) => {
    setFormData(prev => ({
      ...prev,
      category: categoryId
    }))
  }
  
  // Handle icon selection
  const handleIconSelect = (icon: string) => {
    setFormData(prev => ({
      ...prev,
      icon
    }))
  }
  
  // Handle tools update
  const handleToolsUpdate = (tools: any[]) => {
    setFormData(prev => ({
      ...prev,
      tools
    }))
    setAgentTools(tools)
  }
  
  // Handle form submission
  const handleSubmit = async () => {
    try {
      // Here you would typically make an API call to create the agent
      console.log("Creating agent:", formData)
      
      // Simulate API call success
      setTimeout(() => {
        // Redirect to the agent detail page
        router.push("/agents")
      }, 1000)
    } catch (error) {
      console.error("Error creating agent:", error)
    }
  }
  
  // Handle back button
  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    } else {
      router.push("/agents")
    }
  }
  
  // Handle next step
  const handleNextStep = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1)
    } else {
      handleSubmit()
    }
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
        
        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
          <div 
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        <div className="flex justify-between text-sm text-gray-500">
          <span>Basic Info</span>
          <span>Configuration</span>
          <span>Review</span>
        </div>
      </div>
      
      {/* Main content */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Step 1: Basic Information */}
        {currentStep === 1 && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-6">Basic Information</h2>
            
            <div className="space-y-6">
              {/* Name */}
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Agent Name
                </label>
                <Input
                  id="name"
                  placeholder="Enter a descriptive name for your agent"
                  value={formData.name}
                  onChange={(e) => handleInputChange("name", e.target.value)}
                  className="w-full"
                />
              </div>
              
              {/* Description */}
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <Textarea
                  id="description"
                  placeholder="Describe what your agent does and how it helps users"
                  value={formData.description}
                  onChange={(e) => handleInputChange("description", e.target.value)}
                  className="w-full min-h-[100px]"
                />
              </div>
              
              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Category
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {agentCategories.map((category) => (
                    <div
                      key={category.id}
                      className={`
                        p-4 rounded-lg border-2 cursor-pointer transition-all
                        ${formData.category === category.id 
                          ? `${category.color} border-current` 
                          : 'border-gray-200 hover:border-gray-300'}
                      `}
                      onClick={() => handleCategorySelect(category.id)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="text-2xl">{category.icon}</div>
                        <div>
                          <h3 className="font-medium">{category.name}</h3>
                          <p className="text-sm text-gray-500">{category.description}</p>
                        </div>
                        {formData.category === category.id && (
                          <Check className="ml-auto h-5 w-5 text-current" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Icon selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Choose an Icon (Optional)
                </label>
                <div className="flex flex-wrap gap-3">
                  {["🤖", "🧠", "📊", "📝", "🔍", "💬", "📈", "🛠️", "🔧", "🧩"].map((icon) => (
                    <button
                      key={icon}
                      className={`
                        w-10 h-10 text-xl flex items-center justify-center rounded-lg
                        ${formData.icon === icon 
                          ? 'bg-blue-100 border-2 border-blue-500' 
                          : 'bg-gray-100 hover:bg-gray-200'}
                      `}
                      onClick={() => handleIconSelect(icon)}
                    >
                      {icon}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Step 2: Configuration */}
        {currentStep === 2 && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-6">Agent Configuration</h2>
            
            <Tabs defaultValue="tools" className="w-full">
              <TabsList className="mb-6">
                <TabsTrigger value="tools" className="flex items-center gap-2">
                  <Wrench className="h-4 w-4" />
                  Tools
                </TabsTrigger>
                <TabsTrigger value="parameters" className="flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  Parameters
                </TabsTrigger>
                <TabsTrigger value="prompts" className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Prompts
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="tools">
                <AgentToolConfig 
                  tools={agentTools}
                  onToolsChange={handleToolsUpdate}
                />
              </TabsContent>
              
              <TabsContent value="parameters">
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                  <p className="text-gray-500">
                    Configure agent parameters after creating the basic agent.
                  </p>
                </div>
              </TabsContent>
              
              <TabsContent value="prompts">
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                  <p className="text-gray-500">
                    Configure agent prompts after creating the basic agent.
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        )}
        
        {/* Step 3: Review */}
        {currentStep === 3 && (
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-6">Review Your Agent</h2>
            
            <div className="bg-gray-50 rounded-lg p-6 mb-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white text-2xl">
                  {formData.icon}
                </div>
                
                <div className="flex-1">
                  <h3 className="text-lg font-medium">{formData.name}</h3>
                  <p className="text-gray-600 text-sm mt-1">{formData.description}</p>
                  
                  <div className="mt-4 flex flex-wrap gap-2">
                    <span className="px-3 py-1 bg-blue-100 text-blue-600 rounded-full text-xs font-medium">
                      {agentCategories.find(c => c.id === formData.category)?.name || formData.category}
                    </span>
                    
                    {formData.tools && formData.tools.length > 0 && (
                      <span className="px-3 py-1 bg-purple-100 text-purple-600 rounded-full text-xs font-medium">
                        {formData.tools.length} Tools
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <h3 className="font-medium">What happens next?</h3>
              <ul className="space-y-2">
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
                  <span>Your agent will be created and ready to use</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
                  <span>You can further customize parameters and prompts</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
                  <span>You can test your agent and monitor its performance</span>
                </li>
              </ul>
            </div>
          </div>
        )}
        
        {/* Footer with navigation buttons */}
        <div className="border-t border-gray-200 p-6 bg-gray-50 flex justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
          >
            {currentStep === 1 ? "Cancel" : "Back"}
          </Button>
          
          <Button
            onClick={handleNextStep}
            disabled={currentStep === 1 && !formComplete}
            className="bg-gradient-to-r from-[#17B2FF] to-[#0E1036] text-white"
          >
            {currentStep === 3 ? (
              <span className="flex items-center gap-2">
                Create Agent
                <Sparkles className="h-4 w-4" />
              </span>
            ) : (
              <span className="flex items-center gap-2">
                Continue
                <ChevronRight className="h-4 w-4" />
              </span>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
