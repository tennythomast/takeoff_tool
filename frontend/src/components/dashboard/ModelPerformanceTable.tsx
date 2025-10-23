import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowUpDown, ArrowUp, ArrowDown, TrendingUp, TrendingDown } from 'lucide-react';
import { ModelBreakdown } from '@/types/dashboard';
import { cn } from '@/lib/utils';

interface ModelPerformanceTableProps {
  models?: ModelBreakdown[];
  isLoading: boolean;
  error?: Error | null;
}

type SortField = keyof ModelBreakdown;
type SortDirection = 'asc' | 'desc';

export default function ModelPerformanceTable({
  models = [],
  isLoading,
  error,
}: ModelPerformanceTableProps) {
  const [sortField, setSortField] = useState<SortField>('usage_percentage');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedModels = React.useMemo(() => {
    if (!models.length) return [];

    return [...models].sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return 0;
    });
  }, [models, sortField, sortDirection]);

  const SortButton = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => handleSort(field)}
      className="h-auto p-0 font-medium text-slate-600 hover:text-slate-900"
    >
      {children}
      {sortField === field ? (
        sortDirection === 'asc' ? (
          <ArrowUp className="ml-1 h-3 w-3" />
        ) : (
          <ArrowDown className="ml-1 h-3 w-3" />
        )
      ) : (
        <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
      )}
    </Button>
  );

  const formatCurrency = (value: number) => {
    return value < 1 ? `$${value.toFixed(4)}` : `$${value.toLocaleString()}`;
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 95) return 'bg-green-100 text-green-800';
    if (rate >= 90) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getSavingsColor = (savings: number) => {
    if (savings >= 50) return 'text-green-600';
    if (savings >= 25) return 'text-green-500';
    if (savings >= 0) return 'text-green-400';
    return 'text-red-500';
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Model Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-16" />
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
          <CardTitle className="text-red-600">Error Loading Models</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-600">{error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!models.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Model Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-slate-500">
            <div className="text-4xl mb-2">📊</div>
            <p>No model data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Model Performance</span>
          <Badge variant="outline" className="text-xs">
            {models.length} models
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <SortButton field="model_name">Model Name</SortButton>
                </TableHead>
                <TableHead>
                  <SortButton field="usage_percentage">Usage %</SortButton>
                </TableHead>
                <TableHead>
                  <SortButton field="avg_cost">Avg Cost</SortButton>
                </TableHead>
                <TableHead>
                  <SortButton field="savings_percentage">Savings %</SortButton>
                </TableHead>
                <TableHead>
                  <SortButton field="success_rate">Success Rate</SortButton>
                </TableHead>
                <TableHead>
                  <SortButton field="total_requests">Requests</SortButton>
                </TableHead>
              </TableRow>
            </TableHeader>
            
            <TableBody>
              {sortedModels.map((model, index) => (
                <TableRow key={model.model_name} className="hover:bg-slate-50">
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-slate-400" />
                      {model.model_name}
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-slate-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${Math.min(model.usage_percentage, 100)}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {formatPercentage(model.usage_percentage)}
                      </span>
                    </div>
                  </TableCell>
                  
                  <TableCell className="font-mono text-sm">
                    {formatCurrency(model.avg_cost)}
                  </TableCell>
                  
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {model.savings_percentage > 0 ? (
                        <TrendingDown className="h-3 w-3 text-green-500" />
                      ) : (
                        <TrendingUp className="h-3 w-3 text-red-500" />
                      )}
                      <span className={cn("font-medium", getSavingsColor(model.savings_percentage))}>
                        {formatPercentage(model.savings_percentage)}
                      </span>
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <Badge 
                      variant="outline" 
                      className={cn("text-xs", getSuccessRateColor(model.success_rate))}
                    >
                      {formatPercentage(model.success_rate)}
                    </Badge>
                  </TableCell>
                  
                  <TableCell className="text-slate-600">
                    {model.total_requests.toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        
        <div className="mt-4 text-xs text-slate-500">
          <p>Click column headers to sort • Higher savings percentages indicate better cost optimization</p>
        </div>
      </CardContent>
    </Card>
  );
}
