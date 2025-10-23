// API Response Types for Cost Optimization Dashboard

export interface CostSummary {
  total_cost: number;
  avg_cost_per_request: number;
  total_requests: number;
  baseline_cost: number;
}

export interface OptimizationStats {
  savings_percentage: number;
  total_savings: number;
  optimization_rate: number;
  cost_savings_details: CostSavingsDetail[];
  models_breakdown: ModelBreakdown[];
  strategies_used: StrategyUsage[];
  recommendations: OptimizationRecommendation[];
}

export interface CostSavingsDetail {
  date: string;
  actual_cost: number;
  baseline_cost: number;
  savings: number;
  requests: number;
}

export interface ModelBreakdown {
  model_name: string;
  usage_percentage: number;
  avg_cost: number;
  savings_percentage: number;
  success_rate: number;
  total_requests: number;
}

export interface StrategyUsage {
  strategy_name: 'cost_first' | 'balanced' | 'quality_first';
  requests: number;
  avg_savings: number;
  avg_cost: number;
}

export interface OptimizationRecommendation {
  id: string;
  type: 'strategy' | 'model' | 'api_key' | 'general';
  title: string;
  description: string;
  potential_savings: number;
  priority: 'high' | 'medium' | 'low';
  created_at: string;
}

export interface KeyHealth {
  provider: string;
  status: 'active' | 'warning' | 'error';
  usage_percentage: number;
  remaining_quota: number;
}

export interface UsageSummary {
  provider_distribution: ProviderUsage[];
  total_requests: number;
  avg_response_time: number;
}

export interface ProviderUsage {
  provider: string;
  requests: number;
  percentage: number;
  avg_cost: number;
}

export interface DashboardSummary {
  cost_summary: CostSummary;
  optimization_stats: OptimizationStats;
  key_health: KeyHealth[];
  usage_summary: UsageSummary;
}

// Component Props Types
export interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  icon?: React.ReactNode;
  className?: string;
}

export interface TimeRange {
  days: 7 | 30 | 90;
  label: string;
}

export interface ChartDataPoint {
  date: string;
  actualCost: number;
  baselineCost: number;
  savings: number;
}
