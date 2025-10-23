'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle,
  DialogTrigger,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Bot, Sparkles, Settings, ArrowRight } from 'lucide-react'

interface AgentBuilderSelectionDialogProps {
  workspaceId?: string
  children?: React.ReactNode
  trigger?: React.ReactNode
}

export function AgentBuilderSelectionDialog({ 
  workspaceId,
  children,
  trigger
}: AgentBuilderSelectionDialogProps) {
  const router = useRouter()
  const [open, setOpen] = React.useState(false)

  const handleNavigate = (type: 'standard' | 'smart') => {
    // Close the dialog
    setOpen(false)
    
    // Navigate to the appropriate builder with workspace context if available
    const baseUrl = type === 'standard' 
      ? '/build/agent/standard-builder' 
      : '/build/agent/smart-builder'
    
    const url = workspaceId 
      ? `${baseUrl}?workspace=${workspaceId}` 
      : baseUrl
    
    router.push(url)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || children || (
          <Button>
            Create Agent
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Choose Agent Builder Type</DialogTitle>
          <DialogDescription>
            Select the agent builder experience that best fits your needs
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
          <Card className="cursor-pointer hover:border-primary/50 transition-all" onClick={() => handleNavigate('smart')}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Smart Builder</CardTitle>
                <div className="bg-blue-100 p-2 rounded-full">
                  <Sparkles className="h-5 w-5 text-blue-600" />
                </div>
              </div>
              <CardDescription>AI-assisted agent creation</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Answer simple questions and let AI generate your agent instructions, capabilities, and configuration.
              </p>
            </CardContent>
            <CardFooter className="flex justify-between items-center border-t pt-4">
              <span className="text-xs text-muted-foreground">Recommended for beginners</span>
              <Button variant="ghost" size="sm">
                Select <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardFooter>
          </Card>
          
          <Card className="cursor-pointer hover:border-primary/50 transition-all" onClick={() => handleNavigate('standard')}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Standard Builder</CardTitle>
                <div className="bg-gray-100 p-2 rounded-full">
                  <Settings className="h-5 w-5 text-gray-600" />
                </div>
              </div>
              <CardDescription>Full control and customization</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Manually configure every aspect of your agent including instructions, tools, memory, and deployment settings.
              </p>
            </CardContent>
            <CardFooter className="flex justify-between items-center border-t pt-4">
              <span className="text-xs text-muted-foreground">For advanced users</span>
              <Button variant="ghost" size="sm">
                Select <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardFooter>
          </Card>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
