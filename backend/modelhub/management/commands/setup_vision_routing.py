# File: backend/modelhub/management/commands/setup_vision_routing.py

from django.core.management.base import BaseCommand
from modelhub.models import Provider, Model, RoutingRule, RoutingRuleModel


class Command(BaseCommand):
    help = 'Setup default routing rules for vision models'

    def handle(self, *args, **options):
        self.stdout.write('Setting up vision routing rules...')
        
        # Ensure vision models exist
        self._ensure_vision_models()
        
        # Create system-wide routing rules
        self._create_cost_first_rule()
        self._create_quality_first_rule()
        self._create_engineering_drawing_rule()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Vision routing rules setup complete!'))
    
    def _ensure_vision_models(self):
        """Ensure vision models are registered"""
        local_provider, _ = Provider.objects.get_or_create(
            slug='local',
            defaults={
                'name': 'Local Models',
                'supports_vision': True,
                'status': 'ACTIVE'
            }
        )
        
        Model.objects.get_or_create(
            provider=local_provider,
            name='qwen3vl-72b',
            defaults={
                'model_type': 'VISION',
                'capabilities': ['vision', 'chat'],
                'vision_max_image_size': 2048,
                'vision_supported_formats': ['png', 'jpg', 'jpeg'],
                'vision_max_images': 1,
                'cost_input': 0.0,
                'cost_output': 0.0,
                'context_window': 8192,
                'status': 'ACTIVE'
            }
        )
        
        anthropic_provider, _ = Provider.objects.get_or_create(
            slug='anthropic',
            defaults={
                'name': 'Anthropic',
                'supports_vision': True,
                'status': 'ACTIVE'
            }
        )
        
        Model.objects.get_or_create(
            provider=anthropic_provider,
            name='claude-sonnet-4-5',
            defaults={
                'model_type': 'VISION',
                'capabilities': ['vision', 'chat'],
                'vision_max_image_size': 1568,
                'vision_supported_formats': ['png', 'jpg', 'jpeg', 'webp', 'gif'],
                'vision_max_images': 5,
                'cost_input': 3.0,
                'cost_output': 15.0,
                'context_window': 200000,
                'status': 'ACTIVE'
            }
        )
    
    def _create_cost_first_rule(self):
        """Rule: When priority=cost, use free local models"""
        rule, created = RoutingRule.objects.get_or_create(
            name='Vision - Cost First',
            model_type='VISION',
            organization=None,  # System-wide
            defaults={
                'description': 'Use free local vision models when cost is priority',
                'priority': 1,  # Highest priority
                'is_active': True,
                'conditions': [
                    {
                        'field': 'priority',
                        'operator': 'equals',
                        'value': 'cost'
                    }
                ]
            }
        )
        
        if created:
            # Add free models to this rule
            local_models = Model.objects.filter(
                model_type='VISION',
                cost_input=0.0,
                status='ACTIVE'
            )
            
            for model in local_models:
                RoutingRuleModel.objects.get_or_create(
                    rule=rule,
                    model=model,
                    defaults={'weight': 100}  # High weight
                )
            
            self.stdout.write(self.style.SUCCESS('  ✓ Created: Vision - Cost First'))
    
    def _create_quality_first_rule(self):
        """Rule: When priority=quality, use Claude or GPT-4"""
        rule, created = RoutingRule.objects.get_or_create(
            name='Vision - Quality First',
            model_type='VISION',
            organization=None,
            defaults={
                'description': 'Use high-quality vision models when quality is priority',
                'priority': 2,
                'is_active': True,
                'conditions': [
                    {
                        'field': 'priority',
                        'operator': 'equals',
                        'value': 'quality'
                    }
                ]
            }
        )
        
        if created:
            # Add high-quality models
            quality_models = Model.objects.filter(
                model_type='VISION',
                name__in=['claude-sonnet-4-5', 'gpt-4o', 'gpt-4-vision-preview'],
                status='ACTIVE'
            )
            
            for model in quality_models:
                RoutingRuleModel.objects.get_or_create(
                    rule=rule,
                    model=model,
                    defaults={'weight': 50}
                )
            
            self.stdout.write(self.style.SUCCESS('  ✓ Created: Vision - Quality First'))
    
    def _create_engineering_drawing_rule(self):
        """Rule: For engineering drawings, prefer Claude or local"""
        rule, created = RoutingRule.objects.get_or_create(
            name='Vision - Engineering Drawings',
            model_type='VISION',
            organization=None,
            defaults={
                'description': 'Specialized routing for engineering drawings',
                'priority': 3,
                'is_active': True,
                'conditions': [
                    {
                        'field': 'file_type',
                        'operator': 'equals',
                        'value': 'engineering_drawing'
                    }
                ]
            }
        )
        
        if created:
            # Prefer Claude for complex drawings
            claude = Model.objects.filter(
                name='claude-sonnet-4-5',
                status='ACTIVE'
            ).first()
            
            if claude:
                RoutingRuleModel.objects.get_or_create(
                    rule=rule,
                    model=claude,
                    defaults={'weight': 70}
                )
            
            # Fallback to local if budget constrained
            qwen = Model.objects.filter(
                name='qwen3vl-72b',
                status='ACTIVE'
            ).first()
            
            if qwen:
                RoutingRuleModel.objects.get_or_create(
                    rule=rule,
                    model=qwen,
                    defaults={'weight': 30}
                )
            
            self.stdout.write(self.style.SUCCESS('  ✓ Created: Vision - Engineering Drawings'))