from django.core.management.base import BaseCommand
from modelhub.models import RoutingRule, RoutingRuleModel, Model, Provider


class Command(BaseCommand):
    help = 'Fix entity-specific routing rules by associating models with rules'

    def handle(self, *args, **options):
        """Fix entity-specific routing rules"""
        self.stdout.write(self.style.SUCCESS("🔧 Fixing entity-specific routing rules..."))
        
        # Entity-specific rules configuration
        entity_rules_config = [
            {
                'name': 'Agent Session - Quality Focused',
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 50},
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 15}
                ]
            },
            {
                'name': 'Workflow Execution - Function Calling',
                'models': [
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 45},
                    {'provider': 'google', 'model': 'gemini-1.5-pro', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 20}
                ]
            },
            {
                'name': 'Platform Chat - Cost Optimized',
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 40},
                    {'provider': 'google', 'model': 'gemini-1.5-flash', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 25}
                ]
            },
            {
                'name': 'Workspace Chat - Balanced Performance',
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 40},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 35},
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 25}
                ]
            }
        ]
        
        rules_fixed = 0
        models_associated = 0
        
        for rule_config in entity_rules_config:
            try:
                # Find the rule by name
                rule = RoutingRule.objects.get(name=rule_config['name'])
                self.stdout.write(f"Found rule: {rule.name}")
                
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
                
                rules_fixed += 1
                
            except RoutingRule.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Rule not found: {rule_config['name']}"))
        
        self.stdout.write(self.style.SUCCESS(f"✅ Fixed {rules_fixed} rules with {models_associated} model associations"))
