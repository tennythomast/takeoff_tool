import React from 'react';
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, Zap, Activity, Play, Edit3 } from "lucide-react";

export interface WorkflowData {
  id: string;
  name: string;
  description: string;
  status: 'ACTIVE' | 'DRAFT' | 'ERROR' | 'PAUSED';
  agentCount: number;
  avgResponseTime: string;
  executionCount: number;
  health: number;
  lastRun?: string;
  nextTrigger?: string;
}

export interface WorkflowCardProps {
  workflow: WorkflowData;
  onAction: (action: string, id: string) => void;
}

export function WorkflowCard({ workflow, onAction }: WorkflowCardProps) {
  const isActive = workflow.status === 'ACTIVE';
  const isDraft = workflow.status === 'DRAFT';
  
  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-white">
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-medium text-lg">{workflow.name}</h3>
        <Badge variant="outline" className={`${isActive ? 'bg-green-50 text-green-700 border-green-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
          {workflow.status}
        </Badge>
      </div>
      <p className="text-gray-600 mb-4">{workflow.description}</p>
      
      <div className="flex items-center gap-5 mb-5">
        <div className="flex items-center">
          <Users className="h-4 w-4 text-blue-500 mr-2" />
          <span>{workflow.agentCount} agents</span>
        </div>
        {isActive && (
          <>
            <div className="flex items-center">
              <Zap className="h-4 w-4 text-amber-500 mr-2" />
              <span>{workflow.avgResponseTime}</span>
            </div>
            <div className="flex items-center">
              <Activity className="h-4 w-4 text-purple-500 mr-2" />
              <span>{workflow.executionCount} runs</span>
            </div>
            <div className="flex items-center">
              <div className="w-4 h-4 rounded-full bg-green-500 mr-2"></div>
              <span>{workflow.health}%</span>
            </div>
          </>
        )}
        {isDraft && (
          <div className="flex items-center">
            <div className="w-4 h-4 rounded-full bg-yellow-500 mr-2"></div>
            <span>Testing</span>
          </div>
        )}
      </div>
      
      <div className="flex gap-2">
        {isActive ? (
          <>
            <Button 
              size="sm"
              className="bg-blue-500 hover:bg-blue-600"
              onClick={() => onAction('run', workflow.id)}
            >
              <Play className="h-4 w-4 mr-2" /> Run
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => onAction('edit', workflow.id)}
            >
              <Edit3 className="h-4 w-4 mr-2" /> Edit
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => onAction('logs', workflow.id)}
            >
              <Activity className="h-4 w-4 mr-2" /> Logs
            </Button>
          </>
        ) : (
          <>
            <Button 
              size="sm"
              className="bg-blue-500 hover:bg-blue-600"
              onClick={() => onAction('run', workflow.id)}
            >
              <Play className="h-4 w-4 mr-2" /> Test
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => onAction('edit', workflow.id)}
            >
              <Edit3 className="h-4 w-4 mr-2" /> Setup
            </Button>
          </>
        )}
      </div>
      
      <div className="text-xs text-gray-500 mt-4">
        Last run: {workflow.lastRun || 'Never'} • Next: {workflow.nextTrigger || 'Not scheduled'}
      </div>
    </div>
  );
}

export default WorkflowCard;
