import asyncio
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from modelhub.services.routing.router import EnhancedModelRouter
from modelhub.services.routing.types import RequestContext, OptimizationStrategy
from modelhub.models import RoutingRule


class Command(BaseCommand):
    help = 'Test entity-agnostic routing with different entity types'

    async def test_routing(self):
        """Test entity-agnostic routing with different entity types"""
        # We'll test without an organization (system-wide rules)
        organization = None
        
        # Check if we have any routing rules
        rule_count = await sync_to_async(RoutingRule.objects.count)()
        self.stdout.write(f"Found {rule_count} routing rules in the database")
        
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
            
            decision = await router.route_request(
                organization=organization,
                complexity_score=0.5,
                content_type="general",
                context=context,
                strategy=OptimizationStrategy.BALANCED
            )
            
            # Print decision
            self.stdout.write(f"Decision for {entity_type}:")
            self.stdout.write(f"  Selected model: {decision.selected_provider}/{decision.selected_model}")
            self.stdout.write(f"  Confidence: {decision.confidence_score}")
            self.stdout.write(f"  Reasoning: {decision.reasoning}")

    def handle(self, *args, **options):
        """Command entry point"""
        self.stdout.write(self.style.SUCCESS("Testing entity-agnostic routing..."))
        asyncio.run(self.test_routing())
        self.stdout.write(self.style.SUCCESS("Testing complete!"))
