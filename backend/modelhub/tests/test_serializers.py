import json
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from modelhub.models import (
    Provider, Model, APIKey, RoutingRule, 
    RoutingRuleModel, ModelMetrics
)
from modelhub.serializers import (
    ProviderSerializer, ModelSerializer, APIKeySerializer,
    RoutingRuleSerializer, RoutingRuleModelSerializer,
    ModelMetricsSerializer, DashboardModelSerializer,
    DashboardMetricsSerializer, OptimizationInsightSerializer,
    BulkModelUpdateSerializer
)
from core.models import Organization, User


class ProviderSerializerTest(TestCase):
    """Test cases for the ProviderSerializer."""

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
        self.serializer = ProviderSerializer(instance=self.provider)

    def test_contains_expected_fields(self):
        """Test that the serializer contains the expected fields."""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'slug', 'description', 'website',
             'documentation_url', 'status', 'config', 'model_count']
        )

    def test_field_content(self):
        """Test that the serializer fields contain the correct data."""
        data = self.serializer.data
        self.assertEqual(data['name'], self.provider_data['name'])
        self.assertEqual(data['slug'], self.provider_data['slug'])
        self.assertEqual(data['description'], self.provider_data['description'])
        self.assertEqual(data['website'], self.provider_data['website'])
        self.assertEqual(data['documentation_url'], self.provider_data['documentation_url'])
        self.assertEqual(data['status'], self.provider_data['status'])
        self.assertEqual(data['config'], self.provider_data['config'])
        self.assertEqual(data['model_count'], 0)  # No models yet

    def test_model_count_field(self):
        """Test that the model_count field returns the correct count."""
        # Create models for the provider
        Model.objects.create(
            provider=self.provider,
            name='Active Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )
        Model.objects.create(
            provider=self.provider,
            name='Inactive Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='INACTIVE'
        )

        # Refresh serializer
        serializer = ProviderSerializer(instance=self.provider)
        self.assertEqual(serializer.data['model_count'], 1)  # Only active models


class ModelSerializerTest(TestCase):
    """Test cases for the ModelSerializer."""

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
        self.serializer = ModelSerializer(instance=self.model)

    def test_contains_expected_fields(self):
        """Test that the serializer contains the expected fields."""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'provider', 'provider_name', 'provider_slug', 'name', 'version',
             'model_type', 'capabilities', 'config', 'cost_input',
             'cost_output', 'context_window', 'status', 'cost_display',
             'cost_examples']
        )

    def test_field_content(self):
        """Test that the serializer fields contain the correct data."""
        data = self.serializer.data
        self.assertEqual(data['provider'], str(self.provider.id))
        self.assertEqual(data['provider_name'], self.provider.name)
        self.assertEqual(data['provider_slug'], self.provider.slug)
        self.assertEqual(data['name'], self.model_data['name'])
        self.assertEqual(data['version'], self.model_data['version'])
        self.assertEqual(data['model_type'], self.model_data['model_type'])
        self.assertEqual(data['capabilities'], self.model_data['capabilities'])
        self.assertEqual(data['config'], self.model_data['config'])
        self.assertEqual(Decimal(data['cost_input']), self.model_data['cost_input'])
        self.assertEqual(Decimal(data['cost_output']), self.model_data['cost_output'])
        self.assertEqual(data['context_window'], self.model_data['context_window'])
        self.assertEqual(data['status'], self.model_data['status'])

    def test_cost_display_field(self):
        """Test that the cost_display field returns the correct data."""
        data = self.serializer.data
        cost_display = data['cost_display']
        self.assertEqual(cost_display['input_per_1k'], f"${self.model.cost_input:.4f}")
        self.assertEqual(cost_display['output_per_1k'], f"${self.model.cost_output:.4f}")
        self.assertEqual(cost_display['input_per_token'], f"${(self.model.cost_input/1000):.6f}")
        self.assertEqual(cost_display['output_per_token'], f"${(self.model.cost_output/1000):.6f}")

    def test_cost_examples_field(self):
        """Test that the cost_examples field returns the correct data."""
        data = self.serializer.data
        cost_examples = data['cost_examples']
        self.assertEqual(len(cost_examples), 4)  # Four example usage patterns
        
        # Check the first example
        example = cost_examples[0]
        self.assertEqual(example['name'], 'Simple Query')
        self.assertEqual(example['input_tokens'], 100)
        self.assertEqual(example['output_tokens'], 50)
        expected_cost = float(self.model.estimate_cost(100, 50))
        self.assertEqual(example['estimated_cost'], expected_cost)


class APIKeySerializerTest(TestCase):
    """Test cases for the APIKeySerializer."""

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
        self.serializer = APIKeySerializer(instance=self.api_key)

    def test_contains_expected_fields(self):
        """Test that the serializer contains the expected fields."""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'organization', 'organization_name', 'provider',
             'provider_name', 'provider_slug', 'label', 'is_default', 
             'is_active', 'daily_quota', 'monthly_quota', 'last_used_at', 
             'quota_status', 'usage_this_month', 'health_status']
        )

    def test_field_content(self):
        """Test that the serializer fields contain the correct data."""
        data = self.serializer.data
        self.assertEqual(data['organization'], str(self.organization.id))
        self.assertEqual(data['organization_name'], self.organization.name)
        self.assertEqual(data['provider'], str(self.provider.id))
        self.assertEqual(data['provider_name'], self.provider.name)
        self.assertEqual(data['provider_slug'], self.provider.slug)
        self.assertEqual(data['label'], self.api_key_data['label'])
        self.assertEqual(data['is_default'], self.api_key_data['is_default'])
        self.assertEqual(data['is_active'], self.api_key_data['is_active'])
        self.assertEqual(Decimal(data['daily_quota']), self.api_key_data['daily_quota'])
        self.assertEqual(Decimal(data['monthly_quota']), self.api_key_data['monthly_quota'])
        self.assertIsNone(data['last_used_at'])

    def test_usage_this_month_field(self):
        """Test that the usage_this_month field returns the correct data."""
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

        # Refresh serializer
        serializer = APIKeySerializer(instance=self.api_key)
        usage = serializer.data['usage_this_month']
        self.assertEqual(usage['total_cost'], 0.006)  # 0.002 + 0.004
        self.assertEqual(usage['total_requests'], 2)

    def test_health_status_field(self):
        """Test that the health_status field returns the correct data."""
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

        # Create successful metrics
        for _ in range(9):
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
        
        # Create error metrics
        ModelMetrics.objects.create(
            model=model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=timezone.now(),
            latency_ms=150,
            tokens_input=0,
            tokens_output=0,
            cost=Decimal('0.000'),
            status='ERROR',
            error_type='RateLimitError',
            error_message='Rate limit exceeded'
        )

        # Refresh serializer
        serializer = APIKeySerializer(instance=self.api_key)
        health = serializer.data['health_status']
        self.assertEqual(health['status'], 'warning')  # 10% error rate
        self.assertEqual(health['error_rate'], 10.0)
        self.assertEqual(health['recent_errors'], 1)
        self.assertEqual(health['recent_requests'], 10)

    def test_validate_method(self):
        """Test the validate method."""
        # Valid data
        valid_data = {
            'organization': self.organization.id,
            'provider': self.provider.id,
            'label': 'New API Key',
            'key': 'sk-new-api-key-12345',
            'daily_quota': '10.00',
            'monthly_quota': '200.00'
        }
        serializer = APIKeySerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        # Invalid data (daily quota too high compared to monthly quota)
        invalid_data = valid_data.copy()
        invalid_data['daily_quota'] = '20.00'  # 20 * 30 = 600 > 200
        serializer = APIKeySerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Daily quota seems too high compared to monthly quota', str(serializer.errors))


class RoutingRuleSerializerTest(TestCase):
    """Test cases for the RoutingRuleSerializer."""

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
        self.routing_rule_model = RoutingRuleModel.objects.create(
            rule=self.routing_rule,
            model=self.model,
            weight=10,
            notes='Test notes',
            tags=['test', 'preferred']
        )
        self.serializer = RoutingRuleSerializer(instance=self.routing_rule)

    def test_contains_expected_fields(self):
        """Test that the serializer contains the expected fields."""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'organization', 'organization_name', 'name',
             'description', 'priority', 'model_type', 'conditions',
             'models', 'model_count', 'cheapest_model_cost']
        )

    def test_field_content(self):
        """Test that the serializer fields contain the correct data."""
        data = self.serializer.data
        self.assertEqual(data['organization'], str(self.organization.id))
        self.assertEqual(data['organization_name'], self.organization.name)
        self.assertEqual(data['name'], self.routing_rule_data['name'])
        self.assertEqual(data['description'], self.routing_rule_data['description'])
        self.assertEqual(data['priority'], self.routing_rule_data['priority'])
        self.assertEqual(data['model_type'], self.routing_rule_data['model_type'])
        self.assertEqual(data['conditions'], self.routing_rule_data['conditions'])

    def test_models_field(self):
        """Test that the models field returns the correct data."""
        data = self.serializer.data
        models = data['models']
        self.assertEqual(len(models), 1)
        model_data = models[0]
        self.assertEqual(model_data['model'], str(self.model.id))
        self.assertEqual(model_data['model_name'], self.model.name)
        self.assertEqual(model_data['provider_name'], self.provider.name)
        self.assertEqual(Decimal(model_data['model_cost_input']), self.model.cost_input)
        self.assertEqual(Decimal(model_data['model_cost_output']), self.model.cost_output)
        self.assertEqual(model_data['weight'], self.routing_rule_model.weight)
        self.assertEqual(model_data['notes'], self.routing_rule_model.notes)
        self.assertEqual(model_data['tags'], self.routing_rule_model.tags)

    def test_model_count_field(self):
        """Test that the model_count field returns the correct count."""
        data = self.serializer.data
        self.assertEqual(data['model_count'], 1)

        # Create an inactive model
        inactive_model = Model.objects.create(
            provider=self.provider,
            name='Inactive Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='INACTIVE'
        )
        RoutingRuleModel.objects.create(
            rule=self.routing_rule,
            model=inactive_model,
            weight=5
        )

        # Refresh serializer
        serializer = RoutingRuleSerializer(instance=self.routing_rule)
        self.assertEqual(serializer.data['model_count'], 1)  # Only active models

    def test_cheapest_model_cost_field(self):
        """Test that the cheapest_model_cost field returns the correct data."""
        data = self.serializer.data
        cheapest_cost = data['cheapest_model_cost']
        
        # Expected cost for 1000 input, 500 output tokens
        expected_cost = float(self.model.estimate_cost(1000, 500))
        self.assertEqual(cheapest_cost['model_name'], self.model.name)
        self.assertEqual(cheapest_cost['cost'], expected_cost)
        self.assertEqual(cheapest_cost['tokens_input'], 1000)
        self.assertEqual(cheapest_cost['tokens_output'], 500)


class ModelMetricsSerializerTest(TestCase):
    """Test cases for the ModelMetricsSerializer."""

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
        self.serializer = ModelMetricsSerializer(instance=self.model_metrics)

    def test_contains_expected_fields(self):
        """Test that the serializer contains the expected fields."""
        data = self.serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'model', 'model_name', 'provider_name', 'organization',
             'organization_name', 'timestamp', 'latency_ms', 'tokens_input',
             'tokens_output', 'cost', 'status', 'error_type', 'error_message',
             'optimization_metadata', 'cost_per_token', 'efficiency_score']
        )

    def test_field_content(self):
        """Test that the serializer fields contain the correct data."""
        data = self.serializer.data
        self.assertEqual(data['model'], str(self.model.id))
        self.assertEqual(data['model_name'], self.model.name)
        self.assertEqual(data['provider_name'], self.provider.name)
        self.assertEqual(data['organization'], str(self.organization.id))
        self.assertEqual(data['organization_name'], self.organization.name)
        self.assertEqual(data['latency_ms'], self.model_metrics_data['latency_ms'])
        self.assertEqual(data['tokens_input'], self.model_metrics_data['tokens_input'])
        self.assertEqual(data['tokens_output'], self.model_metrics_data['tokens_output'])
        self.assertEqual(Decimal(data['cost']), self.model_metrics_data['cost'])
        self.assertEqual(data['status'], self.model_metrics_data['status'])
        self.assertEqual(data['error_type'], self.model_metrics_data['error_type'])
        self.assertEqual(data['error_message'], self.model_metrics_data['error_message'])
        self.assertEqual(data['optimization_metadata'], self.model_metrics_data['optimization_metadata'])

    def test_cost_per_token_field(self):
        """Test that the cost_per_token field returns the correct data."""
        data = self.serializer.data
        total_tokens = self.model_metrics_data['tokens_input'] + self.model_metrics_data['tokens_output']
        expected_cost_per_token = float(self.model_metrics_data['cost'] / total_tokens)
        self.assertEqual(data['cost_per_token'], expected_cost_per_token)

    def test_efficiency_score_field(self):
        """Test that the efficiency_score field returns the correct data."""
        data = self.serializer.data
        # Efficiency score is based on cost and latency
        self.assertIsNotNone(data['efficiency_score'])
        self.assertTrue(0 <= data['efficiency_score'] <= 100)


class DashboardSerializersTest(TestCase):
    """Test cases for the dashboard serializers."""

    def setUp(self):
        """Set up test data."""
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
        self.organization = Organization.objects.create(
            name='Test Organization',
            slug='test-org'
        )
        self.model_metrics = ModelMetrics.objects.create(
            model=self.model,
            organization=self.organization,
            latency_ms=100,
            tokens_input=1000,
            tokens_output=500,
            cost=Decimal('0.002'),
            status='SUCCESS'
        )

    def test_dashboard_model_serializer(self):
        """Test the DashboardModelSerializer."""
        serializer = DashboardModelSerializer(instance=self.model)
        data = serializer.data
        self.assertCountEqual(
            data.keys(),
            ['id', 'name', 'provider_name', 'model_type', 'cost_input', 'cost_output']
        )
        self.assertEqual(data['name'], self.model.name)
        self.assertEqual(data['provider_name'], self.provider.name)
        self.assertEqual(data['model_type'], self.model.model_type)
        self.assertEqual(Decimal(data['cost_input']), self.model.cost_input)
        self.assertEqual(Decimal(data['cost_output']), self.model.cost_output)

    def test_dashboard_metrics_serializer(self):
        """Test the DashboardMetricsSerializer."""
        serializer = DashboardMetricsSerializer(instance=self.model_metrics)
        data = serializer.data
        self.assertCountEqual(
            data.keys(),
            ['timestamp', 'model_name', 'cost', 'latency_ms', 'status']
        )
        self.assertEqual(data['model_name'], self.model.name)
        self.assertEqual(Decimal(data['cost']), self.model_metrics.cost)
        self.assertEqual(data['latency_ms'], self.model_metrics.latency_ms)
        self.assertEqual(data['status'], self.model_metrics.status)


class OptimizationInsightSerializerTest(TestCase):
    """Test cases for the OptimizationInsightSerializer."""

    def test_serializer_validation(self):
        """Test that the serializer validates data correctly."""
        valid_data = {
            'insight_type': 'cost_saving',
            'title': 'Switch to a cheaper model',
            'description': 'You can save money by switching to Model X',
            'potential_savings': '10.50',
            'confidence': 0.85,
            'action_required': True,
            'details': {
                'current_model': 'Model A',
                'suggested_model': 'Model X',
                'current_cost': '20.00',
                'new_cost': '9.50'
            }
        }
        serializer = OptimizationInsightSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['insight_type'], valid_data['insight_type'])
        self.assertEqual(serializer.validated_data['title'], valid_data['title'])
        self.assertEqual(serializer.validated_data['description'], valid_data['description'])
        self.assertEqual(serializer.validated_data['potential_savings'], Decimal(valid_data['potential_savings']))
        self.assertEqual(serializer.validated_data['confidence'], valid_data['confidence'])
        self.assertEqual(serializer.validated_data['action_required'], valid_data['action_required'])
        self.assertEqual(serializer.validated_data['details'], valid_data['details'])


class BulkModelUpdateSerializerTest(TestCase):
    """Test cases for the BulkModelUpdateSerializer."""

    def setUp(self):
        """Set up test data."""
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        self.model1 = Model.objects.create(
            provider=self.provider,
            name='Model 1',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )
        self.model2 = Model.objects.create(
            provider=self.provider,
            name='Model 2',
            model_type='TEXT',
            cost_input=Decimal('0.002'),
            cost_output=Decimal('0.003'),
            context_window=4096,
            status='ACTIVE'
        )

    def test_serializer_validation(self):
        """Test that the serializer validates data correctly."""
        valid_data = {
            'model_ids': [self.model1.id, self.model2.id],
            'action': 'update_costs',
            'cost_multiplier': 1.5
        }
        serializer = BulkModelUpdateSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['model_ids'], valid_data['model_ids'])
        self.assertEqual(serializer.validated_data['action'], valid_data['action'])
        self.assertEqual(serializer.validated_data['cost_multiplier'], valid_data['cost_multiplier'])

        # Invalid model_ids
        invalid_data = valid_data.copy()
        invalid_data['model_ids'] = [999999]  # Non-existent ID
        serializer = BulkModelUpdateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('model_ids', serializer.errors)

        # Invalid cost_multiplier (too low)
        invalid_data = valid_data.copy()
        invalid_data['cost_multiplier'] = 0.05  # Below min_value of 0.1
        serializer = BulkModelUpdateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('cost_multiplier', serializer.errors)

        # Invalid cost_multiplier (too high)
        invalid_data = valid_data.copy()
        invalid_data['cost_multiplier'] = 11.0  # Above max_value of 10.0
        serializer = BulkModelUpdateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('cost_multiplier', serializer.errors)
