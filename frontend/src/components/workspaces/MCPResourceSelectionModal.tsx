"use client"

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Search, CheckCircle, Link, Filter } from "lucide-react";
import { 
  fetchMCPResources, 
  addResourceToWorkspaceAccess, 
  removeResourceFromWorkspaceAccess,
  MCPResource 
} from '@/lib/api/mcp-service';

interface MCPResourceSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
  connectionId: string | null;
  selectedResources: Record<string, MCPResource[]>;
  onResourcesUpdated: () => void;
}

export default function MCPResourceSelectionModal({
  isOpen,
  onClose,
  workspaceId,
  connectionId,
  selectedResources,
  onResourcesUpdated
}: MCPResourceSelectionModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resources, setResources] = useState<MCPResource[]>([]);
  const [filteredResources, setFilteredResources] = useState<MCPResource[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [resourceType, setResourceType] = useState<string | null>(null);
  const [resourceTypes, setResourceTypes] = useState<string[]>([]);
  const [selectedResourceIds, setSelectedResourceIds] = useState<Set<string>>(new Set());

  // Fetch resources when modal opens
  useEffect(() => {
    if (isOpen && connectionId) {
      fetchResources();
    }
  }, [isOpen, connectionId]);

  // Initialize selected resources from props
  useEffect(() => {
    if (connectionId && selectedResources[connectionId]) {
      const selectedIds = new Set(selectedResources[connectionId].map(r => r.id));
      setSelectedResourceIds(selectedIds);
    } else {
      setSelectedResourceIds(new Set());
    }
  }, [connectionId, selectedResources]);

  // Filter resources based on search query and resource type
  useEffect(() => {
    if (!resources.length) return;
    
    let filtered = [...resources];
    
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(resource => 
        (resource.resource_name?.toLowerCase().includes(query)) || 
        resource.id.toLowerCase().includes(query) ||
        resource.resource_type.toLowerCase().includes(query)
      );
    }
    
    // Filter by resource type
    if (resourceType) {
      filtered = filtered.filter(resource => resource.resource_type === resourceType);
    }
    
    setFilteredResources(filtered);
  }, [resources, searchQuery, resourceType]);

  // Extract unique resource types
  useEffect(() => {
    if (resources.length) {
      const types = Array.from(new Set(resources.map(r => r.resource_type)));
      setResourceTypes(types);
    }
  }, [resources]);

  const fetchResources = async () => {
    if (!connectionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const fetchedResources = await fetchMCPResources(connectionId);
      setResources(fetchedResources);
      setFilteredResources(fetchedResources);
    } catch (err) {
      console.error('Error fetching MCP resources:', err);
      setError('Failed to load resources. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleResourceToggle = async (resource: MCPResource) => {
    if (!connectionId || !workspaceId) return;
    
    const isSelected = selectedResourceIds.has(resource.id);
    const newSelectedIds = new Set(selectedResourceIds);
    
    try {
      if (isSelected) {
        // Remove resource
        await removeResourceFromWorkspaceAccess(workspaceId, resource.id);
        newSelectedIds.delete(resource.id);
      } else {
        // Add resource
        await addResourceToWorkspaceAccess(workspaceId, resource.id);
        newSelectedIds.add(resource.id);
      }
      
      setSelectedResourceIds(newSelectedIds);
      onResourcesUpdated();
    } catch (err) {
      console.error(`Error ${isSelected ? 'removing' : 'adding'} resource:`, err);
      setError(`Failed to ${isSelected ? 'remove' : 'add'} resource. Please try again.`);
    }
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setResourceType(null);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Resources</DialogTitle>
          <DialogDescription>
            Choose resources from this connection to use in your workspace
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex items-center gap-2 my-4">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search resources..."
              className="pl-8"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <select 
              className="border rounded p-2 text-sm"
              value={resourceType || ''}
              onChange={(e) => setResourceType(e.target.value || null)}
            >
              <option value="">All types</option>
              {resourceTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
            
            <Button 
              variant="ghost" 
              size="sm"
              onClick={handleClearFilters}
            >
              Clear
            </Button>
          </div>
        </div>
        
        {error && (
          <div className="bg-red-50 text-red-500 p-2 rounded mb-4">
            {error}
          </div>
        )}
        
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : filteredResources.length > 0 ? (
            <div className="space-y-2">
              {filteredResources.map((resource) => {
                const isSelected = selectedResourceIds.has(resource.id);
                return (
                  <div 
                    key={resource.id} 
                    className={`flex items-center justify-between p-3 rounded-md border ${
                      isSelected ? 'border-green-200 bg-green-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Checkbox 
                        id={`resource-${resource.id}`}
                        checked={isSelected}
                        onCheckedChange={() => handleResourceToggle(resource)}
                      />
                      <div>
                        <Label 
                          htmlFor={`resource-${resource.id}`}
                          className="font-medium cursor-pointer"
                        >
                          {resource.resource_name || resource.id}
                        </Label>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span className="bg-gray-100 px-2 py-0.5 rounded">
                            {resource.resource_type}
                          </span>
                          {resource.operations?.length > 0 && (
                            <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                              {resource.operations.join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {isSelected && (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">
                {searchQuery || resourceType
                  ? 'No resources match your filters'
                  : 'No resources available for this connection'}
              </p>
              {(searchQuery || resourceType) && (
                <Button 
                  variant="link" 
                  onClick={handleClearFilters}
                  className="mt-2"
                >
                  Clear filters
                </Button>
              )}
            </div>
          )}
        </div>
        
        <DialogFooter className="mt-4">
          <div className="flex justify-between items-center w-full">
            <div className="text-sm text-gray-500">
              {selectedResourceIds.size} resources selected
            </div>
            <Button onClick={onClose}>Done</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
