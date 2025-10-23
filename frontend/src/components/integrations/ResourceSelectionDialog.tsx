"use client"

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
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Search, FolderTree, Database, FileText, RefreshCw, CheckCircle2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { MCPResource } from "@/lib/services/integration-service";

interface ResourceSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  resources: MCPResource[];
  selectedResources: string[];
  onSelectionChange: (selectedIds: string[]) => void;
  onConfirm: () => void;
  isLoading?: boolean;
  isSaving?: boolean;
}

export default function ResourceSelectionDialog({
  open,
  onOpenChange,
  resources,
  selectedResources,
  onSelectionChange,
  onConfirm,
  isLoading = false,
  isSaving = false
}: ResourceSelectionDialogProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredResources, setFilteredResources] = useState<MCPResource[]>(resources);
  const [resourcesByType, setResourcesByType] = useState<Record<string, MCPResource[]>>({});
  const [activeTab, setActiveTab] = useState('all');
  
  // Reset search when dialog opens/closes
  useEffect(() => {
    if (open) {
      setSearchQuery('');
    }
  }, [open]);
  
  // Filter resources when search query changes or tab changes
  useEffect(() => {
    let filtered = [...resources];
    
    // Apply type filter if not on 'all' tab
    if (activeTab !== 'all') {
      filtered = filtered.filter(resource => resource.resource_type.toLowerCase() === activeTab);
    }
    
    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(resource => 
        resource.resource_name.toLowerCase().includes(query) ||
        resource.resource_type.toLowerCase().includes(query) ||
        (resource.description && resource.description.toLowerCase().includes(query))
      );
    }
    
    setFilteredResources(filtered);
  }, [searchQuery, resources, activeTab]);
  
  // Group resources by type
  useEffect(() => {
    const grouped: Record<string, MCPResource[]> = {};
    filteredResources.forEach(resource => {
      if (!grouped[resource.resource_type]) {
        grouped[resource.resource_type] = [];
      }
      grouped[resource.resource_type].push(resource);
    });
    setResourcesByType(grouped);
  }, [filteredResources]);
  
  // Get unique resource types for tabs
  const resourceTypes = React.useMemo(() => {
    const types = new Set<string>();
    resources.forEach(resource => types.add(resource.resource_type.toLowerCase()));
    return Array.from(types);
  }, [resources]);
  
  // Toggle selection of a resource
  const toggleResourceSelection = (resourceId: string) => {
    if (selectedResources.includes(resourceId)) {
      onSelectionChange(selectedResources.filter(id => id !== resourceId));
    } else {
      onSelectionChange([...selectedResources, resourceId]);
    }
  };
  
  // Toggle selection of all resources in a type group
  const toggleTypeSelection = (resourceType: string) => {
    const resourcesOfType = resources.filter(r => r.resource_type === resourceType);
    const resourceIdsOfType = resourcesOfType.map(r => r.id);
    
    // Check if all resources of this type are already selected
    const allSelected = resourceIdsOfType.every(id => selectedResources.includes(id));
    
    if (allSelected) {
      // If all are selected, deselect all of this type
      onSelectionChange(selectedResources.filter(id => !resourceIdsOfType.includes(id)));
    } else {
      // If not all are selected, select all of this type
      const newSelection = [...selectedResources];
      resourceIdsOfType.forEach(id => {
        if (!newSelection.includes(id)) {
          newSelection.push(id);
        }
      });
      onSelectionChange(newSelection);
    }
  };
  
  // Get icon for resource type
  const getResourceIcon = (resourceType: string) => {
    switch (resourceType.toLowerCase()) {
      case 'folder':
      case 'directory':
      case 'project':
        return <FolderTree className="h-4 w-4 mr-2" />;
      case 'database':
      case 'collection':
        return <Database className="h-4 w-4 mr-2" />;
      default:
        return <FileText className="h-4 w-4 mr-2" />;
    }
  };
  
  // Check if all resources of a type are selected
  const areAllTypeResourcesSelected = (resourceType: string) => {
    const resourcesOfType = resources.filter(r => r.resource_type === resourceType);
    return resourcesOfType.every(r => selectedResources.includes(r.id));
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>Select Resources</DialogTitle>
          <DialogDescription>
            Choose specific resources to make available in this workspace
          </DialogDescription>
        </DialogHeader>
        
        <div className="relative my-4">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search resources..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            disabled={isLoading}
          />
        </div>
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-4 flex-wrap">
            <TabsTrigger value="all" disabled={isLoading}>
              All Resources
              <Badge variant="outline" className="ml-2">{resources.length}</Badge>
            </TabsTrigger>
            {resourceTypes.map(type => (
              <TabsTrigger key={type} value={type} disabled={isLoading}>
                {type.charAt(0).toUpperCase() + type.slice(1)}s
                <Badge variant="outline" className="ml-2">
                  {resources.filter(r => r.resource_type.toLowerCase() === type).length}
                </Badge>
              </TabsTrigger>
            ))}
          </TabsList>
          
          <TabsContent value={activeTab} className="mt-0">
            {isLoading ? (
              <div className="flex items-center justify-center h-[300px]">
                <RefreshCw className="h-6 w-6 animate-spin text-primary" />
                <span className="ml-2">Loading resources...</span>
              </div>
            ) : (
              <ScrollArea className="h-[350px] pr-4">
                {Object.entries(resourcesByType).map(([resourceType, resources]) => (
                  <div key={resourceType} className="mb-6">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-medium capitalize">{resourceType}s</h3>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => toggleTypeSelection(resourceType)}
                        className="h-6 text-xs"
                      >
                        {areAllTypeResourcesSelected(resourceType) ? 'Deselect All' : 'Select All'}
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {resources.map(resource => (
                        <div key={resource.id} className="flex items-center space-x-2 rounded-md p-1 hover:bg-muted/50">
                          <Checkbox
                            id={`resource-${resource.id}`}
                            checked={selectedResources.includes(resource.id)}
                            onCheckedChange={() => toggleResourceSelection(resource.id)}
                          />
                          <Label
                            htmlFor={`resource-${resource.id}`}
                            className="flex items-center cursor-pointer flex-1"
                          >
                            {getResourceIcon(resource.resource_type)}
                            <div className="flex flex-col">
                              <span>{resource.resource_name}</span>
                              {resource.description && (
                                <span className="text-xs text-muted-foreground">{resource.description}</span>
                              )}
                            </div>
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                
                {filteredResources.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    No resources found matching your search
                  </div>
                )}
              </ScrollArea>
            )}
          </TabsContent>
        </Tabs>
        
        <DialogFooter>
          <div className="flex justify-between w-full items-center">
            <div className="text-sm">
              <Badge variant="secondary">{selectedResources.length}</Badge>
              <span className="ml-2 text-muted-foreground">resources selected</span>
            </div>
            <div className="space-x-2">
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSaving}>
                Cancel
              </Button>
              <Button onClick={onConfirm} disabled={isSaving || isLoading}>
                {isSaving ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Confirm Selection
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
