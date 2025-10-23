import uuid
import json
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from modelhub.models import (
    Provider, Model, APIKey, RoutingRule, 
    RoutingRuleModel, ModelMetrics
)
from core.models import Organization, User


class ProviderModelTest(TestCase):
    """Test cases for the Provider model."""

    def setUp(self):
        """Set up test data."""
        self.provider_data = {
            'name': 'Test Provider',
            'slug': 'test-provider',
            'description': 'A test provider for unit tests',
            'website': 'https://example.com',
            'documentation_url': 'https://docs.example.com',
            'status': 'ACTIVE',
            'config': {'base_url': 'https://api.example.com/v1'}
        }
        self.provider = Provider.objects.create(**self.provider_data)

    def test_provider_creation(self):
        """Test that a provider can be created with proper attributes."""
        self.assertEqual(self.provider.name, self.provider_data['name'])
        self.assertEqual(self.provider.slug, self.provider_data['slug'])
        self.assertEqual(self.provider.description, self.provider_data['description'])
        self.assertEqual(self.provider.website, self.provider_data['website'])
        self.assertEqual(self.provider.documentation_url, self.provider_data['documentation_url'])
        self.assertEqual(self.provider.status, self.provider_data['status'])
        self.assertEqual(self.provider.config, self.provider_data['config'])
        self.assertIsNotNone(self.provider.created_at)
        self.assertIsNotNone(self.provider.updated_at)

    def test_provider_string_representation(self):
        """Test the string representation of a provider."""
        self.assertEqual(str(self.provider), 'Test Provider')

    def test_provider_config_validation(self):
        """Test that config must be a dictionary."""
        # Invalid config (not a dict)
        self.provider.config = "not a dict"
        with self.assertRaises(ValidationError):
            self.provider.full_clean()

        # Valid config
        self.provider.config = {'key': 'value'}
        self.provider.full_clean()  # Should not raise an exception


class ModelModelTest(TestCase):
    """Test cases for the Model model."""

    def setUp(self):
        """Set up test data."""
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        self.model_data = {
            'provider': self.provider,
            'name': 'Test Model',
            'version': '1.0',
            'model_type': 'TEXT',
            'capabilities': ['completion', 'chat'],
            'config': {'temperature': 0.7},
            'cost_input': Decimal('0.001'),
            'cost_output': Decimal('0.002'),
            'context_window': 4096,
            'status': 'ACTIVE'
        }
        self.model = Model.objects.create(**self.model_data)

    def test_model_creation(self):
        """Test that a model can be created with proper attributes."""
        self.assertEqual(self.model.provider, self.provider)
        self.assertEqual(self.model.name, self.model_data['name'])
        self.assertEqual(self.model.version, self.model_data['version'])
        self.assertEqual(self.model.model_type, self.model_data['model_type'])
        self.assertEqual(self.model.capabilities, self.model_data['capabilities'])
        self.assertEqual(self.model.config, self.model_data['config'])
        self.assertEqual(self.model.cost_input, self.model_data['cost_input'])
        self.assertEqual(self.model.cost_output, self.model_data['cost_output'])
        self.assertEqual(self.model.context_window, self.model_data['context_window'])
        self.assertEqual(self.model.status, self.model_data['status'])
        self.assertIsNotNone(self.model.created_at)
        self.assertIsNotNone(self.model.updated_at)

    def test_model_string_representation(self):
        """Test the string representation of a model."""
        expected = f'Test Provider - Test Model 1.0'
        self.assertEqual(str(self.model), expected)

    def test_model_cost_validation(self):
        """Test that cost cannot be negative."""
        # Invalid cost (negative)
        self.model.cost_input = Decimal('-0.001')
        with self.assertRaises(ValidationError):
            self.model.full_clean()

        # Valid cost
        self.model.cost_input = Decimal('0.001')
        self.model.full_clean()  # Should not raise an exception

    def test_model_capabilities_validation(self):
        """Test that capabilities must be a list."""
        # Invalid capabilities (not a list)
        self.model.capabilities = "not a list"
        with self.assertRaises(ValidationError):
            self.model.full_clean()

        # Valid capabilities
        self.model.capabilities = ['completion', 'chat']
        self.model.full_clean()  # Should not raise an exception

    def test_cost_display_property(self):
        """Test the cost_display property."""
        cost_display = self.model.cost_display
        self.assertEqual(cost_display['input_per_1k'], f"${self.model.cost_input:.4f}")
        self.assertEqual(cost_display['output_per_1k'], f"${self.model.cost_output:.4f}")
        self.assertEqual(cost_display['input_per_token'], f"${(self.model.cost_input/1000):.6f}")
        self.assertEqual(cost_display['output_per_token'], f"${(self.model.cost_output/1000):.6f}")

    def test_estimate_cost_method(self):
        """Test the estimate_cost method."""
        input_tokens = 1000
        output_tokens = 500
        expected_cost = (self.model.cost_input * input_tokens / 1000) + (self.model.cost_output * output_tokens / 1000)
        actual_cost = self.model.estimate_cost(input_tokens, output_tokens)
        self.assertEqual(actual_cost, expected_cost)


class APIKeyModelTest(TestCase):
    """Test cases for the APIKey model."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Organization',
            slug='test-org'
        )
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        self.api_key_data = {
            'organization': self.organization,
            'provider': self.provider,
            'label': 'Test API Key',
            'key': 'sk-test-api-key-12345',
            'is_default': True,
            'is_active': True,
            'daily_quota': Decimal('10.00'),
            'monthly_quota': Decimal('200.00')
        }
        self.api_key = APIKey.objects.create(**self.api_key_data)

    def test_api_key_creation(self):
        """Test that an API key can be created with proper attributes."""
        self.assertEqual(self.api_key.organization, self.organization)
        self.assertEqual(self.api_key.provider, self.provider)
        self.assertEqual(self.api_key.label, self.api_key_data['label'])
        self.assertEqual(self.api_key.key, self.api_key_data['key'])
        self.assertEqual(self.api_key.is_default, self.api_key_data['is_default'])
        self.assertEqual(self.api_key.is_active, self.api_key_data['is_active'])
        self.assertEqual(self.api_key.daily_quota, self.api_key_data['daily_quota'])
        self.assertEqual(self.api_key.monthly_quota, self.api_key_data['monthly_quota'])
        self.assertIsNone(self.api_key.last_used_at)
        self.assertIsNotNone(self.api_key.created_at)
        self.assertIsNotNone(self.api_key.updated_at)

    def test_api_key_string_representation(self):
        """Test the string representation of an API key."""
        expected = f'Test Organization - Test Provider - Test API Key'
        self.assertEqual(str(self.api_key), expected)

    def test_api_key_quota_validation(self):
        """Test that quotas cannot be negative."""
        # Invalid daily quota (negative)
        self.api_key.daily_quota = Decimal('-10.00')
        with self.assertRaises(ValidationError):
            self.api_key.full_clean()

        # Valid daily quota
        self.api_key.daily_quota = Decimal('10.00')
        self.api_key.full_clean()  # Should not raise an exception

        # Invalid monthly quota (negative)
        self.api_key.monthly_quota = Decimal('-200.00')
        with self.assertRaises(ValidationError):
            self.api_key.full_clean()

        # Valid monthly quota
        self.api_key.monthly_quota = Decimal('200.00')
        self.api_key.full_clean()  # Should not raise an exception

    def test_get_dataelan_keys_method(self):
        """Test the get_dataelan_keys class method."""
        # Create a system-wide API key (organization=None)
        system_api_key = APIKey.objects.create(
            organization=None,
            provider=self.provider,
            label='System API Key',
            key='sk-system-api-key-12345',
            is_default=True,
            is_active=True
        )

        # Test without provider filter
        dataelan_keys = APIKey.get_dataelan_keys()
        self.assertEqual(dataelan_keys.count(), 1)
        self.assertEqual(dataelan_keys.first(), system_api_key)

        # Test with provider filter
        dataelan_keys = APIKey.get_dataelan_keys(provider=self.provider)
        self.assertEqual(dataelan_keys.count(), 1)
        self.assertEqual(dataelan_keys.first(), system_api_key)

        # Test with a different provider
        other_provider = Provider.objects.create(
            name='Other Provider',
            slug='other-provider',
            status='ACTIVE'
        )
        dataelan_keys = APIKey.get_dataelan_keys(provider=other_provider)
        self.assertEqual(dataelan_keys.count(), 0)

    def test_get_usage_this_month_method(self):
        """Test the get_usage_this_month method."""
        # Create a model
        model = Model.objects.create(
            provider=self.provider,
            name='Test Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )

        # Create model metrics for this month
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Create metrics for this month
        ModelMetrics.objects.create(
            model=model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=timezone.now(),
            latency_ms=100,
            tokens_input=1000,
            tokens_output=500,
            cost=Decimal('0.002'),
            status='SUCCESS'
        )
        
        ModelMetrics.objects.create(
            model=model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=timezone.now(),
            latency_ms=150,
            tokens_input=2000,
            tokens_output=1000,
            cost=Decimal('0.004'),
            status='SUCCESS'
        )

        # Create metrics for last month
        last_month = start_of_month - timedelta(days=1)
        ModelMetrics.objects.create(
            model=model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=last_month,
            latency_ms=200,
            tokens_input=3000,
            tokens_output=1500,
            cost=Decimal('0.006'),
            status='SUCCESS'
        )

        # Test the method
        usage = self.api_key.get_usage_this_month()
        self.assertEqual(usage['total_cost'], Decimal('0.006'))  # 0.002 + 0.004
        self.assertEqual(usage['total_requests'], 2)  # Only this month's requests


class RoutingRuleModelTest(TestCase):
    """Test cases for the RoutingRule model."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Organization',
            slug='test-org'
        )
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        self.model = Model.objects.create(
            provider=self.provider,
            name='Test Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )
        self.routing_rule_data = {
            'organization': self.organization,
            'name': 'Test Routing Rule',
            'description': 'A test routing rule for unit tests',
            'priority': 1,
            'model_type': 'TEXT',
            'conditions': {
                'input_tokens': {'min': 0, 'max': 1000},
                'output_tokens': {'min': 0, 'max': 500},
                'tags': ['test', 'unit-test']
            }
        }
        self.routing_rule = RoutingRule.objects.create(**self.routing_rule_data)
        self.routing_rule_model_data = {
            'rule': self.routing_rule,
            'model': self.model,
            'weight': 10,
            'notes': 'Test notes',
            'tags': ['test', 'preferred']
        }
        self.routing_rule_model = RoutingRuleModel.objects.create(**self.routing_rule_model_data)

    def test_routing_rule_creation(self):
        """Test that a routing rule can be created with proper attributes."""
        self.assertEqual(self.routing_rule.organization, self.organization)
        self.assertEqual(self.routing_rule.name, self.routing_rule_data['name'])
        self.assertEqual(self.routing_rule.description, self.routing_rule_data['description'])
        self.assertEqual(self.routing_rule.priority, self.routing_rule_data['priority'])
        self.assertEqual(self.routing_rule.model_type, self.routing_rule_data['model_type'])
        self.assertEqual(self.routing_rule.conditions, self.routing_rule_data['conditions'])
        self.assertIsNotNone(self.routing_rule.created_at)
        self.assertIsNotNone(self.routing_rule.updated_at)

    def test_routing_rule_string_representation(self):
        """Test the string representation of a routing rule."""
        expected = f'Test Routing Rule (Priority: 1)'
        self.assertEqual(str(self.routing_rule), expected)

    def test_routing_rule_model_creation(self):
        """Test that a routing rule model can be created with proper attributes."""
        self.assertEqual(self.routing_rule_model.rule, self.routing_rule)
        self.assertEqual(self.routing_rule_model.model, self.model)
        self.assertEqual(self.routing_rule_model.weight, self.routing_rule_model_data['weight'])
        self.assertEqual(self.routing_rule_model.notes, self.routing_rule_model_data['notes'])
        self.assertEqual(self.routing_rule_model.tags, self.routing_rule_model_data['tags'])

    def test_routing_rule_model_string_representation(self):
        """Test the string representation of a routing rule model."""
        expected = f'Rule: Test Routing Rule - Model: Test Model'
        self.assertEqual(str(self.routing_rule_model), expected)

    def test_routing_rule_priority_validation(self):
        """Test that priority must be between 1 and 100."""
        # Invalid priority (too low)
        self.routing_rule.priority = 0
        with self.assertRaises(ValidationError):
            self.routing_rule.full_clean()

        # Invalid priority (too high)
        self.routing_rule.priority = 101
        with self.assertRaises(ValidationError):
            self.routing_rule.full_clean()

        # Valid priority
        self.routing_rule.priority = 50
        self.routing_rule.full_clean()  # Should not raise an exception

    def test_routing_rule_model_weight_validation(self):
        """Test that weight must be between 1 and 100."""
        # Invalid weight (too low)
        self.routing_rule_model.weight = 0
        with self.assertRaises(ValidationError):
            self.routing_rule_model.full_clean()

        # Invalid weight (too high)
        self.routing_rule_model.weight = 101
        with self.assertRaises(ValidationError):
            self.routing_rule_model.full_clean()

        # Valid weight
        self.routing_rule_model.weight = 50
        self.routing_rule_model.full_clean()  # Should not raise an exception


class ModelMetricsModelTest(TestCase):
    """Test cases for the ModelMetrics model."""

    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name='Test Organization',
            slug='test-org'
        )
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        self.model = Model.objects.create(
            provider=self.provider,
            name='Test Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )
        self.api_key = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider,
            label='Test API Key',
            key='sk-test-api-key-12345',
            is_default=True,
            is_active=True
        )
        self.model_metrics_data = {
            'model': self.model,
            'organization': self.organization,
            'api_key': self.api_key,
            'latency_ms': 100,
            'tokens_input': 1000,
            'tokens_output': 500,
            'cost': Decimal('0.002'),
            'status': 'SUCCESS',
            'error_type': '',
            'error_message': '',
            'optimization_metadata': {'strategy': 'cost_optimized'}
        }
        self.model_metrics = ModelMetrics.objects.create(**self.model_metrics_data)

    def test_model_metrics_creation(self):
        """Test that model metrics can be created with proper attributes."""
        self.assertEqual(self.model_metrics.model, self.model)
        self.assertEqual(self.model_metrics.organization, self.organization)
        self.assertEqual(self.model_metrics.api_key, self.api_key)
        self.assertEqual(self.model_metrics.latency_ms, self.model_metrics_data['latency_ms'])
        self.assertEqual(self.model_metrics.tokens_input, self.model_metrics_data['tokens_input'])
        self.assertEqual(self.model_metrics.tokens_output, self.model_metrics_data['tokens_output'])
        self.assertEqual(self.model_metrics.cost, self.model_metrics_data['cost'])
        self.assertEqual(self.model_metrics.status, self.model_metrics_data['status'])
        self.assertEqual(self.model_metrics.error_type, self.model_metrics_data['error_type'])
        self.assertEqual(self.model_metrics.error_message, self.model_metrics_data['error_message'])
        self.assertEqual(self.model_metrics.optimization_metadata, self.model_metrics_data['optimization_metadata'])
        self.assertIsNotNone(self.model_metrics.timestamp)

    def test_model_metrics_string_representation(self):
        """Test the string representation of model metrics."""
        expected = f'Test Model - SUCCESS - {self.model_metrics.timestamp.strftime("%Y-%m-%d %H:%M:%S")}'
        self.assertEqual(str(self.model_metrics), expected)

    def test_get_cost_summary_method(self):
        """Test the get_cost_summary class method."""
        # Create additional metrics
        ModelMetrics.objects.create(
            model=self.model,
            organization=self.organization,
            api_key=self.api_key,
            latency_ms=150,
            tokens_input=2000,
            tokens_output=1000,
            cost=Decimal('0.004'),
            status='SUCCESS'
        )

        # Create metrics for a different organization
        other_org = Organization.objects.create(
            name='Other Organization',
            slug='other-org'
        )
        ModelMetrics.objects.create(
            model=self.model,
            organization=other_org,
            api_key=self.api_key,
            latency_ms=200,
            tokens_input=3000,
            tokens_output=1500,
            cost=Decimal('0.006'),
            status='SUCCESS'
        )

        # Test with organization filter
        summary = ModelMetrics.get_cost_summary(organization=self.organization)
        self.assertEqual(summary['total_cost'], Decimal('0.006'))  # 0.002 + 0.004
        self.assertEqual(summary['total_requests'], 2)
        self.assertEqual(summary['successful_requests'], 2)
        self.assertEqual(summary['failed_requests'], 0)
        self.assertEqual(summary['total_tokens_input'], 3000)  # 1000 + 2000
        self.assertEqual(summary['total_tokens_output'], 1500)  # 500 + 1000
        self.assertEqual(len(summary['daily_costs']), 1)  # All metrics are from today
        self.assertEqual(len(summary['model_costs']), 1)  # Only one model used
        self.assertEqual(summary['model_costs'][0]['model_name'], 'Test Model')
        self.assertEqual(summary['model_costs'][0]['total_cost'], Decimal('0.006'))

        # Test without organization filter (all organizations)
        summary = ModelMetrics.get_cost_summary()
        self.assertEqual(summary['total_cost'], Decimal('0.012'))  # 0.002 + 0.004 + 0.006
        self.assertEqual(summary['total_requests'], 3)
        self.assertEqual(summary['successful_requests'], 3)
        self.assertEqual(summary['failed_requests'], 0)
        self.assertEqual(summary['total_tokens_input'], 6000)  # 1000 + 2000 + 3000
        self.assertEqual(summary['total_tokens_output'], 3000)  # 500 + 1000 + 1500
