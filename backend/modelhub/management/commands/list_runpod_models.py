from django.core.management.base import BaseCommand
from modelhub.models import Provider, APIKey
import aiohttp
import asyncio
import json

class Command(BaseCommand):
    help = 'List available models from RunPod OpenAI-compatible endpoint'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Fetching available models from RunPod...")
        
        try:
            # Get Qwen provider and API key
            qwen = Provider.objects.get(slug='qwen')
            api_key = APIKey.objects.filter(provider=qwen, is_active=True).first()
            
            if not api_key:
                self.stdout.write(self.style.ERROR("❌ No active API key found for Qwen"))
                return
                
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                models = loop.run_until_complete(self.fetch_models(api_key.key))
                self.display_models(models)
            finally:
                loop.close()
                
        except Provider.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Qwen provider not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
    
    async def fetch_models(self, api_key):
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.runpod.ai/v2/eqtdb4vp2s366z/openai/v1/models',
                headers=headers
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    return {'error': f'API error ({response.status}): {error}'}
                return await response.json()
    
    def display_models(self, models_data):
        if 'error' in models_data:
            self.stdout.write(self.style.ERROR(f"❌ {models_data['error']}"))
            return
            
        if 'data' not in models_data:
            self.stdout.write(self.style.ERROR("❌ Unexpected response format"))
            self.stdout.write(f"Response: {json.dumps(models_data, indent=2)}")
            return
            
        self.stdout.write(self.style.SUCCESS("\nAvailable Models:"))
        self.stdout.write("-" * 50)
        
        for model in models_data['data']:
            self.stdout.write(f"ID: {model.get('id')}")
            self.stdout.write(f"Object: {model.get('object')}")
            self.stdout.write(f"Created: {model.get('created')}")
            self.stdout.write(f"Owned By: {model.get('owned_by')}")
            self.stdout.write("-" * 50)
