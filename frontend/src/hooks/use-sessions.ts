import { useState, useEffect, useCallback } from 'react';
import { projectService, Session, CreateSessionRequest } from '@/lib/services/project-service';

interface UseSessionsOptions {
  projectId?: string;
  initialFilters?: Record<string, any>;
  autoFetch?: boolean;
}

export function useSessions(options: UseSessionsOptions = {}) {
  const { projectId, initialFilters = {}, autoFetch = true } = options;
  
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState(initialFilters);
  
  const fetchSessions = useCallback(async (currentFilters = filters) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await projectService.getSessions(projectId, currentFilters);
      setSessions(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch sessions'));
      return [];
    } finally {
      setIsLoading(false);
    }
  }, [projectId, filters]);
  
  const createSession = useCallback(async (data: CreateSessionRequest) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const newSession = await projectService.createSession(data);
      setSessions(prev => [newSession, ...prev]);
      return newSession;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to create session'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const updateSession = useCallback(async (id: string, data: Partial<Session>) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedSession = await projectService.updateSession(id, data);
      setSessions(prev => 
        prev.map(session => session.id === id ? updatedSession : session)
      );
      return updatedSession;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to update session'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const reassignSession = useCallback(async (sessionId: string, newProjectId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedSession = await projectService.reassignSession(sessionId, newProjectId);
      
      // If we're viewing sessions for a specific project and the session was moved to another project,
      // remove it from the current list
      if (projectId && projectId !== newProjectId) {
        setSessions(prev => prev.filter(session => session.id !== sessionId));
      } else {
        setSessions(prev => 
          prev.map(session => session.id === sessionId ? updatedSession : session)
        );
      }
      
      return updatedSession;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to reassign session'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);
  
  const applyFilters = useCallback((newFilters: Record<string, any>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    return fetchSessions(updatedFilters);
  }, [filters, fetchSessions]);
  
  useEffect(() => {
    if (autoFetch) {
      fetchSessions();
    }
  }, [autoFetch, fetchSessions]);
  
  return {
    sessions,
    isLoading,
    error,
    filters,
    fetchSessions,
    createSession,
    updateSession,
    reassignSession,
    applyFilters,
  };
}

export function useSession(id: string | null) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchSession = useCallback(async () => {
    if (!id) return null;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await projectService.getSession(id);
      setSession(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch session'));
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [id]);
  
  const updateSession = useCallback(async (data: Partial<Session>) => {
    if (!id || !session) return null;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedSession = await projectService.updateSession(id, data);
      setSession(updatedSession);
      return updatedSession;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to update session'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [id, session]);
  
  const reassignSession = useCallback(async (newProjectId: string) => {
    if (!id || !session) return null;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedSession = await projectService.reassignSession(id, newProjectId);
      setSession(updatedSession);
      return updatedSession;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to reassign session'));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [id, session]);
  
  useEffect(() => {
    if (id) {
      fetchSession();
    } else {
      setSession(null);
    }
  }, [id, fetchSession]);
  
  return {
    session,
    isLoading,
    error,
    fetchSession,
    updateSession,
    reassignSession,
  };
}
