import { useState, useEffect } from 'react';

interface Session {
  id: string;
  name: string;
  status: string;
  agentName: string;
  duration: string;
  timestamp: string;
  // Add other session properties as needed
}

interface UseSessionsOptions {
  projectId?: string;
  agentId?: string;
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export function useSessions(options: UseSessionsOptions) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setIsLoading(true);
        
        // Build query params
        const params = new URLSearchParams();
        if (options.projectId) params.append('projectId', options.projectId);
        if (options.agentId) params.append('agentId', options.agentId);
        if (options.dateRange) {
          params.append('startDate', options.dateRange.start.toISOString());
          params.append('endDate', options.dateRange.end.toISOString());
        }
        
        // Replace with your actual API call
        const response = await fetch(`/api/sessions?${params.toString()}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch sessions: ${response.statusText}`);
        }
        
        const data = await response.json();
        setSessions(data);
      } catch (err: any) {
        setError(err);
        console.error('Error fetching sessions:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSessions();
  }, [options.projectId, options.agentId, options.dateRange]);

  return { sessions, isLoading, error };
}
