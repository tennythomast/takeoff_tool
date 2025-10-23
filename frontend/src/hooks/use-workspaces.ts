import { useState, useEffect, useCallback } from 'react';
import { workspaceService, Workspace, CreateWorkspaceRequest } from '@/lib/services/workspace-service';

interface UseWorkspacesOptions {
  initialFilters?: Record<string, any>;
  autoFetch?: boolean;
}

export function useWorkspaces(options: UseWorkspacesOptions = {}) {
  const { initialFilters = {}, autoFetch = true } = options;
  
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState(initialFilters);
  
  const fetchWorkspaces = useCallback(async (currentFilters = filters) => {
    console.log('fetchWorkspaces called with currentFilters:', currentFilters);
    console.log('Current filters state:', filters);
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Deep clone the filters to avoid reference issues
      const clonedFilters = currentFilters ? {...currentFilters} : {};
      console.log('Cloned filters:', clonedFilters);
      
      // Update the filters state with the current filters
      if (JSON.stringify(clonedFilters) !== JSON.stringify(filters)) {
        console.log('Filters changed, updating state');
        setFilters(clonedFilters);
      } else {
        console.log('Filters unchanged');
      }
      
      // Make the API call with the current filters
      console.log('Making API call with filters:', clonedFilters);
      const data = await workspaceService.getWorkspaces(clonedFilters);
      console.log('useWorkspaces hook received data:', data);
      
      // Check if data is in the expected format
      if (data && typeof data === 'object' && 'workspaces' in data && Array.isArray(data.workspaces)) {
        // If the API returns { workspaces: [...] } structure
        console.log('Found workspaces property in response');
        const workspacesArray = data.workspaces as Workspace[];
        setWorkspaces(workspacesArray);
        return workspacesArray;
      } else if (Array.isArray(data)) {
        // If the API directly returns an array
        const workspacesArray = data as Workspace[];
        setWorkspaces(workspacesArray);
        return workspacesArray;
      } else {
        console.error('Unexpected data format:', data);
        setWorkspaces([]);
        return [];
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch workspaces'));
      return [];
    } finally {
      setIsLoading(false);
    }
  }, [filters]);
  
  const createWorkspace = useCallback(async (data: CreateWorkspaceRequest) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const newWorkspace = await workspaceService.createWorkspace(data);
      setWorkspaces(prev => [newWorkspace, ...prev]);
      return newWorkspace;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to create workspace'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const updateWorkspace = useCallback(async (id: string, data: Partial<Workspace>) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedWorkspace = await workspaceService.updateWorkspace(id, data);
      setWorkspaces(prev => 
        prev.map(workspace => workspace.id === id ? updatedWorkspace : workspace)
      );
      return updatedWorkspace;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to update workspace'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const archiveWorkspace = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const archivedWorkspace = await workspaceService.archiveWorkspace(id);
      setWorkspaces(prev => 
        prev.map(workspace => workspace.id === id ? archivedWorkspace : workspace)
      );
      return archivedWorkspace;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to archive workspace'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const completeWorkspace = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const completedWorkspace = await workspaceService.completeWorkspace(id);
      setWorkspaces(prev => 
        prev.map(workspace => workspace.id === id ? completedWorkspace : workspace)
      );
      return completedWorkspace;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to complete workspace'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const applyFilters = useCallback((newFilters: Record<string, any>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    return fetchWorkspaces(updatedFilters);
  }, [filters, fetchWorkspaces]);
  
  // Fetch workspaces when filters change or on initial load
  useEffect(() => {
    if (autoFetch) {
      console.log('Auto-fetching workspaces with filters:', filters);
      fetchWorkspaces(filters);
    }
  }, [autoFetch, filters, fetchWorkspaces]);
  
  // Update filters when initialFilters change
  useEffect(() => {
    if (JSON.stringify(initialFilters) !== JSON.stringify(filters)) {
      console.log('Updating filters from initialFilters:', initialFilters);
      setFilters(initialFilters);
    }
  }, [initialFilters]);
  
  return {
    workspaces,
    isLoading,
    error,
    filters,
    fetchWorkspaces,
    createWorkspace,
    updateWorkspace,
    archiveWorkspace,
    completeWorkspace,
    applyFilters,
  };
}

export function useWorkspace(id: string | null) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchWorkspace = useCallback(async () => {
    if (!id) return null;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await workspaceService.getWorkspace(id);
      setWorkspace(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch workspace'));
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [id]);
  
  const updateWorkspace = useCallback(async (data: Partial<Workspace>) => {
    if (!id || !workspace) return null;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedWorkspace = await workspaceService.updateWorkspace(id, data);
      setWorkspace(updatedWorkspace);
      return updatedWorkspace;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to update workspace'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [id, workspace]);
  
  useEffect(() => {
    if (id) {
      fetchWorkspace();
    } else {
      setWorkspace(null);
    }
  }, [id, fetchWorkspace]);
  
  return {
    workspace,
    isLoading,
    error,
    fetchWorkspace,
    updateWorkspace,
  };
}
