import { useState, useEffect, useCallback } from 'react';
import { projectService, Project, CreateProjectRequest } from '@/lib/services/project-service';

interface UseProjectsOptions {
  initialFilters?: Record<string, any>;
  autoFetch?: boolean;
}

export function useProjects(options: UseProjectsOptions = {}) {
  const { initialFilters = {}, autoFetch = true } = options;
  
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState(initialFilters);
  
  const fetchProjects = useCallback(async (currentFilters = filters) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await projectService.getProjects(currentFilters);
      setProjects(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch projects'));
      return [];
    } finally {
      setIsLoading(false);
    }
  }, [filters]);
  
  const createProject = useCallback(async (data: CreateProjectRequest) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const newProject = await projectService.createProject(data);
      setProjects(prev => [newProject, ...prev]);
      return newProject;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to create project'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const updateProject = useCallback(async (id: string, data: Partial<Project>) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedProject = await projectService.updateProject(id, data);
      setProjects(prev => 
        prev.map(project => project.id === id ? updatedProject : project)
      );
      return updatedProject;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to update project'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const archiveProject = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const archivedProject = await projectService.archiveProject(id);
      setProjects(prev => 
        prev.map(project => project.id === id ? archivedProject : project)
      );
      return archivedProject;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to archive project'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const applyFilters = useCallback((newFilters: Record<string, any>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    return fetchProjects(updatedFilters);
  }, [filters, fetchProjects]);
  
  useEffect(() => {
    if (autoFetch) {
      fetchProjects();
    }
  }, [autoFetch, fetchProjects]);
  
  return {
    projects,
    isLoading,
    error,
    filters,
    fetchProjects,
    createProject,
    updateProject,
    archiveProject,
    applyFilters,
  };
}

export function useProject(id: string | null) {
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchProject = useCallback(async () => {
    if (!id) return null;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await projectService.getProject(id);
      setProject(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch project'));
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [id]);
  
  const updateProject = useCallback(async (data: Partial<Project>) => {
    if (!id || !project) return null;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedProject = await projectService.updateProject(id, data);
      setProject(updatedProject);
      return updatedProject;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to update project'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [id, project]);
  
  useEffect(() => {
    if (id) {
      fetchProject();
    } else {
      setProject(null);
    }
  }, [id, fetchProject]);
  
  return {
    project,
    isLoading,
    error,
    fetchProject,
    updateProject,
  };
}
