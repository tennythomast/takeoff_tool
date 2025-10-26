import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
django.setup()

from modelhub.models import Provider, APIKey, Model
from asgiref.sync import sync_to_async

async def test_qwen():
    # Get Qwen provider and API key
    qwen = await sync_to_async(Provider.objects.get)(slug='qwen')
    api_key = await sync_to_async(lambda: APIKey.objects.filter(provider=qwen, is_active=True).first())()
    model = await sync_to_async(lambda: Model.objects.filter(provider=qwen, status='ACTIVE').first())()
    
    print(f"Provider: {qwen.name}")
    print(f"Base URL: {qwen.config.get('base_url')}")
    print(f"Model: {model.name}")
    print(f"API Key: {api_key.key[:10]}...")
    
    # Test with OpenAI client
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(
        api_key=api_key.key,
        base_url=qwen.config.get('base_url')
    )
    
    try:
        response = await client.chat.completions.create(
            model=model.name,
            messages=[{'role': 'user', 'content': 'Hello, test message'}],
            max_tokens=50
        )
        print(f"\n✅ Success!")
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == '__main__':
    asyncio.run(test_qwen())
