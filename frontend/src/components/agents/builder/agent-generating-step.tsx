'use client'

import * as React from 'react'
import { AlertCircleIcon, Loader2Icon, RefreshCwIcon, SparklesIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface AgentGeneratingStepProps {
  onRetry?: () => void;
  error?: boolean;
}

export function AgentGeneratingStep({ onRetry, error = false }: AgentGeneratingStepProps) {
  const [loadingText, setLoadingText] = React.useState('Analyzing your requirements...')
  
  // Cycle through different loading messages to make the experience more engaging
  React.useEffect(() => {
    if (error) return; // Don't cycle messages if in error state
    
    const messages = [
      'Analyzing your requirements...',
      'Determining optimal capabilities...',
      'Crafting custom instructions...',
      'Configuring agent settings...',
      'Optimizing for your use case...',
      'Almost ready...',
    ]
    
    let currentIndex = 0
    const interval = setInterval(() => {
      currentIndex = (currentIndex + 1) % messages.length
      setLoadingText(messages[currentIndex])
    }, 2000)
    
    return () => clearInterval(interval)
  }, [error])
  
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="relative">
          <div className="absolute -inset-1 rounded-full opacity-70 blur-sm bg-red-500 animate-pulse" />
          <div className="relative bg-background rounded-full p-6">
            <AlertCircleIcon className="h-12 w-12 text-red-500" />
          </div>
        </div>
        
        <h2 className="text-2xl font-semibold mt-6">Generation Failed</h2>
        
        <div className="max-w-md text-center mt-4 text-muted-foreground">
          <p>
            We encountered an issue while generating your smart agent. This could be due to a temporary service disruption or an issue with the input parameters.
          </p>
        </div>
        
        <Button 
          onClick={onRetry} 
          className="mt-6 bg-blue-600 hover:bg-blue-700"
        >
          <RefreshCwIcon className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    )
  }
  
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative">
        <div className="absolute -inset-1 rounded-full opacity-70 blur-sm bg-gradient-to-r from-primary to-indigo-500 animate-pulse" />
        <div className="relative bg-background rounded-full p-6">
          <SparklesIcon className="h-12 w-12 text-primary animate-pulse" />
        </div>
      </div>
      
      <h2 className="text-2xl font-semibold mt-6">Generating Your Smart Agent</h2>
      
      <div className="flex items-center gap-2 mt-4">
        <Loader2Icon className="h-5 w-5 animate-spin text-muted-foreground" />
        <p className="text-muted-foreground">{loadingText}</p>
      </div>
      
      <div className="max-w-md text-center mt-8 text-sm text-muted-foreground">
        <p>
          We're using AI to generate the optimal configuration for your agent based on your answers.
          This includes custom instructions, capabilities, and settings tailored to your needs.
        </p>
      </div>
    </div>
  )
}
