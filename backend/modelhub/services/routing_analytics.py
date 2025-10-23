import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Avg, Sum, Count, Q

logger = logging.getLogger(__name__)

class RoutingAnalytics:
    """Analytics and reporting for intelligent routing performance"""
    
    @staticmethod
    @database_sync_to_async
    def get_cost_savings_report(organization=None, days=30) -> Dict:
        """Generate cost savings report for the routing system"""
        from modelhub.models import ModelMetrics
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        queryset = ModelMetrics.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        if organization:
            queryset = queryset.filter(organization=organization)
        
        # Get metrics with routing metadata
        routing_metrics = queryset.filter(
            optimization_metadata__has_key='routing_decision'
        )
        
        # Calculate savings
        total_requests = routing_metrics.count()
        if total_requests == 0:
            return {'error': 'No routing data available'}
        
        # Actual costs
        actual_cost = routing_metrics.aggregate(
            total=Sum('cost')
        )['total'] or Decimal('0')
        
        # Estimated costs without optimization (from metadata)
        estimated_without_optimization = Decimal('0')
        cost_savings_details = []
        
        for metric in routing_metrics:
            routing_data = metric.optimization_metadata.get('routing_decision', {})
            estimated_cost = Decimal(str(routing_data.get('estimated_cost', 0)))
            
            # Simulate cost without optimization (assume premium model usage)
            baseline_cost = estimated_cost * Decimal('3.0')  # Assume 3x cost without optimization
            estimated_without_optimization += baseline_cost
            
            savings = baseline_cost - metric.cost
            cost_savings_details.append({
                'timestamp': metric.timestamp.isoformat(),
                'actual_cost': float(metric.cost),
                'baseline_cost': float(baseline_cost),
                'savings': float(savings),
                'model_used': routing_data.get('selected_model', 'unknown'),
                'strategy': metric.optimization_metadata.get('optimization_strategy', 'unknown')
            })
        
        total_savings = estimated_without_optimization - actual_cost
        savings_percentage = (float(total_savings) / float(estimated_without_optimization)) * 100 if estimated_without_optimization > 0 else 0
        
        return {
            'period_days': days,
            'total_requests': total_requests,
            'actual_cost': float(actual_cost),
            'estimated_cost_without_optimization': float(estimated_without_optimization),
            'total_savings': float(total_savings),
            'savings_percentage': round(savings_percentage, 2),
            'average_cost_per_request': float(actual_cost / total_requests) if total_requests > 0 else 0,
            'cost_savings_details': cost_savings_details[-10:]  # Last 10 requests
        }
    
    @staticmethod
    @database_sync_to_async
    def get_routing_performance_report(organization=None, days=7) -> Dict:
        """Generate routing performance report"""
        from modelhub.models import ModelMetrics
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        queryset = ModelMetrics.objects.filter(
            timestamp__gte=start_date,
            optimization_metadata__has_key='routing_decision'
        )
        
        if organization:
            queryset = queryset.filter(organization=organization)
        
        metrics = list(queryset)
        
        if not metrics:
            return {'error': 'No routing performance data available'}
        
        # Extract performance data
        routing_times = []
        complexity_analysis_times = []
        total_times = []
        accuracy_scores = []
        
        model_usage = {}
        strategy_usage = {}
        
        for metric in metrics:
            routing_data = metric.optimization_metadata.get('routing_decision', {})
            performance_data = metric.optimization_metadata.get('performance', {})
            
            # Performance metrics
            if 'decision_time_ms' in routing_data:
                routing_times.append(routing_data['decision_time_ms'])
            
            if 'total_time_ms' in performance_data:
                total_times.append(performance_data['total_time_ms'])
            
            # Model usage tracking
            model_used = routing_data.get('selected_model', 'unknown')
            model_usage[model_used] = model_usage.get(model_used, 0) + 1
            
            # Strategy usage tracking
            strategy = metric.optimization_metadata.get('optimization_strategy', 'unknown')
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
            
            # Cost accuracy
            estimated_cost = routing_data.get('estimated_cost', 0)
            actual_cost = float(metric.cost)
            if estimated_cost > 0:
                accuracy = 1.0 - abs(estimated_cost - actual_cost) / estimated_cost
                accuracy_scores.append(max(0, min(1, accuracy)))
        
        return {
            'period_days': days,
            'total_routed_requests': len(metrics),
            'performance': {
                'avg_routing_time_ms': round(sum(routing_times) / len(routing_times), 2) if routing_times else 0,
                'max_routing_time_ms': max(routing_times) if routing_times else 0,
                'avg_total_time_ms': round(sum(total_times) / len(total_times), 2) if total_times else 0,
                'routing_sla_compliance': len([t for t in routing_times if t <= 50]) / len(routing_times) * 100 if routing_times else 0
            },
            'accuracy': {
                'avg_cost_estimation_accuracy': round(sum(accuracy_scores) / len(accuracy_scores) * 100, 2) if accuracy_scores else 0,
                'cost_estimates_within_10pct': len([s for s in accuracy_scores if s >= 0.9]) / len(accuracy_scores) * 100 if accuracy_scores else 0
            },
            'model_usage': dict(sorted(model_usage.items(), key=lambda x: x[1], reverse=True)),
            'strategy_usage': strategy_usage
        }
    
    @staticmethod
    @database_sync_to_async
    def get_optimization_recommendations(organization=None) -> List[Dict]:
        """Generate optimization recommendations based on usage patterns"""
        from modelhub.models import ModelMetrics
        
        # Get recent data for analysis
        end_date = timezone.now()
        start_date = end_date - timedelta(days=14)  # 2 weeks of data
        
        queryset = ModelMetrics.objects.filter(
            timestamp__gte=start_date,
            optimization_metadata__has_key='routing_decision'
        )
        
        if organization:
            queryset = queryset.filter(organization=organization)
        
        metrics = list(queryset)
        recommendations = []
        
        if len(metrics) < 10:
            return [{'type': 'info', 'message': 'Insufficient data for recommendations. Need at least 10 routed requests.'}]
        
        # Analyze model performance vs cost
        model_performance = {}
        for metric in metrics:
            routing_data = metric.optimization_metadata.get('routing_decision', {})
            model = routing_data.get('selected_model', 'unknown')
            
            if model not in model_performance:
                model_performance[model] = {
                    'requests': 0,
                    'total_cost': Decimal('0'),
                    'total_latency': 0,
                    'success_rate': 0
                }
            
            model_performance[model]['requests'] += 1
            model_performance[model]['total_cost'] += metric.cost
            model_performance[model]['total_latency'] += metric.latency_ms
            if metric.status == 'SUCCESS':
                model_performance[model]['success_rate'] += 1
        
        # Calculate averages and generate recommendations
        for model, perf in model_performance.items():
            if perf['requests'] > 0:
                avg_cost = perf['total_cost'] / perf['requests']
                avg_latency = perf['total_latency'] / perf['requests']
                success_rate = (perf['success_rate'] / perf['requests']) * 100
                
                # High cost, low usage
                if avg_cost > Decimal('0.05') and perf['requests'] < len(metrics) * 0.1:
                    recommendations.append({
                        'type': 'cost_optimization',
                        'priority': 'medium',
                        'message': f'Model {model} has high cost (${avg_cost:.4f}) but low usage. Consider routing simpler tasks to cheaper alternatives.',
                        'model': model,
                        'avg_cost': float(avg_cost),
                        'usage_percentage': (perf['requests'] / len(metrics)) * 100
                    })
                
                # High latency
                if avg_latency > 2000:  # > 2 seconds
                    recommendations.append({
                        'type': 'performance',
                        'priority': 'high',
                        'message': f'Model {model} shows high latency ({avg_latency:.0f}ms). Consider faster alternatives for time-sensitive requests.',
                        'model': model,
                        'avg_latency': avg_latency
                    })
                
                # Low success rate
                if success_rate < 95:
                    recommendations.append({
                        'type': 'reliability',
                        'priority': 'high',
                        'message': f'Model {model} has low success rate ({success_rate:.1f}%). Check API key limits or model availability.',
                        'model': model,
                        'success_rate': success_rate
                    })
        
        # Strategy analysis
        strategy_costs = {}
        strategy_counts = {}
        
        for metric in metrics:
            strategy = metric.optimization_metadata.get('optimization_strategy', 'unknown')
            if strategy not in strategy_costs:
                strategy_costs[strategy] = Decimal('0')
                strategy_counts[strategy] = 0
            
            strategy_costs[strategy] += metric.cost
            strategy_counts[strategy] += 1
        
        # Compare strategy effectiveness
        if len(strategy_costs) > 1:
            avg_costs = {s: strategy_costs[s] / strategy_counts[s] for s in strategy_costs}
            cheapest_strategy = min(avg_costs, key=avg_costs.get)
            most_expensive_strategy = max(avg_costs, key=avg_costs.get)
            
            cost_difference = avg_costs[most_expensive_strategy] - avg_costs[cheapest_strategy]
            if cost_difference > Decimal('0.01'):  # Significant difference
                savings_potential = cost_difference * strategy_counts[most_expensive_strategy]
                recommendations.append({
                    'type': 'strategy_optimization',
                    'priority': 'medium',
                    'message': f'Strategy "{cheapest_strategy}" is ${cost_difference:.4f} cheaper per request than "{most_expensive_strategy}". Potential monthly savings: ${savings_potential:.2f}',
                    'cheapest_strategy': cheapest_strategy,
                    'expensive_strategy': most_expensive_strategy,
                    'potential_savings': float(savings_potential)
                })
        
        # If no specific recommendations, provide general advice
        if not recommendations:
            total_cost = sum(m.cost for m in metrics)
            avg_cost_per_request = total_cost / len(metrics)
            
            recommendations.append({
                'type': 'general',
                'priority': 'info',
                'message': f'Routing system is performing well. Average cost per request: ${avg_cost_per_request:.4f}. Continue monitoring for optimization opportunities.',
                'avg_cost_per_request': float(avg_cost_per_request)
            })
        
        return recommendations