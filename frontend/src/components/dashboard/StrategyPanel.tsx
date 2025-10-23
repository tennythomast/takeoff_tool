import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { DollarSign, Target, Zap, TrendingUp } from 'lucide-react';
import { StrategyUsage } from '@/types/dashboard';
import { cn } from '@/lib/utils';

interface StrategyPanelProps {
  strategies?: StrategyUsage[];
  isLoading: boolean;
  error?: Error | null;
}

const strategyConfig = {
  cost_first: {
    name: 'Cost First',
    description: 'Prioritizes lowest cost models',
    icon: DollarSign,
    color: 'green',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-800',
  },
  balanced: {
    name: 'Balanced',
    description: 'Optimizes cost and quality',
    icon: Target,
    color: 'blue',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
  },
  quality_first: {
    name: 'Quality First',
    description: 'Prioritizes best performing models',
    icon: Zap,
    color: 'purple',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    textColor: 'text-purple-800',
  },
};

export default function StrategyPanel({
  strategies = [],
  isLoading,
  error,
}: StrategyPanelProps) {
  const totalRequests = React.useMemo(() => {
    return strategies.reduce((sum, strategy) => sum + strategy.requests, 0);
  }, [strategies]);

  const bestStrategy = React.useMemo(() => {
    if (!strategies.length) return null;
    return strategies.reduce((best, current) => 
      current.avg_savings > best.avg_savings ? current : best
    );
  }, [strategies]);

  const formatCurrency = (value: number) => {
    return value < 1 ? `$${value.toFixed(4)}` : `$${value.toLocaleString()}`;
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Strategy Effectiveness</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="space-y-3 p-4 border rounded-lg">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-5 w-24" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-2 w-full" />
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16" />
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
          <CardTitle className="text-red-600">Error Loading Strategies</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-600">{error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!strategies.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Strategy Effectiveness</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-slate-500">
            <div className="text-4xl mb-2">🎯</div>
            <p>No strategy data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Strategy Effectiveness</span>
          {bestStrategy && (
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
              <TrendingUp className="h-3 w-3 mr-1" />
              Best: {strategyConfig[bestStrategy.strategy_name]?.name}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <div className="grid gap-4">
          {strategies.map((strategy) => {
            const config = strategyConfig[strategy.strategy_name];
            const Icon = config?.icon || Target;
            const usagePercentage = totalRequests > 0 
              ? (strategy.requests / totalRequests) * 100 
              : 0;

            return (
              <div
                key={strategy.strategy_name}
                className={cn(
                  "p-4 rounded-lg border transition-all duration-200 hover:shadow-md",
                  config?.bgColor || 'bg-slate-50',
                  config?.borderColor || 'border-slate-200'
                )}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "p-2 rounded-lg",
                      config?.bgColor || 'bg-slate-100'
                    )}>
                      <Icon className={cn(
                        "h-4 w-4",
                        config?.textColor || 'text-slate-600'
                      )} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        {config?.name || strategy.strategy_name}
                      </h3>
                      <p className="text-xs text-slate-600">
                        {config?.description || 'Strategy description'}
                      </p>
                    </div>
                  </div>
                  
                  <Badge variant="outline" className="text-xs">
                    {formatPercentage(usagePercentage)} usage
                  </Badge>
                </div>

                {/* Usage Progress Bar */}
                <div className="mb-3">
                  <div className="flex justify-between text-xs text-slate-600 mb-1">
                    <span>Usage Distribution</span>
                    <span>{strategy.requests.toLocaleString()} requests</span>
                  </div>
                  <Progress 
                    value={usagePercentage} 
                    className="h-2"
                  />
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-slate-600">Avg Savings</div>
                    <div className="font-semibold text-green-600">
                      {formatCurrency(strategy.avg_savings)}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-600">Avg Cost</div>
                    <div className="font-semibold text-slate-900">
                      {formatCurrency(strategy.avg_cost)}
                    </div>
                  </div>
                </div>

                {/* Performance Indicator */}
                {strategy === bestStrategy && (
                  <div className="mt-3 pt-3 border-t border-green-200">
                    <div className="flex items-center gap-2 text-xs text-green-700">
                      <TrendingUp className="h-3 w-3" />
                      <span className="font-medium">Best performing strategy</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Summary */}
        <div className="mt-6 pt-4 border-t border-slate-200">
          <div className="grid grid-cols-3 gap-4 text-center text-sm">
            <div>
              <div className="text-slate-600">Total Requests</div>
              <div className="font-semibold text-slate-900">
                {totalRequests.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-slate-600">Strategies Active</div>
              <div className="font-semibold text-slate-900">
                {strategies.length}
              </div>
            </div>
            <div>
              <div className="text-slate-600">Best Savings</div>
              <div className="font-semibold text-green-600">
                {bestStrategy ? formatCurrency(bestStrategy.avg_savings) : '--'}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 text-xs text-slate-500">
          <p>Strategy performance is measured by average savings per request</p>
        </div>
      </CardContent>
    </Card>
  );
}
