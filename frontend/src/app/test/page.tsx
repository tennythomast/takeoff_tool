import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"

export default function Page() {
  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-12 h-12 bg-clay-signal rounded-xl flex items-center justify-center animate-clay-pulse">
              <span className="text-soft-graph font-bold text-2xl">D</span>
            </div>
            <h1 className="text-4xl font-bold text-soft-graph">Dataelan AI</h1>
          </div>
          <p className="text-deep-sky text-lg">Cost Optimization Platform - Dark Theme</p>
        </div>

        {/* Color Showcase */}
        <Card className="ai-card">
          <CardHeader>
            <CardTitle className="ai-card-text">New Color Scheme</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-5 gap-4">
              <div className="text-center space-y-2">
                <div className="h-20 bg-clay-signal rounded-lg flex items-center justify-center">
                  <span className="text-soft-graph text-xs font-medium">Primary</span>
                </div>
                <p className="text-xs ai-card-secondary">Clay Signal</p>
                <p className="text-xs text-muted-foreground">Attention/CTAs</p>
              </div>
              <div className="text-center space-y-2">
                <div className="h-20 bg-obsidian rounded-lg flex items-center justify-center">
                  <span className="text-soft-graph text-xs font-medium">Brand</span>
                </div>
                <p className="text-xs ai-card-secondary">Obsidian</p>
                <p className="text-xs text-muted-foreground">Brand Blue</p>
              </div>
              <div className="text-center space-y-2">
                <div className="h-20 bg-sky-sync rounded-lg flex items-center justify-center">
                  <span className="text-clay-signal text-xs font-medium">Options</span>
                </div>
                <p className="text-xs ai-card-secondary">Sky Sync</p>
                <p className="text-xs text-muted-foreground">Accents</p>
              </div>
              <div className="text-center space-y-2">
                <div className="h-20 bg-deep-sky rounded-lg flex items-center justify-center">
                  <span className="text-soft-graph text-xs font-medium">Secondary</span>
                </div>
                <p className="text-xs ai-card-secondary">Deep Sky</p>
                <p className="text-xs text-muted-foreground">Text on Blue</p>
              </div>
              <div className="text-center space-y-2">
                <div className="h-20 bg-soft-graph rounded-lg flex items-center justify-center">
                  <span className="text-clay-signal text-xs font-medium">Primary</span>
                </div>
                <p className="text-xs ai-card-secondary">Soft Graph</p>
                <p className="text-xs text-muted-foreground">Main Text</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* UI Components Showcase */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card className="ai-card">
            <CardHeader>
              <CardTitle className="ai-card-text">Button Variations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <Button className="w-full primary-cta">Primary CTA (Clay Signal)</Button>
                <Button variant="secondary" className="w-full">Secondary Action</Button>
                <Button variant="outline" className="w-full">Outline Button</Button>
                <Button className="w-full option-button">Option Button (Sky Sync)</Button>
              </div>
            </CardContent>
          </Card>

          <Card className="ai-card">
            <CardHeader>
              <CardTitle className="ai-card-text">Cost Optimization Metrics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center space-y-2">
                  <div className="text-3xl font-bold cost-savings-highlight">67%</div>
                  <div className="text-xs ai-card-secondary">Cost Savings</div>
                </div>
                <div className="text-center space-y-2">
                  <div className="text-3xl font-bold cost-savings-highlight">$0.01</div>
                  <div className="text-xs ai-card-secondary">Per Request</div>
                </div>
                <div className="text-center space-y-2">
                  <div className="text-3xl font-bold cost-savings-highlight">20+</div>
                  <div className="text-xs ai-card-secondary">Templates</div>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm ai-card-text">Optimization Progress</span>
                  <Badge className="bg-clay-signal text-soft-graph">Active</Badge>
                </div>
                <Progress value={67} className="h-2" />
                <p className="text-xs ai-card-secondary">Routing 67% of requests to cost-optimized models</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Agent Cards Preview */}
        <Card className="ai-card">
          <CardHeader>
            <CardTitle className="ai-card-text">AI Agent Templates</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-obsidian-medium border border-sky-sync/30 rounded-lg p-4 hover:border-clay-signal transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-soft-graph">Email Classifier</h3>
                  <Badge className="bg-sky-sync text-clay-signal">67% Saved</Badge>
                </div>
                <p className="text-sm text-deep-sky mb-3">Automatically classify emails by priority and route to appropriate handlers.</p>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-deep-sky">$0.01/email</span>
                  <Button size="sm" className="bg-clay-signal text-soft-graph hover:bg-clay-signal/90">Deploy</Button>
                </div>
              </div>

              <div className="bg-obsidian-medium border border-sky-sync/30 rounded-lg p-4 hover:border-clay-signal transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-soft-graph">Jira Summarizer</h3>
                  <Badge className="bg-sky-sync text-clay-signal">85% Saved</Badge>
                </div>
                <p className="text-sm text-deep-sky mb-3">Generate concise summaries of Jira tickets and project updates.</p>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-deep-sky">$0.008/ticket</span>
                  <Button size="sm" className="bg-clay-signal text-soft-graph hover:bg-clay-signal/90">Deploy</Button>
                </div>
              </div>

              <div className="bg-obsidian-medium border border-sky-sync/30 rounded-lg p-4 hover:border-clay-signal transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-soft-graph">Content Optimizer</h3>
                  <Badge className="bg-sky-sync text-clay-signal">72% Saved</Badge>
                </div>
                <p className="text-sm text-deep-sky mb-3">Optimize content for SEO and readability with smart model routing.</p>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-deep-sky">$0.012/page</span>
                  <Button size="sm" className="bg-clay-signal text-soft-graph hover:bg-clay-signal/90">Deploy</Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}