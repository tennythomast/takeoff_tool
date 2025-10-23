# backend/modelhub/management/commands/setup_intelligent_routing.py
# Enhanced version with entity-aware routing and improved complexity analysis

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '''
    Setup enhanced intelligent routing system with:
    - Provider and model metadata
    - Entity-aware routing rules (platform_chat, agent_session, workflow_execution, workspace_chat)
    - Complexity-based model selection
    - Cost optimization strategies
    
    This command ONLY creates database records for:
    - Provider information (OpenAI, Anthropic, etc.)
    - Model specifications (names, costs, capabilities)
    - Enhanced routing rules for optimization
    
    This does NOT:
    - Create API accounts
    - Set up API keys (those are managed separately)
    - Incur any costs
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing data before setup',
        )
        parser.add_argument(
            '--clean-duplicates',
            action='store_true',
            help='Clean duplicate models before setup',
        )
        parser.add_argument(
            '--entity-rules',
            action='store_true',
            help='Setup entity-specific routing rules',
        )

    def handle(self, *args, **options):
        """Setup the enhanced intelligent routing system"""
        self.stdout.write(self.style.SUCCESS('🚀 Setting up Enhanced Intelligent Routing System...'))
        self.stdout.write(self.style.WARNING('Note: This only creates database records, not API accounts'))
        
        if options['reset']:
            self.reset_data()
        
        if options['clean_duplicates']:
            self.clean_duplicate_models()
        
        with transaction.atomic():
            # Setup provider metadata
            providers_created = self.setup_providers()
            
            # Setup enhanced model specifications
            models_created = self.setup_enhanced_models()
            
            # Setup enhanced routing rules
            rules_created = self.setup_enhanced_routing_rules()
            
            # Setup entity-specific rules if requested
            entity_rules_created = 0
            if options['entity_rules']:
                entity_rules_created = self.setup_entity_specific_rules()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Enhanced Routing System Setup Complete!\n'
                    f'   - Providers: {providers_created}\n'
                    f'   - Models: {models_created}\n'
                    f'   - Base Routing Rules: {rules_created}\n'
                    f'   - Entity-Specific Rules: {entity_rules_created}\n\n'
                    f'🎯 Enhanced Features:\n'
                    f'   - Entity-aware routing (agents, workflows, chat)\n'
                    f'   - Complexity-based model selection\n'
                    f'   - Cost optimization strategies\n'
                    f'   - Session stickiness support\n\n'
                    f'🔑 Next Steps:\n'
                    f'   1. Configure API keys for organizations\n'
                    f'   2. Set organization default_optimization_strategy\n'
                    f'   3. Test enhanced routing with different entity types\n'
                    f'   4. Monitor complexity analysis performance'
                )
            )

    def clean_duplicate_models(self):
        """Clean duplicate models that may have been created"""
        from modelhub.models import Model
        
        self.stdout.write('🧹 Cleaning duplicate models...')
        
        duplicates_found = 0
        models = Model.objects.all().order_by('provider', 'name', 'created_at')
        
        seen_combinations = set()
        models_to_delete = []
        
        for model in models:
            combination = (model.provider.slug, model.name)
            
            if combination in seen_combinations:
                models_to_delete.append(model)
                duplicates_found += 1
                self.stdout.write(f'   🗑️ Found duplicate: {model.provider.name} - {model.name}')
            else:
                seen_combinations.add(combination)
        
        if models_to_delete:
            for model in models_to_delete:
                model.delete()
            self.stdout.write(f'   ✅ Cleaned {duplicates_found} duplicate models')
        else:
            self.stdout.write('   ✅ No duplicate models found')

    def reset_data(self):
        """Reset existing routing data"""
        from modelhub.models import Provider, Model, RoutingRule, ModelMetrics
        
        self.stdout.write('🔄 Resetting existing data...')
        
        ModelMetrics.objects.all().delete()
        RoutingRule.objects.all().delete()
        Model.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('   - Cleared existing routing data'))

    def setup_providers(self):
        """Setup enhanced provider metadata"""
        from modelhub.models import Provider
        
        providers_config = [
            {
                'name': 'OpenAI',
                'slug': 'openai',
                'description': 'OpenAI GPT models - excellent for reasoning and code',
                'website': 'https://openai.com',
                'documentation_url': 'https://platform.openai.com/docs',
                'status': 'ACTIVE',
                'config': {
                    'base_url': 'https://api.openai.com/v1',
                    'supports_streaming': True,
                    'supports_function_calling': True,
                    'requires_org_key': True,
                    'entity_compatibility': ['platform_chat', 'agent_session', 'workflow_execution', 'workspace_chat'],
                    'rate_limits': {
                        'requests_per_minute': 500,
                        'tokens_per_minute': 150000
                    }
                }
            },
            {
                'name': 'Anthropic',
                'slug': 'anthropic',
                'description': 'Anthropic Claude models - excellent reasoning and safety',
                'website': 'https://anthropic.com',
                'documentation_url': 'https://docs.anthropic.com',
                'status': 'ACTIVE',
                'config': {
                    'base_url': 'https://api.anthropic.com',
                    'supports_streaming': True,
                    'requires_org_key': True,
                    'entity_compatibility': ['platform_chat', 'agent_session', 'workspace_chat'],
                    'rate_limits': {
                        'requests_per_minute': 300,
                        'tokens_per_minute': 100000
                    }
                }
            },
            {
                'name': 'Google',
                'slug': 'google',
                'description': 'Google Gemini models - multimodal and fast',
                'website': 'https://cloud.google.com',
                'documentation_url': 'https://cloud.google.com/vertex-ai/docs',
                'status': 'ACTIVE',
                'config': {
                    'base_url': 'https://generativelanguage.googleapis.com/v1',
                    'supports_streaming': True,
                    'supports_function_calling': True,
                    'supports_multimodal': True,
                    'entity_compatibility': ['platform_chat', 'workflow_execution']
                }
            },
            {
                'name': 'Mixtral',
                'slug': 'mixtral',
                'description': 'Cost-effective Mixtral models - best for budget optimization',
                'website': 'https://huggingface.co',
                'documentation_url': 'https://huggingface.co/docs',
                'status': 'ACTIVE',
                'config': {
                    'base_url': 'https://api-inference.huggingface.co',
                    'supports_streaming': False,
                    'cost_tier': 'budget',
                    'entity_compatibility': ['platform_chat', 'workspace_chat']
                }
            }
        ]
        
        providers_created = 0
        for config in providers_config:
            provider, created = Provider.objects.get_or_create(
                slug=config['slug'],
                defaults=config
            )
            if created:
                providers_created += 1
                self.stdout.write(f'   ✅ Created provider: {provider.name}')
            else:
                # Update config with new features
                provider.config = config['config']
                provider.save()
                self.stdout.write(f'   ⚡ Updated provider: {provider.name}')
        
        return providers_created

    def setup_enhanced_models(self):
        """Setup AI models with enhanced capabilities and entity compatibility"""
        from modelhub.models import Provider, Model
        
        models_config = [
            # OpenAI Models - Enhanced with entity compatibility
            {
                'provider_slug': 'openai',
                'name': 'gpt-4',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'completion', 'function_calling', 'advanced_reasoning', 'long_context'],
                'cost_input': Decimal('0.030'),
                'cost_output': Decimal('0.060'),
                'context_window': 8192,
                'config': {
                    'quality_tier': 'premium',
                    'reasoning_capability': 'excellent',
                    'optimization_profile': 'quality_first',
                    'entity_suitability': {
                        'agent_session': 0.9,      # Excellent for agents
                        'workflow_execution': 0.8,  # Good for complex workflows
                        'platform_chat': 0.7,      # Good but expensive for chat
                        'workspace_chat': 0.7
                    },
                    'complexity_range': [0.6, 1.0]  # Handles medium to complex
                }
            },
            {
                'provider_slug': 'openai',
                'name': 'gpt-4-turbo',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'completion', 'function_calling', 'advanced_reasoning', 'long_context'],
                'cost_input': Decimal('0.010'),
                'cost_output': Decimal('0.030'),
                'context_window': 128000,
                'config': {
                    'quality_tier': 'high',
                    'reasoning_capability': 'excellent',
                    'optimization_profile': 'balanced',
                    'entity_suitability': {
                        'agent_session': 0.95,     # Excellent for agents
                        'workflow_execution': 0.9,  # Excellent for workflows
                        'platform_chat': 0.8,      # Good for chat
                        'workspace_chat': 0.8
                    },
                    'complexity_range': [0.4, 1.0]
                }
            },
            {
                'provider_slug': 'openai',
                'name': 'gpt-3.5-turbo',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'completion', 'function_calling'],
                'cost_input': Decimal('0.0015'),
                'cost_output': Decimal('0.002'),
                'context_window': 16384,
                'config': {
                    'quality_tier': 'standard',
                    'reasoning_capability': 'good',
                    'optimization_profile': 'cost_effective',
                    'entity_suitability': {
                        'platform_chat': 0.9,      # Excellent for general chat
                        'workspace_chat': 0.9,     # Excellent for workspace
                        'agent_session': 0.7,      # Decent for simple agents
                        'workflow_execution': 0.6  # Basic workflows only
                    },
                    'complexity_range': [0.0, 0.7]
                }
            },
            
            # Anthropic Models - Enhanced
            {
                'provider_slug': 'anthropic',
                'name': 'claude-3-5-sonnet-20241022',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'advanced_reasoning', 'code_generation', 'long_context'],
                'cost_input': Decimal('0.003'),
                'cost_output': Decimal('0.015'),
                'context_window': 200000,
                'config': {
                    'quality_tier': 'premium',
                    'reasoning_capability': 'excellent',
                    'optimization_profile': 'quality_first',
                    'safety_tier': 'high',
                    'entity_suitability': {
                        'agent_session': 0.95,     # Excellent for agents
                        'platform_chat': 0.9,      # Excellent for chat
                        'workspace_chat': 0.9,     # Excellent for workspace
                        'workflow_execution': 0.8  # Good for workflows
                    },
                    'complexity_range': [0.3, 1.0]
                }
            },
            {
                'provider_slug': 'anthropic',
                'name': 'claude-3-haiku-20240307',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'fast_response'],
                'cost_input': Decimal('0.00025'),
                'cost_output': Decimal('0.00125'),
                'context_window': 200000,
                'config': {
                    'quality_tier': 'good',
                    'reasoning_capability': 'fast',
                    'optimization_profile': 'performance_first',
                    'speed_tier': 'fast',
                    'entity_suitability': {
                        'platform_chat': 0.95,     # Excellent for chat
                        'workspace_chat': 0.9,     # Excellent for workspace
                        'workflow_execution': 0.8, # Good for fast workflows
                        'agent_session': 0.7       # Decent for simple agents
                    },
                    'complexity_range': [0.0, 0.6]
                }
            },
            
            # Google Models - Enhanced
            {
                'provider_slug': 'google',
                'name': 'gemini-1.5-pro',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'multimodal', 'function_calling', 'advanced_reasoning', 'long_context'],
                'cost_input': Decimal('0.0035'),
                'cost_output': Decimal('0.0105'),
                'context_window': 1048576,
                'config': {
                    'quality_tier': 'high',
                    'reasoning_capability': 'excellent',
                    'optimization_profile': 'balanced',
                    'multimodal_support': True,
                    'entity_suitability': {
                        'workflow_execution': 0.9,  # Excellent for complex workflows
                        'agent_session': 0.8,       # Good for agents
                        'platform_chat': 0.7,       # Good for chat
                        'workspace_chat': 0.7
                    },
                    'complexity_range': [0.4, 1.0]
                }
            },
            {
                'provider_slug': 'google',
                'name': 'gemini-1.5-flash',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'fast_response', 'multimodal'],
                'cost_input': Decimal('0.000075'),
                'cost_output': Decimal('0.0003'),
                'context_window': 1048576,
                'config': {
                    'quality_tier': 'good',
                    'reasoning_capability': 'fast',
                    'optimization_profile': 'cost_effective',
                    'speed_tier': 'very_fast',
                    'entity_suitability': {
                        'platform_chat': 0.9,      # Excellent for chat
                        'workflow_execution': 0.8, # Good for simple workflows
                        'workspace_chat': 0.8,
                        'agent_session': 0.6       # Basic agent support
                    },
                    'complexity_range': [0.0, 0.5]
                }
            },
            
            # Mixtral Models - Enhanced
            {
                'provider_slug': 'mixtral',
                'name': 'mixtral-8x7b-instruct',
                'version': 'latest',
                'model_type': 'TEXT',
                'capabilities': ['chat', 'completion'],
                'cost_input': Decimal('0.0002'),
                'cost_output': Decimal('0.0002'),
                'context_window': 32768,
                'config': {
                    'quality_tier': 'good',
                    'reasoning_capability': 'decent',
                    'optimization_profile': 'ultra_cost_effective',
                    'cost_tier': 'budget',
                    'entity_suitability': {
                        'platform_chat': 0.85,     # Very good for basic chat
                        'workspace_chat': 0.8,     # Good for workspace
                        'agent_session': 0.5,      # Basic agent support
                        'workflow_execution': 0.4  # Limited workflow support
                    },
                    'complexity_range': [0.0, 0.4]
                }
            }
        ]
        
        models_created = 0
        for config in models_config:
            try:
                provider = Provider.objects.get(slug=config['provider_slug'])
                
                model, created = Model.objects.get_or_create(
                    provider=provider,
                    name=config['name'],
                    defaults={
                        'version': config['version'],
                        'model_type': config['model_type'],
                        'capabilities': config['capabilities'],
                        'cost_input': config['cost_input'],
                        'cost_output': config['cost_output'],
                        'context_window': config['context_window'],
                        'config': config['config'],
                        'status': 'ACTIVE'
                    }
                )
                
                if created:
                    models_created += 1
                    self.stdout.write(f'   ✅ Created enhanced model: {model.provider.name} - {model.name}')
                else:
                    # Update with enhanced config
                    for field, value in config.items():
                        if field not in ['provider_slug', 'name']:
                            setattr(model, field, value)
                    model.save()
                    self.stdout.write(f'   ⚡ Updated model: {model.provider.name} - {model.name}')
                    
            except Provider.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'   ❌ Provider not found: {config["provider_slug"]}'))
        
        return models_created

    def setup_enhanced_routing_rules(self):
        """Setup enhanced routing rules with complexity and entity awareness"""
        from modelhub.models import RoutingRule, RoutingRuleModel, Model
        
        rules_config = [
            {
                'name': 'Ultra Cost-Effective Simple Queries',
                'description': 'Route very simple queries to ultra-cheap models',
                'priority': 1,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'complexity_score', 'operator': 'lt', 'value': 0.2},
                    {'field': 'optimization_strategy', 'operator': 'eq', 'value': 'cost_first'}
                ],
                'models': [
                    {'provider': 'mixtral', 'model': 'mixtral-8x7b-instruct', 'weight': 70},
                    {'provider': 'google', 'model': 'gemini-1.5-flash', 'weight': 30}
                ]
            },
            {
                'name': 'Cost-Effective Simple Queries',
                'description': 'Route simple queries to cost-effective models',
                'priority': 2,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'complexity_score', 'operator': 'between', 'value': [0.2, 0.4]},
                    {'field': 'optimization_strategy', 'operator': 'in', 'value': ['cost_first', 'balanced']}
                ],
                'models': [
                    {'provider': 'google', 'model': 'gemini-1.5-flash', 'weight': 40},
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 35},
                    {'provider': 'mixtral', 'model': 'mixtral-8x7b-instruct', 'weight': 25}
                ]
            },
            {
                'name': 'Balanced Medium Complexity',
                'description': 'Balance cost and quality for medium complexity tasks',
                'priority': 3,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'complexity_score', 'operator': 'between', 'value': [0.4, 0.7]},
                    {'field': 'optimization_strategy', 'operator': 'eq', 'value': 'balanced'}
                ],
                'models': [
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 35},
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 30},
                    {'provider': 'google', 'model': 'gemini-1.5-pro', 'weight': 20},
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 15}
                ]
            },
            {
                'name': 'Quality-First Complex Tasks',
                'description': 'Use premium models for complex reasoning tasks',
                'priority': 4,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'complexity_score', 'operator': 'gte', 'value': 0.7},
                    {'field': 'optimization_strategy', 'operator': 'in', 'value': ['quality_first', 'balanced']}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 40},
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 35},
                    {'provider': 'google', 'model': 'gemini-1.5-pro', 'weight': 20},
                    {'provider': 'openai', 'model': 'gpt-4', 'weight': 5}
                ]
            },
            {
                'name': 'Performance-First Fast Response',
                'description': 'Prioritize speed for performance-critical applications',
                'priority': 5,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'optimization_strategy', 'operator': 'eq', 'value': 'performance_first'}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 50},
                    {'provider': 'google', 'model': 'gemini-1.5-flash', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 15}
                ]
            },
            {
                'name': 'Code Generation Specialist',
                'description': 'Specialized routing for code-related requests',
                'priority': 6,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'content_type', 'operator': 'eq', 'value': 'code'}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 60},
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 30},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 10}
                ]
            }
        ]
        
        rules_created = 0
        for rule_config in rules_config:
            rule, created = RoutingRule.objects.get_or_create(
                name=rule_config['name'],
                defaults={
                    'description': rule_config['description'],
                    'priority': rule_config['priority'],
                    'model_type': rule_config['model_type'],
                    'conditions': rule_config['conditions']
                }
            )
            
            if created:
                rules_created += 1
                self.stdout.write(f'   ✅ Created enhanced rule: {rule.name}')
                
                # Add models to the rule
                for model_config in rule_config['models']:
                    try:
                        model = Model.objects.filter(
                            provider__slug=model_config['provider'],
                            name=model_config['model']
                        ).first()
                        
                        if model:
                            RoutingRuleModel.objects.get_or_create(
                                rule=rule,
                                model=model,
                                defaults={
                                    'weight': model_config['weight']
                                }
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'     ⚠️ Model not found: {model_config["provider"]}:{model_config["model"]}'
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'     ❌ Error adding model: {str(e)}'
                            )
                        )
            else:
                self.stdout.write(f'   ⚡ Enhanced rule exists: {rule.name}')
        
        return rules_created

    def setup_entity_specific_rules(self):
        """Setup entity-specific routing rules"""
        from modelhub.models import RoutingRule, RoutingRuleModel, Model
        
        entity_rules_config = [
            {
                'name': 'Agent Session - Quality Focused',
                'description': 'High-quality models for agent interactions',
                'priority': 10,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'entity_type', 'operator': 'eq', 'value': 'agent_session'},
                    {'field': 'complexity_score', 'operator': 'gte', 'value': 0.3}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 50},
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 15}
                ]
            },
            {
                'name': 'Workflow Execution - Function Calling',
                'description': 'Models with function calling for workflows',
                'priority': 11,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'entity_type', 'operator': 'eq', 'value': 'workflow_execution'}
                ],
                'models': [
                    {'provider': 'openai', 'model': 'gpt-4-turbo', 'weight': 45},
                    {'provider': 'google', 'model': 'gemini-1.5-pro', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 20}
                ]
            },
            {
                'name': 'Platform Chat - Cost Optimized',
                'description': 'Cost-effective models for general platform chat',
                'priority': 12,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'entity_type', 'operator': 'eq', 'value': 'platform_chat'},
                    {'field': 'complexity_score', 'operator': 'lt', 'value': 0.6}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 40},
                    {'provider': 'google', 'model': 'gemini-1.5-flash', 'weight': 35},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 25}
                ]
            },
            {
                'name': 'Workspace Chat - Balanced Performance',
                'description': 'Balanced models for workspace conversations',
                'priority': 13,
                'model_type': 'TEXT',
                'conditions': [
                    {'field': 'entity_type', 'operator': 'eq', 'value': 'workspace_chat'}
                ],
                'models': [
                    {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022', 'weight': 40},
                    {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'weight': 35},
                    {'provider': 'anthropic', 'model': 'claude-3-haiku-20240307', 'weight': 25}
                ]
            }
        ]
        
        entity_rules_created = 0
        for rule_config in entity_rules_config:
            rule, created = RoutingRule.objects.get_or_create(
                name=rule_config['name'],
                defaults={
                    'description': rule_config['description'],
                    'priority': rule_config['priority'],
                    'model_type': rule_config['model_type'],
                    'conditions': rule_config['conditions']
                }
            )