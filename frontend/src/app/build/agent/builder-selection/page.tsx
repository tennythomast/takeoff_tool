'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowRight, BrainCircuit, Settings, Zap } from 'lucide-react'

export default function BuilderSelectionPage() {
  const router = useRouter()

  return (
    <>
      <div className="max-w-5xl mx-auto py-8">
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Select Your Builder</h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Choose the builder that best fits your needs. The Smart Builder uses AI to guide you through the process,
            while the Standard Builder gives you complete control over all settings.
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Smart Builder Option */}
          <div 
            className="relative group" 
            onClick={() => router.push('/build/agent/smart-builder')}
          >
            <Card className="h-full border-2 group-hover:border-blue-500 group-hover:shadow-lg transition-all cursor-pointer overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500 opacity-10 rounded-full -mr-6 -mt-6 group-hover:opacity-20 transition-opacity"></div>
              
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <BrainCircuit className="h-6 w-6 text-blue-600" />
                    </div>
                    <CardTitle className="text-xl font-semibold">Smart Builder</CardTitle>
                  </div>
                  <div className="flex items-center gap-1 bg-blue-100 text-blue-700 text-xs font-medium px-2 py-1 rounded-full">
                    <Zap className="h-3 w-3" />
                    <span>Recommended</span>
                  </div>
                </div>
                <CardDescription className="mt-2">AI-guided agent creation for quick setup</CardDescription>
              </CardHeader>
              
              <CardContent className="pt-4">
                <p className="text-gray-600">
                  Let our AI guide you through creating an agent by answering simple questions.
                  Perfect for beginners or when you need to create an agent quickly.
                </p>
                
                <div className="mt-6 space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="mt-1 h-4 w-4 rounded-full bg-blue-100 flex items-center justify-center">
                      <div className="h-2 w-2 rounded-full bg-blue-600"></div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">Step-by-step guided process</h4>
                      <p className="text-sm text-gray-500">Answer questions and let AI handle the complexity</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3">
                    <div className="mt-1 h-4 w-4 rounded-full bg-blue-100 flex items-center justify-center">
                      <div className="h-2 w-2 rounded-full bg-blue-600"></div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">AI-generated instructions</h4>
                      <p className="text-sm text-gray-500">Automatically create optimal agent instructions</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3">
                    <div className="mt-1 h-4 w-4 rounded-full bg-blue-100 flex items-center justify-center">
                      <div className="h-2 w-2 rounded-full bg-blue-600"></div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">Quick setup</h4>
                      <p className="text-sm text-gray-500">Create powerful agents with minimal technical knowledge</p>
                    </div>
                  </div>
                </div>
              </CardContent>
              
              <CardFooter className="pt-6">
                <Button 
                  className="w-full" 
                  size="lg"
                >
                  Use Smart Builder <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          </div>

          {/* Standard Builder Option */}
          <div 
            className="relative group" 
            onClick={() => router.push('/build/agent/standard-builder')}
          >
            <Card className="h-full border-2 group-hover:border-gray-400 group-hover:shadow-lg transition-all cursor-pointer overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-gray-400 opacity-10 rounded-full -mr-6 -mt-6 group-hover:opacity-20 transition-opacity"></div>
              
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-lg">
                      <Settings className="h-6 w-6 text-gray-600" />
                    </div>
                    <CardTitle className="text-xl font-semibold">Standard Builder</CardTitle>
                  </div>
                  <div className="flex items-center gap-1 bg-gray-100 text-gray-700 text-xs font-medium px-2 py-1 rounded-full">
                    <span>Advanced</span>
                  </div>
                </div>
                <CardDescription className="mt-2">Complete control over agent configuration</CardDescription>
              </CardHeader>
              
              <CardContent className="pt-4">
                <p className="text-gray-600">
                  Full control over your agent's configuration with advanced options.
                  Ideal for experienced users who need precise customization.
                </p>
                
                <div className="mt-6 space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="mt-1 h-4 w-4 rounded-full bg-gray-100 flex items-center justify-center">
                      <div className="h-2 w-2 rounded-full bg-gray-600"></div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">Complete control</h4>
                      <p className="text-sm text-gray-500">Customize every aspect of your agent's behavior</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3">
                    <div className="mt-1 h-4 w-4 rounded-full bg-gray-100 flex items-center justify-center">
                      <div className="h-2 w-2 rounded-full bg-gray-600"></div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">Advanced tool configuration</h4>
                      <p className="text-sm text-gray-500">Fine-tune tool settings and integrations</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-3">
                    <div className="mt-1 h-4 w-4 rounded-full bg-gray-100 flex items-center justify-center">
                      <div className="h-2 w-2 rounded-full bg-gray-600"></div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">Custom instructions</h4>
                      <p className="text-sm text-gray-500">Write precise prompts and system instructions</p>
                    </div>
                  </div>
                </div>
              </CardContent>
              
              <CardFooter className="pt-6">
                <Button 
                  variant="outline" 
                  className="w-full" 
                  size="lg"
                >
                  Use Standard Builder <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          </div>
        </div>
      </div>
    </>
  )
}
