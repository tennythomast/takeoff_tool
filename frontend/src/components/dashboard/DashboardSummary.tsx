import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  TrendingUp, 
  Target, 
  Award, 
  AlertCircle,
  CheckCircle,
  Lightbulb
} from 'lucide-react';
import { DashboardSummary as DashboardSummaryType } from '@/types/dashboard';
import { useOptimizationStats, useOptimizationInsights } from '@/hooks/useOptimizationStats';
import { useCostAnalytics } from '@/hooks/useCostAnalytics';
import { cn } from '@/lib/utils';

interface DashboardSummaryProps {
  data?: DashboardSummaryType;
  isLoading: boolean;
  error?: Error | null;
}

export default function DashboardSummary({
  data,
  isLoading,
  error,
}: DashboardSummaryProps) {
  const optimizationStats = useOptimizationStats(data);
  const costAnalytics = useCostAnalytics(data);
  const insights = useOptimizationInsights(optimizationStats);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-2 w-full" />
              </div>
              <div className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-2 w-full" />
              </div>
            </div>
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Summary Unavailable</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-600">
            {error?.message || 'Unable to load performance summary'}
          </p>
        </CardContent>
      </Card>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 80) return 'bg-green-100 text-green-800';
    if (score >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Award className="h-5 w-5 text-yellow-500" />
            <span>Performance Summary</span>
          </div>
          <Badge 
            className={cn("text-xs", getScoreBadgeColor(optimizationStats.optimizationScore))}
          >
            {optimizationStats.optimizationScore.toFixed(0)}/100 Score
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Key Performance Indicators */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Optimization Score</span>
              <span className={cn("font-medium", getScoreColor(optimizationStats.optimizationScore))}>
                {optimizationStats.optimizationScore.toFixed(0)}%
              </span>
            </div>
            <Progress 
              value={optimizationStats.optimizationScore} 
              className="h-2"
            />
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Model Diversity</span>
              <span className={cn("font-medium", getScoreColor(optimizationStats.modelDiversityScore))}>
                {optimizationStats.modelDiversityScore.toFixed(0)}%
              </span>
            </div>
            <Progress 
              value={optimizationStats.modelDiversityScore} 
              className="h-2"
            />
          </div>
        </div>

        {/* Top Performers */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium text-green-800">Top Model</span>
            </div>
            <div className="text-lg font-bold text-green-900">
              {optimizationStats.topPerformingModel?.model_name || 'N/A'}
            </div>
            {optimizationStats.topPerformingModel && (
              <div className="text-xs text-green-700">
                {optimizationStats.topPerformingModel.savings_percentage.toFixed(1)}% savings, {' '}
                {optimizationStats.topPerformingModel.success_rate.toFixed(1)}% success
              </div>
            )}
          </div>

          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-800">Best Strategy</span>
            </div>
            <div className="text-lg font-bold text-blue-900">
              {optimizationStats.mostEfficientStrategy?.strategy_name.replace('_', ' ').toUpperCase() || 'N/A'}
            </div>
            {optimizationStats.mostEfficientStrategy && (
              <div className="text-xs text-blue-700">
                ${optimizationStats.mostEfficientStrategy.avg_savings.toFixed(4)} avg savings
              </div>
            )}
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-slate-900">
              {optimizationStats.performanceMetrics.totalRequests.toLocaleString()}
            </div>
            <div className="text-xs text-slate-600">Total Requests</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-600">
              {optimizationStats.performanceMetrics.avgSuccessRate.toFixed(1)}%
            </div>
            <div className="text-xs text-slate-600">Success Rate</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600">
              {costAnalytics.projectedMonthlySavings < 1 
                ? `$${costAnalytics.projectedMonthlySavings.toFixed(4)}`
                : `$${costAnalytics.projectedMonthlySavings.toLocaleString()}`
              }
            </div>
            <div className="text-xs text-slate-600">Projected Monthly</div>
          </div>
        </div>

        {/* AI Insights */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-yellow-500" />
            <span className="text-sm font-medium text-slate-700">AI Insights</span>
          </div>
          
          <div className="space-y-2">
            {insights.slice(0, 3).map((insight, index) => (
              <div key={index} className="flex items-start gap-2 text-sm">
                <div className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-2 flex-shrink-0" />
                <span className="text-slate-600 leading-relaxed">{insight}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations Alert */}
        {optimizationStats.recommendationsSummary.highPriority > 0 && (
          <div className="p-3 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <span className="text-sm font-medium text-red-800">
                {optimizationStats.recommendationsSummary.highPriority} high-priority recommendations
              </span>
            </div>
            <div className="text-xs text-red-700 mt-1">
              Potential savings: ${optimizationStats.recommendationsSummary.potentialSavings.toFixed(2)}/month
            </div>
          </div>
        )}

        {/* Status Indicator */}
        <div className="flex items-center justify-center pt-2 border-t border-slate-200">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span>Live data • Updates every 30 seconds</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
