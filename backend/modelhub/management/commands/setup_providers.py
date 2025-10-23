from django.core.management.base import BaseCommand
from django.db import transaction
from modelhub.models import Provider, Model, APIKey
from decimal import Decimal


class Command(BaseCommand):
    help = 'Setup default providers and models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            help='Setup specific provider (openai, anthropic, or all)',
            default='all'
        )

    def handle(self, *args, **options):
        provider = options['provider']
        
        if provider == 'all' or provider == 'openai':
            self.setup_openai()
        
        if provider == 'all' or provider == 'anthropic':
            self.setup_anthropic()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully setup providers and models')
        )

    @transaction.atomic
    def setup_openai(self):
        """Setup OpenAI provider and models"""
        self.stdout.write("Setting up OpenAI provider...")
        
        # Create or update provider
        provider, created = Provider.objects.get_or_create(
            slug='openai',
            defaults={
                'name': 'OpenAI',
                'description': 'OpenAI language models including GPT-4 and GPT-3.5',
                'website': 'https://openai.com',
                'documentation_url': 'https://platform.openai.com/docs',
                'status': 'ACTIVE',
                'config': {
                    'base_url': 'https://api.openai.com/v1',
                    'api_version': 'v1'
                }
            }
        )
        
        if created:
            self.stdout.write(f"Created OpenAI provider")
        else:
            self.stdout.write(f"OpenAI provider already exists")
        
        # Create models
        models_to_create = [
            {
                'name': 'gpt-4',
                'version': '',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'function_calling'],
                'cost_input': Decimal('0.030000'),
                'cost_output': Decimal('0.060000'),
                'context_window': 8192,
                'config': {'max_tokens': 4096}
            },
            {
                'name': 'gpt-4-turbo',
                'version': '',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'function_calling'],
                'cost_input': Decimal('0.010000'),
                'cost_output': Decimal('0.030000'),
                'context_window': 128000,
                'config': {'max_tokens': 4096}
            },
            {
                'name': 'gpt-3.5-turbo',
                'version': '',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'function_calling'],
                'cost_input': Decimal('0.001500'),
                'cost_output': Decimal('0.002000'),
                'context_window': 16385,
                'config': {'max_tokens': 4096}
            },
            {
                'name': 'text-davinci-003',
                'version': '',
                'model_type': 'TEXT',
                'capabilities': ['completion'],
                'cost_input': Decimal('0.020000'),
                'cost_output': Decimal('0.020000'),
                'context_window': 4097,
                'config': {'max_tokens': 4097}
            }
        ]
        
        for model_data in models_to_create:
            model, created = Model.objects.get_or_create(
                provider=provider,
                name=model_data['name'],
                defaults=model_data
            )
            if created:
                self.stdout.write(f"  Created model: {model_data['name']}")

    @transaction.atomic
    def setup_anthropic(self):
        """Setup Anthropic provider and models"""
        self.stdout.write("Setting up Anthropic provider...")
        
        # Create or update provider
        provider, created = Provider.objects.get_or_create(
            slug='anthropic',
            defaults={
                'name': 'Anthropic',
                'description': 'Anthropic Claude models for safe and helpful AI',
                'website': 'https://anthropic.com',
                'documentation_url': 'https://docs.anthropic.com',
                'status': 'ACTIVE',
                'config': {
                    'base_url': 'https://api.anthropic.com',
                    'api_version': '2023-06-01'
                }
            }
        )
        
        if created:
            self.stdout.write(f"Created Anthropic provider")
        else:
            self.stdout.write(f"Anthropic provider already exists")
        
        # Create models
        models_to_create = [
            {
                'name': 'claude-3-opus-20240229',
                'version': '20240229',
                'model_type': 'TEXT',
                'capabilities': ['chat'],
                'cost_input': Decimal('0.015000'),
                'cost_output': Decimal('0.075000'),
                'context_window': 200000,
                'config': {'max_tokens': 4096}
            },
            {
                'name': 'claude-3-sonnet-20240229',
                'version': '20240229',
                'model_type': 'TEXT',
                'capabilities': ['chat'],
                'cost_input': Decimal('0.003000'),
                'cost_output': Decimal('0.015000'),
                'context_window': 200000,
                'config': {'max_tokens': 4096}
            },
            {
                'name': 'claude-3-haiku-20240307',
                'version': '20240307',
                'model_type': 'TEXT',
                'capabilities': ['chat'],
                'cost_input': Decimal('0.000250'),
                'cost_output': Decimal('0.001250'),
                'context_window': 200000,
                'config': {'max_tokens': 4096}
            }
        ]
        
        for model_data in models_to_create:
            model, created = Model.objects.get_or_create(
                provider=provider,
                name=model_data['name'],
                defaults=model_data
            )
            if created:
                self.stdout.write(f"  Created model: {model_data['name']}")
