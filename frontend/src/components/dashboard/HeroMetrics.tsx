import React from 'react';
import { DollarSign, TrendingDown, Zap, Target } from 'lucide-react';
import MetricCard from './MetricCard';
import { DashboardSummary } from '@/types/dashboard';
import { Skeleton } from '@/components/ui/skeleton';

interface HeroMetricsProps {
  data?: DashboardSummary;
  isLoading: boolean;
  error?: Error | null;
}

export default function HeroMetrics({ data, isLoading, error }: HeroMetricsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <MetricCard
            key={i}
            title="Error Loading"
            value="--"
            subtitle="Unable to load data"
            className="border-red-200 bg-red-50/50"
          />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <MetricCard
            key={i}
            title="No Data"
            value="--"
            subtitle="No data available"
          />
        ))}
      </div>
    );
  }

  const { cost_summary, optimization_stats } = data;
  
  // Calculate metrics
  const totalSavings = optimization_stats.total_savings;
  const savingsPercentage = optimization_stats.savings_percentage;
  const avgCostPerRequest = cost_summary.avg_cost_per_request;
  const optimizationRate = optimization_stats.optimization_rate;

  // Calculate month-over-month trends (mock data for now - would come from API)
  const savingsTrend = { value: 12.5, isPositive: true };
  const costTrend = { value: -8.3, isPositive: true }; // Negative cost change is positive
  const optimizationTrend = { value: 5.2, isPositive: true };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <MetricCard
        title="Total Savings"
        value={totalSavings}
        subtitle={`${savingsPercentage.toFixed(1)}% saved vs standard pricing`}
        trend={savingsTrend}
        icon={<DollarSign className="h-4 w-4" />}
        className="border-green-200 bg-green-50/50"
      />
      
      <MetricCard
        title="This Month"
        value={totalSavings * 0.3} // Approximate current month savings
        subtitle="Current month savings"
        trend={savingsTrend}
        icon={<TrendingDown className="h-4 w-4" />}
        className="border-blue-200 bg-blue-50/50"
      />
      
      <MetricCard
        title="Avg Cost/Request"
        value={avgCostPerRequest}
        subtitle="Optimized cost per API call"
        trend={costTrend}
        icon={<Zap className="h-4 w-4" />}
        className="border-purple-200 bg-purple-50/50"
      />
      
      <MetricCard
        title="Optimization Rate"
        value={optimizationRate}
        subtitle="Requests that were optimized"
        trend={optimizationTrend}
        icon={<Target className="h-4 w-4" />}
        className="border-orange-200 bg-orange-50/50"
      />
    </div>
  );
}
