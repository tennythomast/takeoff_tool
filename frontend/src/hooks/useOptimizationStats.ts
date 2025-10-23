import { useMemo } from 'react';
import { DashboardSummary, ModelBreakdown, StrategyUsage, OptimizationRecommendation } from '@/types/dashboard';

interface OptimizationStatsResult {
  topPerformingModel: ModelBreakdown | null;
  mostEfficientStrategy: StrategyUsage | null;
  optimizationScore: number;
  modelDiversityScore: number;
  recommendationsSummary: {
    total: number;
    highPriority: number;
    potentialSavings: number;
    categories: Record<string, number>;
  };
  performanceMetrics: {
    avgSuccessRate: number;
    totalRequests: number;
    optimizedRequests: number;
    costReduction: number;
  };
}

export function useOptimizationStats(data?: DashboardSummary): OptimizationStatsResult {
  return useMemo(() => {
    if (!data?.optimization_stats) {
      return {
        topPerformingModel: null,
        mostEfficientStrategy: null,
        optimizationScore: 0,
        modelDiversityScore: 0,
        recommendationsSummary: {
          total: 0,
          highPriority: 0,
          potentialSavings: 0,
          categories: {},
        },
        performanceMetrics: {
          avgSuccessRate: 0,
          totalRequests: 0,
          optimizedRequests: 0,
          costReduction: 0,
        },
      };
    }

    const { 
      models_breakdown = [], 
      strategies_used = [], 
      recommendations = [],
      optimization_rate,
      savings_percentage 
    } = data.optimization_stats;

    // Find top performing model (best combination of savings and success rate)
    const topPerformingModel = models_breakdown.reduce((best, current) => {
      if (!best) return current;
      const currentScore = (current.savings_percentage * 0.6) + (current.success_rate * 0.4);
      const bestScore = (best.savings_percentage * 0.6) + (best.success_rate * 0.4);
      return currentScore > bestScore ? current : best;
    }, null as ModelBreakdown | null);

    // Find most efficient strategy (highest average savings)
    const mostEfficientStrategy = strategies_used.reduce((best, current) => {
      if (!best) return current;
      return current.avg_savings > best.avg_savings ? current : best;
    }, null as StrategyUsage | null);

    // Calculate optimization score (0-100)
    const optimizationScore = Math.min(100, 
      (savings_percentage * 0.4) + 
      (optimization_rate * 0.3) + 
      (models_breakdown.reduce((sum, model) => sum + model.success_rate, 0) / models_breakdown.length * 0.3)
    );

    // Calculate model diversity score (how well distributed the usage is)
    const totalUsage = models_breakdown.reduce((sum, model) => sum + model.usage_percentage, 0);
    const idealUsagePerModel = totalUsage / models_breakdown.length;
    const usageVariance = models_breakdown.reduce((sum, model) => {
      return sum + Math.pow(model.usage_percentage - idealUsagePerModel, 2);
    }, 0) / models_breakdown.length;
    const modelDiversityScore = Math.max(0, 100 - (usageVariance / idealUsagePerModel * 10));

    // Analyze recommendations
    const recommendationsSummary = {
      total: recommendations.length,
      highPriority: recommendations.filter(rec => rec.priority === 'high').length,
      potentialSavings: recommendations.reduce((sum, rec) => sum + rec.potential_savings, 0),
      categories: recommendations.reduce((acc, rec) => {
        acc[rec.type] = (acc[rec.type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
    };

    // Calculate performance metrics
    const totalRequests = models_breakdown.reduce((sum, model) => sum + model.total_requests, 0);
    const avgSuccessRate = models_breakdown.length > 0 
      ? models_breakdown.reduce((sum, model) => sum + model.success_rate, 0) / models_breakdown.length
      : 0;
    const optimizedRequests = Math.round(totalRequests * (optimization_rate / 100));
    const costReduction = savings_percentage;

    return {
      topPerformingModel,
      mostEfficientStrategy,
      optimizationScore,
      modelDiversityScore,
      recommendationsSummary,
      performanceMetrics: {
        avgSuccessRate,
        totalRequests,
        optimizedRequests,
        costReduction,
      },
    };
  }, [data]);
}

// Helper hook for generating insights based on optimization stats
export function useOptimizationInsights(stats: OptimizationStatsResult) {
  return useMemo(() => {
    const insights: string[] = [];

    // Performance insights
    if (stats.optimizationScore > 80) {
      insights.push("🎉 Excellent optimization performance! Your system is running efficiently.");
    } else if (stats.optimizationScore > 60) {
      insights.push("👍 Good optimization performance with room for improvement.");
    } else {
      insights.push("⚠️ Optimization performance could be improved. Consider reviewing your strategies.");
    }

    // Model diversity insights
    if (stats.modelDiversityScore < 40) {
      insights.push("📊 Consider diversifying model usage to reduce dependency on single models.");
    } else if (stats.modelDiversityScore > 80) {
      insights.push("🎯 Great model diversity! You're effectively utilizing multiple models.");
    }

    // Recommendations insights
    if (stats.recommendationsSummary.highPriority > 0) {
      insights.push(`🚨 ${stats.recommendationsSummary.highPriority} high-priority recommendations need attention.`);
    }

    if (stats.recommendationsSummary.potentialSavings > 100) {
      insights.push(`💰 Potential monthly savings of $${stats.recommendationsSummary.potentialSavings.toFixed(0)} available.`);
    }

    // Success rate insights
    if (stats.performanceMetrics.avgSuccessRate > 95) {
      insights.push("✅ Excellent model reliability with >95% success rate.");
    } else if (stats.performanceMetrics.avgSuccessRate < 90) {
      insights.push("⚠️ Model success rate below 90%. Consider reviewing model selection.");
    }

    return insights;
  }, [stats]);
}
