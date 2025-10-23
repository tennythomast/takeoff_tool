import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function TestShadcn() {
  return (
    <div className="p-8 space-y-4">
      {/* Tailwind test */}
      <div className="bg-red-500 text-white p-4 rounded">
        ✅ Tailwind Test - This should be RED
      </div>
      
      {/* ShadCN Components test */}
      <Card>
        <CardHeader>
          <CardTitle>ShadCN Test</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="test">Test Label</Label>
            <Input id="test" placeholder="Test input" />
          </div>
          <Button>Test Button</Button>
          <Button variant="outline">Outline Button</Button>
        </CardContent>
      </Card>
    </div>
  )
}