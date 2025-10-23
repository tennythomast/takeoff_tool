"use client"

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertCircle,
  Edit,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Database,
  Settings,
  Trash2
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  integrationService,
  MCPServerConnection,
  MCPResource
} from "@/lib/services/integration-service";

interface ConnectionManagePageProps {
  connectionId: string;
}

export default function ConnectionManagePage({ connectionId }: ConnectionManagePageProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [testingConnection, setTestingConnection] = useState(false);
  const [discoveringResources, setDiscoveringResources] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  
  // Data states
  const [connection, setConnection] = useState<MCPServerConnection | null>(null);
  const [resources, setResources] = useState<MCPResource[]>([]);
  
  // Function to fetch resources for the current connection
  const fetchResources = async () => {
    try {
      const resourcesData = await integrationService.getResources(connectionId);
      setResources(resourcesData);
      return resourcesData;
    } catch (err) {
      console.error('Error fetching resources:', err);
      setError('Failed to load resources. Please try again later.');
      return [];
    }
  };

  const debugAuthData = async () => {
    try {
      console.log('=== DEBUGGING CONNECTION AUTH ===');
      const debugInfo = await integrationService.debugConnectionAuth(connectionId);
      console.log('Connection auth debug info:', debugInfo);
      
      // Show the debug info to user
      setSuccess(`Auth Debug: Method=${debugInfo.decryption_method}, Keys=[${debugInfo.auth_data_keys?.join(', ')}], HasToken=${debugInfo.has_token_field}`);
      
      return debugInfo;
    } catch (error) {
      console.error('Debug auth failed:', error);
      // Type check the error before accessing message property
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setError(`Auth debug failed: ${errorMessage}`);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        console.log(`Fetching data for connection ID: ${connectionId}`);
        
        // Fetch connection details
        try {
          const connectionData = await integrationService.getConnectionDetails(connectionId);
          setConnection(connectionData);
          console.log('Connection data loaded successfully');
        } catch (error: unknown) {
          console.error('Error fetching connection details:', error);
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          setError(`Failed to load connection details: ${errorMessage}`);
          setLoading(false);
          return; // Stop if we can't get connection details
        }
        
        // Fetch resources for this connection
        try {
          await fetchResources();
          console.log('Resources loaded successfully');
        } catch (error: unknown) {
          console.error('Error fetching resources:', error);
          // Continue even if resources fail to load
        }
        
        setLoading(false);
      } catch (error: unknown) {
        console.error('Unexpected error in fetchData:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        setError(`An unexpected error occurred: ${errorMessage}`);
        setLoading(false);
      }
    };
    
    fetchData();
  }, [connectionId]);
  
  // Handle test connection
  const handleTestConnection = async () => {
    if (!connection) return;
    
    try {
      setTestingConnection(true);
      setError(null);
      setSuccess(null);
      
      const result = await integrationService.testConnection(connection.id);
      setSuccess(`Connection test successful: ${result.message || 'Connection is healthy'}`);
      
      // Refresh connection data to get updated health status
      const updatedConnection = await integrationService.getConnectionDetails(connectionId);
      setConnection(updatedConnection);
      
      setTestingConnection(false);
    } catch (err) {
      console.error('Connection test failed:', err);
      setError('Connection test failed. Please check your configuration and try again.');
      setTestingConnection(false);
    }
  };
  
  // Handle discover resources
  const handleDiscoverResources = async () => {
    if (!connection) return;
    
    try {
      setDiscoveringResources(true);
      setError(null);
      setSuccess(null);
      
      console.log(`Initiating resource discovery for connection: ${connection.connection_name} (ID: ${connection.id})`);
      const result = await integrationService.discoverResources(connection.id);
      
      console.log('Resource discovery result:', result);
      setSuccess(`Resource discovery successful: ${result.message || 'Resources discovered'}`);
      
      // Refresh resources list
      await fetchResources();
      
      setDiscoveringResources(false);
    } catch (err: unknown) {
      console.error('Resource discovery failed:', err);
      
      // Extract the most useful error message
      let errorMessage = 'Resource discovery failed';
      
      if (err instanceof Error) {
        errorMessage = err.message || errorMessage;
      } else if (typeof err === 'object' && err !== null && 'message' in err) {
        errorMessage = String(err.message) || errorMessage;
      }
      
      // Check for specific error patterns
      if (errorMessage.includes('authentication') || errorMessage.includes('auth')) {
        errorMessage += '. Please check your connection authentication settings.';
      } else if (errorMessage.includes('timeout') || errorMessage.includes('timed out')) {
        errorMessage += '. The server took too long to respond.';
      }
      setError(errorMessage);
      setDiscoveringResources(false);
    }
  };
  
  // Handle delete connection
  const handleDeleteConnection = async () => {
    if (!connection) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Call API to delete connection using the integration service
      await integrationService.deleteConnection(connection.id);
      
      setDeleteDialogOpen(false);
      setSuccess('Connection deleted successfully');
      
      // Redirect to integrations page after a short delay
      setTimeout(() => {
        router.push('/settings/integrations');
      }, 1500);
    } catch (err: unknown) {
      console.error('Error deleting connection:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete connection. Please try again later.';
      setError(errorMessage);
      setLoading(false);
      setDeleteDialogOpen(false);
    }
  };
  
  // Render health status badge
  const renderHealthStatus = (status: string) => {
    switch (status) {
      case 'healthy':
        return (
          <div className="flex items-center">
            <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
            <span>Healthy</span>
          </div>
        );
      case 'warning':
        return (
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-yellow-500 mr-2" />
            <span>Warning</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center">
            <XCircle className="h-5 w-5 text-red-500 mr-2" />
            <span>Error</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center">
            <HelpCircle className="h-5 w-5 text-gray-500 mr-2" />
            <span>Unknown</span>
          </div>
        );
    }
  };
  
  // Group resources by type
  const resourcesByType = resources.reduce((acc, resource) => {
    const type = resource.resource_type;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(resource);
    return acc;
  }, {} as Record<string, MCPResource[]>);
  
  return (
    <div className="container mx-auto pt-4 pb-4">
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-4 text-gray-600">Loading connection details...</p>
        </div>
      ) : error ? (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : success ? (
        <Alert className="mb-6 bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertTitle className="text-green-800">Success</AlertTitle>
          <AlertDescription className="text-green-700">{success}</AlertDescription>
        </Alert>
      ) : null}
      
      {connection && (
        <>
          <Card className="mb-8 border-0 shadow-sm bg-gradient-to-r from-blue-50 to-indigo-50">
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                <div className="flex items-center">
                  <div className="bg-blue-100 p-3 rounded-full mr-4">
                    <Settings size={24} className="text-blue-600" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                      {connection.connection_name}
                    </h1>
                    <p className="text-gray-600 mt-1">
                      {connection.description || `Connection to ${connection.server_name}`}
                    </p>
                    <div className="mt-2">
                      {renderHealthStatus(connection.health_status)}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3 mt-4 md:mt-0">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleTestConnection}
                    disabled={testingConnection}
                    className="bg-obsidian hover:bg-obsidian-dark text-white"
                  >
                    <RefreshCw size={16} className={`mr-2 ${testingConnection ? 'animate-spin' : ''}`} />
                    Test Connection
                  </Button>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/settings/integrations/edit/${connection.id}`)}
                    className="border-obsidian text-obsidian hover:bg-sky-sync/10"
                  >
                    <Edit size={16} className="mr-2" />
                    Edit
                  </Button>
                  
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setDeleteDialogOpen(true)}
                  >
                    <Trash2 size={16} className="mr-2" />
                    Delete
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete Connection</DialogTitle>
                <DialogDescription>
                  Are you sure you want to delete this connection? This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" onClick={handleDeleteConnection}>
                  Delete
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          
          <div className="grid grid-cols-1 gap-6">
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="mb-4">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="resources">Resources</TabsTrigger>
                <TabsTrigger value="usage">Usage</TabsTrigger>
              </TabsList>
              
              <TabsContent value="overview">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Connection Details Card */}
                  <div className="md:col-span-2">
                    <Card>
                      <CardHeader>
                        <CardTitle>Connection Details</CardTitle>
                        <CardDescription>Information about this integration connection</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          <div>
                            <h3 className="text-sm font-medium text-gray-500">Server Type</h3>
                            <p className="mt-1">{connection.server_name}</p>
                          </div>
                          <div>
                            <h3 className="text-sm font-medium text-gray-500">Connection Name</h3>
                            <p className="mt-1">{connection.connection_name}</p>
                          </div>
                          {connection.description && (
                            <div>
                              <h3 className="text-sm font-medium text-gray-500">Description</h3>
                              <p className="mt-1">{connection.description}</p>
                            </div>
                          )}
                          <div>
                            <h3 className="text-sm font-medium text-gray-500">Created</h3>
                            <p className="mt-1">{new Date(connection.created_at).toLocaleString()}</p>
                          </div>
                          <div>
                            <h3 className="text-sm font-medium text-gray-500">Last Updated</h3>
                            <p className="mt-1">{new Date(connection.updated_at).toLocaleString()}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                  
                  {/* Connection Status Card */}
                  <div className="md:col-span-1">
                    <Card>
                      <CardHeader>
                        <CardTitle>Connection Status</CardTitle>
                        <CardDescription>Current health and status</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          <div>
                            <h3 className="text-sm font-medium text-gray-500">Health Status</h3>
                            <div className="mt-2">
                              {renderHealthStatus(connection.health_status)}
                            </div>
                          </div>
                          <div>
                            <h3 className="text-sm font-medium text-gray-500">Last Checked</h3>
                            <p className="mt-1">
                              {connection.last_health_check 
                                ? new Date(connection.last_health_check).toLocaleString() 
                                : 'Never'}
                            </p>
                          </div>
                          <div className="pt-2">
                            <Button 
                              onClick={handleDiscoverResources}
                              disabled={discoveringResources}
                              className="w-full"
                            >
                              <Database className={`mr-2 h-4 w-4 ${discoveringResources ? 'animate-pulse' : ''}`} />
                              {discoveringResources ? 'Discovering...' : 'Discover Resources'}
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="resources">
                <Card>
                  <CardHeader>
                    <CardTitle>Available Resources</CardTitle>
                    <CardDescription>
                      Resources discovered from this connection
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {resources.length === 0 ? (
                      <div className="text-center py-8">
                        <Database className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900">No resources discovered yet</h3>
                        <p className="mt-1 text-gray-500">
                          Click the "Discover Resources" button to find available resources from this connection.
                        </p>
                        <Button 
                          onClick={handleDiscoverResources} 
                          disabled={discoveringResources} 
                          className="mt-4"
                        >
                          <Database className={`mr-2 h-4 w-4 ${discoveringResources ? 'animate-pulse' : ''}`} />
                          {discoveringResources ? 'Discovering...' : 'Discover Resources'}
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-6">
                        {Object.entries(resourcesByType).map(([type, typeResources]) => (
                          <div key={type} className="space-y-2">
                            <h3 className="text-lg font-medium text-gray-900 flex items-center">
                              <Badge variant="outline" className="mr-2">
                                {typeResources.length}
                              </Badge>
                              {type}
                            </h3>
                            <Separator className="my-2" />
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                              {typeResources.map((resource) => (
                                <Card key={resource.id} className="overflow-hidden">
                                  <CardContent className="p-4">
                                    <div className="flex items-start justify-between">
                                      <div>
                                        <h4 className="font-medium text-gray-900 truncate">
                                          {resource.resource_name || resource.id}
                                        </h4>
                                        <p className="text-sm text-gray-500 mt-1 truncate">
                                          {resource.description || 'No description'}
                                        </p>
                                      </div>
                                    </div>
                                  </CardContent>
                                </Card>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="usage">
                <Card>
                  <CardHeader>
                    <CardTitle>Usage Statistics</CardTitle>
                    <CardDescription>
                      Usage metrics for this connection
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-8">
                      <p className="text-gray-500">
                        Usage statistics will be available in a future update.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </>
      )}
    </div>
  );
}
