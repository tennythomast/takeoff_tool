from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count, Avg
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, inline_serializer
from .models import PromptSession, Prompt
from modelhub.models import ModelMetrics


class ExecutePromptRequestSerializer(serializers.Serializer):
    """Serializer for prompt execution requests."""
    optimization_strategy = serializers.ChoiceField(
        choices=['cost_first', 'balanced', 'quality_first', 'performance_first'],
        default='balanced',
        required=False,
        help_text='Cost optimization strategy for model selection'
    )
    max_tokens = serializers.IntegerField(
        default=512,
        required=False,
        help_text='Maximum tokens to generate'
    )
    temperature = serializers.FloatField(
        default=0.7,
        required=False,
        help_text='Temperature for model generation (0.0-2.0)'
    )


class ModelMetricsSerializer(serializers.ModelSerializer):
    """Serializer for ModelMetrics with session references."""
    prompt_text = serializers.CharField(read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    provider_name = serializers.CharField(source='model.provider.name', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    
    class Meta:
        model = ModelMetrics
        fields = (
            'id', 'model_name', 'provider_name', 'prompt_text',
            'session_id', 'session_type', 'session_title',
            'context_session_id', 'tokens_input', 'tokens_output', 
            'model_execution_cost', 'latency_ms', 'status', 
            'error_type', 'error_message', 'optimization_metadata',
            'created_at'
        )
        read_only_fields = fields


class PromptSerializer(serializers.ModelSerializer):
    """Serializer for Prompt with execution metadata."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    execution_cost = serializers.ReadOnlyField()
    model_used = serializers.ReadOnlyField()
    context_strategy_used = serializers.ReadOnlyField()
    conversation_context = serializers.SerializerMethodField()

    class Meta:
        model = Prompt
        fields = (
            'id', 'session', 'session_title', 'user', 'user_email',
            'input_text', 'execution_metadata', 'importance_score', 
            'is_starred', 'execution_cost', 'model_used', 
            'context_strategy_used', 'conversation_context',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'user', 'session',
            'execution_cost', 'model_used', 'context_strategy_used'
        )

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_conversation_context(self, obj: Prompt) -> list:
        """Get conversation context entries for this prompt."""
        try:
            context_entries = obj.get_conversation_context()
            return [
                {
                    'id': str(entry.id),
                    'role': entry.role,
                    'content': entry.content[:500] + '...' if len(entry.content) > 500 else entry.content,
                    'created_at': entry.created_at.isoformat(),
                    'importance_score': entry.importance_score,
                    'context_preparation_cost': float(entry.context_preparation_cost or 0)
                }
                for entry in context_entries[:10]  # Limit to last 10 entries
            ]
        except Exception:
            return []


class OptimizationMetricsSerializer(serializers.Serializer):
    """Serializer for optimization metrics data."""
    cost_savings = serializers.FloatField(help_text='Percentage of cost saved through optimization')
    performance_impact = serializers.FloatField(help_text='Percentage impact on performance (negative is better)')
    recommended_strategy = serializers.CharField(help_text='Recommended optimization strategy for this workload')
    strategy_breakdown = serializers.DictField(help_text='Breakdown of metrics by strategy')
    context_efficiency = serializers.DictField(help_text='Context preparation efficiency metrics')


class PromptSessionSerializer(serializers.ModelSerializer):
    """Serializer for PromptSession with comprehensive metrics."""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    creator_email = serializers.EmailField(source='creator.email', read_only=True)
    creator_name = serializers.CharField(source='creator.name', read_only=True)
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Cost properties from model
    total_cost = serializers.ReadOnlyField()
    model_execution_cost = serializers.ReadOnlyField()
    context_preparation_cost = serializers.ReadOnlyField()
    cost_breakdown = serializers.ReadOnlyField()
    
    # Metrics from model
    execution_count = serializers.SerializerMethodField()
    conversation_length = serializers.SerializerMethodField()
    context_metrics = serializers.ReadOnlyField()
    
    # Optimization stats
    optimization_stats = serializers.SerializerMethodField()

    class Meta:
        model = PromptSession
        fields = (
            'id', 'title', 'description', 'workspace', 'workspace_name',
            'creator', 'creator_email', 'creator_name',
            'model_type', 'model_type_display', 'status', 'status_display',
            'context_session_id', 'started_at', 'completed_at',
            'total_cost', 'model_execution_cost', 'context_preparation_cost',
            'cost_breakdown', 'execution_count', 'conversation_length',
            'context_metrics', 'optimization_stats',
            'created_at', 'updated_at', 'is_active'
        )
        read_only_fields = (
            'id', 'creator', 'context_session_id', 'started_at', 'completed_at',
            'total_cost', 'model_execution_cost', 'context_preparation_cost',
            'cost_breakdown', 'execution_count', 'conversation_length',
            'context_metrics', 'created_at', 'updated_at', 'is_active'
        )
        
    def get_execution_count(self, obj: PromptSession) -> int:
        """Get the number of executions in this session."""
        return obj.get_execution_count()
    
    def get_conversation_length(self, obj: PromptSession) -> int:
        """Get the total conversation entries."""
        return obj.get_conversation_length()
    
    @extend_schema_field(OptimizationMetricsSerializer)
    def get_optimization_stats(self, obj: PromptSession) -> dict:
        """Get optimization statistics for this session."""
        try:
            # Get metrics with optimization metadata
            metrics = ModelMetrics.objects.filter(
                session_id=obj.id,
                session_type='prompt_session'
            )
            metrics_with_optimization = metrics.exclude(optimization_metadata__isnull=True)
            
            if not metrics_with_optimization.exists():
                return {
                    'cost_savings': 0.0,
                    'performance_impact': 0.0,
                    'recommended_strategy': 'balanced',
                    'strategy_breakdown': {},
                    'context_efficiency': {
                        'cache_hit_rate': 0.0,
                        'avg_preparation_time_ms': 0.0,
                        'total_context_cost': 0.0
                    }
                }
            
            # Get strategies used from execution metadata
            strategies_used = []
            for metric in metrics_with_optimization:
                if (metric.optimization_metadata and 
                    'optimization_strategy' in metric.optimization_metadata):
                    strategies_used.append(metric.optimization_metadata['optimization_strategy'])
            
            strategies_used = list(set(filter(None, strategies_used)))
            
            # Calculate metrics by strategy
            strategy_breakdown = {}
            for strategy in strategies_used:
                strategy_metrics = metrics_with_optimization.filter(
                    optimization_metadata__optimization_strategy=strategy
                )
                
                if strategy_metrics.exists():
                    strategy_breakdown[strategy] = {
                        'count': strategy_metrics.count(),
                        'avg_cost': float(strategy_metrics.aggregate(
                            Avg('model_execution_cost'))['model_execution_cost__avg'] or 0),
                        'total_cost': float(strategy_metrics.aggregate(
                            Sum('model_execution_cost'))['model_execution_cost__sum'] or 0),
                        'avg_latency_ms': float(strategy_metrics.aggregate(
                            Avg('latency_ms'))['latency_ms__avg'] or 0)
                    }
            
            # Determine recommended strategy based on cost efficiency
            recommended_strategy = 'balanced'
            if strategy_breakdown:
                recommended_strategy = min(
                    strategy_breakdown.items(),
                    key=lambda x: x[1]['avg_cost']
                )[0]
            
            # Estimate cost savings
            baseline_cost = metrics.aggregate(Avg('model_execution_cost'))['model_execution_cost__avg'] or 0
            optimized_cost = metrics_with_optimization.aggregate(
                Avg('model_execution_cost'))['model_execution_cost__avg'] or 0
            cost_savings = max(0, (baseline_cost - optimized_cost) / baseline_cost * 100) if baseline_cost > 0 else 0
            
            # Estimate performance impact
            baseline_latency = metrics.aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
            optimized_latency = metrics_with_optimization.aggregate(
                Avg('latency_ms'))['latency_ms__avg'] or 0
            performance_impact = ((optimized_latency - baseline_latency) / baseline_latency * 100) if baseline_latency > 0 else 0
            
            # Get context efficiency metrics
            context_metrics = obj.get_context_metrics()
            
            return {
                'cost_savings': round(cost_savings, 2),
                'performance_impact': round(performance_impact, 2),
                'recommended_strategy': recommended_strategy,
                'strategy_breakdown': strategy_breakdown,
                'context_efficiency': context_metrics
            }
            
        except Exception as e:
            # Return safe defaults on error
            return {
                'cost_savings': 0.0,
                'performance_impact': 0.0,
                'recommended_strategy': 'balanced',
                'strategy_breakdown': {},
                'context_efficiency': {
                    'cache_hit_rate': 0.0,
                    'avg_preparation_time_ms': 0.0,
                    'total_context_cost': 0.0
                }
            }


class ContextMetricsSerializer(serializers.Serializer):
    """Serializer for context session metrics."""
    cache_hit_rate = serializers.FloatField()
    avg_preparation_time_ms = serializers.FloatField()
    total_context_cost = serializers.FloatField()
    total_entries = serializers.IntegerField()
    strategy_usage = serializers.DictField()


class SessionSummarySerializer(serializers.Serializer):
    """Serializer for session summary data."""
    session_id = serializers.UUIDField()
    session_title = serializers.CharField()
    total_cost = serializers.FloatField()
    model_execution_cost = serializers.FloatField()
    context_preparation_cost = serializers.FloatField()
    total_tokens_input = serializers.IntegerField()
    total_tokens_output = serializers.IntegerField()
    avg_latency_ms = serializers.FloatField()
    execution_count = serializers.IntegerField()
    conversation_length = serializers.IntegerField()
    success_rate = serializers.FloatField()
    model_breakdown = serializers.ListField()
    context_metrics = ContextMetricsSerializer()