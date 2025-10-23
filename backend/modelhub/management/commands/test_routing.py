from django.core.management.base import BaseCommand
from modelhub.services.routing.router import EnhancedModelRouter
from modelhub.services.routing.types import RequestContext, OptimizationStrategy
from modelhub.models import RoutingRule, RoutingRuleModel


class Command(BaseCommand):
    help = 'Test entity-agnostic routing with different entity types'

    def handle(self, *args, **options):
        """Test entity-agnostic routing with different entity types"""
        self.stdout.write(self.style.SUCCESS("🧪 Testing entity-agnostic routing..."))
        
        # Check if we have any routing rules
        rule_count = RoutingRule.objects.count()
        self.stdout.write(f"Found {rule_count} routing rules in the database")
        
        # Check if rules have models associated
        rules_with_models = 0
        for rule in RoutingRule.objects.all():
            model_count = RoutingRuleModel.objects.filter(rule=rule).count()
            if model_count > 0:
                rules_with_models += 1
                self.stdout.write(f"Rule '{rule.name}' has {model_count} models")
            else:
                self.stdout.write(self.style.WARNING(f"Rule '{rule.name}' has NO models"))
        
        self.stdout.write(f"{rules_with_models} out of {rule_count} rules have models associated")
        
        # Create router
        router = EnhancedModelRouter()
        
        # Test different entity types
        entity_types = [
            "platform_chat",
            "workspace_chat",
            "agent_session",
            "workflow_execution"
        ]
        
        for entity_type in entity_types:
            # Create request context
            context = RequestContext(
                entity_type=entity_type,
                session_id="test-session",
                max_tokens=1000,
                temperature=0.7,
                metadata={}
            )
            
            # Route request
            self.stdout.write(self.style.SUCCESS(f"\n{'='*50}"))
            self.stdout.write(self.style.SUCCESS(f"Testing entity_type={entity_type}"))
            
            # Test with different complexity scores
            for complexity in [0.2, 0.5, 0.8]:
                self.stdout.write(f"\nComplexity score: {complexity}")
                
                # Test with different optimization strategies
                for strategy in [OptimizationStrategy.COST, OptimizationStrategy.BALANCED, OptimizationStrategy.QUALITY]:
                    decision = router.route_request_sync(
                        organization=None,
                        complexity_score=complexity,
                        content_type="general",
                        context=context,
                        strategy=strategy
                    )
                    
                    # Print decision
                    self.stdout.write(f"  Strategy: {strategy.value}")
                    self.stdout.write(f"    Selected: {decision.selected_provider}/{decision.selected_model}")
                    self.stdout.write(f"    Confidence: {decision.confidence_score}")
                    self.stdout.write(f"    Reasoning: {decision.reasoning}")
        
        self.stdout.write(self.style.SUCCESS("\n✅ Testing complete!"))
