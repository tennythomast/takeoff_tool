'use client'

import React, { useState } from 'react';
import { Agent, AgentConfiguration, AgentMemorySettings, AgentResponseStyle } from '@/lib/api/agent-service';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { toast } from '@/components/ui/use-toast';
import { 
  Edit, 
  Info, 
  MessageSquare, 
  Settings, 
  AlertTriangle as ExclamationTriangleIcon, 
  Info as InformationCircleIcon, 
  Loader2 
} from 'lucide-react';

// Extended interface to include generation metadata
interface ExtendedAgentConfiguration extends AgentConfiguration {
  memory: AgentMemorySettings & {
    relevanceThreshold: number;
  };
  responseStyle: AgentResponseStyle & {
    creativity: number;
  };
  description: string;
  role: string;
  communicationStyle: string;
  instructions: string;
  hasMemory: boolean;
  hasWebSearch: boolean;
  hasFileUpload: boolean;
  temperature: number;
  // Generation metadata fields
  generationMethod?: 'primary_llm' | 'alternative_llm' | 'smart_template' | 'basic_fallback' | 'emergency_fallback';
  generationQuality?: 'high' | 'medium-high' | 'medium' | 'basic' | 'minimal';
  canEnhance?: boolean;
  generationMetadata?: {
    is_fallback?: boolean;
    is_emergency_fallback?: boolean;
    note?: string;
    enhancement_suggestion?: string;
    provider?: string;
    model_used?: string;
    character_count?: number;
    template_used?: string;
  };
}

// Extended Agent interface
interface ExtendedAgent extends Omit<Agent, 'configuration'> {
  configuration: ExtendedAgentConfiguration;
}

interface AgentSmartPreviewProps {
  agent: ExtendedAgent;
  onUpdate: (agent: ExtendedAgent) => void;
}

export function AgentSmartPreview({ agent, onUpdate }: AgentSmartPreviewProps) {
  // Enhanced debug logs
  console.log('=== AGENT SMART PREVIEW DEBUG ===');
  console.log('Full agent object:', JSON.stringify(agent, null, 2));
  console.log('Generation method:', agent.configuration?.generationMethod);
  console.log('Generation quality:', agent.configuration?.generationQuality);
  console.log('Can enhance:', agent.configuration?.canEnhance);
  console.log('Generation metadata:', agent.configuration?.generationMetadata);
  console.log('Custom instructions:', agent.configuration?.customInstructions);
  console.log('Instructions field:', agent.configuration?.instructions);
  console.log('Instructions length:', (agent.configuration?.customInstructions || agent.configuration?.instructions || '').length);
  
  const [activeTab, setActiveTab] = useState('overview');
  const [isEditing, setIsEditing] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [editedAgent, setEditedAgent] = useState<ExtendedAgent>(() => ({
    ...agent,
    configuration: {
      ...agent.configuration,
      description: agent.configuration?.description || agent.description || '',
      role: agent.configuration?.role || 'Assistant',
      communicationStyle: agent.configuration?.communicationStyle || 'friendly',
      instructions: agent.configuration?.instructions || agent.configuration?.customInstructions || '',
      hasMemory: agent.configuration?.hasMemory ?? true,
      hasWebSearch: agent.configuration?.hasWebSearch ?? false,
      hasFileUpload: agent.configuration?.hasFileUpload ?? false,
      temperature: agent.configuration?.temperature ?? 0.7,
      memory: {
        enabled: agent.configuration?.memory?.enabled ?? true,
        maxTokens: agent.configuration?.memory?.maxTokens ?? 2000,
        relevanceThreshold: (agent.configuration?.memory as any)?.relevanceThreshold ?? 0.5,
      },
      responseStyle: {
        tone: agent.configuration?.responseStyle?.tone || 'professional',
        format: agent.configuration?.responseStyle?.format || 'concise',
        creativity: (agent.configuration?.responseStyle as any)?.creativity ?? 50,
      },
    },
  }));

  // Get generation status info
  const generationMethod = agent.configuration?.generationMethod;
  const generationQuality = agent.configuration?.generationQuality;
  const canEnhance = agent.configuration?.canEnhance;
  const generationMetadata = agent.configuration?.generationMetadata;

  // Determine if we should show quality indicator
  const showQualityIndicator = generationMethod && generationMethod !== 'primary_llm';

  // Add enhancement function
  const enhanceInstructions = async () => {
    setIsEnhancing(true);
    try {
      // Import the agent instruction service
      const { agentInstructionService, ModelRoutingRule } = await import('@/lib/services/agent-instruction-service');
      
      // Reconstruct the original request from the agent data
      const enhancementRequest = {
        name: agent.name,
        primaryRole: agent.category, // Use category as primary role
        problemStatement: agent.description,
        targetUsers: ['Users'], // Default since we don't store this
        communicationStyle: agent.configuration?.responseStyle?.tone || 'professional',
        outputFormat: agent.configuration?.responseStyle?.format || 'markdown',
        qualityPreference: 3, // Always use high quality for enhancements
        capabilities: agent.capabilities || [],
        routingRule: ModelRoutingRule.QUALITY,
        additionalContext: 'This is an enhancement request for an existing agent with basic instructions.'
      };
      
      console.log('Enhancing instructions with request:', enhancementRequest);
      
      // Call the instruction service
      const generationResponse = await agentInstructionService.generateInstructions(enhancementRequest);
      
      // Update the agent with enhanced instructions
      const enhancedAgent = {
        ...agent,
        configuration: {
          ...agent.configuration,
          customInstructions: generationResponse.instructions,
          instructions: generationResponse.instructions,
          generationMethod: generationResponse.generation_method,
          generationQuality: generationResponse.quality_score,
          canEnhance: generationResponse.can_enhance,
          generationMetadata: generationResponse.metadata
        }
      };
      
      onUpdate(enhancedAgent);
      
      toast({
        title: 'Instructions Enhanced Successfully',
        description: 'Your agent now has AI-generated instructions',
      });
      
    } catch (error) {
      console.error('Error enhancing instructions:', error);
      toast({
        title: 'Enhancement Failed',
        description: 'Could not enhance instructions. Please try again later.',
        variant: 'destructive'
      });
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setEditedAgent(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleConfigChange = (field: keyof ExtendedAgentConfiguration, value: any) => {
    setEditedAgent(prev => ({
      ...prev,
      configuration: {
        ...prev.configuration,
        [field]: value
      }
    }));
  };

  const handleSave = () => {
    onUpdate(editedAgent);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedAgent(agent);
    setIsEditing(false);
  };

  return (
    <Card className="w-full max-w-3xl mx-auto">
      {/* Show quality indicator and enhancement options */}
      {showQualityIndicator && (
        <div className={`border-l-4 p-4 mb-4 ${
          generationMethod === 'emergency_fallback' || generationMethod === 'basic_fallback' 
            ? 'bg-red-50 border-red-400' 
            : 'bg-yellow-50 border-yellow-400'
        }`}>
          <div className="flex items-start justify-between">
            <div className="flex">
              <div className="flex-shrink-0">
                {generationMethod === 'emergency_fallback' || generationMethod === 'basic_fallback' ? (
                  <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
                ) : (
                  <InformationCircleIcon className="h-5 w-5 text-yellow-400" />
                )}
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-gray-800">
                  {generationMethod === 'emergency_fallback' && 'Minimal Instructions Generated'}
                  {generationMethod === 'basic_fallback' && 'Basic Instructions Generated'}
                  {generationMethod === 'smart_template' && 'Template-Based Instructions'}
                  {generationMethod === 'alternative_llm' && 'Alternative AI Service Used'}
                </h3>
                <div className="mt-1 text-sm text-gray-600">
                  <p>
                    {generationMetadata?.enhancement_suggestion || 
                     generationMetadata?.note || 
                     'Instructions generated using fallback method due to service unavailability'}
                  </p>
                  {generationQuality && (
                    <p className="mt-1">
                      <span className="font-medium">Quality Level:</span> {generationQuality}
                    </p>
                  )}
                </div>
              </div>
            </div>
            {canEnhance && (
              <Button 
                onClick={enhanceInstructions}
                disabled={isEnhancing}
                size="sm"
                className="ml-4 bg-blue-600 hover:bg-blue-700 text-white"
              >
                {isEnhancing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Enhancing...
                  </>
                ) : (
                  'Enhance with AI'
                )}
              </Button>
            )}
          </div>
        </div>
      )}

      <CardHeader>
        <div className="flex justify-between items-start">
          <div className="flex-1">
            {isEditing ? (
              <div className="space-y-4 w-full">
                <Input
                  name="name"
                  value={editedAgent.name}
                  onChange={handleInputChange}
                  placeholder="Agent name"
                  className="text-2xl font-bold"
                />
                <Textarea
                  value={editedAgent.configuration.description}
                  onChange={(e) => handleConfigChange('description', e.target.value)}
                  placeholder="Agent description"
                  className="text-muted-foreground"
                  rows={2}
                />
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <CardTitle>{agent.name}</CardTitle>
                  {/* Quality badge */}
                  {generationQuality && (
                    <Badge variant={
                      generationQuality === 'high' ? 'default' :
                      generationQuality === 'medium-high' || generationQuality === 'medium' ? 'secondary' :
                      'outline'
                    }>
                      {generationQuality} quality
                    </Badge>
                  )}
                  {/* Generation method badge */}
                  {generationMethod && generationMethod !== 'primary_llm' && (
                    <Badge variant="outline">
                      {generationMethod === 'smart_template' ? 'Template' :
                       generationMethod === 'basic_fallback' ? 'Basic' :
                       generationMethod === 'emergency_fallback' ? 'Minimal' :
                       generationMethod === 'alternative_llm' ? 'Alt AI' : 'Generated'}
                    </Badge>
                  )}
                </div>
                {agent.configuration?.description ? (
                  <CardDescription>{agent.configuration.description}</CardDescription>
                ) : (
                  <CardDescription className="text-gray-400">No description provided</CardDescription>
                )}
              </>
            )}
          </div>
          
          {!isEditing && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="text-gray-500 hover:text-gray-700"
            >
              <Edit className="h-4 w-4 mr-1" />
              Edit
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 rounded-none border-b bg-transparent p-0">
            <TabsTrigger
              value="overview"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none"
            >
              <Info className="h-4 w-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger
              value="instructions"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Instructions
            </TabsTrigger>
            <TabsTrigger
              value="settings"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none"
            >
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </TabsTrigger>
          </TabsList>

          <div className="pt-6">
            <TabsContent value="overview" className="space-y-4">
              <div className="space-y-2">
                <Label>Role</Label>
                {isEditing ? (
                  <Input
                    value={editedAgent.configuration?.role || ''}
                    onChange={(e) => handleConfigChange('role', e.target.value)}
                    placeholder="e.g., Customer Support, Research Assistant"
                  />
                ) : (
                  <p className="text-sm">{editedAgent.configuration?.role || agent.category || 'Not specified'}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Capabilities</Label>
                {isEditing ? (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="memory"
                        checked={editedAgent.configuration?.hasMemory || false}
                        onCheckedChange={(checked) => handleConfigChange('hasMemory', checked)}
                      />
                      <Label htmlFor="memory">Memory</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="web-search"
                        checked={editedAgent.configuration?.hasWebSearch || false}
                        onCheckedChange={(checked) => handleConfigChange('hasWebSearch', checked)}
                      />
                      <Label htmlFor="web-search">Web Search</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="file-upload"
                        checked={editedAgent.configuration?.hasFileUpload || false}
                        onCheckedChange={(checked) => handleConfigChange('hasFileUpload', checked)}
                      />
                      <Label htmlFor="file-upload">File Upload</Label>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {agent.capabilities && agent.capabilities.length > 0 ? (
                      agent.capabilities.map((capability, index) => (
                        <Badge key={index} variant="secondary">{capability}</Badge>
                      ))
                    ) : (
                      <>
                        {editedAgent.configuration?.hasMemory && <Badge>Memory</Badge>}
                        {editedAgent.configuration?.hasWebSearch && <Badge>Web Search</Badge>}
                        {editedAgent.configuration?.hasFileUpload && <Badge>File Upload</Badge>}
                        {!editedAgent.configuration?.hasMemory &&
                          !editedAgent.configuration?.hasWebSearch &&
                          !editedAgent.configuration?.hasFileUpload &&
                          (!agent.capabilities || agent.capabilities.length === 0) && (
                            <span className="text-sm text-muted-foreground">No capabilities specified</span>
                          )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="instructions" className="space-y-4">
              <div className="space-y-2">
                <Label>Communication Style</Label>
                {isEditing ? (
                  <Input
                    value={editedAgent.configuration?.communicationStyle || ''}
                    onChange={(e) => handleConfigChange('communicationStyle', e.target.value)}
                    placeholder="e.g., Professional, Friendly, Concise"
                  />
                ) : (
                  <p className="text-sm">{editedAgent.configuration?.communicationStyle || editedAgent.configuration?.responseStyle?.tone || 'Not specified'}</p>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Instructions</Label>
                  {!isEditing && canEnhance && generationMethod !== 'primary_llm' && (
                    <Button
                      onClick={enhanceInstructions}
                      disabled={isEnhancing}
                      size="sm"
                      variant="outline"
                      className="text-blue-600 border-blue-600 hover:bg-blue-50"
                    >
                      {isEnhancing ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Enhancing...
                        </>
                      ) : (
                        'Enhance with AI'
                      )}
                    </Button>
                  )}
                </div>
                {isEditing ? (
                  <Textarea
                    value={editedAgent.configuration?.instructions || editedAgent.configuration?.customInstructions || ''}
                    onChange={(e) => {
                      // Update both instructions and customInstructions fields
                      handleConfigChange('instructions', e.target.value);
                      handleConfigChange('customInstructions', e.target.value);
                    }}
                    rows={8}
                    placeholder="Enter detailed instructions for the agent..."
                  />
                ) : (
                  <div className="text-sm whitespace-pre-line bg-gray-50 p-4 rounded-md border max-h-96 overflow-y-auto">
                    {editedAgent.configuration?.instructions || 
                     editedAgent.configuration?.customInstructions || 
                     agent.configuration?.customInstructions ||
                     'No instructions provided'}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="settings" className="space-y-6">
              <div className="space-y-2">
                <Label>Model</Label>
                <p className="text-sm text-muted-foreground">
                  {generationMetadata?.model_used || 'GPT-4'} 
                  {generationMetadata?.provider && ` (${generationMetadata.provider})`}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Temperature: {editedAgent.configuration?.temperature?.toFixed(1)}</Label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={editedAgent.configuration?.temperature || 0.7}
                  onChange={(e) => handleConfigChange('temperature', parseFloat(e.target.value))}
                  className="w-full"
                  disabled={!isEditing}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>More Focused</span>
                  <span>Balanced</span>
                  <span>More Creative</span>
                </div>
              </div>

              {/* Rest of settings remain the same... */}
              
            </TabsContent>
          </div>
        </Tabs>

        {isEditing && (
          <div className="border-t pt-4 mt-6 bg-gray-50 -mx-6 -mb-6 px-6 pb-6 flex justify-end space-x-2">
            <Button variant="outline" size="sm" onClick={handleCancel}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave}>
              Save Changes
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}