'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { 
  Agent, 
  AgentConfiguration, 
  createAgent, 
  getDefaultAgentConfiguration,
  generateAgentInstructions,
  AgentGenerationRequest,
  AgentGenerationResponse
} from '@/lib/api/agent-service'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { toast } from '@/components/ui/use-toast'
// Import agent builder components
import { 
  AgentQuestionStep, 
  AgentGeneratingStep, 
  AgentSmartPreview 
} from './'
import { Loader2Icon } from 'lucide-react'



// Define the question flow steps
type QuestionStep = 
  | 'role'
  | 'problem'
  | 'users'
  | 'style'
  | 'capabilities'
  | 'generating'
  | 'preview'

// Define the answers that will be collected
interface AgentAnswers {
  name: string
  icon: string
  primaryRole: string
  problemStatement: string
  targetUsers: string[]
  communicationStyle: string
  outputFormat: string
  qualityPreference: number
  capabilities: string[]
}

// Helper function to map role to appropriate category
const mapRoleToCategory = (role: string): string => {
  // First check for exact matches with standard categories
  const roleToCategory: Record<string, string> = {
    'Customer Support': 'Customer Support',
    'Data Analyst': 'Data Analysis',
    'Researcher': 'Research',
    'Content Creator': 'Content Creation',
    'Personal Assistant': 'Productivity',
    'Developer': 'Development',
    'Teacher': 'Education',
    // Legacy mappings
    'ASSISTANT': 'Productivity',
    'ANALYZER': 'Data Analysis',
    'CLASSIFIER': 'Organization',
    'GENERATOR': 'Content Creation',
    'MONITOR': 'Monitoring'
  };
  
  if (roleToCategory[role]) {
    return roleToCategory[role];
  }
  
  // If no exact match, try to find a category based on keywords
  const lowerRole = role.toLowerCase();
  if (lowerRole.includes('support') || lowerRole.includes('service')) {
    return 'Customer Support';
  } else if (lowerRole.includes('data') || lowerRole.includes('analy')) {
    return 'Data Analysis';
  } else if (lowerRole.includes('research') || lowerRole.includes('study')) {
    return 'Research';
  } else if (lowerRole.includes('content') || lowerRole.includes('writ') || lowerRole.includes('creat')) {
    return 'Content Creation';
  } else if (lowerRole.includes('develop') || lowerRole.includes('code') || lowerRole.includes('program')) {
    return 'Development';
  } else if (lowerRole.includes('teach') || lowerRole.includes('learn') || lowerRole.includes('educat')) {
    return 'Education';
  }
  
  // Default fallback
  return 'Other';
}

interface SmartAgentBuilderFlowProps {
  workspaceId?: string | null;
}

export function SmartAgentBuilderFlow({ workspaceId }: SmartAgentBuilderFlowProps) {
  const router = useRouter()
  const [currentStep, setCurrentStep] = React.useState<QuestionStep>('role')
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [generationError, setGenerationError] = React.useState(false)
  const [generatedAgent, setGeneratedAgent] = React.useState<Agent | null>(null)
  
  // Initialize answers with defaults
  const [answers, setAnswers] = React.useState<AgentAnswers>({
    name: '',
    icon: '🤖',
    primaryRole: 'ASSISTANT',
    problemStatement: '',
    targetUsers: [],
    communicationStyle: 'PROFESSIONAL',
    outputFormat: 'MARKDOWN',
    qualityPreference: 2,
    capabilities: [],
  })

  // Define the steps for the question flow
  const steps: { id: QuestionStep; label: string }[] = [
    { id: 'role', label: 'Define Role' },
    { id: 'problem', label: 'Problem Statement' },
    { id: 'users', label: 'Target Users' },
    { id: 'style', label: 'Communication Style' },
    { id: 'capabilities', label: 'Capabilities' },
    { id: 'generating', label: 'Generating' },
    { id: 'preview', label: 'Review & Create' },
  ]

  const currentStepIndex = steps.findIndex((step) => step.id === currentStep)
  const progress = ((currentStepIndex + 1) / (steps.length - 1)) * 100 // Exclude generating step from progress

  // Update answers
  const updateAnswers = (updates: Partial<AgentAnswers>) => {
    setAnswers((prev) => ({ ...prev, ...updates }))
  }

  // Handle next step
  const handleNext = () => {
    // Validate the current step
    const isValid = validateStep()
    
    if (!isValid) {
      // Show validation errors
      validationErrors.forEach(error => {
        toast({
          title: 'Validation Error',
          description: error,
          variant: 'destructive',
        })
      })
      return
    }
    
    const currentIndex = steps.findIndex((step) => step.id === currentStep)
    if (currentIndex < steps.length - 1) {
      // Clear any previous validation errors
      setValidationErrors([])
      
      // If moving to the generating step, trigger the agent generation
      if (steps[currentIndex + 1].id === 'generating') {
        generateAgent()
      } else {
        setCurrentStep(steps[currentIndex + 1].id)
      }
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  // Handle back step
  const handleBack = () => {
    const currentIndex = steps.findIndex((step) => step.id === currentStep)
    if (currentIndex > 0) {
      // Skip the generating step when going back
      const prevStep = currentIndex === 6 ? 'capabilities' : steps[currentIndex - 1].id
      setCurrentStep(prevStep)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  // Generate agent configuration and instructions
  const generateAgent = async () => {
    console.log('=== AGENT GENERATION DEBUG START ===');
    console.log('Starting agent generation process...');
    console.log('Current answers:', JSON.stringify(answers, null, 2));
    
    setCurrentStep('generating')
    setGenerationError(false)
    
    try {
      // Import the agent instruction service
      const { agentInstructionService, ModelRoutingRule } = await import('@/lib/services/agent-instruction-service');
      
      // Determine the appropriate routing rule based on quality preference
      let routingRule = ModelRoutingRule.BALANCED;
      if (answers.qualityPreference === 3) {
        routingRule = ModelRoutingRule.QUALITY;
      } else if (answers.qualityPreference === 1) {
        routingRule = ModelRoutingRule.SPEED;
      }
      
      // Prepare the enhanced request payload
      const enhancedRequest = {
        name: answers.name,
        primaryRole: answers.primaryRole,
        problemStatement: answers.problemStatement,
        targetUsers: answers.targetUsers,
        communicationStyle: answers.communicationStyle,
        outputFormat: answers.outputFormat,
        qualityPreference: answers.qualityPreference,
        capabilities: answers.capabilities,
        routingRule,
        additionalContext: `This agent is being created through the Smart Agent Builder flow. The user wants an agent that specializes in ${answers.primaryRole} and can help with ${answers.problemStatement}.`
      };
      
      console.log('=== REQUEST PAYLOAD ===');
      console.log('Sending enhanced request:', JSON.stringify(enhancedRequest, null, 2));
      
      // Call the instruction service to generate instructions and configuration
      const generationResponse = await agentInstructionService.generateInstructions(enhancedRequest);
      
      console.log('=== API RESPONSE ===');
      console.log('Received generation response:', JSON.stringify(generationResponse, null, 2));
      
      // Handle different generation methods and show appropriate user feedback
      if (generationResponse.metadata?.is_emergency_fallback) {
        toast({
          title: 'Agent Created with Minimal Setup',
          description: 'Service temporarily unavailable. You can enhance instructions manually.',
          variant: 'default',
        });
      } else if (generationResponse.metadata?.is_fallback || generationResponse.generation_method === 'basic_fallback') {
        toast({
          title: 'Agent Created with Basic Instructions',
          description: generationResponse.metadata?.enhancement_suggestion || 'AI-generated instructions available when services are restored',
          variant: 'default',
        });
      } else if (generationResponse.generation_method === 'alternative_llm') {
        toast({
          title: 'Agent Created Successfully',
          description: generationResponse.metadata?.note || 'Using alternative AI service',
          variant: 'default'
        });
      } else if (generationResponse.generation_method === 'smart_template') {
        toast({
          title: 'Agent Created with Smart Template',
          description: 'Template-based instructions generated. Can be enhanced with AI when available.',
          variant: 'default'
        });
      } else {
        // Primary LLM success
        toast({
          title: 'Agent Created Successfully',
          description: 'AI-generated instructions ready',
          variant: 'default'
        });
      }
      
      // Create a base agent with the collected answers
      const baseConfig = getDefaultAgentConfiguration()
      
      console.log('=== BASE CONFIG ===');
      console.log('Base configuration:', JSON.stringify(baseConfig, null, 2));
      
      // Map API-suggested tools to the agent configuration (with fallback)
      const suggestedTools = generationResponse.suggestedConfiguration?.tools || [];
      const enabledTools = baseConfig.tools.map(tool => {
        const shouldEnable = suggestedTools.includes(tool.id);
        console.log(`Tool ${tool.id}: ${shouldEnable ? 'ENABLED' : 'disabled'}`);
        return { ...tool, enabled: shouldEnable };
      });
      
      // Use API-suggested memory settings or fall back to defaults
      const memoryConfig = {
        ...baseConfig.memory,
        ...(generationResponse.suggestedConfiguration?.memory || {}),
        enabled: true, // Always enable memory
      };
      
      // Use API-suggested response style or fall back to defaults
      const responseStyle = {
        ...baseConfig.responseStyle,
        ...(generationResponse.suggestedConfiguration?.responseStyle || {}),
      };
      
      // Use the AI-generated instructions from the API
      const generatedInstructions = generationResponse.instructions;
      
      console.log('=== GENERATED INSTRUCTIONS ===');
      console.log('Instructions length:', generatedInstructions.length);
      console.log('Instructions preview:', generatedInstructions.substring(0, 200) + '...');
      console.log('Generation method:', generationResponse.generation_method);
      console.log('Quality score:', generationResponse.quality_score);
      
      // Create agent object with the API-generated configuration
      const agent = {
        id: `temp-${Date.now()}`, // Temporary ID for preview
        name: answers.name || 'New Agent',
        description: answers.problemStatement || `An AI assistant that specializes in ${answers.primaryRole}`,
        icon: answers.icon || '🤖',
        category: mapRoleToCategory(answers.primaryRole),
        capabilities: answers.capabilities,
        isActive: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        configuration: {
          ...baseConfig,
          tools: enabledTools,
          memory: memoryConfig,
          responseStyle: responseStyle,
          customInstructions: generatedInstructions,
          instructions: generatedInstructions, // Both fields for compatibility
          
          // Add generation metadata for user awareness and enhancement options
          generationMethod: generationResponse.generation_method,
          generationQuality: generationResponse.quality_score,
          canEnhance: generationResponse.can_enhance,
          generationMetadata: generationResponse.metadata,
          
          // Additional fields for the preview component
          description: answers.problemStatement,
          role: answers.primaryRole,
          communicationStyle: answers.communicationStyle,
          hasMemory: true,
          hasWebSearch: answers.capabilities.includes('Web Browsing'),
          hasFileUpload: answers.capabilities.includes('File Analysis'),
          temperature: 0.7
        }
      }
      
      console.log('=== FINAL AGENT OBJECT ===');
      console.log('Final agent configuration:', JSON.stringify(agent, null, 2));
      
      console.log('=== SETTING STATE ===');
      setGeneratedAgent(agent as any)
      
      console.log('=== MOVING TO PREVIEW ===');
      setCurrentStep('preview')
      
      console.log('=== AGENT GENERATION DEBUG END ===');
      
    } catch (error: unknown) {
      console.error('=== ERROR IN AGENT GENERATION ===');
      console.error('Error generating agent:', error);
      
      // Extract error message for user display
      let errorMessage = 'There was a problem generating your agent. Please try again.';
      let errorDetails = '';
      
      if (error instanceof Error) {
        console.error('Error type:', error.constructor.name);
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
        
        errorMessage = 'Error generating agent';
        errorDetails = error.message;
        
        // Check for specific error types
        if (error.message.includes('404') || error.message.includes('not found')) {
          console.log('=== HANDLING 404 ERROR ===');
          
          // Create a fallback agent for 404 errors
          const fallbackAgent = createFallbackAgent('basic_fallback');
          setGeneratedAgent(fallbackAgent as any);
          setCurrentStep('preview');
          
          toast({
            title: 'Agent Created with Basic Instructions',
            description: 'AI service unavailable. Created with template instructions.',
          });
          return;
          
        } else if (error.message.includes('Failed to fetch') || error.message.includes('Network')) {
          errorMessage = 'Network error';
          errorDetails = 'Could not connect to the agent instruction service. Check your connection.';
        } else if (error.message.includes('JSON')) {
          console.log('=== HANDLING JSON PARSE ERROR ===');
          
          // Create a fallback agent for JSON errors
          const fallbackAgent = createFallbackAgent('smart_template');
          setGeneratedAgent(fallbackAgent as any);
          setCurrentStep('preview');
          
          toast({
            title: 'Agent Created with Template Instructions',
            description: 'Service response error. Created with template instructions.',
          });
          return;
        }
      }
      
      console.log('=== LOGGING ERROR STATE ===');
      console.log('Current step when error occurred:', currentStep);
      console.log('Current answers state:', JSON.stringify(answers, null, 2));
      
      toast({
        title: errorMessage,
        description: errorDetails || 'There was a problem generating your agent. Please try again.',
        variant: 'destructive',
      })
      
      setGenerationError(true)
    }
  }
  
  // Add this helper function to create a fallback agent when API fails
  const createFallbackAgent = (fallbackType: 'basic_fallback' | 'smart_template' | 'emergency_fallback' = 'basic_fallback') => {
    console.log('=== CREATING FALLBACK AGENT ===');
    console.log('Fallback type:', fallbackType);
    
    const baseConfig = getDefaultAgentConfiguration();
    
    let fallbackInstructions = '';
    let generationMethod: 'basic_fallback' | 'smart_template' | 'emergency_fallback' = fallbackType;
    let qualityScore: 'basic' | 'medium' | 'minimal' = 'basic';
    let enhancementSuggestion = 'Upgrade to AI-generated instructions for better performance';
    
    // Create different quality levels of fallback instructions
    switch (fallbackType) {
      case 'smart_template':
        qualityScore = 'medium';
        enhancementSuggestion = 'AI-generated instructions available when services are restored';
        fallbackInstructions = `# ${answers.name} - ${answers.primaryRole} Assistant
  
  You are an AI assistant specialized in ${answers.primaryRole.toLowerCase()}, designed to help ${answers.targetUsers.join(', ')} with ${answers.problemStatement}.
  
  ## Core Identity & Purpose
  - **Name**: ${answers.name}
  - **Role**: ${answers.primaryRole}
  - **Mission**: ${answers.problemStatement}
  - **Target Users**: ${answers.targetUsers.join(', ')}
  
  ## Communication Guidelines
  - Maintain a ${answers.communicationStyle.toLowerCase()} tone in all interactions
  - Format responses in ${answers.outputFormat.toLowerCase()} format
  - Adapt your communication style to match user expertise levels
  - Be clear, helpful, and professional
  
  ## Capabilities & Tools
  ${answers.capabilities.map(cap => `- **${cap}**: Utilize this capability effectively to solve user problems and provide comprehensive assistance`).join('\n')}
  
  ## Operational Guidelines
  - Always strive for accuracy and helpfulness in your responses
  - When uncertain, acknowledge limitations and offer alternative approaches
  - Ask clarifying questions when user intent is unclear
  - Provide step-by-step guidance for complex tasks
  - Stay focused on your specialized role and domain expertise
  
  ## Quality Standards
  - Ensure all responses are relevant to the user's specific needs
  - Maintain consistency in your communication style and approach
  - Provide actionable advice and solutions when possible
  - Follow up to ensure user understanding and satisfaction
  
  ## Context Awareness
  Your users are ${answers.targetUsers.join(', ')}. Consider their likely background, expertise level, and specific needs when crafting responses. Always aim to provide maximum value within your defined role and capabilities.`;
        break;
        
      case 'emergency_fallback':
        generationMethod = 'emergency_fallback';
        qualityScore = 'minimal';
        enhancementSuggestion = 'AI services are temporarily unavailable. Manual enhancement recommended';
        fallbackInstructions = `You are ${answers.name}, an AI assistant for ${answers.primaryRole}.
  
  Your task: ${answers.problemStatement}
  
  Users: ${answers.targetUsers.join(', ')}
  Style: ${answers.communicationStyle}
  Format: ${answers.outputFormat}
  
  Capabilities: ${answers.capabilities.join(', ')}
  
  Be helpful and stay within your role.`;
        break;
        
      default: // basic_fallback
        fallbackInstructions = `# ${answers.name} - ${answers.primaryRole}
  
  You are ${answers.name}, an AI assistant specialized in ${answers.primaryRole}. 
  
  ## Primary Task
  Your primary task is to ${answers.problemStatement}
  
  ## Communication Guidelines
  - Communicate in a ${answers.communicationStyle.toLowerCase()} manner
  - Your target users are: ${answers.targetUsers.join(', ')}
  - Format your responses in ${answers.outputFormat.toLowerCase()}
  
  ## Your Capabilities
  ${answers.capabilities.map(cap => `- ${cap}`).join('\n')}
  
  ## Guidelines
  - Always be helpful and accurate in your responses
  - If you're unsure about something, say so clearly
  - Stay focused on your role as a ${answers.primaryRole}
  - Provide step-by-step guidance when appropriate
  - Ask clarifying questions when needed
  
  Always maintain a helpful attitude while acknowledging any limitations in your knowledge or capabilities.`;
    }
  
    const fallbackAgent = {
      id: `temp-${Date.now()}`,
      name: answers.name || 'New Agent',
      description: answers.problemStatement || `An AI assistant that specializes in ${answers.primaryRole}`,
      icon: answers.icon || '🤖',
      category: mapRoleToCategory(answers.primaryRole),
      capabilities: answers.capabilities,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      configuration: {
        ...baseConfig,
        customInstructions: fallbackInstructions,
        instructions: fallbackInstructions,
        
        // Generation metadata
        generationMethod: generationMethod,
        generationQuality: qualityScore,
        canEnhance: true,
        generationMetadata: {
          is_fallback: true,
          enhancement_suggestion: enhancementSuggestion,
          template_used: `local_${fallbackType}`,
          character_count: fallbackInstructions.length,
          created_reason: 'API service unavailable'
        },
        
        // Additional fields for preview component
        description: answers.problemStatement,
        role: answers.primaryRole,
        communicationStyle: answers.communicationStyle,
        hasMemory: true,
        hasWebSearch: answers.capabilities.includes('Web Browsing'),
        hasFileUpload: answers.capabilities.includes('File Analysis'),
        temperature: 0.7,
        
        tools: baseConfig.tools.map(tool => ({
          ...tool,
          enabled: answers.capabilities.some(cap => 
            tool.name.toLowerCase().includes(cap.toLowerCase()) ||
            cap.toLowerCase().includes(tool.name.toLowerCase())
          )
        })),
        memory: {
          ...baseConfig.memory,
          enabled: true,
        }
      }
    };
    
    console.log('Fallback agent created:', JSON.stringify(fallbackAgent, null, 2));
    return fallbackAgent;
  };
  // Handle final submission
  const handleSubmit = async () => {
    if (!generatedAgent) {
      console.error('Cannot submit: generatedAgent is null');
      return;
    }
    
    console.log('Submitting agent for creation:', generatedAgent.name);
    setIsSubmitting(true);
    
    try {
      // Extract the instructions from the configuration
      const instructions = generatedAgent.configuration.customInstructions || 
        (generatedAgent.configuration as any).instructions || 
        '';
      
      // Create a capabilities object from the array
      const capabilitiesObj: Record<string, boolean> = {};
      if (generatedAgent.capabilities && Array.isArray(generatedAgent.capabilities)) {
        generatedAgent.capabilities.forEach(cap => {
          if (typeof cap === 'string') {
            capabilitiesObj[cap.toLowerCase().replace(/ /g, '_')] = true;
          }
        });
      }
      
      // Ensure we have at least one capability
      if (Object.keys(capabilitiesObj).length === 0) {
        capabilitiesObj.text_generation = true;
      }
      
      // Map the frontend agent structure to the backend expected structure
      // Using type assertion to bypass TypeScript errors since we know the API expects this structure
      
      // Map frontend categories to valid backend categories
      const categoryMap: Record<string, string> = {
        'Customer Support': 'CUSTOMER_SERVICE',
        'Data Analysis': 'ANALYSIS',
        'Research': 'RESEARCH',
        'Content Creation': 'GENERAL', // No direct match, map to GENERAL
        'Productivity': 'PRODUCTIVITY', // This is a valid backend category
        'Development': 'DEVELOPMENT',
        'Education': 'GENERAL', // No direct match, map to GENERAL
        'Other': 'GENERAL'
      };
      
      const backendAgentData: any = {
        // Required fields
        name: generatedAgent.name || 'Untitled Agent',
        description: generatedAgent.description || 'No description provided',
        instructions: instructions || 'No instructions provided',
        category: categoryMap[generatedAgent.category] || 'GENERAL', // Use mapped category
        status: 'DRAFT',
        icon: generatedAgent.icon || 'robot',
        
        // Smart configuration fields
        primary_role: answers?.primaryRole || 'ASSISTANT',
        target_users: answers?.targetUsers || [],
        problem_statement: answers?.problemStatement || '',
        communication_style: answers?.communicationStyle || 'PROFESSIONAL',
        output_format: answers?.outputFormat || 'MARKDOWN',
        quality_preference: answers?.qualityPreference || 2,
        
        // Capability settings - convert to object with string keys and boolean values
        capabilities: capabilitiesObj,
        capability_level: 'BASIC',
        
        // Memory settings
        memory_type: 'SHORT_TERM',
        memory_window: 10,
        memory_config: {},
        
        // Additional settings
        is_public: false,
        is_template: false,
        project: null, // Project field can be null as it's nullable in the backend model
        // The organization will be set by the backend based on the authenticated user
        // We don't need to send it in the payload
        config: {
          generationMethod: generatedAgent.configuration?.generationMethod || 'manual',
          generationQuality: generatedAgent.configuration?.generationQuality || 'standard',
          canEnhance: generatedAgent.configuration?.canEnhance || false,
          generationMetadata: generatedAgent.configuration?.generationMetadata || {}
        },
        
        // Empty arrays for related objects if not provided
        parameters: [],
      };
      
      // Ensure the capabilities object has the correct format
      // The backend expects a dictionary with string keys and boolean values
      if (Object.keys(capabilitiesObj).length === 0) {
        backendAgentData.capabilities = { text_generation: true };
      }
      
      // Ensure tools is properly formatted
      if (!backendAgentData.tools || !Array.isArray(backendAgentData.tools) || backendAgentData.tools.length === 0) {
        backendAgentData.tools = [];
      }
      
      // Make sure each tool has the required fields
      backendAgentData.tools = backendAgentData.tools.map((tool: any) => ({
        name: tool.name || '',
        description: tool.description || '',
        enabled: tool.enabled === true,
        config: tool.config || {}
      }));
      
      // Ensure parameters is an array
      if (!backendAgentData.parameters || !Array.isArray(backendAgentData.parameters)) {
        backendAgentData.parameters = [];
      }
      
      // Add tools if they exist
      if (generatedAgent.configuration?.tools && Array.isArray(generatedAgent.configuration.tools)) {
        backendAgentData.tools = generatedAgent.configuration.tools
          .filter(tool => tool.enabled)
          .map(tool => ({
            name: tool.name || 'Unnamed Tool',
            description: tool.description || '',
            tool_type: 'FUNCTION',
            is_required: false,
            config: tool.config || {}
          }));
      } else {
        backendAgentData.tools = [];
      }
      
      // Add workspace ID if available
      if (workspaceId) {
        console.log('Adding workspace ID to agent:', workspaceId);
        backendAgentData.workspace = workspaceId;
      }
      
      // Log the payload for debugging
      console.log('Final backend agent data payload:', JSON.stringify(backendAgentData, null, 2));
      
      try {
        // Make the API call to create the agent
        const result = await createAgent(backendAgentData as any);
        console.log('Create agent API response:', result);
        
        if (result && result.id) {
          // Success - show toast and navigate
          toast({
            title: 'Agent created successfully',
            description: `${generatedAgent.name} has been created and is ready to use.`,
            variant: 'default',
          });
          
          // Ensure we have the ID before navigation
          console.log('Navigating to agent detail page:', `/agents/${result.id}`);
          
          // Use a slight delay to ensure toast is visible before navigation
          setTimeout(() => {
            router.push(`/agents/${result.id}`);
          }, 500);
        } else {
          // We got a response but no ID
          console.error('API returned success but no agent ID was found:', result);
          throw new Error('Failed to create agent: No ID returned');
        }
      } catch (apiError: any) {
        console.error('API error during agent creation:', apiError);
        
        // Try to extract validation errors from the error message
        const errorMessage = apiError?.message || '';
        if (errorMessage.includes('API error')) {
          try {
            // Extract the JSON part from the error message
            const jsonStart = errorMessage.indexOf('{');
            if (jsonStart > -1) {
              const jsonPart = errorMessage.substring(jsonStart);
              const errorData = JSON.parse(jsonPart);
              console.error('Parsed validation errors:', errorData);
              
              // Format validation errors for display
              const formattedErrors = Object.entries(errorData)
                .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
                .join('\n');
              
              toast({
                title: 'Validation errors',
                description: formattedErrors,
                variant: 'destructive',
              });
              throw apiError; // Re-throw to be caught by the outer catch block
            }
          } catch (parseError) {
            console.error('Error parsing validation errors:', parseError);
            // Fall through to the generic error message
          }
        }
        
        // If we couldn't extract specific validation errors, show a generic message
        toast({
          title: 'Error creating agent',
          description: apiError?.message || 'An unknown error occurred',
          variant: 'destructive',
        });
        throw apiError; // Re-throw to be caught by the outer catch block
      }
    } catch (error: unknown) {
      console.error('Error creating agent:', error);
      
      // Log detailed error information if available
      if (error instanceof Error) {
        console.error('Error details:', error.message);
        console.error('Error stack:', error.stack);
        
        // Try to extract more detailed error information from the response
        if ((error as any).response) {
          const responseData = (error as any).response.data;
          console.error('API Error Response:', responseData);
          
          // If we have detailed validation errors, show them in the toast
          if (responseData && typeof responseData === 'object') {
            const errorDetails = Object.entries(responseData)
              .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
              .join('\n');
            
            if (errorDetails) {
              toast({
                title: 'Error creating agent',
                description: `Validation errors:\n${errorDetails}`,
                variant: 'destructive',
              });
              setIsSubmitting(false);
              return;
            }
          }
        }
      }
      
      toast({
        title: 'Error creating agent',
        description: 'There was a problem creating your agent. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  // Validation for each step with error messages
  const [validationErrors, setValidationErrors] = React.useState<string[]>([])
  
  const validateStep = () => {
    const errors: string[] = []
    
    switch (currentStep) {
      case 'role':
        if (answers.name.trim() === '') {
          errors.push('Please provide a name for your agent')
        }
        if (answers.primaryRole === '') {
          errors.push('Please select a primary role for your agent')
        }
        break
      case 'problem':
        if (answers.problemStatement.trim() === '') {
          errors.push('Please describe the problem your agent will solve')
        } else if (answers.problemStatement.trim().length < 20) {
          errors.push('Please provide a more detailed problem statement (at least 20 characters)')
        }
        break
      case 'users':
        if (answers.targetUsers.length === 0) {
          errors.push('Please select at least one target user type')
        }
        break
      case 'style':
        // Always valid as we have defaults
        break
      case 'capabilities':
        if (answers.capabilities.length === 0) {
          errors.push('Please select at least one capability for your agent')
        }
        break
    }
    
    setValidationErrors(errors)
    return errors.length === 0
  }
  
  // Check if current step is valid
  const isStepValid = () => {
    switch (currentStep) {
      case 'role':
        return answers.name.trim() !== '' && answers.primaryRole !== ''
      case 'problem':
        return answers.problemStatement.trim() !== '' && answers.problemStatement.trim().length >= 20
      case 'users':
        return answers.targetUsers.length > 0
      case 'style':
        return true // Always valid as we have defaults
      case 'capabilities':
        return answers.capabilities.length > 0
      default:
        return true
    }
  }

  // Render the current step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 'role':
        return (
          <AgentQuestionStep
            title="What's your agent's primary role?"
            description="Define what your agent will do and give it a name."
            answers={answers}
            updateAnswers={updateAnswers}
            questionType="role"
          />
        )
      case 'problem':
        return (
          <AgentQuestionStep
            title="What problem does your agent solve?"
            description="Describe the specific problem or task your agent will help with."
            answers={answers}
            updateAnswers={updateAnswers}
            questionType="problem"
          />
        )
      case 'users':
        return (
          <AgentQuestionStep
            title="Who will use this agent?"
            description="Select the types of users who will interact with your agent."
            answers={answers}
            updateAnswers={updateAnswers}
            questionType="users"
          />
        )
      case 'style':
        return (
          <AgentQuestionStep
            title="How should your agent communicate?"
            description="Choose the communication style and output format for your agent."
            answers={answers}
            updateAnswers={updateAnswers}
            questionType="style"
          />
        )
      case 'capabilities':
        return (
          <AgentQuestionStep
            title="What capabilities should your agent have?"
            description="Select the capabilities your agent needs to solve the problem."
            answers={answers}
            updateAnswers={updateAnswers}
            questionType="capabilities"
          />
        )
      case 'generating':
        return <AgentGeneratingStep error={generationError} onRetry={generateAgent} />
      case 'preview':
        console.log('=== PREVIEW STEP DEBUG ===');
        console.log('generatedAgent:', generatedAgent);
        console.log('generatedAgent exists:', !!generatedAgent);
        
        if (generatedAgent) {
          console.log('Agent name:', generatedAgent.name);
          console.log('Agent description:', generatedAgent.description);
          console.log('Agent configuration:', generatedAgent.configuration);
          console.log('Generation method:', generatedAgent.configuration?.generationMethod);
          console.log('Generation quality:', generatedAgent.configuration?.generationQuality);
          console.log('Can enhance:', generatedAgent.configuration?.canEnhance);
        }
        
        return generatedAgent ? (
          <AgentSmartPreview 
            agent={generatedAgent as any} 
            onUpdate={(updatedAgent) => {
              console.log('Agent updated in preview:', updatedAgent);
              setGeneratedAgent(updatedAgent as any);
            }} 
          />
        ) : (
          <div className="text-center py-8">
            <p>No agent generated. Please try again.</p>
            <Button onClick={() => setCurrentStep('capabilities')} className="mt-4">
              Go Back
            </Button>
          </div>
        );
      default:
        return null
    }
  }

  // Render navigation buttons
  const renderButtons = () => {
    const isFirstStep = currentStep === 'role'
    const isGeneratingStep = currentStep === 'generating'
    const isPreviewStep = currentStep === 'preview'

    // Show Try Standard Builder button when there's an error in the generating step
    if (isGeneratingStep && generationError) {
      return (
        <div className="flex justify-center">
          <Button
            variant="outline"
            onClick={() => router.push('/build/agent/standard-builder')}
            className="min-w-[180px]"
          >
            Try Standard Builder
          </Button>
        </div>
      )
    }
    
    if (isGeneratingStep) return null

    return (
      <div className="flex justify-between items-center">
        {/* Left side - Back button */}
        <div>
          {!isFirstStep ? (
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={isSubmitting}
              className="min-w-[100px]"
            >
              Back
            </Button>
          ) : (
            <div className="min-w-[100px]">
              {/* Spacer when no back button */}
            </div>
          )}
        </div>
        
        {/* Right side - Cancel and Continue/Create buttons */}
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => router.push('/agents')}
            disabled={isSubmitting}
            className="min-w-[100px]"
          >
            Cancel
          </Button>
          {!isPreviewStep ? (
            <Button 
              onClick={handleNext} 
              disabled={!isStepValid() || isSubmitting}
              className="min-w-[120px] bg-blue-600 hover:bg-blue-700"
            >
              Continue
            </Button>
          ) : (
            <Button 
              onClick={handleSubmit} 
              disabled={isSubmitting}
              className="min-w-[140px] bg-blue-600 hover:bg-blue-700"
            >
              {isSubmitting ? (
                <>
                  <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : 'Create Agent'}
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="h-full p-6">
      <div className="flex flex-col h-full max-h-[calc(100vh-120px)] bg-white border rounded-lg shadow-sm">
        {/* Progress indicator - Fixed at top */}
        <div className="p-6 pb-2 border-b">
          <div className="flex justify-between items-center mb-2">
            <h2 className="text-lg font-semibold">
              {currentStep !== 'generating' && steps[currentStepIndex].label}
            </h2>
            <span className="text-sm text-muted-foreground">
              Step {currentStepIndex + 1} of {steps.length - 1}
            </span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
        
        {/* Step content - Scrollable */}
        <div className="p-6 overflow-y-auto flex-1">
          {renderStepContent()}
          
          {/* Validation errors */}
          {validationErrors.length > 0 && (
            <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-md mt-4">
              <h4 className="font-medium mb-1">Please fix the following issues:</h4>
              <ul className="list-disc list-inside space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index} className="text-sm">{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        
        {/* Navigation buttons - Fixed at bottom */}
        <div className="p-4 border-t bg-gray-50 rounded-b-lg">
          {renderButtons()}
        </div>
      </div>
    </div>
  )
}
