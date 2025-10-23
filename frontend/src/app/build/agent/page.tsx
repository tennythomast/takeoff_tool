'use client'

import * as React from 'react'
import { MainLayout } from '@/components/layout/main-layout'
import { PageHeader } from '@/components/layout/page-header'
import { fetchAgents, Agent } from '@/lib/api/agent-service'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
// Using Lucide React icons instead of Radix UI
import { Plus as PlusIcon, Search as SearchIcon } from 'lucide-react'
import Link from 'next/link'

export default function AgentsPage() {
  const [agents, setAgents] = React.useState<Agent[]>([])
  const [isLoading, setIsLoading] = React.useState(true)
  const [searchTerm, setSearchTerm] = React.useState('')
  
  React.useEffect(() => {
    const loadAgents = async () => {
      setIsLoading(true)
      try {
        const result = await fetchAgents({ search: searchTerm })
        setAgents(result.agents)
      } catch (error) {
        console.error('Error loading agents:', error)
      } finally {
        setIsLoading(false)
      }
    }
    
    loadAgents()
  }, [searchTerm])

  return (
    <MainLayout>
      <div className="container mx-auto py-6 space-y-8 max-w-6xl">
        <PageHeader title="AI Agents">
          <div className="flex items-center gap-2">
            <div className="relative w-64">
              <SearchIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search agents..."
                className="pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div>
              <Button asChild>
                <Link href="/agents/builder-selection">
                  <PlusIcon className="mr-2 h-4 w-4" /> Create Agent
                </Link>
              </Button>
            </div>
          </div>
        </PageHeader>
        
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="opacity-70">
                <CardHeader className="animate-pulse bg-muted h-24" />
                <CardContent className="h-32 animate-pulse">
                  <div className="h-4 w-3/4 bg-muted rounded mb-4" />
                  <div className="h-4 w-1/2 bg-muted rounded mb-4" />
                  <div className="h-4 w-5/6 bg-muted rounded" />
                </CardContent>
                <CardFooter className="animate-pulse bg-muted h-12" />
              </Card>
            ))}
          </div>
        ) : (
          <>
            {agents.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {agents.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} />
                ))}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <div className="space-y-4">
                  <h3 className="text-xl font-medium">No agents found</h3>
                  <p className="text-muted-foreground">
                    {searchTerm ? 'Try a different search term or ' : ''}
                    create your first AI agent to get started.
                  </p>
                  <div className="flex justify-center mt-4">
                    <Button asChild>
                      <Link href="/agents/builder-selection">
                        <PlusIcon className="mr-2 h-4 w-4" /> Create Agent
                      </Link>
                    </Button>
                  </div>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </MainLayout>
  )
}

function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Card className="overflow-hidden transition-all hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-xl">
            {agent.icon || '🤖'}
          </div>
          <div>
            <CardTitle className="text-lg">{agent.name}</CardTitle>
            {agent.category && (
              <Badge variant="outline" className="text-xs">
                {agent.category}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-3">
          {agent.description}
        </CardDescription>
        {agent.capabilities?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {agent.capabilities.slice(0, 3).map((capability: string) => (
              <Badge key={capability} variant="secondary" className="text-xs">
                {capability}
              </Badge>
            ))}
            {agent.capabilities.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{agent.capabilities.length - 3} more
              </Badge>
            )}
          </div>
        )}
      </CardContent>
      <CardFooter className="border-t bg-muted/50 flex justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/agents/${agent.id}`}>View Details</Link>
        </Button>
        <Button variant="outline" size="sm" asChild>
          <Link href={`/agents/${agent.id}/chat`}>Chat</Link>
        </Button>
      </CardFooter>
    </Card>
  )
}
