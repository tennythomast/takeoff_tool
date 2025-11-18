import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getCurrentUser, type User } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData = await getCurrentUser()
        setUser(userData)
      } catch (error) {
        toast({
          variant: 'destructive',
          title: 'Error',
          description: 'Failed to load user data',
        })
      } finally {
        setLoading(false)
      }
    }

    fetchUser()
  }, [toast])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Mobile header with sidebar trigger */}
      <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4 lg:hidden">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />
        <h1 className="text-lg font-semibold">Dashboard</h1>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6">
        <div className="mb-8">
          <h2 className="text-3xl font-bold">
            Welcome back, {user?.first_name || user?.email}!
          </h2>
          <p className="text-muted-foreground">
            Here's what's happening with your projects today.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Getting Started</CardTitle>
              <CardDescription>
                Start building your canvas-based application
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full">Create New Project</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Projects</CardTitle>
              <CardDescription>
                Your recently accessed projects
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                No projects yet. Create your first project to get started.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Documentation</CardTitle>
              <CardDescription>
                Learn how to use Takeoff Tool
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full">
                View Docs
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
