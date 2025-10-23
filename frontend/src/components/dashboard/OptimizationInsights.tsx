import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Lightbulb, 
  AlertTriangle, 
  TrendingUp, 
  Settings, 
  Key,
  Clock,
  ChevronRight,
  CheckCircle
} from 'lucide-react';
import { OptimizationRecommendation } from '@/types/dashboard';
import { cn } from '@/lib/utils';

interface OptimizationInsightsProps {
  recommendations?: OptimizationRecommendation[];
  isLoading: boolean;
  error?: Error | null;
}

const recommendationConfig = {
  strategy: {
    icon: TrendingUp,
    color: 'blue',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
  },
  model: {
    icon: Settings,
    color: 'purple',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    textColor: 'text-purple-800',
  },
  api_key: {
    icon: Key,
    color: 'orange',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    textColor: 'text-orange-800',
  },
  general: {
    icon: Lightbulb,
    color: 'green',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-800',
  },
};

const priorityConfig = {
  high: {
    label: 'High Priority',
    color: 'bg-red-100 text-red-800',
    icon: AlertTriangle,
  },
  medium: {
    label: 'Medium Priority',
    color: 'bg-yellow-100 text-yellow-800',
    icon: Clock,
  },
  low: {
    label: 'Low Priority',
    color: 'bg-slate-100 text-slate-600',
    icon: CheckCircle,
  },
};

export default function OptimizationInsights({
  recommendations = [],
  isLoading,
  error,
}: OptimizationInsightsProps) {
  const [dismissedIds, setDismissedIds] = React.useState<Set<string>>(new Set());

  const visibleRecommendations = recommendations.filter(
    rec => !dismissedIds.has(rec.id)
  );

  const sortedRecommendations = React.useMemo(() => {
    const priorityOrder = { high: 3, medium: 2, low: 1 };
    return [...visibleRecommendations].sort((a, b) => {
      // Sort by priority first, then by potential savings
      const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return b.potential_savings - a.potential_savings;
    });
  }, [visibleRecommendations]);

  const handleDismiss = (id: string) => {
    setDismissedIds(prev => new Set([...prev, id]));
  };

  const formatCurrency = (value: number) => {
    return value < 1 ? `$${value.toFixed(4)}` : `$${value.toLocaleString()}`;
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}d ago`;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Optimization Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 p-3 border rounded-lg">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-full" />
                  <div className="flex gap-2">
                    <Skeleton className="h-5 w-16" />
                    <Skeleton className="h-5 w-20" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Error Loading Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-600">{error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!sortedRecommendations.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Optimization Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-slate-500">
            <div className="text-4xl mb-2">💡</div>
            <p className="font-medium mb-1">All optimized!</p>
            <p className="text-sm">No new recommendations at this time</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-yellow-500" />
            <span>Optimization Insights</span>
          </div>
          <Badge variant="outline" className="text-xs">
            {sortedRecommendations.length} active
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          {sortedRecommendations.map((recommendation) => {
            const typeConfig = recommendationConfig[recommendation.type];
            const priorityInfo = priorityConfig[recommendation.priority];
            const TypeIcon = typeConfig?.icon || Lightbulb;
            const PriorityIcon = priorityInfo?.icon || CheckCircle;

            return (
              <div
                key={recommendation.id}
                className={cn(
                  "p-4 rounded-lg border transition-all duration-200 hover:shadow-md",
                  typeConfig?.bgColor || 'bg-slate-50',
                  typeConfig?.borderColor || 'border-slate-200'
                )}
              >
                <div className="flex items-start gap-3">
                  {/* Type Icon */}
                  <div className={cn(
                    "p-2 rounded-lg flex-shrink-0",
                    typeConfig?.bgColor || 'bg-slate-100'
                  )}>
                    <TypeIcon className={cn(
                      "h-4 w-4",
                      typeConfig?.textColor || 'text-slate-600'
                    )} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-semibold text-slate-900 text-sm">
                        {recommendation.title}
                      </h3>
                      
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Badge 
                          variant="outline" 
                          className={cn("text-xs", priorityInfo?.color)}
                        >
                          <PriorityIcon className="h-3 w-3 mr-1" />
                          {priorityInfo?.label}
                        </Badge>
                      </div>
                    </div>

                    <p className="text-sm text-slate-600 mb-3 leading-relaxed">
                      {recommendation.description}
                    </p>

                    {/* Metrics */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <div className="flex items-center gap-1">
                          <span>Potential savings:</span>
                          <span className="font-medium text-green-600">
                            {formatCurrency(recommendation.potential_savings)}/month
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          <span>{formatTimeAgo(recommendation.created_at)}</span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDismiss(recommendation.id)}
                          className="text-xs text-slate-500 hover:text-slate-700"
                        >
                          Dismiss
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs"
                        >
                          View Details
                          <ChevronRight className="h-3 w-3 ml-1" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Summary */}
        {sortedRecommendations.length > 0 && (
          <div className="mt-6 pt-4 border-t border-slate-200">
            <div className="grid grid-cols-3 gap-4 text-center text-sm">
              <div>
                <div className="text-slate-600">Total Potential</div>
                <div className="font-semibold text-green-600">
                  {formatCurrency(
                    sortedRecommendations.reduce((sum, rec) => sum + rec.potential_savings, 0)
                  )}/month
                </div>
              </div>
              <div>
                <div className="text-slate-600">High Priority</div>
                <div className="font-semibold text-red-600">
                  {sortedRecommendations.filter(rec => rec.priority === 'high').length}
                </div>
              </div>
              <div>
                <div className="text-slate-600">This Week</div>
                <div className="font-semibold text-slate-900">
                  {sortedRecommendations.filter(rec => {
                    const weekAgo = new Date();
                    weekAgo.setDate(weekAgo.getDate() - 7);
                    return new Date(rec.created_at) > weekAgo;
                  }).length} new
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-4 text-xs text-slate-500">
          <p>Recommendations are updated in real-time based on your usage patterns</p>
        </div>
      </CardContent>
    </Card>
  );
}
