import logging
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Provider, Model, APIKey, RoutingRule, ModelMetrics
from .serializers import (
    ProviderSerializer, ModelSerializer, APIKeySerializer,
    RoutingRuleSerializer, ModelMetricsSerializer
)
from .services.api_key_manager import APIKeyManager

logger = logging.getLogger(__name__)


class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'status']
    ordering = ['name']

    def get_queryset(self):
        return self.queryset.filter(status='ACTIVE')  # Fixed: was is_active


class ModelViewSet(viewsets.ModelViewSet):
    queryset = Model.objects.all()
    serializer_class = ModelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'version', 'provider__name']
    ordering_fields = ['name', 'provider__name', 'status']
    ordering = ['provider__name', 'name']

    def get_queryset(self):
        queryset = self.queryset.filter(status='ACTIVE')  # Fixed: was is_active
        model_type = self.request.query_params.get('model_type')
        if model_type:
            queryset = queryset.filter(model_type=model_type)
        return queryset
    
    @action(detail=False, methods=['get'])
    def get_api_type(self, request):
        """Get the preferred API type for a model without needing the model instance"""
        provider_slug = request.query_params.get('provider_slug')
        model_name = request.query_params.get('model_name')
        
        if not provider_slug or not model_name:
            return Response(
                {'error': 'provider_slug and model_name are required parameters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            api_type = Model.get_api_type_for_model(provider_slug, model_name)
            return Response({
                'provider_slug': provider_slug,
                'model_name': model_name,
                'api_type': api_type
            })
        except Exception as e:
            logger.error(f"API type detection error: {str(e)}")
            return Response(
                {'error': 'Failed to determine API type', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=True, methods=['post'])
    def estimate_cost(self, request, pk=None):
        """Estimate cost for a given model and token counts"""
        try:
            model = self.get_object()
            input_tokens = request.data.get('input_tokens', 0)
            output_tokens = request.data.get('output_tokens', 0)
            
            # Better validation
            try:
                input_tokens = int(input_tokens)
                output_tokens = int(output_tokens)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'input_tokens and output_tokens must be valid numbers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if input_tokens < 0 or output_tokens < 0:
                return Response(
                    {'error': 'Token counts cannot be negative'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            estimated_cost = model.estimate_cost(input_tokens, output_tokens)
            
            return Response({
                'model_id': model.id,
                'model_name': model.name,
                'provider': model.provider.name,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'estimated_cost': float(estimated_cost),
                'cost_details': model.cost_display
            })
            
        except Exception as e:
            logger.error(f"Cost estimation error: {str(e)}")
            return Response(
                {'error': 'Failed to estimate cost'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class APIKeyViewSet(viewsets.ModelViewSet):
    queryset = APIKey.objects.all()
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['label', 'provider__name']
    ordering_fields = ['label', 'provider__name', 'is_default']
    ordering = ['provider__name', 'label']

    def get_queryset(self):
        user = self.request.user
        if not user.default_org:
            return APIKey.objects.none()
            
        return self.queryset.filter(
            Q(organization=user.default_org) | Q(organization__isnull=True),
            is_active=True
        )

    def perform_create(self, serializer):
        if not self.request.user.default_org:
            raise ValidationError("User must have a default organization")
        serializer.save(organization=self.request.user.default_org)
        
    @action(detail=False, methods=['get'])
    def usage_summary(self, request):
        """Get usage summary for all API keys"""
        try:
            user = request.user
            organization = user.default_org
            
            if not organization:
                return Response(
                    {'error': 'User must have a default organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use the APIKeyManager to get usage summary
            key_manager = APIKeyManager()
            summary = key_manager.get_usage_summary(organization)
            
            return Response(summary)
            
        except Exception as e:
            logger.error(f"Usage summary error: {str(e)}")
            return Response(
                {'error': 'Failed to get usage summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=False, methods=['get'])
    def health_status(self, request):
        """Get health status of API keys"""
        try:
            user = request.user
            organization = user.default_org
            
            if not organization:
                return Response(
                    {'error': 'User must have a default organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use the APIKeyManager to get key health
            key_manager = APIKeyManager()
            health = key_manager.get_key_health(organization)
            
            return Response(health)
            
        except Exception as e:
            logger.error(f"Health status error: {str(e)}")
            return Response(
                {'error': 'Failed to get health status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def quota_status(self, request, pk=None):
        """Get quota status for a specific API key"""
        try:
            api_key = self.get_object()
            quota_info = api_key.quota_status
            
            return Response({
                'key_id': api_key.id,
                'label': api_key.label,
                'provider': api_key.provider.name,
                **quota_info
            })
            
        except Exception as e:
            logger.error(f"Quota status error: {str(e)}")
            return Response(
                {'error': 'Failed to get quota status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RoutingRuleViewSet(viewsets.ModelViewSet):
    queryset = RoutingRule.objects.all()
    serializer_class = RoutingRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'priority', 'model_type', 'is_active']
    filterset_fields = ['is_active', 'model_type']
    ordering = ['priority']

    def get_queryset(self):
        user = self.request.user
        if not user.default_org:
            return RoutingRule.objects.none()
            
        return self.queryset.filter(
            Q(organization=user.default_org) | Q(organization__isnull=True)
        )

    def perform_create(self, serializer):
        if not self.request.user.default_org:
            raise ValidationError("User must have a default organization")
        serializer.save(organization=self.request.user.default_org)

    @action(detail=False, methods=['post'])
    def evaluate(self, request):
        """Evaluate routing rules for a given model type and context"""
        try:
            model_type = request.data.get('model_type')
            context = request.data.get('context', {})
            
            if not model_type:
                return Response(
                    {'error': 'model_type is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get applicable rules
            rules = self.get_queryset().filter(model_type=model_type)
            
            if not rules.exists():
                return Response(
                    {'error': f'No rules found for model_type: {model_type}'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Evaluate rules in priority order
            for rule in rules:
                # Simple condition evaluation (enhanced version)
                conditions_met = self._evaluate_rule_conditions(rule.conditions, context)
                
                if conditions_met:
                    # Return the matching models with their weights
                    rule_models = rule.routingrulemodel_set.select_related('model', 'model__provider').all()
                    
                    return Response({
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'rule_priority': rule.priority,
                        'models': [
                            {
                                'model_id': rm.model.id,
                                'model_name': rm.model.name,
                                'provider': rm.model.provider.name,
                                'weight': rm.weight,
                                'cost_input': float(rm.model.cost_input),
                                'cost_output': float(rm.model.cost_output)
                            } for rm in rule_models if rm.model.status == 'ACTIVE'
                        ]
                    })
            
            return Response(
                {'error': 'No matching rules found for the given context'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"Rule evaluation error: {str(e)}")
            return Response(
                {'error': 'Failed to evaluate routing rules'},  
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _evaluate_rule_conditions(self, conditions, context):
        """Evaluate rule conditions against context"""
        if not conditions:
            return True
            
        try:
            for condition in conditions:
                field = condition.get('field')
                operator = condition.get('operator')
                value = condition.get('value')
                
                if not all([field, operator, value is not None]):
                    continue
                
                context_value = context.get(field)
                
                if context_value is None:
                    return False
                
                # Evaluate condition
                if operator == 'equals' and context_value != value:
                    return False
                elif operator == 'contains' and value not in str(context_value):
                    return False
                elif operator == 'gt' and not (isinstance(context_value, (int, float)) and context_value > value):
                    return False
                elif operator == 'lt' and not (isinstance(context_value, (int, float)) and context_value < value):
                    return False
                elif operator == 'gte' and not (isinstance(context_value, (int, float)) and context_value >= value):
                    return False
                elif operator == 'lte' and not (isinstance(context_value, (int, float)) and context_value <= value):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Condition evaluation error: {str(e)}")
            return False


class ModelMetricsViewSet(viewsets.ModelViewSet):
    queryset = ModelMetrics.objects.all()
    serializer_class = ModelMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['model__name', 'model__provider__name']
    ordering_fields = ['timestamp', 'latency_ms', 'cost']
    ordering = ['-timestamp']

    def get_queryset(self):
        user = self.request.user
        if not user.default_org:
            return ModelMetrics.objects.none()
            
        return self.queryset.filter(
            Q(organization=user.default_org) | Q(organization__isnull=True)
        )

    def perform_create(self, serializer):
        if not self.request.user.default_org:
            raise ValidationError("User must have a default organization")
        serializer.save(organization=self.request.user.default_org)
        
    @action(detail=False, methods=['get'])
    def cost_summary(self, request):
        """Get cost summary for the organization"""
        try:
            user = request.user
            organization = user.default_org
            
            if not organization:
                return Response(
                    {'error': 'User must have a default organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get and validate days parameter
            try:
                days = int(request.query_params.get('days', 30))
                if days < 1 or days > 365:
                    days = 30
            except (ValueError, TypeError):
                days = 30
                
            summary = ModelMetrics.get_cost_summary(organization, days)
            
            # Add additional stats with error handling
            start_date = timezone.now() - timedelta(days=days)
            
            try:
                # Cost by model (top 10)
                cost_by_model = list(ModelMetrics.objects.filter(
                    organization=organization,
                    timestamp__gte=start_date
                ).values(
                    'model__name', 'model__provider__name'
                ).annotate(
                    total_cost=Sum('cost'),
                    request_count=Count('id'),
                    avg_latency=Avg('latency_ms')
                ).order_by('-total_cost')[:10])
                
                # Cost by day (last 30 days max for performance)
                from django.db.models.functions import TruncDay
                days_for_trend = min(days, 30)
                trend_start_date = timezone.now() - timedelta(days=days_for_trend)
                
                cost_by_day = list(ModelMetrics.objects.filter(
                    organization=organization,
                    timestamp__gte=trend_start_date
                ).annotate(
                    day=TruncDay('timestamp')
                ).values('day').annotate(
                    total_cost=Sum('cost'),
                    request_count=Count('id')
                ).order_by('day'))
                
                # Convert dates to strings for JSON serialization
                for item in cost_by_day:
                    item['day'] = item['day'].strftime('%Y-%m-%d')
                
            except Exception as e:
                logger.error(f"Cost breakdown error: {str(e)}")
                cost_by_model = []
                cost_by_day = []
            
            return Response({
                'summary': summary,
                'cost_by_model': cost_by_model,
                'cost_by_day': cost_by_day,
                'days': days,
                'organization': organization.name
            })
            
        except Exception as e:
            logger.error(f"Cost summary error: {str(e)}")
            return Response(
                {'error': 'Failed to get cost summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=False, methods=['get'])
    def optimization_stats(self, request):
        """Get optimization statistics"""
        try:
            user = request.user
            organization = user.default_org
            
            if not organization:
                return Response(
                    {'error': 'User must have a default organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get and validate days parameter
            try:
                days = int(request.query_params.get('days', 30))
                if days < 1 or days > 365:
                    days = 30
            except (ValueError, TypeError):
                days = 30
                
            start_date = timezone.now() - timedelta(days=days)
            
            # Get metrics with optimization metadata
            metrics = ModelMetrics.objects.filter(
                organization=organization,
                timestamp__gte=start_date
            ).exclude(optimization_metadata={})  # Better than isnull check
            
            # Calculate savings
            total_savings = Decimal('0.00')
            total_optimized_requests = 0
            strategies_used = {}
            models_optimized = {}
            
            for metric in metrics:
                metadata = metric.optimization_metadata
                if metadata and isinstance(metadata, dict):
                    total_optimized_requests += 1
                    
                    # Track strategies
                    strategy = metadata.get('strategy', 'unknown')
                    strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
                    
                    # Track models
                    model_name = metric.model.name
                    models_optimized[model_name] = models_optimized.get(model_name, 0) + 1
                    
                    # Calculate savings if available
                    if 'estimated_savings' in metadata:
                        savings_str = metadata['estimated_savings']
                        if savings_str and isinstance(savings_str, str) and savings_str.endswith('%'):
                            try:
                                savings_pct = float(savings_str.rstrip('%'))
                                request_savings = metric.cost * (savings_pct / 100)
                                total_savings += request_savings
                            except (ValueError, TypeError):
                                pass
            
            # Calculate average savings percentage
            total_requests = ModelMetrics.objects.filter(
                organization=organization,
                timestamp__gte=start_date
            ).count()
            
            optimization_rate = (total_optimized_requests / max(total_requests, 1)) * 100
            
            return Response({
                'total_requests': total_requests,
                'total_optimized_requests': total_optimized_requests,
                'optimization_rate': round(optimization_rate, 1),
                'total_estimated_savings': float(total_savings),
                'strategies_used': strategies_used,
                'models_optimized': models_optimized,
                'days': days,
                'organization': organization.name
            })
            
        except Exception as e:
            logger.error(f"Optimization stats error: {str(e)}")
            return Response(
                {'error': 'Failed to get optimization statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get all dashboard data in one call - MVP optimization"""
        try:
            user = request.user
            organization = user.default_org
            
            if not organization:
                return Response(
                    {'error': 'User must have a default organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get both cost summary and optimization stats in one response
            # This reduces frontend API calls for MVP
            days = int(request.query_params.get('days', 30))
            
            # Get cost summary
            cost_summary_response = self.cost_summary(request)
            cost_data = cost_summary_response.data if cost_summary_response.status_code == 200 else {}
            
            # Get optimization stats  
            opt_stats_response = self.optimization_stats(request)
            opt_data = opt_stats_response.data if opt_stats_response.status_code == 200 else {}
            
            # Get API key health
            key_manager = APIKeyManager()
            key_health = key_manager.get_key_health(organization)
            usage_summary = key_manager.get_usage_summary(organization)
            
            return Response({
                'cost_summary': cost_data,
                'optimization_stats': opt_data,
                'key_health': key_health,
                'usage_summary': usage_summary,
                'organization': organization.name,
                'last_updated': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Dashboard summary error: {str(e)}")
            return Response(
                {'error': 'Failed to get dashboard summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )