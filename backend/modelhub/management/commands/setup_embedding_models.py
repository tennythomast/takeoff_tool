# management/commands/setup_embedding_models.py
from django.core.management.base import BaseCommand
from modelhub.models import Provider, Model

class Command(BaseCommand):
    help = 'Setup embedding models in ModelHub'
    
    def handle(self, *args, **options):
        
        # Create Voyage AI provider
        voyage_provider, created = Provider.objects.get_or_create(
            slug='voyage',
            defaults={
                'name': 'Voyage AI',
                'supports_embeddings': True,
                'embedding_endpoint': 'https://api.voyageai.com/v1/embeddings',
                'description': 'Leading embedding model provider',
                'website': 'https://voyageai.com',
                'status': 'ACTIVE'
            }
        )
        
        # Create Mistral provider
        mistral_provider, created = Provider.objects.get_or_create(
            slug='mistral',
            defaults={
                'name': 'Mistral AI',
                'supports_embeddings': True,
                'embedding_endpoint': 'https://api.mistral.ai/v1/embeddings',
                'description': 'Cost-effective embedding provider',
                'website': 'https://mistral.ai',
                'status': 'ACTIVE'
            }
        )
        
        # Create embedding models
        embedding_models = [
            {
                'provider': voyage_provider,
                'name': 'voyage-3.5-lite',
                'model_type': 'EMBEDDING',
                'capabilities': ['embedding', 'semantic_search', 'rag'],
                'embedding_dimensions': 2048,
                'cost_input': 0.00002,  # $0.00002 per 1k tokens
                'cost_output': 0.00000,  # No output cost for embeddings
                'context_window': 32000,
                'config': {
                    'supports_matryoshka': True,
                    'quantization_options': ['float32', 'int8', 'binary'],
                    'dimension_options': [256, 512, 1024, 2048]
                }
            },
            {
                'provider': voyage_provider,
                'name': 'voyage-3.5',
                'model_type': 'EMBEDDING',
                'capabilities': ['embedding', 'semantic_search', 'rag', 'premium'],
                'embedding_dimensions': 2048,
                'cost_input': 0.00012,
                'cost_output': 0.00000,
                'context_window': 32000,
                'config': {
                    'supports_matryoshka': True,
                    'quantization_options': ['float32', 'int8', 'binary'],
                    'dimension_options': [256, 512, 1024, 2048]
                }
            },
            {
                'provider': mistral_provider,
                'name': 'mistral-embed',
                'model_type': 'EMBEDDING',
                'capabilities': ['embedding', 'semantic_search', 'cost_optimized'],
                'embedding_dimensions': 1024,
                'cost_input': 0.0001,
                'cost_output': 0.00000,
                'context_window': 8192,
                'config': {
                    'supports_matryoshka': False,
                    'quantization_options': ['float32']
                }
            }
        ]
        
        for model_config in embedding_models:
            model, created = Model.objects.get_or_create(
                provider=model_config['provider'],
                name=model_config['name'],
                defaults=model_config
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created model: {model.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Model already exists: {model.name}')
                )