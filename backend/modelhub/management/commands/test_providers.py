from django.core.management.base import BaseCommand
from modelhub.services.unified_llm_client import UnifiedLLMClient
from modelhub.models import Provider, APIKey
import asyncio


class Command(BaseCommand):
    help = 'Test provider setups and API connections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            help='Test specific provider (openai, anthropic, or all)',
            default='all'
        )
        parser.add_argument(
            '--test-api',
            action='store_true',
            help='Test actual API calls (requires valid API keys)',
        )

    def handle(self, *args, **options):
        provider = options['provider']
        test_api = options['test_api']
        
        self.stdout.write("Testing provider setups...")
        
        # Get supported providers
        supported_providers = UnifiedLLMClient.get_supported_providers()
        self.stdout.write(f"Supported providers: {supported_providers}")
        
        providers_to_test = []
        if provider == 'all':
            providers_to_test = supported_providers
        elif provider in supported_providers:
            providers_to_test = [provider]
        else:
            self.stdout.write(
                self.style.ERROR(f"Provider '{provider}' not supported")
            )
            return
        
        # Test each provider
        for provider_slug in providers_to_test:
            self.test_provider(provider_slug, test_api)

    def test_provider(self, provider_slug, test_api=False):
        """Test a specific provider"""
        self.stdout.write(f"\n--- Testing {provider_slug} ---")
        
        # Run async validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            validation_result = loop.run_until_complete(
                UnifiedLLMClient.validate_provider_setup(provider_slug)
            )
            
            if validation_result['valid']:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {provider_slug} setup is valid")
                )
                
                if test_api:
                    self.test_api_call(provider_slug, loop)
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ {provider_slug} setup failed: {validation_result['error']}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error testing {provider_slug}: {str(e)}")
            )
        finally:
            loop.close()

    def test_api_call(self, provider_slug, loop):
        """Test actual API call"""
        try:
            # Get API key from database
            provider = Provider.objects.get(slug=provider_slug)
            api_key = APIKey.objects.filter(
                provider=provider, 
                is_active=True
            ).first()
            
            if not api_key:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ No API key found for {provider_slug}")
                )
                return
            
            # Get a model
            from modelhub.models import Model
            model = Model.objects.filter(
                provider=provider,
                status='ACTIVE'
            ).first()
            
            if not model:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ No models found for {provider_slug}")
                )
                return
            
            self.stdout.write(f"🔄 Testing API call with {model.name}...")
            
            # Make test API call
            response = loop.run_until_complete(
                UnifiedLLMClient.call_llm(
                    provider_slug=provider_slug,
                    model_name=model.name,
                    api_key=api_key.key,
                    prompt="Hello, this is a test message. Please respond with 'Test successful!'",
                    max_tokens=50
                )
            )
            
            if response.content and not response.raw_response.get('error'):
                self.stdout.write(
                    self.style.SUCCESS(f"✅ API test successful!")
                )
                self.stdout.write(f"   Response: {response.content[:100]}...")
                self.stdout.write(f"   Tokens: {response.tokens_input} in, {response.tokens_output} out")
                self.stdout.write(f"   Cost: ${response.cost}")
                self.stdout.write(f"   Latency: {response.latency_ms}ms")
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ API test failed: {response.content}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ API test error: {str(e)}")
            )

