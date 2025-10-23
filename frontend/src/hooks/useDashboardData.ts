import { useQuery } from '@tanstack/react-query';
import { DashboardSummary, TimeRange } from '@/types/dashboard';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

interface UseDashboardDataOptions {
  days?: 7 | 30 | 90;
  refetchInterval?: number;
}

async function fetchDashboardSummary(days: number): Promise<DashboardSummary> {
  const token = localStorage.getItem('authToken');
  
  if (!token) {
    throw new Error('Authentication token not found');
  }

  const response = await fetch(
    `${API_BASE_URL}/api/modelhub/metrics/dashboard_summary/?days=${days}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized - please log in again');
    }
    if (response.status === 400) {
      throw new Error('Invalid request parameters');
    }
    throw new Error(`Failed to fetch dashboard data: ${response.statusText}`);
  }

  return response.json();
}

export function useDashboardData(options: UseDashboardDataOptions = {}) {
  const { days = 30, refetchInterval = 30000 } = options; // Default 30 seconds auto-refresh

  return useQuery({
    queryKey: ['dashboard-summary', days],
    queryFn: () => fetchDashboardSummary(days),
    refetchInterval,
    refetchIntervalInBackground: true,
    staleTime: 25000, // Consider data stale after 25 seconds
    retry: (failureCount, error) => {
      // Don't retry on auth errors
      if (error.message.includes('Unauthorized')) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

// Helper hook for time range management
export function useTimeRange() {
  const timeRanges: TimeRange[] = [
    { days: 7, label: '7 days' },
    { days: 30, label: '30 days' },
    { days: 90, label: '90 days' },
  ];

  return { timeRanges };
}
