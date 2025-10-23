import React, { useState } from 'react';
import {
  LineChart,
  Line,
  Area,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw, TrendingDown } from 'lucide-react';
import { DashboardSummary, ChartDataPoint, TimeRange } from '@/types/dashboard';
import { useTimeRange } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

interface CostComparisonChartProps {
  data?: DashboardSummary;
  isLoading: boolean;
  error?: Error | null;
  selectedTimeRange: TimeRange['days'];
  onTimeRangeChange: (days: TimeRange['days']) => void;
  onRefresh: () => void;
}

export default function CostComparisonChart({
  data,
  isLoading,
  error,
  selectedTimeRange,
  onTimeRangeChange,
  onRefresh,
}: CostComparisonChartProps) {
  const { timeRanges } = useTimeRange();

  // Transform API data to chart format
  const chartData: ChartDataPoint[] = React.useMemo(() => {
    if (!data?.optimization_stats?.cost_savings_details) return [];

    return data.optimization_stats.cost_savings_details.map((detail) => ({
      date: new Date(detail.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      actualCost: detail.actual_cost,
      baselineCost: detail.baseline_cost,
      savings: detail.savings,
    }));
  }, [data]);

  // Calculate total savings for display
  const totalSavings = React.useMemo(() => {
    return chartData.reduce((sum, point) => sum + point.savings, 0);
  }, [chartData]);

  const savingsPercentage = React.useMemo(() => {
    if (!data?.optimization_stats?.savings_percentage) return 0;
    return data.optimization_stats.savings_percentage;
  }, [data]);

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const actualCost = payload.find((p: any) => p.dataKey === 'actualCost')?.value || 0;
      const baselineCost = payload.find((p: any) => p.dataKey === 'baselineCost')?.value || 0;
      const savings = baselineCost - actualCost;
      const savingsPercent = baselineCost > 0 ? (savings / baselineCost) * 100 : 0;

      return (
        <div className="bg-white p-4 border border-slate-200 rounded-lg shadow-lg">
          <p className="font-medium text-slate-900 mb-2">{label}</p>
          <div className="space-y-1 text-sm">
            <div className="flex items-center justify-between gap-4">
              <span className="text-green-600">Your Cost:</span>
              <span className="font-medium">${actualCost.toFixed(4)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-red-600">Standard Cost:</span>
              <span className="font-medium">${baselineCost.toFixed(4)}</span>
            </div>
            <hr className="my-2" />
            <div className="flex items-center justify-between gap-4">
              <span className="text-slate-600">Savings:</span>
              <span className="font-medium text-green-600">
                ${savings.toFixed(4)} ({savingsPercent.toFixed(1)}%)
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Cost Comparison</CardTitle>
            <Skeleton className="h-8 w-24" />
          </div>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-80 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Error Loading Chart</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <p className="text-slate-600 mb-4">{error.message}</p>
            <Button onClick={onRefresh} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold text-slate-900">
              Cost Comparison
            </CardTitle>
            <div className="flex items-center gap-2 mt-2">
              <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                <TrendingDown className="h-3 w-3 mr-1" />
                ${totalSavings.toFixed(2)} saved ({savingsPercentage.toFixed(1)}%)
              </Badge>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-slate-200 p-1">
              {timeRanges.map((range) => (
                <Button
                  key={range.days}
                  variant={selectedTimeRange === range.days ? "default" : "ghost"}
                  size="sm"
                  onClick={() => onTimeRangeChange(range.days)}
                  className={cn(
                    "text-xs",
                    selectedTimeRange === range.days
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:text-slate-900"
                  )}
                >
                  {range.label}
                </Button>
              ))}
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              className="text-slate-600"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="savingsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis 
                dataKey="date" 
                stroke="#64748b"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                stroke="#64748b"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => `$${value.toFixed(3)}`}
              />
              <Tooltip content={<CustomTooltip />} />
              
              {/* Savings area fill */}
              <Area
                type="monotone"
                dataKey="baselineCost"
                stroke="none"
                fill="url(#savingsGradient)"
                fillOpacity={1}
              />
              
              {/* Baseline cost line (red) */}
              <Line
                type="monotone"
                dataKey="baselineCost"
                stroke="#ef4444"
                strokeWidth={2}
                dot={{ fill: '#ef4444', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, stroke: '#ef4444', strokeWidth: 2 }}
              />
              
              {/* Actual cost line (green) */}
              <Line
                type="monotone"
                dataKey="actualCost"
                stroke="#22c55e"
                strokeWidth={3}
                dot={{ fill: '#22c55e', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, stroke: '#22c55e', strokeWidth: 2 }}
              />
              
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                iconType="line"
                formatter={(value) => (
                  <span className="text-sm text-slate-600">
                    {value === 'actualCost' ? 'Your Optimized Cost' : 'Standard Pricing'}
                  </span>
                )}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 text-center">
          <p className="text-sm text-slate-600">
            Green area represents your savings through intelligent model routing
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
