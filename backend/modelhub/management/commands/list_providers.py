from django.core.management.base import BaseCommand
from modelhub.services.unified_llm_client import UnifiedLLMClient
from modelhub.models import Provider, Model, APIKey
from django.db.models import Count


class Command(BaseCommand):
    help = 'List all providers and their status'

    def handle(self, *args, **options):
        self.stdout.write("=== Provider Status Report ===\n")
        
        # Get supported providers from client
        supported_providers = UnifiedLLMClient.get_supported_providers()
        self.stdout.write(f"Dynamically supported providers: {', '.join(supported_providers)}")
        
        # Get providers from database
        providers = Provider.objects.annotate(
            model_count=Count('model', filter=models.Q(model__status='ACTIVE')),
            api_key_count=Count('apikey', filter=models.Q(apikey__is_active=True))
        ).order_by('name')
        
        self.stdout.write(f"\nDatabase providers: {providers.count()}\n")
        
        for provider in providers:
            status_icon = "✅" if provider.status == 'ACTIVE' else "❌"
            dynamic_support = "🔧" if provider.slug in supported_providers else "⚠️"
            
            self.stdout.write(f"{status_icon} {dynamic_support} {provider.name} ({provider.slug})")
            self.stdout.write(f"   Status: {provider.status}")
            self.stdout.write(f"   Models: {provider.model_count} active")
            self.stdout.write(f"   API Keys: {provider.api_key_count} active")
            
            if provider.slug in supported_providers:
                self.stdout.write(f"   ✅ Dynamic support available")
            else:
                self.stdout.write(f"   ⚠️ No dynamic support (implement provider class)")
            
            self.stdout.write("")
        
        self.stdout.write("Legend:")
        self.stdout.write("✅/❌ = Database status")
        self.stdout.write("🔧 = Dynamic support available")
        self.stdout.write("⚠️ = No dynamic support")
