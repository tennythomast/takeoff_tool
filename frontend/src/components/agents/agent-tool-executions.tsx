"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { AgentToolExecution } from "./types"
import AgentService from "@/services/agent-service"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Code, Webhook, Globe, CheckCircle, XCircle, Clock } from "lucide-react"

interface AgentToolExecutionsProps {
  executionId: string;
}

export function AgentToolExecutions({ executionId }: AgentToolExecutionsProps) {
  const [toolExecutions, setToolExecutions] = useState<AgentToolExecution[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchToolExecutions = async () => {
      try {
        setLoading(true);
        const data = await AgentService.toolExecutions.getToolExecutions(executionId);
        setToolExecutions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
        console.error('Error fetching tool executions:', err);
      } finally {
        setLoading(false);
      }
    };

    if (executionId) {
      fetchToolExecutions();
    }
  }, [executionId]);

  // Get icon for tool type
  const getToolTypeIcon = (type: string) => {
    switch (type) {
      case "WEBHOOK": return <Webhook className="h-4 w-4" />;
      case "API": return <Globe className="h-4 w-4" />;
      case "FUNCTION": return <Code className="h-4 w-4" />;
      default: return <Code className="h-4 w-4" />;
    }
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "SUCCESS": return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "FAILED": return <XCircle className="h-4 w-4 text-red-500" />;
      case "PENDING": return <Clock className="h-4 w-4 text-yellow-500" />;
      default: return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case "SUCCESS": return "bg-green-100 text-green-800";
      case "FAILED": return "bg-red-100 text-red-800";
      case "PENDING": return "bg-yellow-100 text-yellow-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  // Format JSON for display
  const formatJson = (json: any) => {
    try {
      return JSON.stringify(json, null, 2);
    } catch (e) {
      return String(json);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 rounded-full border-t-transparent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border border-red-200 bg-red-50 rounded-md text-red-700">
        <p>Error loading tool executions: {error}</p>
      </div>
    );
  }

  if (toolExecutions.length === 0) {
    return (
      <div className="p-4 border border-gray-200 bg-gray-50 rounded-md text-gray-500 text-center">
        <p>No tool executions found for this agent run.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium">Tool Executions</h3>
      
      <div className="space-y-4">
        {toolExecutions.map((execution) => (
          <Card key={execution.id} className="overflow-hidden">
            <CardHeader className="py-4 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getToolTypeIcon(execution.tool_type)}
                  <CardTitle className="text-base">{execution.tool_name}</CardTitle>
                </div>
                <Badge className={getStatusColor(execution.status)}>
                  <div className="flex items-center gap-1">
                    {getStatusIcon(execution.status)}
                    <span>{execution.status_display}</span>
                  </div>
                </Badge>
              </div>
              <CardDescription>
                Execution time: {execution.execution_time.toFixed(2)}ms • {new Date(execution.created_at).toLocaleString()}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="pt-4">
              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="input">
                  <AccordionTrigger className="text-sm font-medium">
                    Input Data
                  </AccordionTrigger>
                  <AccordionContent>
                    <pre className="bg-gray-50 p-4 rounded-md overflow-x-auto text-xs font-mono">
                      {formatJson(execution.input_data)}
                    </pre>
                  </AccordionContent>
                </AccordionItem>
                
                <AccordionItem value="output">
                  <AccordionTrigger className="text-sm font-medium">
                    Output Data
                  </AccordionTrigger>
                  <AccordionContent>
                    <pre className="bg-gray-50 p-4 rounded-md overflow-x-auto text-xs font-mono">
                      {formatJson(execution.output_data)}
                    </pre>
                  </AccordionContent>
                </AccordionItem>
                
                {execution.error_message && (
                  <AccordionItem value="error">
                    <AccordionTrigger className="text-sm font-medium text-red-600">
                      Error Message
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="bg-red-50 p-4 rounded-md text-red-700 text-xs font-mono whitespace-pre-wrap">
                        {execution.error_message}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )}
              </Accordion>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
