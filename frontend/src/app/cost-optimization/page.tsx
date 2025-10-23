'use client';

import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import HeroMetrics from '@/components/dashboard/HeroMetrics';
import CostComparisonChart from '@/components/dashboard/CostComparisonChart';
import ModelPerformanceTable from '@/components/dashboard/ModelPerformanceTable';
import StrategyPanel from '@/components/dashboard/StrategyPanel';
import OptimizationInsights from '@/components/dashboard/OptimizationInsights';
import DashboardSummary from '@/components/dashboard/DashboardSummary';
import { useDashboardData } from '@/hooks/useDashboardData';
import { TimeRange } from '@/types/dashboard';
import { Button } from '@/components/ui/button';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

// Create a query client instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

function DashboardContent() {
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange['days']>(30);
  
  const {
    data,
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useDashboardData({
    days: selectedTimeRange,
    refetchInterval: 30000, // 30 seconds
  });

  const handleTimeRangeChange = (days: TimeRange['days']) => {
    setSelectedTimeRange(days);
  };

  const handleRefresh = () => {
    refetch();
  };

  return (
    <DashboardLayout>
      {/* Error Alert */}
      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-red-800">
            {error.message}
            <Button
              variant="link"
              size="sm"
              onClick={handleRefresh}
              className="ml-2 p-0 h-auto text-red-600 underline"
            >
              Try again
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Hero Metrics Section */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-900">
            Key Performance Metrics
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefetching}
            className="text-slate-600"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`} />
            {isRefetching ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
        
        <HeroMetrics
          data={data}
          isLoading={isLoading}
          error={error}
        />
      </section>

      {/* Cost Comparison Chart Section */}
      <section>
        <CostComparisonChart
          data={data}
          isLoading={isLoading}
          error={error}
          selectedTimeRange={selectedTimeRange}
          onTimeRangeChange={handleTimeRangeChange}
          onRefresh={handleRefresh}
        />
      </section>

      {/* Performance Summary */}
      <section>
        <DashboardSummary
          data={data}
          isLoading={isLoading}
          error={error}
        />
      </section>

      {/* Model Performance and Strategy Effectiveness */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelPerformanceTable
          models={data?.optimization_stats?.models_breakdown}
          isLoading={isLoading}
          error={error}
        />
        
        <StrategyPanel
          strategies={data?.optimization_stats?.strategies_used}
          isLoading={isLoading}
          error={error}
        />
      </section>

      {/* Optimization Insights */}
      <section>
        <OptimizationInsights
          recommendations={data?.optimization_stats?.recommendations}
          isLoading={isLoading}
          error={error}
        />
      </section>

      {/* Auto-refresh indicator */}
      <div className="text-center text-sm text-slate-500">
        <p>Dashboard auto-refreshes every 30 seconds</p>
        {data && (
          <p className="mt-1">
            Last updated: {new Date().toLocaleTimeString()}
          </p>
        )}
      </div>
    </DashboardLayout>
  );
}

export default function CostOptimizationDashboard() {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardContent />
    </QueryClientProvider>
  );
}
