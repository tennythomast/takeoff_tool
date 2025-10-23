# File: backend/modelhub/models.py
# Update the Model class with the async wrapper method

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from core.models import BaseModel
from encrypted_model_fields.fields import EncryptedCharField
from channels.db import database_sync_to_async


class Provider(BaseModel):
    """Model for LLM providers like OpenAI, Anthropic, etc."""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    supports_embeddings = models.BooleanField(default=False)
    embedding_endpoint = models.URLField(blank=True)  
    supports_vision = models.BooleanField(default=False)  # NEW
    vision_endpoint = models.URLField(blank=True)  # NEW
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('INACTIVE', 'Inactive'),
            ('DEPRECATED', 'Deprecated')
        ],
        default='ACTIVE'
    )
    config = models.JSONField(default=dict, blank=True)
    # Provider-specific configuration like base URLs, API versions, etc.

    class Meta:
        ordering = ['name']

    def clean(self):
        super().clean()
        if not isinstance(self.config, dict):
            raise ValidationError({'config': 'Config must be a dictionary'})

    def __str__(self):
        return self.name


class Model(BaseModel):
    """Model representing an AI model from a provider."""
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50, blank=True)
    model_type = models.CharField(
        max_length=20,
        choices=[
            ('TEXT', 'Text'),
            ('CODE', 'Code'),
            ('IMAGE', 'Image'),
            ('VOICE', 'Voice'),
            ('VIDEO', 'Video'),
            ('EMBEDDING', 'Embedding Model'),
            ('VISION', 'Vision Model')
        ]
    )
    capabilities = models.JSONField(default=list)
    # List of capabilities like ['chat', 'completion', 'function_calling', 'embedding', 'vision']
    embedding_dimensions = models.IntegerField(null=True, blank=True) 
    # Vision-specific fields
    vision_max_image_size = models.IntegerField(
        null=True, 
        blank=True, 
        help_text='Maximum image size in pixels (width or height)'
    )
    vision_supported_formats = models.JSONField(
        default=list,
        blank=True,
        help_text='List of supported image formats (e.g., ["png", "jpeg", "webp"])'
    )
    vision_max_images = models.IntegerField(
        null=True, 
        blank=True, 
        help_text='Maximum number of images per request'
    )
    config = models.JSONField(default=dict, blank=True)
    # Model-specific configuration
    
    cost_input = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        help_text='Cost per 1K input tokens in USD'
    )
    cost_output = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        help_text='Cost per 1K output tokens in USD'
    )
    cost_image = models.DecimalField(  # NEW
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Cost per image in USD (for vision models)'
    )
    context_window = models.IntegerField(
        help_text='Maximum context length in tokens'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('INACTIVE', 'Inactive'),
            ('DEPRECATED', 'Deprecated')
        ],
        default='ACTIVE'
    )

    class Meta:
        ordering = ['provider', 'name']
        unique_together = ['provider', 'name', 'version']

    def clean(self):
        super().clean()
        if self.cost_input < 0 or self.cost_output < 0:
            raise ValidationError({'cost': 'Cost cannot be negative'})
        if not isinstance(self.capabilities, list):
            raise ValidationError({'capabilities': 'Capabilities must be a list'})

    def supports_chat(self):
        """Check if this model supports chat completions"""
        return 'chat' in self.capabilities

    def supports_completion(self):
        """Check if this model supports text completions"""
        return 'completion' in self.capabilities

    def supports_embedding(self):
        """Check if this model supports embeddings"""
        return 'embedding' in self.capabilities

    def supports_vision(self):
        """Check if this model supports vision/image inputs"""
        return 'vision' in self.capabilities or self.model_type == 'VISION'

    def get_preferred_api_type(self):
        """Get the preferred API type for this model based on capabilities"""
        if self.supports_vision() and self.supports_chat():
            return 'VISION_CHAT'
        elif self.supports_chat():
            return 'CHAT'
        elif self.supports_completion():
            return 'COMPLETION'
        elif self.supports_embedding():
            return 'EMBEDDING'
        elif self.supports_vision():
            return 'VISION'
        else:
            # Default fallback based on provider and model name
            return self._get_fallback_api_type()

    def _get_fallback_api_type(self):
        """Fallback API type detection based on provider and model name"""
        if self.provider.slug == 'openai':
            model_name_lower = self.name.lower()
            if any(name in model_name_lower for name in ['gpt-4', 'gpt-3.5-turbo', 'chatgpt']):
                return 'CHAT'
            elif any(name in model_name_lower for name in ['embedding', 'ada']):
                return 'EMBEDDING'
            elif any(name in model_name_lower for name in ['davinci', 'curie', 'babbage', 'instruct']):
                return 'COMPLETION'
            else:
                return 'CHAT'  # Default to chat for newer OpenAI models
        elif self.provider.slug == 'anthropic':
            return 'CHAT'  # Anthropic uses messages format (similar to chat)
        else:
            return 'CHAT'  # Default for unknown providers
            
    def supports_embedding(self):
            """Check if this model supports embeddings"""
            return 'embedding' in self.capabilities

    def get_embedding_config(self, strategy='balanced'):
        """Get embedding-specific configuration based on strategy"""
        base_config = {
            'model_name': self.name,
            'dimensions': self.embedding_dimensions,
            'max_tokens': self.context_window,
            'cost_per_1k': float(self.cost_input)
        }
        
        # Strategy-specific optimizations
        if strategy == 'cost_first':
            base_config.update({
                'batch_size': 1000,  # Larger batches for cost efficiency
                'priority': 'cost'
            })
        elif strategy == 'quality_first':
            base_config.update({
                'batch_size': 100,   # Smaller batches for quality
                'priority': 'accuracy'
            })
        
        return base_config

    def get_vision_config(self):
        """Get vision configuration with defaults"""
        default_config = {
            'max_image_size': self.vision_max_image_size or 2048,
            'supported_formats': self.vision_supported_formats or ['png', 'jpg', 'jpeg'],
            'max_images_per_request': self.vision_max_images or 1,
            'recommended_dpi': 300,
            'encoding': 'base64',
        }
        
        if 'vision' in self.config:
            return {**default_config, **self.config['vision']}
        
        return default_config
    
    def estimate_vision_cost(self, image_count, expected_output_tokens=2000):
        """Estimate cost for vision request"""
        config = self.get_vision_config()
        image_tokens = image_count * 85  # Standard estimate
        prompt_tokens = 1000
        total_input_tokens = image_tokens + prompt_tokens
        
        input_cost = (total_input_tokens / 1000) * float(self.cost_input)
        if self.cost_image:
            input_cost += float(self.cost_image) * image_count
        
        output_cost = (expected_output_tokens / 1000) * float(self.cost_output)
        
        return {
            'total_cost': input_cost + output_cost,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'cost_per_image': (input_cost + output_cost) / image_count if image_count > 0 else 0
        }

    @classmethod
    def get_api_type_for_model(cls, provider_slug, model_name):
        """Get API type for a specific model - class method for easy access"""
        try:
            model = cls.objects.get(
                provider__slug=provider_slug,
                name=model_name,
                status='ACTIVE'
            )
            return model.get_preferred_api_type()
        except cls.DoesNotExist:
            # Create a temporary model instance for fallback logic
            try:
                provider = Provider.objects.get(slug=provider_slug)
                temp_model = cls(provider=provider, name=model_name)
                return temp_model._get_fallback_api_type()
            except Provider.DoesNotExist:
                return 'CHAT'  # Ultimate fallback


    # Async wrapper methods for use in async contexts
    @classmethod
    @database_sync_to_async
    def get_api_type_for_model_async(cls, provider_slug, model_name):
        """Async version of get_api_type_for_model"""
        return cls.get_api_type_for_model(provider_slug, model_name)

    @classmethod
    @database_sync_to_async  
    def get_model_async(cls, provider_slug, model_name):
        """Get model object asynchronously"""
        return cls.objects.select_related('provider').get(
            provider__slug=provider_slug,
            name=model_name,
            status='ACTIVE'
        )

    @classmethod
    @database_sync_to_async
    def get_active_models_for_provider_async(cls, provider_slug):
        """Get all active models for a provider asynchronously"""
        return list(cls.objects.filter(
            provider__slug=provider_slug,
            status='ACTIVE'
        ).select_related('provider'))

    @property
    def cost_display(self):
        """Friendly display of costs for frontend"""
        display = {
            'input_per_1k': f"${self.cost_input:.4f}",
            'output_per_1k': f"${self.cost_output:.4f}",
            'input_per_token': f"${(self.cost_input/1000):.6f}",
            'output_per_token': f"${(self.cost_output/1000):.6f}"
        }
        
        if self.cost_image:
            display['per_image'] = f"${self.cost_image:.4f}"
        
        return display
    
    def estimate_cost(self, input_tokens, output_tokens, image_count=0):
        """Estimate cost for given token counts and optional images"""
        cost = (self.cost_input * input_tokens / 1000) + \
            (self.cost_output * output_tokens / 1000)
        
        if image_count > 0 and self.cost_image:
            cost += float(self.cost_image) * image_count
        
        return cost

    def __str__(self):
        return f'{self.provider.name} - {self.name} {self.version}'


class APIKey(BaseModel):
    """Model for storing API keys for providers."""
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='If null, this is a system-wide API key'
    )
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    key = EncryptedCharField(max_length=255)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    daily_quota = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Daily spending limit in USD'
    )
    monthly_quota = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monthly spending limit in USD'
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last successful API call'
    )

    class Meta:
        unique_together = ['organization', 'provider', 'label']
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'label'],
                condition=models.Q(organization__isnull=True),
                name='unique_system_apikey'
            )
        ]

    def clean(self):
        super().clean()
        if self.daily_quota is not None and self.daily_quota < 0:
            raise ValidationError({'daily_quota': 'Daily quota cannot be negative'})
        if self.monthly_quota is not None and self.monthly_quota < 0:
            raise ValidationError({'monthly_quota': 'Monthly quota cannot be negative'})

    def __str__(self):
        org = self.organization.name if self.organization else 'System'
        return f'{org} - {self.provider.name} - {self.label}'

    @classmethod
    def get_dataelan_keys(cls, provider=None):
        """Get Dataelan's system-wide API keys.
        
        Args:
            provider (Provider, optional): Filter keys by provider.
        
        Returns:
            QuerySet: QuerySet of system-wide API keys (organization=None)
        """
        queryset = cls.objects.filter(organization__isnull=True)
        if provider:
            queryset = queryset.filter(provider=provider)
        return queryset.order_by('provider__name', 'label')

    @classmethod
    @database_sync_to_async
    def get_active_key_for_provider_async(cls, provider_slug, organization=None):
        """Get active API key for provider asynchronously"""
        try:
            query = cls.objects.filter(
                provider__slug=provider_slug,
                is_active=True
            ).select_related('provider')
            
            if organization:
                query = query.filter(organization=organization)
            else:
                query = query.filter(organization__isnull=True)  # System keys
            
            return query.first()
        except Exception:
            return None

    def get_usage_this_month(self):
        """Get current month usage for this key"""
        from django.utils import timezone
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return ModelMetrics.objects.filter(
            api_key=self,
            timestamp__gte=start_of_month
        ).aggregate(
            total_cost=models.Sum('cost'),
            total_requests=models.Count('id')
        )
    
    @property
    def quota_status(self):
        """Get quota status for dashboard"""
        usage = self.get_usage_this_month()
        monthly_used = usage['total_cost'] or 0
        monthly_quota = self.monthly_quota or 0
        
        if monthly_quota > 0:
            usage_percent = (monthly_used / monthly_quota) * 100
            status = 'healthy' if usage_percent < 75 else ('warning' if usage_percent < 90 else 'critical')
        else:
            usage_percent = 0
            status = 'no_limit'
        
        return {
            'used': float(monthly_used),
            'quota': float(monthly_quota),
            'usage_percent': usage_percent,
            'status': status
        }

    @classmethod
    @database_sync_to_async
    def get_embedding_key_async(cls, provider_slug, organization=None):
        """Get API key specifically for embedding operations"""
        try:
            query = cls.objects.filter(
                provider__slug=provider_slug,
                provider__supports_embeddings=True,  # Only embedding-capable providers
                is_active=True
            ).select_related('provider')
            
            if organization:
                # Try organization key first
                org_key = query.filter(organization=organization).first()
                if org_key:
                    return org_key
            
            # Fallback to system key
            return query.filter(organization__isnull=True).first()
            
        except Exception:
            return None
    
    def get_embedding_quota_status(self):
        """Specialized quota check for embedding operations"""
        usage = self.get_usage_this_month()
        
        # Estimate remaining embedding capacity
        monthly_used = usage['total_cost'] or 0
        if self.monthly_quota:
            remaining_budget = float(self.monthly_quota) - monthly_used
            
            # Estimate tokens remaining (assuming average $0.00002/1k for voyage-3.5-lite)
            estimated_tokens_remaining = remaining_budget / 0.00002 * 1000
            
            return {
                **self.quota_status,
                'estimated_tokens_remaining': int(estimated_tokens_remaining),
                'can_process_embeddings': remaining_budget > 1.0  # At least $1 remaining
            }
        
        return {**self.quota_status, 'can_process_embeddings': True}
    @classmethod
    @database_sync_to_async
    def get_vision_key_async(cls, provider_slug, organization=None):
        """Get API key specifically for vision operations"""
        try:
            query = cls.objects.filter(
                provider__slug=provider_slug,
                provider__supports_vision=True,
                is_active=True
            ).select_related('provider')
            
            if organization:
                org_key = query.filter(organization=organization).first()
                if org_key:
                    return org_key
            
            # Fallback to system key
            return query.filter(organization__isnull=True).first()
            
        except Exception:
            return None

    def get_vision_quota_status(self, cost_per_image=0.04):
        """Specialized quota check for vision operations"""
        usage = self.get_usage_this_month()
        monthly_used = usage['total_cost'] or 0
        
        if self.monthly_quota:
            remaining_budget = float(self.monthly_quota) - monthly_used
            estimated_images_remaining = int(remaining_budget / cost_per_image)
            
            return {
                **self.quota_status,
                'estimated_images_remaining': estimated_images_remaining,
                'can_process_vision': remaining_budget > cost_per_image
            }
        
        return {**self.quota_status, 'can_process_vision': True}

class RoutingRule(BaseModel):
    """Model for defining model routing rules."""
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='If null, this is a system-wide rule'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text='1 is highest priority'
    )
    is_active = models.BooleanField(default=True)
    model_type = models.CharField(
        max_length=20,
        choices=[
            ('TEXT', 'Text'),
            ('CODE', 'Code'),
            ('IMAGE', 'Image'),
            ('VOICE', 'Voice'),
            ('VIDEO', 'Video'),
            ('VISION', 'Vision'),
            ('EMBEDDING', 'Embedding')
        ]
    )
    conditions = models.JSONField(
        help_text='Conditions that must be met to use this rule'
    )
    models = models.ManyToManyField(
        Model,
        through='RoutingRuleModel',
        help_text='Models to use when conditions are met'
    )

    class Meta:
        ordering = ['priority']

    def clean(self):
        super().clean()
        if not isinstance(self.conditions, list):
            raise ValidationError({'conditions': 'Conditions must be a list of condition objects'})
        
        # Validate condition structure for MVP
        for condition in self.conditions:
            if not isinstance(condition, dict):
                raise ValidationError({'conditions': 'Each condition must be a dictionary'})
            if not all(key in condition for key in ['field', 'operator', 'value']):
                raise ValidationError({'conditions': 'Each condition must have field, operator, and value'})

    def __str__(self):
        return f'{self.name} ({self.priority})'


class RoutingRuleModel(BaseModel):
    """Through model for RoutingRule and Model with weights."""
    rule = models.ForeignKey(RoutingRule, on_delete=models.CASCADE)
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    weight = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text='Relative weight for random selection'
    )
    notes = models.TextField(
        blank=True,
        help_text='Optional notes about why this model was chosen for this rule'
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='List of tags for filtering and organizing model choices'
    )

    class Meta:
        unique_together = ['rule', 'model']


class ModelMetrics(BaseModel):
    """Model for tracking model performance metrics."""
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='API key used for this request'
    )
    session = models.ForeignKey(
        'prompt.PromptSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='metrics',
        help_text='Prompt session associated with this metric'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    latency_ms = models.IntegerField(help_text='Response time in milliseconds')
    tokens_input = models.IntegerField()
    tokens_output = models.IntegerField()
    image_count = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6)
    status = models.CharField(
        max_length=20,
        choices=[
            ('SUCCESS', 'Success'),
            ('ERROR', 'Error'),
            ('TIMEOUT', 'Timeout')
        ]
    )
    error_type = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    optimization_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Metadata about cost optimization decisions'
    )

    class Meta:
        indexes = [
            models.Index(fields=['model', 'timestamp']),
            models.Index(fields=['organization', 'timestamp'])
        ]

    def clean(self):
        super().clean()
        if self.cost < 0:
            raise ValidationError({'cost': 'Cost cannot be negative'})

    def __str__(self):
        return f'{self.model.name} - {self.organization.name if self.organization else "System"}'
    
    @classmethod
    def get_cost_summary(cls, organization=None, days=30):
        """Simple cost summary for dashboard"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = cls.objects.filter(timestamp__gte=start_date)
        
        if organization:
            queryset = queryset.filter(organization=organization)
        
        result = queryset.aggregate(
            total_cost=models.Sum('cost'),
            total_requests=models.Count('id'),
            avg_latency=models.Avg('latency_ms'),
            success_rate=models.Count('id', filter=models.Q(status='SUCCESS')) * 100.0 / models.Count('id')
        )
        
        return {
            'total_cost': result['total_cost'] or 0,
            'total_requests': result['total_requests'] or 0,
            'avg_latency': result['avg_latency'] or 0,
            'success_rate': result['success_rate'] or 0
        }
    
    @classmethod
    @database_sync_to_async
    def log_embedding_usage_async(cls, model, organization, tokens_processed, 
                                 cost, latency_ms, api_key=None):
        """Log embedding-specific usage metrics"""
        return cls.objects.acreate(
            model=model,
            organization=organization,
            api_key=api_key,
            latency_ms=latency_ms,
            tokens_input=tokens_processed,
            tokens_output=0,  # Embeddings don't have output tokens
            cost=cost,
            status='SUCCESS',
            optimization_metadata={
                'operation_type': 'embedding',
                'tokens_per_second': int(tokens_processed / (latency_ms / 1000)) if latency_ms > 0 else 0,
                'cost_per_token': float(cost / tokens_processed) if tokens_processed > 0 else 0,
                'model_strategy': model.name
            }
        )
    
    @classmethod
    def get_embedding_analytics(cls, organization=None, days=30):
        """Get embedding-specific analytics"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = cls.objects.filter(
            timestamp__gte=start_date,
            optimization_metadata__operation_type='embedding'
        )
        
        if organization:
            queryset = queryset.filter(organization=organization)
        
        return queryset.aggregate(
            total_embedding_cost=models.Sum('cost'),
            total_tokens_processed=models.Sum('tokens_input'),
            avg_embedding_latency=models.Avg('latency_ms'),
            total_embedding_requests=models.Count('id')
        )

    @classmethod
    @database_sync_to_async
    def log_vision_usage_async(cls, model, organization, tokens_input, tokens_output,
                            image_count, cost, latency_ms, api_key=None, 
                            metadata=None):
        """Log vision-specific usage metrics"""
        return cls.objects.acreate(
            model=model,
            organization=organization,
            api_key=api_key,
            latency_ms=latency_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            image_count=image_count,
            cost=cost,
            status='SUCCESS',
            optimization_metadata={
                'operation_type': 'vision',
                'images_per_second': image_count / (latency_ms / 1000) if latency_ms > 0 else 0,
                'cost_per_image': float(cost / image_count) if image_count > 0 else 0,
                'cost_per_token': float(cost / (tokens_input + tokens_output)) if (tokens_input + tokens_output) > 0 else 0,
                'model_strategy': model.name,
                **(metadata or {})
            }
        )

    @classmethod
    def get_vision_analytics(cls, organization=None, days=30):
        """Get vision-specific analytics"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = cls.objects.filter(
            timestamp__gte=start_date,
            optimization_metadata__operation_type='vision'
        )
        
        if organization:
            queryset = queryset.filter(organization=organization)
        
        return queryset.aggregate(
            total_vision_cost=models.Sum('cost'),
            total_images_processed=models.Sum('image_count'),
            avg_vision_latency=models.Avg('latency_ms'),
            total_vision_requests=models.Count('id'),
            avg_cost_per_image=models.Avg(
                models.ExpressionWrapper(
                    models.F('cost') / models.F('image_count'),
                    output_field=models.DecimalField()
                ),
                filter=models.Q(image_count__gt=0)
            )
        )