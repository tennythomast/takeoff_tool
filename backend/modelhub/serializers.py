from rest_framework import serializers
from decimal import Decimal
from .models import Provider, Model, APIKey, RoutingRule, RoutingRuleModel, ModelMetrics


class ProviderSerializer(serializers.ModelSerializer):
    # Add model count for dashboard
    model_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Provider
        fields = [
            'id', 'name', 'slug', 'description', 'website',
            'documentation_url', 'status', 'config', 'model_count',
            'supports_embeddings', 'embedding_endpoint'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'model_count']
    
    def get_model_count(self, obj):
        """Get count of active models for this provider"""
        return obj.model_set.filter(status='ACTIVE').count()


class ModelSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)
    cost_display = serializers.ReadOnlyField()
    
    # Add capability flags for frontend
    supports_chat = serializers.SerializerMethodField()
    supports_completion = serializers.SerializerMethodField()
    supports_embedding = serializers.SerializerMethodField()
    preferred_api_type = serializers.SerializerMethodField()
    
    # Add estimated costs for common token ranges (helpful for frontend)
    cost_examples = serializers.SerializerMethodField()
    
    class Meta:
        model = Model
        fields = [
            'id', 'provider', 'provider_name', 'provider_slug', 'name', 'version',
            'model_type', 'capabilities', 'config', 'cost_input',
            'cost_output', 'context_window', 'status', 'cost_display',
            'cost_examples', 'supports_chat', 'supports_completion', 'supports_embedding',
            'preferred_api_type', 'embedding_dimensions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'cost_display', 'cost_examples',
                           'supports_chat', 'supports_completion', 'supports_embedding',
                           'preferred_api_type']
    
    def get_supports_chat(self, obj):
        """Check if model supports chat completions"""
        return obj.supports_chat()
    
    def get_supports_completion(self, obj):
        """Check if model supports text completions"""
        return obj.supports_completion()
    
    def get_supports_embedding(self, obj):
        """Check if model supports embeddings"""
        return obj.supports_embedding()
    
    def get_preferred_api_type(self, obj):
        """Get the preferred API type for this model"""
        return obj.get_preferred_api_type()
    
    def get_cost_examples(self, obj):
        """Provide cost examples for common usage patterns - great for frontend display"""
        examples = []
        
        # Common usage patterns
        patterns = [
            {'name': 'Simple Query', 'input': 100, 'output': 50},
            {'name': 'Document Summary', 'input': 2000, 'output': 200},
            {'name': 'Code Generation', 'input': 500, 'output': 1000},
            {'name': 'Long Conversation', 'input': 4000, 'output': 1500}
        ]
        
        for pattern in patterns:
            cost = obj.estimate_cost(pattern['input'], pattern['output'])
            examples.append({
                'name': pattern['name'],
                'input_tokens': pattern['input'],
                'output_tokens': pattern['output'],
                'estimated_cost': float(cost)
            })
        
        return examples


class APIKeySerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    quota_status = serializers.ReadOnlyField()
    usage_this_month = serializers.SerializerMethodField()
    
    # Add health status for dashboard
    health_status = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            'id', 'organization', 'organization_name', 'provider',
            'provider_name', 'provider_slug', 'label', 'is_default', 
            'is_active', 'daily_quota', 'monthly_quota', 'last_used_at', 
            'quota_status', 'usage_this_month', 'health_status'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_used_at', 
            'quota_status', 'usage_this_month', 'health_status'
        ]
        extra_kwargs = {
            'key': {'write_only': True}  # Never expose API keys in responses
        }
    
    def get_usage_this_month(self, obj):
        """Get usage data for this month"""
        try:
            usage = obj.get_usage_this_month()
            return {
                'total_cost': float(usage['total_cost'] or 0),
                'total_requests': usage['total_requests'] or 0
            }
        except Exception:
            return {'total_cost': 0.0, 'total_requests': 0}
    
    def get_health_status(self, obj):
        """Get health status for this key - useful for dashboard alerts"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Check for recent errors (last 24 hours)
            yesterday = timezone.now() - timedelta(hours=24)
            recent_errors = ModelMetrics.objects.filter(
                api_key=obj,
                timestamp__gte=yesterday,
                status__in=['ERROR', 'TIMEOUT']
            ).count()
            
            recent_requests = ModelMetrics.objects.filter(
                api_key=obj,
                timestamp__gte=yesterday
            ).count()
            
            if recent_requests == 0:
                return {'status': 'idle', 'error_rate': 0}
            
            error_rate = (recent_errors / recent_requests) * 100
            
            if error_rate > 10:
                status = 'unhealthy'
            elif error_rate > 5:
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'error_rate': round(error_rate, 1),
                'recent_errors': recent_errors,
                'recent_requests': recent_requests
            }
            
        except Exception:
            return {'status': 'unknown', 'error_rate': 0}

    def validate(self, data):
        """Add custom validation for quotas"""
        daily_quota = data.get('daily_quota')
        monthly_quota = data.get('monthly_quota')
        
        if daily_quota and monthly_quota:
            # Daily quota shouldn't be more than monthly quota
            if daily_quota * 30 > monthly_quota:
                raise serializers.ValidationError(
                    "Daily quota seems too high compared to monthly quota"
                )
        
        return data


class RoutingRuleModelSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source='model.name', read_only=True)
    provider_name = serializers.CharField(source='model.provider.name', read_only=True)
    model_cost_input = serializers.DecimalField(source='model.cost_input', max_digits=10, decimal_places=6, read_only=True)
    model_cost_output = serializers.DecimalField(source='model.cost_output', max_digits=10, decimal_places=6, read_only=True)

    class Meta:
        model = RoutingRuleModel
        fields = [
            'id', 'model', 'model_name', 'provider_name', 
            'model_cost_input', 'model_cost_output', 'weight', 'notes', 'tags'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoutingRuleSerializer(serializers.ModelSerializer):
    models = RoutingRuleModelSerializer(source='routingrulemodel_set', many=True, read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    # Add summary stats
    model_count = serializers.SerializerMethodField()
    cheapest_model_cost = serializers.SerializerMethodField()

    class Meta:
        model = RoutingRule
        fields = [
            'id', 'organization', 'organization_name', 'name',
            'description', 'priority', 'is_active', 'model_type', 'conditions',
            'models', 'model_count', 'cheapest_model_cost'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'model_count', 'cheapest_model_cost']

    def get_model_count(self, obj):
        """Get count of models in this rule"""
        return obj.models.filter(status='ACTIVE').count()
    
    def get_cheapest_model_cost(self, obj):
        """Get the cheapest model's cost for quick comparison"""
        try:
            models = obj.models.filter(status='ACTIVE')
            if not models.exists():
                return None
            
            # Find cheapest model (assuming 1000 input, 500 output tokens)
            cheapest_cost = None
            cheapest_model = None
            
            for model in models:
                cost = model.cost_input + (model.cost_output * 0.5)  # Rough estimate
                if cheapest_cost is None or cost < cheapest_cost:
                    cheapest_cost = cost
                    cheapest_model = model
            
            return {
                'model_name': cheapest_model.name,
                'provider': cheapest_model.provider.name,
                'estimated_cost_per_1k': float(cheapest_cost)
            }
        except Exception:
            return None

    def create(self, validated_data):
        """Enhanced create with better error handling"""
        try:
            # Don't pop models_data since it's read_only now
            rule = RoutingRule.objects.create(**validated_data)
            return rule
        except Exception as e:
            raise serializers.ValidationError(f"Failed to create routing rule: {str(e)}")

    def update(self, instance, validated_data):
        """Enhanced update with better error handling"""
        try:
            # Update the rule
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Failed to update routing rule: {str(e)}")

    def validate_conditions(self, value):
        """Validate routing rule conditions structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Conditions must be a list")
        
        valid_operators = ['equals', 'contains', 'gt', 'lt', 'gte', 'lte']
        
        for condition in value:
            if not isinstance(condition, dict):
                raise serializers.ValidationError("Each condition must be a dictionary")
            
            required_fields = ['field', 'operator', 'value']
            if not all(field in condition for field in required_fields):
                raise serializers.ValidationError(
                    "Each condition must have 'field', 'operator', and 'value'"
                )
            
            if condition['operator'] not in valid_operators:
                raise serializers.ValidationError(
                    f"Operator must be one of: {', '.join(valid_operators)}"
                )
        
        return value


class ModelMetricsSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source='model.name', read_only=True)
    provider_name = serializers.CharField(source='model.provider.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    # Add computed fields for better frontend display
    cost_per_token = serializers.SerializerMethodField()
    efficiency_score = serializers.SerializerMethodField()
    
    class Meta:
        model = ModelMetrics
        fields = [
            'id', 'model', 'model_name', 'provider_name', 'organization',
            'organization_name', 'timestamp', 'latency_ms', 'tokens_input',
            'tokens_output', 'cost', 'status', 'error_type', 'error_message',
            'cost_per_token', 'efficiency_score', 'optimization_metadata'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'model_name',
            'provider_name', 'organization_name', 'cost_per_token', 
            'efficiency_score'
        ]
    
    def get_cost_per_token(self, obj):
        """Calculate cost per token for this request"""
        total_tokens = obj.tokens_input + obj.tokens_output
        if total_tokens > 0:
            return float(obj.cost / total_tokens)
        return 0.0
    
    def get_efficiency_score(self, obj):
        """Calculate efficiency score (cost vs speed) - useful for optimization display"""
        try:
            # Simple efficiency metric: tokens per second per dollar
            if obj.cost > 0 and obj.latency_ms > 0:
                tokens_per_second = (obj.tokens_input + obj.tokens_output) / (obj.latency_ms / 1000)
                efficiency = tokens_per_second / float(obj.cost)
                return round(efficiency, 2)
            return 0.0
        except (ZeroDivisionError, TypeError):
            return 0.0


# Simplified serializers for dashboard/summary endpoints
class DashboardModelSerializer(serializers.ModelSerializer):
    """Lightweight model serializer for dashboard lists"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    
    class Meta:
        model = Model
        fields = ['id', 'name', 'provider_name', 'model_type', 'cost_input', 'cost_output']


class DashboardMetricsSerializer(serializers.ModelSerializer):
    """Lightweight metrics serializer for dashboard charts"""
    model_name = serializers.CharField(source='model.name', read_only=True)
    
    class Meta:
        model = ModelMetrics
        fields = ['timestamp', 'model_name', 'cost', 'latency_ms', 'status']


# Serializer for the optimization insights
class OptimizationInsightSerializer(serializers.Serializer):
    """Serializer for optimization recommendations - no model backing"""
    insight_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    potential_savings = serializers.DecimalField(max_digits=10, decimal_places=2)
    confidence = serializers.FloatField()
    action_required = serializers.BooleanField()
    details = serializers.DictField()


# Bulk operations serializer for enterprise features
class BulkModelUpdateSerializer(serializers.Serializer):
    """For bulk model updates - useful for admin operations"""
    model_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=['activate', 'deactivate', 'update_costs'])
    cost_multiplier = serializers.FloatField(required=False, min_value=0.1, max_value=10.0)
    
    def validate_model_ids(self, value):
        if len(value) > 100:  # Reasonable limit
            raise serializers.ValidationError("Too many models selected (max 100)")
        return value