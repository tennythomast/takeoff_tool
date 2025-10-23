import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Plus, TrendingUp, Bot, Zap } from "lucide-react"

export default function DashboardPage() {
  return (
    <div className="space-y-6">


      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="bg-[#C87C6D] text-white border-0">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cost Savings</CardTitle>
            <TrendingUp className="h-4 w-4 text-white" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">67%</div>
            <p className="text-xs text-white/70">
              vs direct API usage
            </p>
          </CardContent>
        </Card>

        <Card className="bg-[#98C0D9] text-[#192026] border-0">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Bot className="h-4 w-4 text-[#192026]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-[#192026]/70">
              +2 from last week
            </p>
          </CardContent>
        </Card>

        <Card className="bg-white border">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-[#192026]">Active Customers</CardTitle>
            <Zap className="h-4 w-4 text-[#3D5B81]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#192026]">33%</div>
            <p className="text-xs text-[#192026]/70">
              of total customer base
            </p>
          </CardContent>
        </Card>

        <Card className="bg-[#3D5B81] text-white border-0">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Churn Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-white" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2%</div>
            <p className="text-xs text-white/70">
              -0.5% from last month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Agents</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-[#A76052]/20 rounded-lg flex items-center justify-center">
                  <Bot className="h-4 w-4 text-[#A76052]" />
                </div>
                <div>
                  <p className="font-medium">Email Classifier</p>
                  <p className="text-sm text-muted-foreground">67% cost savings</p>
                </div>
              </div>
              <Badge variant="outline" className="text-[#A76052] border-[#A76052]">
                Active
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-[#98C0D9]/20 rounded-lg flex items-center justify-center">
                  <Bot className="h-4 w-4 text-[#98C0D9]" />
                </div>
                <div>
                  <p className="font-medium">Jira Summarizer</p>
                  <p className="text-sm text-muted-foreground">85% cost savings</p>
                </div>
              </div>
              <Badge variant="outline" className="text-[#98C0D9] border-[#98C0D9]">
                Active
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-[#3D5B81]/20 rounded-lg flex items-center justify-center">
                  <Bot className="h-4 w-4 text-[#3D5B81]" />
                </div>
                <div>
                  <p className="font-medium">Content Optimizer</p>
                  <p className="text-sm text-muted-foreground">72% cost savings</p>
                </div>
              </div>
              <Badge variant="secondary">
                Testing
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button variant="outline" className="w-full justify-start gap-3">
              <Plus className="h-4 w-4" />
              Create New Agent
            </Button>
            <Button variant="outline" className="w-full justify-start gap-3">
              <Bot className="h-4 w-4" />
              Browse Templates
            </Button>
            <Button variant="outline" className="w-full justify-start gap-3">
              <TrendingUp className="h-4 w-4" />
              View Cost Analytics
            </Button>
            <Button variant="outline" className="w-full justify-start gap-3">
              <Zap className="h-4 w-4" />
              Build Workflow
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}