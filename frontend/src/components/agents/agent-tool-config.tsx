"use client"

import * as React from "react"
import { useState } from "react"
import { 
  AgentTool, 
  ToolType, 
  WebhookMethod, 
  WebhookAuthType 
} from "./types"
import { 
  Plus, 
  Trash2, 
  Save,
  AlertCircle,
  Code,
  Globe,
  Webhook
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"

interface AgentToolConfigProps {
  tools: AgentTool[];
  onToolsChange: (tools: AgentTool[]) => void;
}

export function AgentToolConfig({ tools = [], onToolsChange }: AgentToolConfigProps) {
  const [editingTool, setEditingTool] = useState<AgentTool | null>(null);
  const [isAddingTool, setIsAddingTool] = useState(false);

  // Create a new empty tool
  const createEmptyTool = (): AgentTool => ({
    id: `temp-${Date.now()}`,
    name: "",
    description: "",
    tool_type: "WEBHOOK",
    is_required: false,
    webhook_method: "GET",
    webhook_auth_type: "NONE",
    webhook_headers: {},
    webhook_auth_config: {},
    input_schema: {},
    output_schema: {}
  });

  // Start adding a new tool
  const handleAddTool = () => {
    setEditingTool(createEmptyTool());
    setIsAddingTool(true);
  };

  // Edit an existing tool
  const handleEditTool = (tool: AgentTool) => {
    setEditingTool({ ...tool });
    setIsAddingTool(false);
  };

  // Delete a tool
  const handleDeleteTool = (toolId: string) => {
    const updatedTools = tools.filter(tool => tool.id !== toolId);
    onToolsChange(updatedTools);
  };

  // Save tool changes
  const handleSaveTool = () => {
    if (!editingTool) return;
    
    let updatedTools: AgentTool[];
    
    if (isAddingTool) {
      // Add new tool
      updatedTools = [...tools, editingTool];
    } else {
      // Update existing tool
      updatedTools = tools.map(tool => 
        tool.id === editingTool.id ? editingTool : tool
      );
    }
    
    onToolsChange(updatedTools);
    setEditingTool(null);
  };

  // Cancel editing
  const handleCancelEdit = () => {
    setEditingTool(null);
  };

  // Update tool field
  const updateToolField = (field: string, value: any) => {
    if (!editingTool) return;
    setEditingTool({
      ...editingTool,
      [field]: value
    });
  };

  // Get icon for tool type
  const getToolTypeIcon = (type: ToolType) => {
    switch (type) {
      case "WEBHOOK": return <Webhook className="h-4 w-4" />;
      case "API": return <Globe className="h-4 w-4" />;
      case "FUNCTION": return <Code className="h-4 w-4" />;
      default: return <AlertCircle className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Agent Tools</h3>
        <Button onClick={handleAddTool} size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Add Tool
        </Button>
      </div>

      {/* Tool List */}
      {tools.length === 0 ? (
        <div className="text-center py-8 border border-dashed rounded-lg">
          <p className="text-gray-500">No tools configured yet</p>
          <Button onClick={handleAddTool} variant="outline" className="mt-4">
            <Plus className="h-4 w-4 mr-2" />
            Add Your First Tool
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {tools.map(tool => (
            <Card key={tool.id}>
              <CardHeader className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getToolTypeIcon(tool.tool_type)}
                    <CardTitle className="text-base">{tool.name}</CardTitle>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleEditTool(tool)}
                    >
                      Edit
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => handleDeleteTool(tool.id)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
                <CardDescription>{tool.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Type:</span> {tool.tool_type}
                  </div>
                  <div>
                    <span className="font-medium">Required:</span> {tool.is_required ? "Yes" : "No"}
                  </div>
                  {tool.tool_type === "WEBHOOK" && (
                    <>
                      <div className="col-span-2">
                        <span className="font-medium">URL:</span> {tool.webhook_url}
                      </div>
                      <div>
                        <span className="font-medium">Method:</span> {tool.webhook_method}
                      </div>
                      <div>
                        <span className="font-medium">Auth:</span> {tool.webhook_auth_type}
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Tool Edit Modal */}
      {editingTool && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-lg font-medium mb-4">
                {isAddingTool ? "Add New Tool" : "Edit Tool"}
              </h3>
              
              <div className="space-y-4">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="tool-name">Name</Label>
                    <Input 
                      id="tool-name"
                      value={editingTool.name} 
                      onChange={(e) => updateToolField("name", e.target.value)}
                      placeholder="Tool name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="tool-type">Type</Label>
                    <Select 
                      value={editingTool.tool_type}
                      onValueChange={(value) => updateToolField("tool_type", value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select tool type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="WEBHOOK">Webhook</SelectItem>
                        <SelectItem value="API">API</SelectItem>
                        <SelectItem value="FUNCTION">Function</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="tool-description">Description</Label>
                  <Textarea 
                    id="tool-description"
                    value={editingTool.description} 
                    onChange={(e) => updateToolField("description", e.target.value)}
                    placeholder="Describe what this tool does"
                    rows={2}
                  />
                </div>
                
                <div className="flex items-center space-x-2">
                  <Switch 
                    id="tool-required"
                    checked={editingTool.is_required}
                    onCheckedChange={(checked) => updateToolField("is_required", checked)}
                  />
                  <Label htmlFor="tool-required">Required</Label>
                </div>
                
                {/* Tool Type Specific Configuration */}
                <Tabs defaultValue="config" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="config">Configuration</TabsTrigger>
                    <TabsTrigger value="input">Input Schema</TabsTrigger>
                    <TabsTrigger value="output">Output Schema</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="config" className="space-y-4 pt-4">
                    {editingTool.tool_type === "WEBHOOK" && (
                      <>
                        <div className="space-y-2">
                          <Label htmlFor="webhook-url">Webhook URL</Label>
                          <Input 
                            id="webhook-url"
                            value={editingTool.webhook_url || ""} 
                            onChange={(e) => updateToolField("webhook_url", e.target.value)}
                            placeholder="https://api.example.com/webhook"
                          />
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label htmlFor="webhook-method">HTTP Method</Label>
                            <Select 
                              value={editingTool.webhook_method || "GET"}
                              onValueChange={(value) => updateToolField("webhook_method", value)}
                            >
                              <SelectTrigger id="webhook-method">
                                <SelectValue placeholder="Select method" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="GET">GET</SelectItem>
                                <SelectItem value="POST">POST</SelectItem>
                                <SelectItem value="PUT">PUT</SelectItem>
                                <SelectItem value="DELETE">DELETE</SelectItem>
                                <SelectItem value="PATCH">PATCH</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          
                          <div className="space-y-2">
                            <Label htmlFor="webhook-auth">Authentication</Label>
                            <Select 
                              value={editingTool.webhook_auth_type || "NONE"}
                              onValueChange={(value) => updateToolField("webhook_auth_type", value as WebhookAuthType)}
                            >
                              <SelectTrigger id="webhook-auth">
                                <SelectValue placeholder="Select auth type" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="NONE">None</SelectItem>
                                <SelectItem value="BASIC">Basic Auth</SelectItem>
                                <SelectItem value="BEARER">Bearer Token</SelectItem>
                                <SelectItem value="API_KEY">API Key</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        
                        {/* Auth Configuration */}
                        {editingTool.webhook_auth_type === "BASIC" && (
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label htmlFor="auth-username">Username</Label>
                              <Input 
                                id="auth-username"
                                value={editingTool.webhook_auth_config?.username || ""} 
                                onChange={(e) => updateToolField("webhook_auth_config", {
                                  ...editingTool.webhook_auth_config,
                                  username: e.target.value
                                })}
                                placeholder="Username"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label htmlFor="auth-password">Password</Label>
                              <Input 
                                id="auth-password"
                                type="password"
                                value={editingTool.webhook_auth_config?.password || ""} 
                                onChange={(e) => updateToolField("webhook_auth_config", {
                                  ...editingTool.webhook_auth_config,
                                  password: e.target.value
                                })}
                                placeholder="Password"
                              />
                            </div>
                          </div>
                        )}
                        
                        {editingTool.webhook_auth_type === "BEARER" && (
                          <div className="space-y-2">
                            <Label htmlFor="auth-token">Bearer Token</Label>
                            <Input 
                              id="auth-token"
                              value={editingTool.webhook_auth_config?.token || ""} 
                              onChange={(e) => updateToolField("webhook_auth_config", {
                                ...editingTool.webhook_auth_config,
                                token: e.target.value
                              })}
                              placeholder="Bearer token"
                            />
                          </div>
                        )}
                        
                        {editingTool.webhook_auth_type === "API_KEY" && (
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label htmlFor="api-key-name">Key Name</Label>
                              <Input 
                                id="api-key-name"
                                value={editingTool.webhook_auth_config?.key_name || ""} 
                                onChange={(e) => updateToolField("webhook_auth_config", {
                                  ...editingTool.webhook_auth_config,
                                  key_name: e.target.value
                                })}
                                placeholder="API key name"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label htmlFor="api-key-value">Key Value</Label>
                              <Input 
                                id="api-key-value"
                                value={editingTool.webhook_auth_config?.key_value || ""} 
                                onChange={(e) => updateToolField("webhook_auth_config", {
                                  ...editingTool.webhook_auth_config,
                                  key_value: e.target.value
                                })}
                                placeholder="API key value"
                              />
                            </div>
                            <div className="space-y-2 col-span-2">
                              <Label htmlFor="api-key-location">Key Location</Label>
                              <Select 
                                value={editingTool.webhook_auth_config?.key_location || "header"}
                                onValueChange={(value) => updateToolField("webhook_auth_config", {
                                  ...editingTool.webhook_auth_config,
                                  key_location: value
                                })}
                              >
                                <SelectTrigger id="api-key-location">
                                  <SelectValue placeholder="Select location" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="header">Header</SelectItem>
                                  <SelectItem value="query">Query Parameter</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          </div>
                        )}
                        
                        {/* Headers */}
                        <Accordion type="single" collapsible className="w-full">
                          <AccordionItem value="headers">
                            <AccordionTrigger>Custom Headers</AccordionTrigger>
                            <AccordionContent>
                              <div className="space-y-2">
                                <Label htmlFor="headers">Headers (JSON)</Label>
                                <Textarea 
                                  id="headers"
                                  value={JSON.stringify(editingTool.webhook_headers || {}, null, 2)} 
                                  onChange={(e) => {
                                    try {
                                      const headers = JSON.parse(e.target.value);
                                      updateToolField("webhook_headers", headers);
                                    } catch (error) {
                                      // Handle invalid JSON
                                    }
                                  }}
                                  placeholder='{"Content-Type": "application/json"}'
                                  rows={4}
                                />
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        </Accordion>
                      </>
                    )}
                    
                    {editingTool.tool_type === "FUNCTION" && (
                      <div className="space-y-2">
                        <Label htmlFor="function-code">Function Code</Label>
                        <Textarea 
                          id="function-code"
                          value={editingTool.config?.code || ""} 
                          onChange={(e) => updateToolField("config", {
                            ...editingTool.config,
                            code: e.target.value
                          })}
                          placeholder="def execute(input_data):\n    # Your code here\n    return {'result': 'success'}"
                          rows={8}
                          className="font-mono"
                        />
                      </div>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="input" className="space-y-4 pt-4">
                    <div className="space-y-2">
                      <Label htmlFor="input-schema">Input Schema (JSON Schema)</Label>
                      <Textarea 
                        id="input-schema"
                        value={JSON.stringify(editingTool.input_schema || {}, null, 2)} 
                        onChange={(e) => {
                          try {
                            const schema = JSON.parse(e.target.value);
                            updateToolField("input_schema", schema);
                          } catch (error) {
                            // Handle invalid JSON
                          }
                        }}
                        placeholder='{"type": "object", "properties": {"query": {"type": "string"}}}'
                        rows={8}
                        className="font-mono"
                      />
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="output" className="space-y-4 pt-4">
                    <div className="space-y-2">
                      <Label htmlFor="output-schema">Output Schema (JSON Schema)</Label>
                      <Textarea 
                        id="output-schema"
                        value={JSON.stringify(editingTool.output_schema || {}, null, 2)} 
                        onChange={(e) => {
                          try {
                            const schema = JSON.parse(e.target.value);
                            updateToolField("output_schema", schema);
                          } catch (error) {
                            // Handle invalid JSON
                          }
                        }}
                        placeholder='{"type": "object", "properties": {"result": {"type": "string"}}}'
                        rows={8}
                        className="font-mono"
                      />
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
              
              <div className="flex justify-end gap-2 mt-6">
                <Button variant="outline" onClick={handleCancelEdit}>
                  Cancel
                </Button>
                <Button onClick={handleSaveTool}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Tool
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
