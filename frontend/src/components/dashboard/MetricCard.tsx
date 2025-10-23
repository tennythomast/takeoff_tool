import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { MetricCardProps } from '@/types/dashboard';
import { cn } from '@/lib/utils';

export default function MetricCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  className,
}: MetricCardProps) {
  const formatValue = (val: string | number): string => {
    if (typeof val === 'number') {
      // Format currency values
      if (title.toLowerCase().includes('cost') || title.toLowerCase().includes('savings')) {
        return val < 1 ? `$${val.toFixed(4)}` : `$${val.toLocaleString()}`;
      }
      // Format percentage values
      if (title.toLowerCase().includes('rate') || title.toLowerCase().includes('%')) {
        return `${val.toFixed(1)}%`;
      }
      // Format regular numbers
      return val.toLocaleString();
    }
    return val.toString();
  };

  return (
    <Card className={cn(
      "relative overflow-hidden transition-all duration-200 hover:shadow-lg border-0 bg-white/80 backdrop-blur-sm",
      className
    )}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-600">
          {title}
        </CardTitle>
        {icon && (
          <div className="h-4 w-4 text-slate-400">
            {icon}
          </div>
        )}
      </CardHeader>
      
      <CardContent>
        <div className="flex items-baseline space-x-2">
          <div className="text-2xl font-bold text-slate-900">
            {formatValue(value)}
          </div>
          
          {trend && (
            <Badge 
              variant={trend.isPositive ? "default" : "destructive"}
              className={cn(
                "text-xs font-medium",
                trend.isPositive 
                  ? "bg-green-100 text-green-800 hover:bg-green-100" 
                  : "bg-red-100 text-red-800 hover:bg-red-100"
              )}
            >
              {trend.isPositive ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-1" />
              )}
              {Math.abs(trend.value).toFixed(1)}%
            </Badge>
          )}
        </div>
        
        {subtitle && (
          <p className="text-xs text-slate-500 mt-1">
            {subtitle}
          </p>
        )}
      </CardContent>
      
      {/* Subtle gradient overlay for visual appeal */}
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-slate-50/20 pointer-events-none" />
    </Card>
  );
}
