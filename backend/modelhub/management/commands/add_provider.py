from django.core.management.base import BaseCommand
from modelhub.services.unified_llm_client import UnifiedLLMClient, BaseLLMProvider
from modelhub.models import Provider, Model, APIKey
from decimal import Decimal
import importlib


class Command(BaseCommand):
    help = 'Add a new custom provider to the system'

    def add_arguments(self, parser):
        parser.add_argument('provider_slug', type=str, help='Provider slug (e.g., "google", "cohere")')
        parser.add_argument('provider_name', type=str, help='Provider display name')
        parser.add_argument('--class-path', type=str, help='Python path to provider class')
        parser.add_argument('--website', type=str, help='Provider website URL')
        parser.add_argument('--docs', type=str, help='Provider documentation URL')

    def handle(self, *args, **options):
        provider_slug = options['provider_slug']
        provider_name = options['provider_name']
        class_path = options.get('class_path')
        website = options.get('website', '')
        docs = options.get('docs', '')
        
        self.stdout.write(f"Adding provider: {provider_name} ({provider_slug})")
        
        # Create provider in database
        try:
            provider, created = Provider.objects.get_or_create(
                slug=provider_slug,
                defaults={
                    'name': provider_name,
                    'description': f'{provider_name} language models',
                    'website': website,
                    'documentation_url': docs,
                    'status': 'ACTIVE',
                    'config': {}
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created provider: {provider_name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Provider {provider_name} already exists")
                )
            
            # If class path provided, try to register the provider class
            if class_path:
                self.register_provider_class(provider_slug, class_path)
            
            self.stdout.write(
                self.style.SUCCESS(f"Provider {provider_name} setup complete!")
            )
            self.stdout.write("Next steps:")
            self.stdout.write("1. Add API key using Django admin or API")
            self.stdout.write("2. Add models for this provider")
            self.stdout.write("3. Implement provider class if not done already")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error adding provider: {str(e)}")
            )

    def register_provider_class(self, provider_slug, class_path):
        """Register a provider class dynamically"""
        try:
            # Import the class
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            provider_class = getattr(module, class_name)
            
            # Validate it's a proper provider class
            if not issubclass(provider_class, BaseLLMProvider):
                raise ValueError("Provider class must inherit from BaseLLMProvider")
            
            # Register with UnifiedLLMClient
            UnifiedLLMClient.register_provider(provider_slug, provider_class)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ Registered provider class: {class_path}")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error registering provider class: {str(e)}")
            )
