from django.core.management.base import BaseCommand
from modelhub.models import Provider, APIKey
from modelhub.services.unified_llm_client import UnifiedLLMClient
import asyncio

class Command(BaseCommand):
    help = 'Check Qwen provider status and test connection'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking Qwen provider status...")
        
        # Check if Qwen provider exists
        try:
            qwen_provider = Provider.objects.get(slug='qwen')
            self.stdout.write(self.style.SUCCESS(f"✅ Found Qwen provider: {qwen_provider.name}"))
            
            # Check API key
            api_key = APIKey.objects.filter(
                provider=qwen_provider,
                is_active=True
            ).first()
            
            if not api_key:
                self.stdout.write(self.style.WARNING("⚠️ No active API key found for Qwen"))
                return
                
            self.stdout.write("🔑 Found active API key")
            
            # Get a model for testing
            from modelhub.models import Model
            model = Model.objects.filter(
                provider=qwen_provider,
                status='ACTIVE'
            ).first()
            
            if not model:
                self.stdout.write(self.style.WARNING("⚠️ No active models found for Qwen"))
                return
                
            self.stdout.write(f"🤖 Found model: {model.name}")
            
            # Test the connection
            self.stdout.write("🔄 Testing Qwen connection...")
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # First validate the provider setup
                validation_result = loop.run_until_complete(
                    UnifiedLLMClient.validate_provider_setup('qwen')
                )
                
                if not validation_result['valid']:
                    self.stdout.write(self.style.ERROR(f"❌ Qwen provider validation failed: {validation_result.get('error', 'Unknown error')}"))
                    return
                    
                self.stdout.write(self.style.SUCCESS("✅ Qwen provider validation passed"))
                
                # Test OpenAI-compatible API call
                import aiohttp
                import json
                
                async def test_openai_api():
                    headers = {
                        'Authorization': f'Bearer {api_key.key}',
                        'Content-Type': 'application/json'
                    }
                    
                    # Try the model name from RunPod environment
                    model_name = model.name  # This should be 'Qwen3-4B' from database
                    
                    payload = {
                        'model': model_name,
                        'messages': [
                            {'role': 'user', 'content': 'Hello, this is a test message. Please respond with "Test successful!"'}
                        ],
                        'max_tokens': 50,
                        'temperature': 0.7
                    }
                    
                    self.stdout.write(f"🤖 Testing with model: {model_name}")
                    
                    async with aiohttp.ClientSession() as session:
                        # Make the request to the OpenAI-compatible endpoint
                        async with session.post(
                            'https://api.runpod.ai/v2/eqtdb4vp2s366z/openai/v1/chat/completions',
                            headers=headers,
                            json=payload
                        ) as response:
                            if response.status != 200:
                                error = await response.text()
                                return {'error': f'API error ({response.status}): {error}'}
                            
                            result = await response.json()
                            return result
                
                # Run the test
                response = loop.run_until_complete(test_openai_api())
                
                if 'choices' in response and len(response['choices']) > 0:
                    self.stdout.write(self.style.SUCCESS("✅ Qwen API request successful!"))
                    self.stdout.write(f"   Model: {response.get('model')}")
                    self.stdout.write(f"   Response: {response['choices'][0]['message']['content']}")
                    
                    # Show usage if available
                    if 'usage' in response:
                        usage = response['usage']
                        self.stdout.write("   Usage:")
                        self.stdout.write(f"     Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
                        self.stdout.write(f"     Completion tokens: {usage.get('completion_tokens', 'N/A')}")
                        self.stdout.write(f"     Total tokens: {usage.get('total_tokens', 'N/A')}")
                    
                elif 'error' in response:
                    self.stdout.write(self.style.ERROR(f"❌ Qwen API error: {response.get('error')}"))
                else:
                    self.stdout.write(self.style.ERROR("❌ Unexpected response format from RunPod API"))
                    self.stdout.write(f"   Response: {response}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error testing Qwen API: {str(e)}"))
                
            finally:
                loop.close()
                
        except Provider.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Qwen provider not found. Please run setup_providers first."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error checking Qwen status: {str(e)}"))
