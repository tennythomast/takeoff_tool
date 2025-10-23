"use client"

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  AlertCircle,
  ArrowLeft,
  Save,
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle,
  Search,
  FolderOpen,
  Settings
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  integrationService,
  MCPServerConnection,
  MCPWorkspaceAccess,
  MCPResource
} from "@/lib/services/integration-service";
import ResourceSelectionDialog from "./ResourceSelectionDialog";

interface WorkspaceAccessPageProps {
  connectionId: string;
}

export default function WorkspaceAccessPage({ connectionId }: WorkspaceAccessPageProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedAccessId, setSelectedAccessId] = useState<string | null>(null);
  
  // Data states
  const [connection, setConnection] = useState<MCPServerConnection | null>(null);
  const [workspaceAccesses, setWorkspaceAccesses] = useState<MCPWorkspaceAccess[]>([]);
  const [resources, setResources] = useState<MCPResource[]>([]);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Form states for adding new access
  const [selectedWorkspace, setSelectedWorkspace] = useState('');
  const [accessName, setAccessName] = useState('');
  const [description, setDescription] = useState('');
  const [permissionLevel, setPermissionLevel] = useState<'read' | 'write' | 'admin'>('read');
  const [isActive, setIsActive] = useState(true);
  const [autoSync, setAutoSync] = useState(false);
  const [selectedResources, setSelectedResources] = useState<string[]>([]);
  
  // Resource selection dialog
  const [resourceSelectionOpen, setResourceSelectionOpen] = useState(false);
  const [selectedWorkspaceResources, setSelectedWorkspaceResources] = useState<string[]>([]);
  const [selectedWorkspaceForResources, setSelectedWorkspaceForResources] = useState<string>('');
  
  // Clear success/error messages after 5 seconds
  useEffect(() => {
    if (success || error) {
      const timer = setTimeout(() => {
        setSuccess(null);
        setError(null);
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [success, error]);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch connection details
        const connectionData = await integrationService.getConnectionDetails(connectionId);
        setConnection(connectionData);
        
        // Fetch resources for this connection
        const resourcesData = await integrationService.getResources(connectionId);
        setResources(resourcesData);
        
        // Fetch workspace accesses for this connection
        try {
          const workspaceAccessesData = await integrationService.getWorkspaceAccesses(connectionId);
          setWorkspaceAccesses(workspaceAccessesData);
        } catch (err) {
          console.error("Failed to fetch workspace accesses:", err);
          // Use empty array if API fails
          setWorkspaceAccesses([]);
        }
        
        // Fetch available workspaces
        // In a real implementation, you would fetch from the API
        // For now, we'll use mock data until the API is available
        const mockWorkspaces = [
          { id: 'ws-1', name: 'Data Science Workspace' },
          { id: 'ws-2', name: 'Marketing Analytics' },
          { id: 'ws-3', name: 'Sales Dashboard' },
          { id: 'ws-4', name: 'Customer Support' }
        ];
        setWorkspaces(mockWorkspaces);
      } catch (err: any) {
        setError(err.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [connectionId]);
  
  // Filter workspaces based on search query
  const filteredWorkspaceAccesses = workspaceAccesses.filter(access => {
    const query = searchQuery.toLowerCase();
    return (
      access.workspace_name.toLowerCase().includes(query) ||
      access.access_name.toLowerCase().includes(query) ||
      (access.description && access.description.toLowerCase().includes(query))
    );
  });
  
  // Handle adding new workspace access
  const handleAddAccess = async () => {
    if (!selectedWorkspace || !accessName) {
      setError('Workspace and access name are required');
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      
      const newAccessData = {
        workspace: selectedWorkspace,
        connection: connectionId,
        access_name: accessName,
        description,
        permission_level: permissionLevel,
        is_active: isActive,
        auto_sync: autoSync,
        allowed_resources: selectedResources,
        resource_filters: {}
      };
      
      // Call the API to create the workspace access
      const newAccess = await integrationService.createWorkspaceAccess(newAccessData);
      
      // Update the local state with the new access
      setWorkspaceAccesses([...workspaceAccesses, newAccess]);
      setSuccess('Workspace access added successfully');
      setAddDialogOpen(false);
      
      // Reset form
      setSelectedWorkspace('');
      setAccessName('');
      setDescription('');
      setPermissionLevel('read');
      setIsActive(true);
      setAutoSync(false);
      setSelectedResources([]);
    } catch (err: any) {
      setError(err.message || 'Failed to add workspace access');
    } finally {
      setSaving(false);
    }
  };
  
  // Handle deleting workspace access
  const handleDeleteAccess = async () => {
    if (!selectedAccessId) return;
    
    try {
      setSaving(true);
      setError(null);
      
      // Call the API to delete the workspace access
      await integrationService.deleteWorkspaceAccess(selectedAccessId);
      
      // Update the local state
      setWorkspaceAccesses(workspaceAccesses.filter(access => access.id !== selectedAccessId));
      setSuccess('Workspace access deleted successfully');
      setDeleteDialogOpen(false);
      setSelectedAccessId(null);
    } catch (err: any) {
      setError(err.message || 'Failed to delete workspace access');
    } finally {
      setSaving(false);
    }
  };
  
  // Handle opening resource selection dialog for a workspace
  const handleOpenResourceSelection = (workspaceId: string, accessId: string) => {
    // Find the access for this workspace
    const access = workspaceAccesses.find(a => a.id === accessId);
    if (access) {
      setSelectedWorkspaceForResources(accessId); // Store the access ID, not workspace ID
      setSelectedWorkspaceResources(access.allowed_resources);
      setResourceSelectionOpen(true);
    }
  };
  
  // Handle resource selection confirmation
  const handleResourceSelectionConfirm = async () => {
    try {
      setSaving(true);
      setError(null);
      
      const accessId = selectedWorkspaceForResources;
      
      // Call the API to update the resources
      await integrationService.updateWorkspaceResources(accessId, selectedWorkspaceResources);
      
      // Update the local state
      const updatedAccesses = workspaceAccesses.map(access => {
        if (access.id === accessId) {
          return {
            ...access,
            allowed_resources: selectedWorkspaceResources,
            allowed_resource_count: selectedWorkspaceResources.length
          };
        }
        return access;
      });
      
      setWorkspaceAccesses(updatedAccesses);
      setSuccess('Resources updated successfully');
      
      // Close the dialog
      setResourceSelectionOpen(false);
    } catch (err: any) {
      setError(err.message || 'Failed to update resources');
    } finally {
      setSaving(false);
    }
  };
  
  return (
    <div className="container mx-auto py-8">
      <Button
        variant="outline"
        className="mb-8"
        onClick={() => router.push(`/integrations/connections/${connectionId}`)}
      >
        <ArrowLeft size={16} className="mr-2" /> Back to Connection
      </Button>
      
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">
            Workspace Access
          </h1>
          <p className="text-gray-600 mt-2">
            {connection ? `Manage workspace access for ${connection.connection_name}` : 'Loading...'}
          </p>
        </div>
        
        <Button
          className="mt-4 md:mt-0"
          onClick={() => setAddDialogOpen(true)}
        >
          <Plus size={16} className="mr-2" />
          Add Workspace Access
        </Button>
      </div>
      
      {loading && !connection ? (
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
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertTitle className="text-green-800">Success</AlertTitle>
          <AlertDescription className="text-green-700">{success}</AlertDescription>
        </Alert>
      ) : null}
      
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Workspace Access</CardTitle>
          <CardDescription>
            Manage which workspaces have access to this connection and what resources they can use
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
              <Input
                placeholder="Search workspaces..."
                className="pl-8"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Button
              variant="outline"
              className="ml-2"
              onClick={() => setAddDialogOpen(true)}
            >
              <Plus size={16} className="mr-2" />
              Add Access
            </Button>
          </div>
          
          {filteredWorkspaceAccesses.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No workspace access found</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setAddDialogOpen(true)}
              >
                <Plus size={16} className="mr-2" />
                Add Workspace Access
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Workspace</TableHead>
                  <TableHead>Access Name</TableHead>
                  <TableHead>Permission</TableHead>
                  <TableHead>Resources</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredWorkspaceAccesses.map((access) => (
                  <TableRow key={access.id}>
                    <TableCell className="font-medium">{access.workspace_name}</TableCell>
                    <TableCell>
                      <div>
                        <div>{access.access_name}</div>
                        {access.description && (
                          <div className="text-xs text-gray-500">{access.description}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={access.permission_level === 'read' ? 'outline' : 
                        access.permission_level === 'write' ? 'secondary' : 'default'}>
                        {access.permission_level}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        <span className="mr-2">{access.allowed_resource_count}</span>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => handleOpenResourceSelection(access.workspace, access.id)}
                        >
                          <FolderOpen size={16} className="mr-1" />
                          Select
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={access.is_active ? 'default' : 'outline'}>
                        {access.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {access.last_used ? new Date(access.last_used).toLocaleDateString() : 'Never'}
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedAccessId(access.id);
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Trash2 size={16} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                        >
                          <Settings size={16} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      
      {/* Add Workspace Access Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Add Workspace Access</DialogTitle>
            <DialogDescription>
              Configure access to this connection for a workspace
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-1 gap-4">
              <div>
                <Label htmlFor="workspace" className="mb-2 block">
                  Workspace <span className="text-red-500">*</span>
                </Label>
                <Select value={selectedWorkspace} onValueChange={setSelectedWorkspace}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a workspace" />
                  </SelectTrigger>
                  <SelectContent>
                    {workspaces.map((workspace) => (
                      <SelectItem key={workspace.id} value={workspace.id}>
                        {workspace.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label htmlFor="access-name" className="mb-2 block">
                  Access Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="access-name"
                  value={accessName}
                  onChange={(e) => setAccessName(e.target.value)}
                  placeholder="Enter a name for this access"
                />
              </div>
              
              <div>
                <Label htmlFor="description" className="mb-2 block">
                  Description
                </Label>
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter a description for this access"
                />
              </div>
              
              <div>
                <Label htmlFor="permission-level" className="mb-2 block">
                  Permission Level <span className="text-red-500">*</span>
                </Label>
                <Select 
                  value={permissionLevel} 
                  onValueChange={(value) => setPermissionLevel(value as 'read' | 'write' | 'admin')}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select permission level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="read">Read</SelectItem>
                    <SelectItem value="write">Write</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex items-center justify-between">
                <Label htmlFor="is-active" className="cursor-pointer">
                  Active
                </Label>
                <Switch
                  id="is-active"
                  checked={isActive}
                  onCheckedChange={setIsActive}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <Label htmlFor="auto-sync" className="cursor-pointer">
                  Auto-sync new resources
                </Label>
                <Switch
                  id="auto-sync"
                  checked={autoSync}
                  onCheckedChange={setAutoSync}
                />
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddAccess} disabled={saving}>
              {saving ? (
                <>
                  <RefreshCw size={16} className="mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save size={16} className="mr-2" />
                  Save
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Delete Workspace Access</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this workspace access? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteAccess} disabled={saving}>
              {saving ? (
                <>
                  <RefreshCw size={16} className="mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 size={16} className="mr-2" />
                  Delete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Resource Selection Dialog */}
      <ResourceSelectionDialog
        open={resourceSelectionOpen}
        onOpenChange={setResourceSelectionOpen}
        resources={resources}
        selectedResources={selectedWorkspaceResources}
        onSelectionChange={setSelectedWorkspaceResources}
        onConfirm={handleResourceSelectionConfirm}
      />
    </div>
  );
}
