import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Check, AlertCircle } from "lucide-react";

import { fetchMCPServerRegistries, MCPServerRegistry } from '@/lib/api/mcp-service';

interface ConfigureMCPConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
  organizationId: string;
  onConnectionCreated?: () => void;
}

export default function ConfigureMCPConnectionModal({
  isOpen,
  onClose,
  workspaceId,
  organizationId,
  onConnectionCreated
}: ConfigureMCPConnectionModalProps) {
  const [activeTab, setActiveTab] = useState('select');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serverRegistries, setServerRegistries] = useState<MCPServerRegistry[]>([]);
  const [selectedServer, setSelectedServer] = useState<MCPServerRegistry | null>(null);
  const [connectionName, setConnectionName] = useState('');
  const [connectionDescription, setConnectionDescription] = useState('');
  const [connectionConfig, setConnectionConfig] = useState<Record<string, string>>({});
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [testMessage, setTestMessage] = useState('');

  // Fetch available server registries on mount
  useEffect(() => {
    const fetchRegistries = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const registries = await fetchMCPServerRegistries();
        // Ensure registries is always an array
        setServerRegistries(Array.isArray(registries) ? registries : []);
      } catch (err) {
        console.error('Error fetching MCP server registries:', err);
        setError('Failed to load available MCP servers. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    if (isOpen) {
      fetchRegistries();
    }
  }, [isOpen]);

  // Handle server selection
  const handleServerSelect = (server: MCPServerRegistry) => {
    setSelectedServer(server);
    setConnectionName(`${server.display_name} Connection`);
    setConnectionDescription(`Connection to ${server.display_name}`);
    
    // Reset connection config based on server type
    // This would be expanded based on the server's required configuration
    setConnectionConfig({
      api_key: '',
      base_url: '',
    });
  };

  // Handle connection config change
  const handleConfigChange = (key: string, value: string) => {
    setConnectionConfig(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // Test connection
  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);
    setTestMessage('');
    
    try {
      // This would be replaced with an actual API call to test the connection
      // For now, we'll simulate a successful test after a delay
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setTestResult('success');
      setTestMessage('Connection successful!');
    } catch (err) {
      console.error('Error testing connection:', err);
      setTestResult('error');
      setTestMessage('Connection failed. Please check your configuration and try again.');
    } finally {
      setTestingConnection(false);
    }
  };

  // Create connection
  const handleCreateConnection = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // This would be replaced with an actual API call to create the connection
      // For now, we'll simulate a successful creation after a delay
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Call the onConnectionCreated callback if provided
      if (onConnectionCreated) {
        onConnectionCreated();
      }
      
      // Close the modal
      onClose();
    } catch (err) {
      console.error('Error creating connection:', err);
      setError('Failed to create connection. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Configure MCP Connection</DialogTitle>
          <DialogDescription>
            Connect your workspace to external tools and resources
          </DialogDescription>
        </DialogHeader>
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="select">Select Server</TabsTrigger>
            <TabsTrigger value="configure" disabled={!selectedServer}>Configure</TabsTrigger>
            <TabsTrigger value="test" disabled={!selectedServer || Object.values(connectionConfig).some(v => !v)}>Test & Create</TabsTrigger>
          </TabsList>
          
          {/* Select Server Tab */}
          <TabsContent value="select" className="space-y-4 py-4">
            {loading ? (
              <div className="flex justify-center items-center h-40">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : error ? (
              <div className="text-center p-4 border border-red-200 rounded-md bg-red-50">
                <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                <p className="text-red-600">{error}</p>
                <Button variant="outline" className="mt-4" onClick={() => fetchMCPServerRegistries()}>
                  Retry
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {(Array.isArray(serverRegistries) ? serverRegistries : []).map(server => (
                  <Card 
                    key={server.id} 
                    className={`cursor-pointer transition-all ${selectedServer?.id === server.id ? 'border-primary ring-2 ring-primary/20' : 'hover:border-gray-300'}`}
                    onClick={() => handleServerSelect(server)}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">{server.display_name}</CardTitle>
                        <Badge>{server.category}</Badge>
                      </div>
                      <CardDescription>{server.description}</CardDescription>
                    </CardHeader>
                    <CardFooter className="pt-2 flex justify-between">
                      <div className="flex gap-2">
                        {server.capabilities.map(cap => (
                          <Badge key={cap} variant="outline">{cap}</Badge>
                        ))}
                      </div>
                      {server.is_verified && (
                        <Badge variant="secondary" className="bg-green-100 text-green-800">Verified</Badge>
                      )}
                    </CardFooter>
                  </Card>
                ))}
              </div>
            )}
            
            <DialogFooter>
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button 
                onClick={() => setActiveTab('configure')} 
                disabled={!selectedServer}
              >
                Next
              </Button>
            </DialogFooter>
          </TabsContent>
          
          {/* Configure Tab */}
          <TabsContent value="configure" className="space-y-4 py-4">
            {selectedServer && (
              <>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="connection-name">Connection Name</Label>
                    <Input 
                      id="connection-name" 
                      value={connectionName} 
                      onChange={e => setConnectionName(e.target.value)} 
                      placeholder="Enter a name for this connection"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="connection-description">Description</Label>
                    <Input 
                      id="connection-description" 
                      value={connectionDescription} 
                      onChange={e => setConnectionDescription(e.target.value)} 
                      placeholder="Enter a description for this connection"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="api-key">API Key</Label>
                    <Input 
                      id="api-key" 
                      type="password"
                      value={connectionConfig.api_key || ''} 
                      onChange={e => handleConfigChange('api_key', e.target.value)} 
                      placeholder="Enter your API key"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="base-url">Base URL (Optional)</Label>
                    <Input 
                      id="base-url" 
                      value={connectionConfig.base_url || ''} 
                      onChange={e => handleConfigChange('base_url', e.target.value)} 
                      placeholder="Enter the base URL if different from default"
                    />
                  </div>
                </div>
                
                <DialogFooter>
                  <Button variant="outline" onClick={() => setActiveTab('select')}>Back</Button>
                  <Button 
                    onClick={() => setActiveTab('test')} 
                    disabled={!connectionName || Object.values(connectionConfig).some(v => !v)}
                  >
                    Next
                  </Button>
                </DialogFooter>
              </>
            )}
          </TabsContent>
          
          {/* Test & Create Tab */}
          <TabsContent value="test" className="space-y-4 py-4">
            <div className="space-y-4">
              <div className="border rounded-md p-4">
                <h3 className="font-medium mb-2">Connection Summary</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-gray-500">Server:</div>
                  <div>{selectedServer?.display_name}</div>
                  <div className="text-gray-500">Name:</div>
                  <div>{connectionName}</div>
                  <div className="text-gray-500">Description:</div>
                  <div>{connectionDescription}</div>
                </div>
              </div>
              
              <div className="flex justify-center">
                <Button 
                  variant="outline" 
                  onClick={handleTestConnection}
                  disabled={testingConnection}
                  className="w-full"
                >
                  {testingConnection ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Testing Connection...
                    </>
                  ) : (
                    'Test Connection'
                  )}
                </Button>
              </div>
              
              {testResult && (
                <div className={`p-4 border rounded-md ${testResult === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <div className="flex items-center gap-2">
                    {testResult === 'success' ? (
                      <Check className="h-5 w-5 text-green-500" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-red-500" />
                    )}
                    <span className={testResult === 'success' ? 'text-green-700' : 'text-red-700'}>
                      {testMessage}
                    </span>
                  </div>
                </div>
              )}
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setActiveTab('configure')}>Back</Button>
              <Button 
                onClick={handleCreateConnection}
                disabled={loading || (testResult !== 'success' && testResult !== null)}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Connection'
                )}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
        
        {error && (
          <div className="mt-4 p-3 border border-red-200 rounded-md bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
