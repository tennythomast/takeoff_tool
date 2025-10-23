"use client"

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { 
  AlertCircle, ArrowLeft, Save, RefreshCw, Key, Shield, Link, ExternalLink
} from "lucide-react";
import { 
  integrationService, 
  MCPServerRegistry, 
  MCPServerConnection,
  CreateConnectionRequest,
  UpdateConnectionRequest
} from "@/lib/services/integration-service";
import { fetchUserOrganizations } from '@/lib/api/organization-api';

interface ConnectionFormProps {
  serverId?: string;
  connectionId?: string;
  isEdit?: boolean;
}

export default function ConnectionForm({ serverId, connectionId, isEdit = false }: ConnectionFormProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Data states
  const [server, setServer] = useState<MCPServerRegistry | null>(null);
  const [connection, setConnection] = useState<MCPServerConnection | null>(null);
  const [configSchema, setConfigSchema] = useState<Record<string, any> | null>(null);
  
  // Form states
  const [connectionName, setConnectionName] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [config, setConfig] = useState<Record<string, any>>({});
  const [authData, setAuthData] = useState<Record<string, any>>({});
  const [userOrganizations, setUserOrganizations] = useState<any[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');

  // Separate effect for fetching organizations to ensure it runs independently
  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        console.log('Fetching user organizations...');
        const organizations = await fetchUserOrganizations();
        console.log('Fetched user organizations:', organizations);
        
        if (!organizations || organizations.length === 0) {
          console.error('No organizations found for user');
          setError('No organizations found. Please create an organization first.');
          return;
        }
        
        setUserOrganizations(organizations);
        
        // Set the user's organization ID (users can only belong to one organization)
        if (Array.isArray(organizations) && organizations.length > 0) {
          const userOrg = organizations[0];
          console.log('Setting user organization:', userOrg);
          if (userOrg && userOrg.id) {
            setSelectedOrgId(userOrg.id);
          }
        } else {
          console.error('No organization found for user:', organizations);
        }
      } catch (orgError) {
        console.error('Error fetching user organizations:', orgError);
        setError('Failed to fetch organizations. Please try again later.');
      }
    };
    
    fetchOrganizations();
  }, []); // Run only once on component mount
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        if (isEdit && connectionId) {
          // Fetch existing connection details
          const connectionData = await integrationService.getConnectionDetails(connectionId);
          setConnection(connectionData);
          
          // Fetch server details
          const serverData = await integrationService.getMCPServerDetails(connectionData.server);
          setServer(serverData);
          
          // Fetch config schema
          const schemaData = await integrationService.getServerConfigSchema(connectionData.server);
          setConfigSchema(schemaData);
          
          // Set form values
          setConnectionName(connectionData.connection_name);
          setDescription(connectionData.description || '');
          setIsActive(connectionData.is_active);
          setConfig(connectionData.config || {});
          // Auth data is not returned from the API for security reasons
          
        } else if (serverId) {
          // Fetch server details for new connection
          const serverData = await integrationService.getMCPServerDetails(serverId);
          setServer(serverData);
          
          // Fetch config schema
          const schemaData = await integrationService.getServerConfigSchema(serverId);
          setConfigSchema(schemaData);
          
          // Set default connection name
          setConnectionName(`${serverData.display_name} Connection`);
        } else {
          setError('No server or connection ID provided');
        }
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load server or connection details. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchData();
  }, [serverId, connectionId, isEdit]);
  
  // Handle form input changes
  const handleConfigChange = (key: string, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };
  
  const handleAuthDataChange = (key: string, value: any) => {
    // For API key type connections, always use 'token' as the key for Notion
    // This ensures compatibility with the backend's expected format
    const actualKey = key === 'apiKey' && server?.qualified_name?.includes('notion') ? 'token' : key;
    
    // Ensure auth_data is always a proper object
    setAuthData(prev => {
      // If value is empty and it's the only key, don't remove it completely
      // to ensure we always have at least an empty object structure
      if (value === '' && Object.keys(prev).length <= 1) {
        return { [actualKey]: '' };
      }
      return { ...prev, [actualKey]: value };
    });
    
    console.log('Updated auth data:', { ...authData, [actualKey]: value });
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setSaving(true);
      setError(null);
      
      // Debug logging for organization data
      console.log('User organizations:', userOrganizations);
      console.log('Selected organization ID:', selectedOrgId);
      
      // Validate all required fields
      if (!connectionName || connectionName.trim() === '') {
        setError('Connection name is required');
        setSaving(false);
        return;
      }
      
      if (!server || !server.id) {
        setError('Server selection is required');
        setSaving(false);
        return;
      }
      
      // Validate auth data
      if (!isEdit && Object.keys(authData).length === 0) {
        setError('Authentication data is required');
        setSaving(false);
        return;
      }
      
      // Get the user's organization ID (users can only belong to one organization)
      if (userOrganizations && userOrganizations.length > 0) {
        // Use the user's organization
        const userOrg = userOrganizations[0];
        if (userOrg && userOrg.id) {
          setSelectedOrgId(userOrg.id);
          console.log('Using user organization ID:', userOrg.id);
        } else {
          console.warn('User has no valid organization');
        }
      } else {
        console.log('No organization available for user');
      }
      
      if (isEdit && connection) {
        // Update existing connection
        const updateData: UpdateConnectionRequest = {
          connection_name: connectionName,
          description,
          config,
          is_active: isActive
        };
        
        // Only include auth_data if it has been modified
        if (Object.keys(authData).length > 0) {
          updateData.auth_data = authData;
        }
        
        try {
          await integrationService.updateConnection(connection.id, updateData);
          setSuccess('Connection updated successfully');
          
          // Redirect to connection's manage page after a short delay
          setTimeout(() => {
            router.push(`/settings/integrations/manage/${connection.id}`);
          }, 1500);
        } catch (error: any) {
          console.error('Connection update error:', error);
          
          // Extract more detailed error message if available
          let errorMessage = 'Failed to update connection';
          
          if (error.message) {
            errorMessage = error.message;
          }
          
          setError(errorMessage);
        }
        
      } else if (server) {
        // Ensure auth_data is not empty and is properly formatted
        if (Object.keys(authData).length === 0) {
          setError('Authentication data is required');
          setSaving(false);
          return;
        }
        
        // For API Key type, ensure it's not empty
        if (configSchema?.auth_schema?.type === 'apiKey' && (!authData.apiKey || authData.apiKey.trim() === '')) {
          setError('API Key is required');
          setSaving(false);
          return;
        }
        
        // For custom credentials, ensure it's not empty
        if (configSchema?.auth_schema?.type !== 'apiKey' && configSchema?.auth_schema?.type !== 'oauth2' && 
            (!authData.credentials || authData.credentials.trim() === '')) {
          setError('Authentication credentials are required');
          setSaving(false);
          return;
        }
        
        // Create new connection
        const createData: CreateConnectionRequest = {
          organization: selectedOrgId, // Use the actual organization ID
          server: server.id,
          connection_name: connectionName,
          description: description || '', // Ensure description is not undefined
          config: config || {}, // Ensure config is not undefined
          auth_data: authData
        };
        
        // Debug log the full request payload
        console.log('Creating connection with payload:', JSON.stringify(createData, null, 2));
        console.log('Connection payload types:', {
          organization: typeof createData.organization,
          server: typeof createData.server,
          connection_name: typeof createData.connection_name,
          description: typeof createData.description,
          config: typeof createData.config,
          auth_data: typeof createData.auth_data
        });
        console.log('Auth data keys:', Object.keys(authData));
        
        try {
          const result = await integrationService.createConnection(createData);
          console.log('Connection created successfully:', result);
          setSuccess('Connection created successfully');
          
          // Redirect to connection's manage page after a short delay
          setTimeout(() => {
            router.push(`/settings/integrations/manage/${result.id}`);
          }, 1500);
        } catch (error: any) {
          console.error('Connection creation error:', error);
          
          // Extract more detailed error message if available
          let errorMessage = 'Failed to create connection';
          
          if (error.message) {
            errorMessage = error.message;
          }
          
          setError(errorMessage);
        }
      }
      
      setSaving(false);
    } catch (err: any) {
      console.error('Error saving connection:', err);
      setError(err?.message || 'Failed to save connection. Please check your inputs and try again.');
      setSaving(false);
    }
  };
  
  // Handle test connection
  const handleTestConnection = async () => {
    if (!connection) return;
    
    try {
      setLoading(true);
      const result = await integrationService.testConnection(connection.id);
      setSuccess(`Connection test successful: ${result.message}`);
      setLoading(false);
    } catch (err) {
      console.error('Connection test failed:', err);
      setError('Connection test failed. Please check your configuration and try again.');
      setLoading(false);
    }
  };
  
  // Render config form fields based on schema
  const renderConfigFields = () => {
    if (!configSchema || !configSchema.config_schema) return null;
    
    const schema = configSchema.config_schema;
    const requiredFields = schema.required || [];
    const properties = schema.properties || {};
    
    return Object.entries(properties).map(([key, prop]: [string, any]) => {
      const isRequired = requiredFields.includes(key);
      const value = config[key] || '';
      
      return (
        <div key={`config-${key}`} className="mb-4">
          <Label htmlFor={`config-${key}`} className="mb-2 block">
            {prop.title || key}{isRequired && <span className="text-red-500 ml-1">*</span>}
          </Label>
          {prop.description && (
            <p className="text-sm text-gray-500 mb-2">{prop.description}</p>
          )}
          <Input
            id={`config-${key}`}
            value={value}
            onChange={(e) => handleConfigChange(key, e.target.value)}
            placeholder={prop.examples?.[0] || ''}
            required={isRequired}
          />
        </div>
      );
    });
  };
  
  // Render auth form fields based on schema
  const renderAuthFields = () => {
    if (!configSchema || !configSchema.auth_schema) return null;
    
    const schema = configSchema.auth_schema;
    const type = schema.type || '';
    
    if (type === 'apiKey') {
      // Determine if this is a Notion connection
      const isNotion = server?.qualified_name?.includes('notion');
      // Use the appropriate key name based on the server type
      const keyName = isNotion ? 'token' : 'apiKey';
      const displayValue = isNotion ? (authData.token || '') : (authData.apiKey || '');
      
      return (
        <div className="mb-4">
          <Label htmlFor="auth-apiKey" className="mb-2 block">
            {isNotion ? 'Notion Token' : 'API Key'} <span className="text-red-500">*</span>
          </Label>
          <div className="flex items-center">
            <Key size={16} className="mr-2 text-gray-500" />
            <Input
              id="auth-apiKey"
              type="password"
              value={displayValue}
              onChange={(e) => handleAuthDataChange(keyName, e.target.value)}
              placeholder={isNotion ? "Enter Notion token" : "Enter API key"}
              required={!isEdit}
              className="flex-1"
            />
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {isEdit ? 
              `Leave blank to keep existing ${isNotion ? 'token' : 'API key'}` : 
              `Enter your ${isNotion ? 'Notion integration token' : 'API key'} for authentication`
            }
          </p>
        </div>
      );
    }
    
    if (type === 'oauth2') {
      return (
        <div className="mb-4">
          <Label className="mb-2 block">OAuth2 Authentication</Label>
          <Button variant="outline" className="w-full">
            <Shield size={16} className="mr-2" />
            Connect with OAuth
          </Button>
          <p className="text-sm text-gray-500 mt-1">
            You'll be redirected to authorize this application
          </p>
        </div>
      );
    }
    
    return (
      <div className="mb-4">
        <Label htmlFor="auth-custom" className="mb-2 block">
          Authentication Credentials <span className="text-red-500">*</span>
        </Label>
        <Textarea
          id="auth-custom"
          value={authData.credentials || ''}
          onChange={(e) => handleAuthDataChange('credentials', e.target.value)}
          placeholder="Enter authentication credentials (JSON format)"
          required={!isEdit}
          className="min-h-[100px]"
        />
        <p className="text-sm text-gray-500 mt-1">
          {isEdit ? 'Leave blank to keep existing credentials' : 'Enter your authentication credentials in JSON format'}
        </p>
      </div>
    );
  };
  
  return (
    <div className="container mx-auto py-2 px-4">
      <Button 
        variant="ghost" 
        className="mb-6"
        onClick={() => router.push('/integrations')}
      >
        <ArrowLeft size={16} className="mr-2" /> Back to Integrations
      </Button>
      
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          {isEdit ? 'Edit Connection' : 'New Connection'}
        </h1>
        <p className="text-gray-600 mt-2 text-lg">
          {isEdit 
            ? `Update your connection to ${server?.display_name || 'the service'}`
            : `Configure a new connection to ${server?.display_name || 'the service'}`
          }
        </p>
      </div>
      
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      ) : error ? (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : success ? (
        <Alert className="mb-6 bg-green-50 border-green-200">
          <AlertTitle className="text-green-800">Success</AlertTitle>
          <AlertDescription className="text-green-700">{success}</AlertDescription>
        </Alert>
      ) : null}
      
      {server && (
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Connection Details */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>Connection Details</CardTitle>
                  <CardDescription>
                    Configure how this integration appears in your workspace
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="connection-name" className="mb-2 block">
                        Connection Name <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="connection-name"
                        value={connectionName}
                        onChange={(e) => setConnectionName(e.target.value)}
                        placeholder="Enter a name for this connection"
                        required
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="description" className="mb-2 block">
                        Description
                      </Label>
                      <Textarea
                        id="description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Enter a description for this connection"
                        className="min-h-[100px]"
                      />
                    </div>
                    
                    {isEdit && (
                      <div className="flex items-center justify-between">
                        <div>
                          <Label htmlFor="is-active" className="mb-2 block">
                            Active Status
                          </Label>
                          <p className="text-sm text-gray-500">
                            Enable or disable this connection
                          </p>
                        </div>
                        <Switch
                          id="is-active"
                          checked={isActive}
                          onCheckedChange={setIsActive}
                        />
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
              
              {/* Configuration */}
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>Configuration</CardTitle>
                  <CardDescription>
                    Configure the connection settings for {server.display_name}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {renderConfigFields()}
                  </div>
                </CardContent>
              </Card>
              
              {/* Authentication */}
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>Authentication</CardTitle>
                  <CardDescription>
                    Provide authentication credentials for {server.display_name}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {renderAuthFields()}
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Right Column - Server Info */}
            <div>
              <Card>
                <CardHeader>
                  <CardTitle>{server.display_name}</CardTitle>
                  <CardDescription>
                    {server.category} Integration
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 mb-4">{server.description}</p>
                  
                  <Separator className="my-4" />
                  
                  <div className="space-y-3">
                    <div>
                      <h4 className="text-sm font-medium text-gray-700">Capabilities</h4>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {server.capabilities.map((capability, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {capability}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium text-gray-700">Supported Operations</h4>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {server.supported_operations.map((operation, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {operation}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    
                    {server.documentation_url && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700">Documentation</h4>
                        <a 
                          href={server.documentation_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1 mt-1"
                        >
                          <ExternalLink size={14} /> View Documentation
                        </a>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
              
              {isEdit && connection && (
                <Card className="mt-8">
                  <CardHeader>
                    <CardTitle>Connection Status</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Status</span>
                        <Badge 
                          className={`
                            ${connection.health_status === 'healthy' ? 'bg-green-100 text-green-800 border-green-200' : ''}
                            ${connection.health_status === 'warning' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' : ''}
                            ${connection.health_status === 'error' ? 'bg-red-100 text-red-800 border-red-200' : ''}
                            ${connection.health_status === 'unknown' ? 'bg-gray-100 text-gray-800 border-gray-200' : ''}
                          `}
                        >
                          {connection.health_status.charAt(0).toUpperCase() + connection.health_status.slice(1)}
                        </Badge>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Last Checked</span>
                        <span className="text-sm">
                          {connection.last_health_check 
                            ? new Date(connection.last_health_check).toLocaleString() 
                            : 'Never'
                          }
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Total Requests</span>
                        <span className="text-sm">{connection.total_requests}</span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Failed Requests</span>
                        <span className="text-sm">{connection.failed_requests}</span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Avg Response Time</span>
                        <span className="text-sm">{typeof connection.avg_response_time === 'number' ? connection.avg_response_time.toFixed(3) : '0.000'}s</span>
                      </div>
                      
                      <Button 
                        type="button"
                        variant="outline" 
                        className="w-full mt-4"
                        onClick={handleTestConnection}
                        disabled={loading}
                      >
                        <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
                        Test Connection
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
          
          {/* Form Actions */}
          <div className="mt-8 flex justify-end gap-4">
            <Button 
              type="button" 
              variant="outline"
              onClick={() => router.push('/integrations')}
            >
              Cancel
            </Button>
            <Button 
              type="submit"
              disabled={saving}
            >
              {saving ? (
                <>
                  <RefreshCw size={16} className="mr-2 animate-spin" />
                  {isEdit ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <Save size={16} className="mr-2" />
                  {isEdit ? 'Update Connection' : 'Create Connection'}
                </>
              )}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
