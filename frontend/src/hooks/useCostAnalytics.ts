import { useMemo } from 'react';
import { DashboardSummary, ChartDataPoint } from '@/types/dashboard';

interface CostAnalyticsResult {
  chartData: ChartDataPoint[];
  totalSavings: number;
  averageSavingsPercentage: number;
  savingsTrend: {
    value: number;
    isPositive: boolean;
  };
  costEfficiencyScore: number;
  projectedMonthlySavings: number;
}

export function useCostAnalytics(data?: DashboardSummary): CostAnalyticsResult {
  return useMemo(() => {
    if (!data?.optimization_stats?.cost_savings_details) {
      return {
        chartData: [],
        totalSavings: 0,
        averageSavingsPercentage: 0,
        savingsTrend: { value: 0, isPositive: true },
        costEfficiencyScore: 0,
        projectedMonthlySavings: 0,
      };
    }

    const { cost_savings_details, savings_percentage, total_savings } = data.optimization_stats;

    // Transform data for chart
    const chartData: ChartDataPoint[] = cost_savings_details.map((detail) => ({
      date: new Date(detail.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      actualCost: detail.actual_cost,
      baselineCost: detail.baseline_cost,
      savings: detail.savings,
    }));

    // Calculate savings trend (comparing first half vs second half of data)
    const midPoint = Math.floor(cost_savings_details.length / 2);
    const firstHalfAvg = cost_savings_details
      .slice(0, midPoint)
      .reduce((sum, detail) => sum + detail.savings, 0) / midPoint;
    const secondHalfAvg = cost_savings_details
      .slice(midPoint)
      .reduce((sum, detail) => sum + detail.savings, 0) / (cost_savings_details.length - midPoint);
    
    const trendValue = firstHalfAvg > 0 ? ((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100 : 0;
    const savingsTrend = {
      value: Math.abs(trendValue),
      isPositive: trendValue >= 0,
    };

    // Calculate cost efficiency score (0-100)
    const maxPossibleSavings = cost_savings_details.reduce((sum, detail) => sum + detail.baseline_cost, 0);
    const actualSavings = cost_savings_details.reduce((sum, detail) => sum + detail.savings, 0);
    const costEfficiencyScore = maxPossibleSavings > 0 ? (actualSavings / maxPossibleSavings) * 100 : 0;

    // Project monthly savings based on recent trend
    const recentDays = Math.min(7, cost_savings_details.length);
    const recentSavings = cost_savings_details
      .slice(-recentDays)
      .reduce((sum, detail) => sum + detail.savings, 0);
    const dailyAverage = recentSavings / recentDays;
    const projectedMonthlySavings = dailyAverage * 30;

    return {
      chartData,
      totalSavings: total_savings,
      averageSavingsPercentage: savings_percentage,
      savingsTrend,
      costEfficiencyScore,
      projectedMonthlySavings,
    };
  }, [data]);
}

// Helper hook for currency formatting
export function useCurrencyFormatter() {
  return useMemo(() => ({
    format: (value: number): string => {
      if (value < 0.01) return `$${value.toFixed(4)}`;
      if (value < 1) return `$${value.toFixed(3)}`;
      if (value < 1000) return `$${value.toFixed(2)}`;
      return `$${(value / 1000).toFixed(1)}k`;
    },
    formatPrecise: (value: number): string => {
      return value < 1 ? `$${value.toFixed(4)}` : `$${value.toLocaleString()}`;
    },
  }), []);
}

// Helper hook for percentage formatting
export function usePercentageFormatter() {
  return useMemo(() => ({
    format: (value: number): string => `${value.toFixed(1)}%`,
    formatPrecise: (value: number): string => `${value.toFixed(2)}%`,
  }), []);
}
