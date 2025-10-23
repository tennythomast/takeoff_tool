"""
USAGE EXAMPLES:

1. Setup default providers:
   python manage.py setup_providers

2. Setup only OpenAI:
   python manage.py setup_providers --provider openai

3. Test all provider setups:
   python manage.py test_providers

4. Test with actual API calls:
   python manage.py test_providers --test-api

5. Add a new provider:
   python manage.py add_provider google "Google AI" --website https://ai.google.dev

6. List all providers:
   python manage.py list_providers

7. Add a custom provider with implementation:
   python manage.py add_provider cohere "Cohere" --class-path myapp.providers.CohereProvider
"""