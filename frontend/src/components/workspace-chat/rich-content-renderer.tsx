"use client";

import React from "react";
import { RichContent } from "@/context/workspace-chat-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { 
  Zap, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  DollarSign, 
  TrendingDown, 
  TrendingUp,
  FileText,
  Wrench
} from "lucide-react";

interface RichContentRendererProps {
  content: RichContent[];
}

export function RichContentRenderer({ content }: RichContentRendererProps) {
  return (
    <div className="space-y-4">
      {content.map((item, index) => (
        <div key={index} className="mt-2">
          {renderContentByType(item)}
        </div>
      ))}
    </div>
  );
}

function renderContentByType(content: RichContent) {
  switch (content.type) {
    case "cost-analysis":
      return <CostAnalysis data={content.data} />;
    case "agent-card":
      return <AgentCard data={content.data} />;
    case "workflow-visualization":
      return <WorkflowVisualization data={content.data} />;
    case "file-preview":
      return <FilePreview data={content.data} />;
    case "tool-usage":
      return <ToolUsage data={content.data} />;
    default:
      return null;
  }
}

// Cost Analysis Component
function CostAnalysis({ data }: { data: any }) {
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center">
          <DollarSign className="h-4 w-4 mr-2 text-blue-600" />
          Cost Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="breakdown">
          <TabsList className="mb-4">
            <TabsTrigger value="breakdown">Breakdown</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="savings">Savings</TabsTrigger>
          </TabsList>
          
          <TabsContent value="breakdown" className="space-y-4">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data?.costBreakdown || [
                      { name: 'Agent 1', value: 400 },
                      { name: 'Agent 2', value: 300 },
                      { name: 'Workflow 1', value: 200 },
                      { name: 'Workflow 2', value: 100 }
                    ]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  >
                    {data?.costBreakdown?.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    )) || []}
                  </Pie>
                  <Tooltip formatter={(value) => `$${value}`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            <div className="text-sm text-gray-500">
              <div className="flex justify-between mb-1">
                <span>Total Monthly Cost:</span>
                <span className="font-medium text-gray-900">${data?.totalCost || "42.50"}</span>
              </div>
              <div className="flex justify-between">
                <span>Average Cost per Execution:</span>
                <span className="font-medium text-gray-900">${data?.avgCostPerExecution || "0.13"}</span>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="trends">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={data?.costTrends || [
                    { date: 'Week 1', cost: 24 },
                    { date: 'Week 2', cost: 13 },
                    { date: 'Week 3', cost: 38 },
                    { date: 'Week 4', cost: 42 }
                  ]}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip formatter={(value) => `$${value}`} />
                  <Legend />
                  <Line type="monotone" dataKey="cost" stroke="#8884d8" activeDot={{ r: 8 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>
          
          <TabsContent value="savings" className="space-y-4">
            <div className="flex items-center justify-between bg-green-50 p-3 rounded-lg">
              <div className="flex items-center">
                <TrendingDown className="h-5 w-5 text-green-600 mr-2" />
                <div>
                  <div className="font-medium">Potential Monthly Savings</div>
                  <div className="text-sm text-gray-500">By implementing recommendations</div>
                </div>
              </div>
              <div className="text-xl font-bold text-green-600">${data?.potentialSavings || "18.75"}</div>
            </div>
            
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Recommendations:</h4>
              <ul className="space-y-2">
                <li className="bg-white p-2 rounded border border-gray-200">
                  <div className="font-medium">Switch Agent 1 to Mixtral</div>
                  <div className="text-sm text-gray-500">Save $12.50/month</div>
                  <Button size="sm" variant="outline" className="mt-1">Apply</Button>
                </li>
                <li className="bg-white p-2 rounded border border-gray-200">
                  <div className="font-medium">Optimize Workflow 2 Prompts</div>
                  <div className="text-sm text-gray-500">Save $6.25/month</div>
                  <Button size="sm" variant="outline" className="mt-1">View Details</Button>
                </li>
              </ul>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// Agent Card Component
function AgentCard({ data }: { data: any }) {
  const agent = data || {
    name: "Email Classifier",
    status: "active",
    model: "gpt-4",
    successRate: 94,
    avgExecutionTime: 1.2,
    costPerRun: 0.08,
    executionCount: 156
  };
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-base">{agent.name}</CardTitle>
          <Badge variant={agent.status === "active" ? "default" : "secondary"}>
            {agent.status === "active" ? "Active" : "Inactive"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex flex-col">
            <span className="text-gray-500">Model</span>
            <span className="font-medium">{agent.model}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-gray-500">Executions</span>
            <span className="font-medium">{agent.executionCount}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-gray-500">Success Rate</span>
            <div className="flex items-center">
              <span className="font-medium">{agent.successRate}%</span>
              <Progress value={agent.successRate} className="h-1 w-12 ml-2" />
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-gray-500">Cost per Run</span>
            <span className="font-medium">${agent.costPerRun}</span>
          </div>
        </div>
        
        <div className="flex space-x-2">
          <Button size="sm" variant="outline" className="flex-1">
            <Zap className="h-3 w-3 mr-1" />
            Optimize
          </Button>
          <Button size="sm" variant="outline" className="flex-1">
            View Details
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Workflow Visualization Component
function WorkflowVisualization({ data }: { data: any }) {
  const workflow = data || {
    name: "Customer Support Workflow",
    steps: [
      { name: "Email Classification", status: "success", time: 1.2 },
      { name: "Sentiment Analysis", status: "success", time: 0.8 },
      { name: "Response Generation", status: "warning", time: 3.5 },
      { name: "Quality Check", status: "success", time: 0.5 }
    ],
    successRate: 86,
    avgExecutionTime: 6.0,
    bottleneck: "Response Generation"
  };
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{workflow.name}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          {workflow.steps.map((step: any, index: number) => (
            <div key={index} className="flex items-center">
              <div className="mr-2">
                {step.status === "success" && <CheckCircle className="h-4 w-4 text-green-500" />}
                {step.status === "warning" && <AlertCircle className="h-4 w-4 text-amber-500" />}
                {step.status === "error" && <AlertCircle className="h-4 w-4 text-red-500" />}
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium">{step.name}</div>
                <Progress 
                  value={100} 
                  className={`h-1 ${
                    step.status === "success" ? "bg-green-100" : 
                    step.status === "warning" ? "bg-amber-100" : "bg-red-100"
                  }`}
                />
              </div>
              <div className="ml-2 flex items-center text-xs text-gray-500">
                <Clock className="h-3 w-3 mr-1" />
                {step.time}s
              </div>
            </div>
          ))}
        </div>
        
        <div className="bg-amber-50 p-2 rounded-md text-sm">
          <div className="font-medium text-amber-800">Bottleneck Detected</div>
          <div className="text-amber-700">
            {workflow.bottleneck} is taking {workflow.steps.find((s: any) => s.name === workflow.bottleneck)?.time}s on average.
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex flex-col">
            <span className="text-gray-500">Success Rate</span>
            <div className="flex items-center">
              <span className="font-medium">{workflow.successRate}%</span>
              <Progress value={workflow.successRate} className="h-1 w-12 ml-2" />
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-gray-500">Avg. Execution Time</span>
            <span className="font-medium">{workflow.avgExecutionTime}s</span>
          </div>
        </div>
        
        <Button size="sm" variant="outline" className="w-full">
          Optimize Workflow
        </Button>
      </CardContent>
    </Card>
  );
}

// File Preview Component
function FilePreview({ data }: { data: any }) {
  const file = data || {
    name: "training_data.csv",
    type: "csv",
    size: "2.4 MB",
    lastModified: "2025-07-15",
    preview: "id,email,category\n1,support@example.com,inquiry\n2,sales@acme.com,lead\n3,help@company.org,complaint"
  };
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-base flex items-center">
            <FileText className="h-4 w-4 mr-2 text-blue-600" />
            {file.name}
          </CardTitle>
          <Badge variant="outline">{file.type}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex justify-between text-xs text-gray-500">
          <span>{file.size}</span>
          <span>Modified: {file.lastModified}</span>
        </div>
        
        <div className="bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs overflow-x-auto">
          {file.preview}
        </div>
        
        <Button size="sm" variant="outline" className="w-full">
          Open File
        </Button>
      </CardContent>
    </Card>
  );
}

// Tool Usage Component
function ToolUsage({ data }: { data: any }) {
  const toolData = data || {
    name: "Text Extractor",
    usageCount: 87,
    successRate: 92,
    integrations: ["Email Classifier", "Document Processor"],
    lastUsed: "2 hours ago"
  };
  
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center">
          <Wrench className="h-4 w-4 mr-2 text-blue-600" />
          {toolData.name}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex flex-col">
            <span className="text-gray-500">Usage Count</span>
            <span className="font-medium">{toolData.usageCount}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-gray-500">Success Rate</span>
            <div className="flex items-center">
              <span className="font-medium">{toolData.successRate}%</span>
              <Progress value={toolData.successRate} className="h-1 w-12 ml-2" />
            </div>
          </div>
        </div>
        
        <div className="text-sm">
          <div className="text-gray-500 mb-1">Integrated with:</div>
          <div className="flex flex-wrap gap-1">
            {toolData.integrations.map((integration: string, index: number) => (
              <Badge key={index} variant="outline">{integration}</Badge>
            ))}
          </div>
        </div>
        
        <div className="text-xs text-gray-500">
          Last used: {toolData.lastUsed}
        </div>
      </CardContent>
    </Card>
  );
}
