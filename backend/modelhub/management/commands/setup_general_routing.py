from django.core.management.base import BaseCommand
from modelhub.models import RoutingRule, RoutingRuleModel, Model, Provider


class Command(BaseCommand):
    help = 'Setup general routing rules that work for all entity types'

    def handle(self, *args, **options):
        """Setup general routing rules"""
        self.stdout.write(self.style.SUCCESS("🚀 Setting up general routing rules..."))
        
        # General routing rules configuration
        general_rules_config = [
            {
                'name': 'Cost Effective',
                'description': 'Cost-optimized models for general use',
                'priority': 10,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'complexity_score', 'operator': 'lt', 'value': 0.6},
                    {'field': 'optimization_strategy', 'operator': 'eq', 'value': 'cost'}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 40},
                    {'provider': 'google', 'model': 'gemini-1.5-flash', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 25}
                ]
            },
            {
                'name': 'Balanced Performance',
                'description': 'Balanced performance and cost for general use',
                'priority': 20,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'optimization_strategy', 'operator': 'eq', 'value': 'balanced'}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 40},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 35},
                    {'provider': 'google', 'model': 'gemini-1.5-flash', 'weight': 25}
                ]
            },
            {
                'name': 'Quality First',
                'description': 'High-quality models for complex tasks',
                'priority': 30,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'optimization_strategy', 'operator': 'eq', 'value': 'quality'}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 40},
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 35},
                    {'provider': 'google', 'model': 'gemini-1.5-pro', 'weight': 25}
                ]
            },
            {
                'name': 'High Complexity',
                'description': 'Advanced models for high complexity tasks',
                'priority': 40,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'complexity_score', 'operator': 'gte', 'value': 0.7}
                ],
                'models': [
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 40},
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 35},
                    {'provider': 'google', 'model': 'gemini-1.5-pro', 'weight': 25}
                ]
            }
        ]
        
        rules_created = 0
        models_associated = 0
        
        # First, clear any existing entity-specific rules
        entity_specific_rules = RoutingRule.objects.filter(
            name__in=[
                'Agent Session - Quality Focused',
                'Workflow Execution - Function Calling',
                'Platform Chat - Cost Optimized',
                'Workspace Chat - Balanced Performance'
            ]
        )
        entity_rules_count = entity_specific_rules.count()
        entity_specific_rules.delete()
        self.stdout.write(f"Removed {entity_rules_count} entity-specific rules")
        
        # Create or update general rules
        for rule_config in general_rules_config:
            # Create or update the rule
            rule, created = RoutingRule.objects.update_or_create(
                name=rule_config['name'],
                defaults={
                    'description': rule_config['description'],
                    'priority': rule_config['priority'],
                    'model_type': rule_config['model_type'],
                    'conditions': rule_config['conditions'],
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f"✅ Created rule: {rule.name}")
            else:
                self.stdout.write(f"✅ Updated rule: {rule.name}")
            
            # Clear existing model associations
            RoutingRuleModel.objects.filter(rule=rule).delete()
            
            # Associate models with the rule
            for model_config in rule_config['models']:
                provider_slug = model_config['provider']
                model_name = model_config['model']
                weight = model_config['weight']
                
                try:
                    # Get provider
                    provider = Provider.objects.get(slug=provider_slug)
                    
                    # Get model
                    model = Model.objects.get(provider=provider, name=model_name)
                    
                    # Create association
                    RoutingRuleModel.objects.create(
                        rule=rule,
                        model=model,
                        weight=weight
                    )
                    
                    self.stdout.write(f"  ✅ Associated {provider_slug}/{model_name} with weight {weight}")
                    models_associated += 1
                    
                except (Provider.DoesNotExist, Model.DoesNotExist) as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Error: {e}"))
            
            rules_created += 1
        
        self.stdout.write(self.style.SUCCESS(f"✅ Setup complete: {rules_created} rules with {models_associated} model associations"))
