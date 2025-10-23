from django.core.management.base import BaseCommand
from modelhub.models import Provider, APIKey
import aiohttp
import asyncio

class Command(BaseCommand):
    help = 'Test different Qwen model names to find the correct one'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing different Qwen model names...")
        
        try:
            # Get Qwen provider and API key
            qwen = Provider.objects.get(slug='qwen')
            api_key = APIKey.objects.filter(provider=qwen, is_active=True).first()
            
            if not api_key:
                self.stdout.write(self.style.ERROR("❌ No active API key found for Qwen"))
                return
                
            # Test different model names based on RunPod environment
            model_names_to_test = [
                'Qwen3-4B',  # Current override
                'Qwen/Qwen3-4B-Thinking-2507-F',  # Full model name
                'qwen3-4b',  # Lowercase
                'Qwen3-4B-Thinking-2507-F',  # Without prefix
                'qwen',  # Simple name
                'default',  # Default model
            ]
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                for model_name in model_names_to_test:
                    self.stdout.write(f"\n🧪 Testing model: {model_name}")
                    result = loop.run_until_complete(self.test_model(api_key.key, model_name))
                    
                    if 'choices' in result:
                        self.stdout.write(self.style.SUCCESS(f"✅ SUCCESS with model: {model_name}"))
                        self.stdout.write(f"   Response: {result['choices'][0]['message']['content']}")
                        break
                    elif 'error' in result:
                        if 'does not exist' in result['error']:
                            self.stdout.write(self.style.WARNING(f"⚠️ Model not found: {model_name}"))
                        else:
                            self.stdout.write(self.style.ERROR(f"❌ Error with {model_name}: {result['error']}"))
                    else:
                        self.stdout.write(f"❓ Unexpected response: {result}")
                        
            finally:
                loop.close()
                
        except Provider.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Qwen provider not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
    
    async def test_model(self, api_key, model_name):
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model_name,
            'messages': [
                {'role': 'user', 'content': 'Hello! Please respond with just "Test successful!"'}
            ],
            'max_tokens': 10,
            'temperature': 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.runpod.ai/v2/wbm6kfsbasn1k7/openai/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        return {'error': f'API error ({response.status}): {error}'}
                    return await response.json()
        except Exception as e:
            return {'error': f'Request failed: {str(e)}'}
