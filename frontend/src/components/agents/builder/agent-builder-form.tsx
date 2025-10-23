'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Agent, AgentConfiguration, createAgent, agentCategories, getDefaultAgentConfiguration } from '@/lib/api/agent-service'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from '@/components/ui/use-toast'
import { 
  Bot, 
  Brain, 
  Settings, 
  Zap, 
  Play, 
  Target,
  MessageSquare,
  Database,
  Globe,
  Clock,
  CheckCircle,
  Loader2,
  Plus,
  X,
  Sparkles,
  AlertTriangle,
  Trash2,
  Rocket,
  Users2,
  Building,
  Send
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'
import { Slider } from '@/components/ui/slider'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { fetchMCPConnections, MCPServerConnection } from '@/lib/api/mcp-service'

// Enhanced agent state interface
interface EnhancedAgent extends Agent {
  primaryRole?: string
  problemStatement?: string
  communicationStyle?: 'professional' | 'friendly' | 'technical' | 'concise' | 'conversational'
  outputFormat?: 'free_text' | 'structured' | 'markdown' | 'json' | 'html'
  memoryType?: 'none' | 'short_term' | 'long_term' | 'hybrid'
  capabilityLevel?: 'basic' | 'intermediate' | 'advanced' | 'expert'
  qualityPreference?: number
  customInstructions?: string
  isDraft?: boolean
  visibility?: 'team' | 'organization' | 'public'
  tags?: string[]
}

interface AgentTool {
  id: string
  name: string
  description: string
  enabled: boolean
  config?: Record<string, any>
}

type BuilderStep = 'overview' | 'instructions' | 'tools' | 'testing' | 'deployment'

const BUILDER_STEPS = [
  { id: 'overview', label: 'Overview', icon: Bot, description: 'Basic information and purpose' },
  { id: 'instructions', label: 'Instructions', icon: Brain, description: 'Core behavior and personality' },
  { id: 'tools', label: 'Tools & Actions', icon: Zap, description: 'External integrations' },
  { id: 'testing', label: 'Test & Preview', icon: Play, description: 'Test your agent' },
  { id: 'deployment', label: 'Deploy & Share', icon: Globe, description: 'Make your agent available' }
] as const

interface AgentBuilderFormProps {
  workspaceId?: string | null;
}

export function AgentBuilderForm({ workspaceId }: AgentBuilderFormProps) {
  const router = useRouter()
  const [currentStep, setCurrentStep] = React.useState<BuilderStep>('overview')
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [isTesting, setIsTesting] = React.useState(false)
  const [validationErrors, setValidationErrors] = React.useState<Record<string, string>>({})
  const [unsavedChanges, setUnsavedChanges] = React.useState(false)
  const [showValidation, setShowValidation] = React.useState(false)
  
  const [agent, setAgent] = React.useState<EnhancedAgent>({
    name: '',
    description: '',
    icon: '🤖',
    category: 'Productivity',
    capabilities: [],
    configuration: {
      ...getDefaultAgentConfiguration(),
      tools: []
    },
    primaryRole: '',
    problemStatement: '',
    communicationStyle: 'professional',
    outputFormat: 'free_text',
    memoryType: 'short_term',
    capabilityLevel: 'intermediate',
    qualityPreference: 80,
    customInstructions: '',
    isDraft: true
  })

  const currentStepIndex = BUILDER_STEPS.findIndex((step) => step.id === currentStep)
  const progress = ((currentStepIndex + 1) / BUILDER_STEPS.length) * 100

  // Real-time validation
  React.useEffect(() => {
    const errors: Record<string, string> = {}
    
    if (!agent.name.trim()) errors.name = 'Agent name is required'
    if (!agent.description.trim()) errors.description = 'Description is required'
    if (!agent.primaryRole?.trim()) errors.primaryRole = 'Primary role is required'
    if (currentStep === 'instructions' && !agent.configuration.customInstructions?.trim()) {
      errors.instructions = 'Instructions are required'
    }
    
    setValidationErrors(errors)
  }, [agent, currentStep])

  const updateAgent = (updates: Partial<EnhancedAgent>) => {
    setAgent((prev) => ({ ...prev, ...updates }))
    setUnsavedChanges(true)
  }

  const validateCurrentStep = (): boolean => {
    switch (currentStep) {
      case 'overview':
        return !validationErrors.name && !validationErrors.description && !validationErrors.primaryRole
      case 'instructions':
        return !validationErrors.instructions
      default:
        return true
    }
  }

  const handleNext = () => {
    // Show validation errors when user tries to proceed
    setShowValidation(true)
    
    if (validateCurrentStep()) {
      const nextIndex = currentStepIndex + 1
      if (nextIndex < BUILDER_STEPS.length) {
        setCurrentStep(BUILDER_STEPS[nextIndex].id)
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
    }
  }

  const handleBack = () => {
    const prevIndex = currentStepIndex - 1
    if (prevIndex >= 0) {
      setCurrentStep(BUILDER_STEPS[prevIndex].id)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const handleSubmit = async () => {
    // Show validation errors when user tries to submit
    setShowValidation(true)
    
    if (Object.keys(validationErrors).length > 0) {
      toast({
        title: 'Validation errors',
        description: 'Please fix all validation errors before creating the agent.',
        variant: 'destructive',
      })
      return
    }

    setIsSubmitting(true)
    try {
      // Create a copy of the agent data with properly mapped fields for the backend
      const backendAgentData = {
        ...agent,
        // Map the instructions field from configuration.customInstructions to the root level
        instructions: agent.configuration?.customInstructions || '',
        // Ensure category is one of the valid backend enum values
        category: agent.category,
        isDraft: false
      }
      
      // Add workspace ID if available
      if (workspaceId) {
        console.log('Adding workspace ID to agent:', workspaceId);
        // Use type assertion since the createAgent function accepts 'any'
        (backendAgentData as any).workspace = workspaceId;
      }
      
      const result = await createAgent(backendAgentData)
      
      if (result) {
        toast({
          title: 'Agent created successfully',
          description: `${agent.name} has been created and is ready to use.`,
        })
        router.push(`/agents/${result.id}`)
      } else {
        throw new Error('Failed to create agent')
      }
    } catch (error) {
      console.error('Error creating agent:', error)
      toast({
        title: 'Error creating agent',
        description: 'There was a problem creating your agent. Please try again.',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 'overview':
        return <OverviewStep agent={agent} updateAgent={updateAgent} validationErrors={validationErrors} showValidation={showValidation} />
      case 'instructions':
        return <InstructionsStep agent={agent} updateAgent={updateAgent} validationErrors={validationErrors} showValidation={showValidation} />
      case 'tools':
        return <ToolsStep agent={agent} updateAgent={updateAgent} />
      case 'testing':
        return <TestingStep agent={agent} isTesting={isTesting} />
      case 'deployment':
        return <DeploymentStep agent={agent} updateAgent={updateAgent} />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8">
        {/* Enhanced Header with Progress */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Custom Agent Builder
              </h1>
              <p className="text-muted-foreground mt-2 text-lg">
                Create a powerful AI agent tailored to your specific needs
              </p>
            </div>
            <div className="flex items-center gap-3">
              {unsavedChanges && (
                <Badge variant="outline" className="text-orange-600 border-orange-200">
                  <Clock className="w-3 h-3 mr-1" />
                  Unsaved changes
                </Badge>
              )}
              <Button variant="outline" onClick={() => router.push('/agents')}>
                Cancel
              </Button>
            </div>
          </div>
          
          {/* Build Progress - Moved to top */}
          <div className="bg-white/80 backdrop-blur-sm rounded-lg border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-500" />
                <span className="font-medium">Build Progress</span>
              </div>
              <span className="text-sm text-muted-foreground">
                Step {currentStepIndex + 1} of {BUILDER_STEPS.length}
              </span>
            </div>
            <Progress value={progress} className="h-2" />
            
            <div className="flex flex-wrap gap-2 mt-4">
              {BUILDER_STEPS.map((step, index) => {
                const Icon = step.icon
                const isActive = step.id === currentStep
                const isCompleted = index < currentStepIndex
                const isAccessible = index <= currentStepIndex
                
                return (
                  <Button
                    key={step.id}
                    variant="ghost"
                    size="sm"
                    disabled={!isAccessible}
                    onClick={() => isAccessible && setCurrentStep(step.id)}
                    className={cn(
                      "flex items-center gap-2 py-1 px-3 rounded-full text-sm transition-all",
                      isActive && "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
                      isCompleted && !isActive && "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
                      !isActive && !isCompleted && "bg-slate-100 dark:bg-slate-700"
                    )}>
                    {isCompleted ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                    {step.label}
                  </Button>
                )
              })}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 xl:grid-cols-3 gap-6">
          {/* Main Content - Expanded */}
          <div className="lg:col-span-3 xl:col-span-3">
            <Card className="min-h-[600px] shadow-xl border-0 bg-white/90 backdrop-blur-sm">
              <CardContent className="p-6 lg:p-8">
                {renderStepContent()}
                
                {/* Enhanced Navigation Buttons */}
                <div className="flex justify-between items-center mt-8 pt-6 border-t">
                  <Button
                    variant="outline"
                    onClick={handleBack}
                    disabled={currentStepIndex === 0 || isSubmitting}
                    className="flex items-center gap-2"
                  >
                    ← Back
                  </Button>
                  
                  <div className="flex gap-3">
                    {currentStep === 'deployment' ? (
                      <Button
                        onClick={handleSubmit}
                        disabled={isSubmitting || Object.keys(validationErrors).length > 0}
                        className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600"
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Creating...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4" />
                            Create Agent
                          </>
                        )}
                      </Button>
                    ) : (
                      <Button
                        onClick={handleNext}
                        disabled={!validateCurrentStep() || isSubmitting}
                        className="flex items-center gap-2"
                      >
                        Continue →
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Validation Status Panel */}
          <div className="lg:col-span-1 xl:col-span-1">
            <div className="sticky top-8 space-y-6">
              <AgentValidationStatus validationErrors={validationErrors} showValidation={showValidation} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Step Components
function OverviewStep({ agent, updateAgent, validationErrors, showValidation }: {
  agent: EnhancedAgent
  updateAgent: (updates: Partial<EnhancedAgent>) => void
  validationErrors: Record<string, string>
  showValidation: boolean
}) {
  return (
    <div className="space-y-2 flex flex-col min-h-[600px]">
      <div className="mb-4">
        <h2 className="text-3xl font-bold mb-2">Agent Overview</h2>
        <p className="text-muted-foreground text-lg">
          Define the basic identity and purpose of your AI agent
        </p>
      </div>

      <Card className="border shadow-md bg-card flex-grow flex flex-col">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Bot className="w-5 h-5" />
            Agent Details
          </CardTitle>
          <CardDescription>
            Configure the basic information about your agent
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 flex-grow">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm font-medium">Agent Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., Customer Support Assistant"
                  value={agent.name}
                  onChange={(e) => updateAgent({ name: e.target.value })}
                  className={cn(
                    validationErrors.name ? 'border-destructive focus-visible:ring-destructive' : ''
                  )}
                />
                {validationErrors.name && showValidation && (
                  <p className="text-sm text-destructive flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    {validationErrors.name}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="category" className="text-sm font-medium">Category</Label>
                <Select value={agent.category} onValueChange={(value) => updateAgent({ category: value })}>
                  <SelectTrigger>
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
              </div>

              <div className="space-y-2">
                <Label htmlFor="communicationStyle" className="text-sm font-medium">Communication Style</Label>
                <Select 
                  value={agent.communicationStyle || 'professional'} 
                  onValueChange={(value) => updateAgent({ communicationStyle: value as any })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select style" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="friendly">Friendly</SelectItem>
                    <SelectItem value="technical">Technical</SelectItem>
                    <SelectItem value="concise">Concise</SelectItem>
                    <SelectItem value="conversational">Conversational</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="outputFormat" className="text-sm font-medium">Output Format</Label>
                <Select 
                  value={agent.outputFormat || 'markdown'} 
                  onValueChange={(value) => updateAgent({ outputFormat: value as any })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select format" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="free_text">Free Text</SelectItem>
                    <SelectItem value="structured">Structured</SelectItem>
                    <SelectItem value="markdown">Markdown</SelectItem>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="html">HTML</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="primaryRole" className="text-sm font-medium">Primary Role *</Label>
                <Input
                  id="primaryRole"
                  placeholder="e.g., Help customers with product questions"
                  value={agent.primaryRole}
                  onChange={(e) => updateAgent({ primaryRole: e.target.value })}
                  className={cn(
                    validationErrors.primaryRole ? 'border-destructive focus-visible:ring-destructive' : ''
                  )}
                />
                {validationErrors.primaryRole && showValidation && (
                  <p className="text-sm text-destructive flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    {validationErrors.primaryRole}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-sm font-medium">Description *</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what this agent does and how it helps users..."
                  value={agent.description}
                  onChange={(e) => updateAgent({ description: e.target.value })}
                  className={cn(
                    "min-h-[220px] resize-none",
                    validationErrors.description ? 'border-destructive focus-visible:ring-destructive' : ''
                  )}
                />
                {validationErrors.description && showValidation && (
                  <p className="text-sm text-destructive flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    {validationErrors.description}
                  </p>
                )}
              </div>

              
            </div>
          </div>

          <Separator className="my-4" />

          <div className="space-y-4">
            <div className="space-y-2">
                  <Label htmlFor="problemStatement" className="text-sm font-medium">Problem Statement</Label>
                  <Textarea
                    id="problemStatement"
                    placeholder="What specific problem does this agent solve?"
                    value={agent.problemStatement}
                    onChange={(e) => updateAgent({ problemStatement: e.target.value })}
                    className="min-h-[80px]"
                  />
              </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Instructions Step Component
function InstructionsStep({ agent, updateAgent, validationErrors, showValidation }: {
  agent: EnhancedAgent
  updateAgent: (updates: Partial<EnhancedAgent>) => void
  validationErrors: Record<string, string>
  showValidation: boolean
}) {
  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">Agent Instructions</h2>
        <p className="text-muted-foreground text-lg">
          Define how your agent should behave and respond to users
        </p>
      </div>

      <Card className="border shadow-md bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Brain className="h-5 w-5" />
            Instructions
          </CardTitle>
          <CardDescription>
            These instructions will guide your agent's behavior and responses
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="instructions" className="text-sm font-medium">System Instructions *</Label>
            <Textarea
              id="instructions"
              placeholder="You are a helpful AI assistant that..."
              value={agent.configuration.customInstructions || ''}
              onChange={(e) => updateAgent({ configuration: { ...agent.configuration, customInstructions: e.target.value } })}
              className={cn(
                "min-h-[180px] resize-none",
                validationErrors.instructions ? 'border-destructive focus-visible:ring-destructive' : ''
              )}
            />
            {validationErrors.instructions && showValidation && (
              <p className="text-sm text-destructive flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {validationErrors.instructions}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Provide detailed instructions that define how your agent should behave, respond, and handle different scenarios.
            </p>
          </div>

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="capabilityLevel" className="text-sm font-medium">Capability Level</Label>
              <Select
                value={agent.capabilityLevel || 'intermediate'}
                onValueChange={(value) => updateAgent({ capabilityLevel: value as any })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select capability level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="basic">Basic</SelectItem>
                  <SelectItem value="intermediate">Intermediate</SelectItem>
                  <SelectItem value="advanced">Advanced</SelectItem>
                  <SelectItem value="expert">Expert</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Determines the complexity of tasks your agent can handle
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="memoryType" className="text-sm font-medium">Memory Type</Label>
              <Select
                value={agent.memoryType || 'short_term'}
                onValueChange={(value) => updateAgent({ memoryType: value as any })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select memory type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No Memory</SelectItem>
                  <SelectItem value="short_term">Short Term</SelectItem>
                  <SelectItem value="long_term">Long Term</SelectItem>
                  <SelectItem value="hybrid">Hybrid</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Controls how your agent remembers past interactions
              </p>
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <Label className="text-sm font-medium">Quality vs Speed Preference</Label>
            <div className="space-y-4">
              <Slider
                defaultValue={[agent.qualityPreference || 50]}
                min={0}
                max={100}
                step={1}
                onValueChange={(value) => updateAgent({ qualityPreference: value[0] })}
              />
              <div className="flex justify-between items-center">
                <Badge variant="outline" className="font-normal">Speed</Badge>
                <span className="text-sm font-medium">
                  {agent.qualityPreference || 50}%
                </span>
                <Badge variant="outline" className="font-normal">Quality</Badge>
              </div>
              <p className="text-xs text-muted-foreground text-center">
                Adjust the slider to balance between faster responses and higher quality outputs
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Tools Step Component
function ToolsStep({ agent, updateAgent }: {
  agent: EnhancedAgent
  updateAgent: (updates: Partial<EnhancedAgent>) => void
}) {
  const [newToolName, setNewToolName] = React.useState('')
  const [newToolDescription, setNewToolDescription] = React.useState('')
  const [isAddingTool, setIsAddingTool] = React.useState(false)
  const [mcpConnections, setMcpConnections] = React.useState<MCPServerConnection[]>([]) 
  const [isLoadingConnections, setIsLoadingConnections] = React.useState(false)
  const [connectionError, setConnectionError] = React.useState<string | null>(null)
  
  // Fetch MCP connections when component mounts
  React.useEffect(() => {
    const loadMcpConnections = async () => {
      try {
        setIsLoadingConnections(true)
        setConnectionError(null)
        const connections = await fetchMCPConnections()
        setMcpConnections(Array.isArray(connections) ? connections : [])
      } catch (error) {
        console.error('Failed to fetch MCP connections:', error)
        setConnectionError('Failed to load MCP connections. Please try again later.')
        setMcpConnections([]) 
      } finally {
        setIsLoadingConnections(false)
      }
    }
    
    loadMcpConnections()
  }, [])
  
  const handleAddTool = () => {
    if (!newToolName.trim()) return
    
    const newTool: AgentTool = {
      id: `tool-${Date.now()}`,
      name: newToolName.trim(),
      description: newToolDescription.trim(),
      enabled: true
    }
    
    const updatedTools = [...(agent.configuration.tools || []), newTool]
    updateAgent({ configuration: { ...agent.configuration, tools: updatedTools } })
    
    setNewToolName('')
    setNewToolDescription('')
    setIsAddingTool(false)
  }
  
  const handleToggleTool = (toolId: string) => {
    const updatedTools = agent.configuration.tools?.map(tool => 
      tool.id === toolId ? { ...tool, enabled: !tool.enabled } : tool
    )
    updateAgent({ configuration: { ...agent.configuration, tools: updatedTools } })
  }
  
  const handleRemoveTool = (toolId: string) => {
    const updatedTools = agent.configuration.tools?.filter(tool => tool.id !== toolId)
    updateAgent({ configuration: { ...agent.configuration, tools: updatedTools } })
  }
  
  const handleToggleMcpConnection = (connectionId: string) => {
    const currentConnections = agent.configuration.mcpConnections || []
    let updatedConnections: string[]
    
    if (currentConnections.includes(connectionId)) {
      updatedConnections = currentConnections.filter(id => id !== connectionId)
    } else {
      updatedConnections = [...currentConnections, connectionId]
    }
    
    updateAgent({ 
      configuration: { 
        ...agent.configuration, 
        mcpConnections: updatedConnections 
      } 
    })
  }
  
  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">Tools & Capabilities</h2>
        <p className="text-muted-foreground text-lg">
          Configure the tools and external capabilities your agent can use
        </p>
      </div>
      
      <Card className="border shadow-md bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Zap className="h-5 w-5" />
            Available Tools
          </CardTitle>
          <CardDescription>
            Enable tools to extend your agent's capabilities
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {agent.configuration.tools && agent.configuration.tools.length > 0 ? (
            <div className="space-y-4">
              {agent.configuration.tools.map((tool) => (
                <div 
                  key={tool.id} 
                  className={cn(
                    "flex items-start justify-between p-4 rounded-lg border",
                    tool.enabled ? "bg-primary/5 border-primary/20" : "bg-muted/20 border-muted"
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "p-1.5 rounded-md",
                      tool.enabled ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                    )}>
                      <Zap className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className={cn(
                        "font-medium",
                        tool.enabled ? "text-foreground" : "text-muted-foreground"
                      )}>
                        {tool.name}
                      </h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        {tool.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch 
                      checked={tool.enabled} 
                      onCheckedChange={() => handleToggleTool(tool.id)}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveTool(tool.id)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="bg-muted/20 p-3 rounded-full mb-3">
                <Zap className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium mb-1">No tools configured</h3>
              <p className="text-muted-foreground max-w-md mb-4">
                Add tools to extend your agent's capabilities and enable it to perform specific actions
              </p>
            </div>
          )}
          
          {isAddingTool ? (
            <Card className="border-dashed border-primary/30 bg-primary/5">
              <CardContent className="pt-6 space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="toolName" className="text-sm font-medium">Tool Name *</Label>
                  <Input
                    id="toolName"
                    placeholder="e.g., Weather API"
                    value={newToolName}
                    onChange={(e) => setNewToolName(e.target.value)}
                    className="focus-visible:ring-primary"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="toolDescription" className="text-sm font-medium">Description</Label>
                  <Textarea
                    id="toolDescription"
                    placeholder="What does this tool do?"
                    value={newToolDescription}
                    onChange={(e) => setNewToolDescription(e.target.value)}
                    className="min-h-[80px] resize-none"
                  />
                </div>
                
                <div className="flex items-center justify-end gap-2 pt-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsAddingTool(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleAddTool}
                    disabled={!newToolName.trim()}
                  >
                    Add Tool
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Button
              variant="outline"
              onClick={() => setIsAddingTool(true)}
              className="w-full flex items-center justify-center gap-2 border-dashed border-primary/30 hover:border-primary/50 hover:bg-primary/5"
            >
              <Plus className="h-4 w-4" />
              Add New Tool
            </Button>
          )}
          
          <Separator />
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Web Browsing</Label>
              <Switch 
                checked={agent.configuration.webBrowsingEnabled || false}
                onCheckedChange={(checked) => 
                  updateAgent({ configuration: { ...agent.configuration, webBrowsingEnabled: checked } })
                }
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Allow your agent to search and browse the web for information
            </p>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Code Execution</Label>
              <Switch 
                checked={agent.configuration.codeExecutionEnabled || false}
                onCheckedChange={(checked) => 
                  updateAgent({ configuration: { ...agent.configuration, codeExecutionEnabled: checked } })
                }
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Allow your agent to write and execute code to solve problems
            </p>
          </div>
          
          <Separator />
          
          {/* MCP Connections Section */}
          <div className="space-y-4">
            <div>
              <h3 className="text-base font-medium flex items-center gap-2">
                <Database className="h-4 w-4" />
                External Connections
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Select connections your agent can use to access external services and data
              </p>
            </div>
            
            {isLoadingConnections ? (
              <div className="flex justify-center py-4">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : connectionError ? (
              <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
                {connectionError}
              </div>
            ) : mcpConnections.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <div className="bg-muted/20 p-3 rounded-full mb-3">
                  <Database className="h-5 w-5 text-muted-foreground" />
                </div>
                <h4 className="text-base font-medium mb-1">No connections available</h4>
                <p className="text-sm text-muted-foreground max-w-md">
                  Your organization doesn't have any external connections configured yet
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {mcpConnections.map((connection) => (
                  <div 
                    key={connection.id}
                    className={cn(
                      "flex items-start justify-between p-3 rounded-lg border",
                      (agent.configuration.mcpConnections || []).includes(connection.id) 
                        ? "bg-primary/5 border-primary/20" 
                        : "bg-muted/10 border-muted"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className={cn(
                        "p-1.5 rounded-md",
                        (agent.configuration.mcpConnections || []).includes(connection.id)
                          ? "bg-primary/10 text-primary" 
                          : "bg-muted/20 text-muted-foreground"
                      )}>
                        {connection.server.icon ? (
                          <img 
                            src={connection.server.icon} 
                            alt={connection.server.display_name} 
                            className="h-4 w-4" 
                          />
                        ) : (
                          <Database className="h-4 w-4" />
                        )}
                      </div>
                      <div>
                        <h4 className={cn(
                          "text-sm font-medium",
                          (agent.configuration.mcpConnections || []).includes(connection.id)
                            ? "text-foreground" 
                            : "text-muted-foreground"
                        )}>
                          {connection.connection_name}
                        </h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {connection.server.display_name} • {connection.health_status}
                        </p>
                      </div>
                    </div>
                    <Switch 
                      checked={(agent.configuration.mcpConnections || []).includes(connection.id)}
                      onCheckedChange={() => handleToggleMcpConnection(connection.id)}
                      disabled={!connection.is_connected || connection.health_status === 'error'}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Testing Step Component
function TestingStep({ agent, isTesting }: {
  agent: EnhancedAgent
  isTesting: boolean
}) {
  const [testPrompt, setTestPrompt] = React.useState('')
  const [testResponses, setTestResponses] = React.useState<Array<{ role: 'user' | 'agent', content: string }>>([])
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  
  const handleSubmitTest = async () => {
    if (!testPrompt.trim() || isSubmitting) return
    
    // Add user message to the conversation
    setTestResponses(prev => [...prev, { role: 'user', content: testPrompt }])
    setIsSubmitting(true)
    
    // Simulate agent response (in a real app, this would call your API)
    setTimeout(() => {
      const agentResponse = `This is a simulated response from your agent "${agent.name}". In a real implementation, this would be generated by your agent's AI model based on its configuration and instructions.`
      setTestResponses(prev => [...prev, { role: 'agent', content: agentResponse }])
      setTestPrompt('')
      setIsSubmitting(false)
    }, 1500)
  }
  
  // Scroll to bottom of messages when new ones are added
  React.useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [testResponses])
  
  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">Test Your Agent</h2>
        <p className="text-muted-foreground text-lg">
          Try out your agent to see how it responds before deployment
        </p>
      </div>
      
      <Card className="border shadow-md bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Bot className="h-5 w-5" />
            Agent Testing Console
          </CardTitle>
          <CardDescription>
            Interact with your agent to test its responses and behavior
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="bg-muted/20 rounded-lg border p-4 min-h-[300px] max-h-[400px] overflow-y-auto flex flex-col">
            {testResponses.length > 0 ? (
              <div className="space-y-4">
                {testResponses.map((message, index) => (
                  <div 
                    key={index} 
                    className={cn(
                      "flex",
                      message.role === 'user' ? "justify-end" : "justify-start"
                    )}
                  >
                    <div className={cn(
                      "max-w-[80%] rounded-lg px-4 py-2",
                      message.role === 'user' 
                        ? "bg-primary text-primary-foreground" 
                        : "bg-muted border"
                    )}>
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="bg-muted/20 p-3 rounded-full mb-3">
                  <MessageSquare className="h-6 w-6 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-medium mb-1">No test messages yet</h3>
                <p className="text-muted-foreground max-w-md mb-4">
                  Send a message to see how your agent responds based on its current configuration
                </p>
              </div>
            )}
          </div>
          
          <div className="flex gap-2">
            <Textarea
              placeholder="Type a message to test your agent..."
              value={testPrompt}
              onChange={(e) => setTestPrompt(e.target.value)}
              className="min-h-[60px] resize-none"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmitTest()
                }
              }}
              disabled={isSubmitting}
            />
            <Button 
              onClick={handleSubmitTest} 
              disabled={!testPrompt.trim() || isSubmitting}
              className="self-end"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          
          <Separator />
          
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Test Scenarios</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                "Tell me about yourself",
                "What can you help me with?",
                "How do you handle sensitive information?",
                "What are your capabilities?"
              ].map((prompt, index) => (
                <Button 
                  key={index} 
                  variant="outline" 
                  className="justify-start h-auto py-2 px-3"
                  onClick={() => setTestPrompt(prompt)}
                  disabled={isSubmitting}
                >
                  <MessageSquare className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <span className="truncate text-left">{prompt}</span>
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Deployment Step Component
function DeploymentStep({ agent, updateAgent }: {
  agent: EnhancedAgent
  updateAgent: (updates: Partial<EnhancedAgent>) => void
}) {
  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">Deploy Your Agent</h2>
        <p className="text-muted-foreground text-lg">
          Configure deployment settings and share your agent
        </p>
      </div>
      
      <Card className="border shadow-md bg-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-primary">
            <Rocket className="h-5 w-5" />
            Deployment Settings
          </CardTitle>
          <CardDescription>
            Configure how your agent will be deployed and accessed
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Publish Agent</Label>
                <p className="text-sm text-muted-foreground">
                  Make your agent available to others
                </p>
              </div>
              <Switch 
                checked={agent.isPublished || false}
                onCheckedChange={(checked) => updateAgent({ isPublished: checked })}
              />
            </div>
            
            <Separator />
            
            <div className="space-y-2">
              <Label htmlFor="visibility" className="text-sm font-medium">Visibility</Label>
              <RadioGroup 
                defaultValue={agent.visibility || 'team'} 
                onValueChange={(value) => updateAgent({ visibility: value as 'team' | 'organization' | 'public' })}
                className="flex flex-col space-y-1"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="team" id="team" />
                  <Label htmlFor="team" className="flex items-center gap-2 cursor-pointer">
                    <Users2 className="h-4 w-4 text-muted-foreground" />
                    Team Only
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="organization" id="organization" />
                  <Label htmlFor="organization" className="flex items-center gap-2 cursor-pointer">
                    <Building className="h-4 w-4 text-muted-foreground" />
                    Organization
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="public" id="public" />
                  <Label htmlFor="public" className="flex items-center gap-2 cursor-pointer">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    Public
                  </Label>
                </div>
              </RadioGroup>
            </div>
            
            <Separator />
            
            <div className="space-y-2">
              <Label htmlFor="tags" className="text-sm font-medium">Tags</Label>
              <div className="flex flex-wrap gap-2">
                {agent.tags?.map((tag, index) => (
                  <Badge key={index} variant="secondary" className="flex items-center gap-1">
                    {tag}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        const updatedTags = [...(agent.tags || [])].filter((_, i) => i !== index)
                        updateAgent({ tags: updatedTags })
                      }}
                      className="h-4 w-4 p-0 ml-1 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
                <Input
                  placeholder="Add tag..."
                  className="w-24 h-7 text-xs"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                      const newTag = e.currentTarget.value.trim()
                      updateAgent({ tags: [...(agent.tags || []), newTag] })
                      e.currentTarget.value = ''
                    }
                  }}
                />
              </div>
            </div>
          </div>
          
          <Separator />
          
          <div className="space-y-4">
            <h3 className="text-base font-medium">Agent Summary</h3>
            <div className="bg-muted/20 rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/10 to-secondary/10 flex items-center justify-center text-white font-bold text-lg">
                  {agent.icon}
                </div>
                <div>
                  <h3 className="font-medium text-lg">{agent.name || 'Unnamed Agent'}</h3>
                  <p className="text-sm text-muted-foreground">{agent.category || 'Uncategorized'}</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Primary Role:</span>
                  <p className="text-muted-foreground">{agent.primaryRole || 'Not specified'}</p>
                </div>
                <div>
                  <span className="font-medium">Memory Type:</span>
                  <p className="text-muted-foreground">{agent.memoryType || 'Not specified'}</p>
                </div>
                <div>
                  <span className="font-medium">Tools:</span>
                  <p className="text-muted-foreground">
                    {agent.configuration.tools?.length 
                      ? `${agent.configuration.tools.length} configured` 
                      : 'None configured'}
                  </p>
                </div>
                <div>
                  <span className="font-medium">Communication Style:</span>
                  <p className="text-muted-foreground">{agent.communicationStyle || 'Not specified'}</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Agent Validation Status Component
function AgentValidationStatus({ validationErrors, showValidation }: { validationErrors: Record<string, string>, showValidation: boolean }) {
  const errorCount = Object.keys(validationErrors).length

  // If no errors or validation shouldn't be shown, return null
  if (errorCount === 0 || !showValidation) {
    return null
  }

  return (
    <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-red-700 dark:text-red-300">
          <AlertTriangle className="h-5 w-5" />
          Validation Errors ({errorCount})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {Object.entries(validationErrors).map(([field, error]) => (
          <div key={field} className="text-sm">
            <span className="font-medium capitalize">{field}: </span>
            <span className="text-red-600 dark:text-red-400">{error}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
