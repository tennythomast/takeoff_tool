from django.core.management.base import BaseCommand
from django.db import transaction
import os

class Command(BaseCommand):
    help = '''
    Setup API key management for organizations and Dataelan.
    
    This sets up the API key strategy to protect Dataelan from unexpected costs
    while providing organizations control over their AI spending.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--setup-dataelan-keys',
            action='store_true',
            help='Setup Dataelan system keys (for free tier only)',
        )
        parser.add_argument(
            '--org-slug',
            type=str,
            help='Setup keys for specific organization',
        )

    def handle(self, *args, **options):
        """Setup API key management"""
        
        if options['setup_dataelan_keys']:
            self.setup_dataelan_emergency_keys()
        
        if options['org_slug']:
            self.setup_organization_keys(options['org_slug'])
        
        self.display_api_key_strategy()

    def setup_dataelan_emergency_keys(self):
        """Setup Dataelan keys for emergency fallback only"""
        from modelhub.models import Provider, APIKey
        
        self.stdout.write(self.style.WARNING('🚨 Setting up Dataelan Emergency Keys'))
        self.stdout.write(self.style.WARNING('These should ONLY be used for free tier users or emergencies!'))
        
        # Only setup keys if environment variables exist
        dataelan_keys = {
            'openai': os.environ.get('DATAELAN_OPENAI_KEY'),
            'anthropic': os.environ.get('DATAELAN_ANTHROPIC_KEY'),
        }
        
        keys_created = 0
        for provider_slug, key in dataelan_keys.items():
            if key and key != 'your-key-here':
                try:
                    provider = Provider.objects.get(slug=provider_slug)
                    api_key, created = APIKey.objects.get_or_create(
                        organization=None,  # System key
                        provider=provider,
                        label=f"Dataelan Emergency {provider.name}",
                        defaults={
                            'key': key,
                            'is_active': True,
                            'daily_quota': 5.00,  # $5 daily limit
                            'monthly_quota': 50.00,  # $50 monthly limit
                        }
                    )
                    if created:
                        keys_created += 1
                        self.stdout.write(f'   ✅ Created emergency key for {provider.name} (${api_key.monthly_quota}/month limit)')
                except Provider.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'   ❌ Provider {provider_slug} not found'))
        
        if keys_created == 0:
            self.stdout.write(self.style.WARNING('   ⚠️ No Dataelan keys created. Set environment variables if needed.'))

    def setup_organization_keys(self, org_slug):
        """Help setup organization API keys"""
        from core.models import Organization
        
        try:
            org = Organization.objects.get(slug=org_slug)
            self.stdout.write(f'🏢 Setting up API keys for: {org.name}')
            self.stdout.write(f'Current strategy: {org.get_api_key_strategy_display()}')
            
            # Show instructions for adding their keys
            self.stdout.write(self.style.SUCCESS('\n📋 To add organization API keys:'))
            self.stdout.write('1. Go to Django Admin > Model Hub > API Keys')
            self.stdout.write('2. Click "Add API Key"')
            self.stdout.write(f'3. Select Organization: {org.name}')
            self.stdout.write('4. Select Provider (OpenAI, Anthropic, etc.)')
            self.stdout.write('5. Enter their API key')
            self.stdout.write('6. Set monthly quota limits')
            
            # Check current keys
            from modelhub.models import APIKey
            current_keys = APIKey.objects.filter(organization=org)
            
            if current_keys.exists():
                self.stdout.write(f'\n🔑 Current keys for {org.name}:')
                for key in current_keys:
                    status = "✅ Active" if key.is_active else "❌ Inactive"
                    quota = f"${key.monthly_quota}/month" if key.monthly_quota else "No limit"
                    self.stdout.write(f'   - {key.provider.name}: {status} ({quota})')
            else:
                self.stdout.write(f'\n⚠️ No API keys configured for {org.name}')
                
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Organization with slug "{org_slug}" not found'))

    def display_api_key_strategy(self):
        """Display the API key strategy explanation"""
        self.stdout.write(self.style.SUCCESS('\n🎯 API Key Strategy Overview:'))
    