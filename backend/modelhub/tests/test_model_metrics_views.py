import json
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from modelhub.models import Provider, Model, APIKey, ModelMetrics
from core.models import Organization, User


class ModelMetricsViewSetTest(APITestCase):
    """Test cases for the ModelMetricsViewSet."""

    def setUp(self):
        """Set up test data."""
        # Create a user and organization
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword'
        )
        self.organization = Organization.objects.create(
            name='Test Organization',
            slug='test-org'
        )
        self.user.default_org = self.organization
        self.user.save()
        
        # Set up authentication
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create provider
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        
        # Create models
        self.text_model = Model.objects.create(
            provider=self.provider,
            name='Text Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )
        
        self.code_model = Model.objects.create(
            provider=self.provider,
            name='Code Model',
            model_type='CODE',
            cost_input=Decimal('0.002'),
            cost_output=Decimal('0.003'),
            context_window=8192,
            status='ACTIVE'
        )
        
        # Create API key
        self.api_key = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider,
            label='Test API Key',
            key='sk-test-api-key-12345',
            is_default=True,
            is_active=True
        )
        
        # Create model metrics
        self.now = timezone.now()
        self.yesterday = self.now - timedelta(days=1)
        self.last_week = self.now - timedelta(days=7)
        
        # Today's metrics
        self.text_model_metrics = ModelMetrics.objects.create(
            model=self.text_model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=self.now,
            latency_ms=100,
            tokens_input=1000,
            tokens_output=500,
            cost=Decimal('0.002'),
            status='SUCCESS',
            optimization_metadata={'strategy': 'cost_optimized'}
        )
        
        self.code_model_metrics = ModelMetrics.objects.create(
            model=self.code_model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=self.now,
            latency_ms=150,
            tokens_input=2000,
            tokens_output=1000,
            cost=Decimal('0.005'),
            status='SUCCESS',
            optimization_metadata={'strategy': 'performance_optimized'}
        )
        
        # Yesterday's metrics
        self.yesterday_metrics = ModelMetrics.objects.create(
            model=self.text_model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=self.yesterday,
            latency_ms=120,
            tokens_input=1500,
            tokens_output=700,
            cost=Decimal('0.003'),
            status='SUCCESS'
        )
        
        # Last week's metrics
        self.last_week_metrics = ModelMetrics.objects.create(
            model=self.text_model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=self.last_week,
            latency_ms=130,
            tokens_input=1800,
            tokens_output=800,
            cost=Decimal('0.0035'),
            status='SUCCESS'
        )
        
        # Error metrics
        self.error_metrics = ModelMetrics.objects.create(
            model=self.text_model,
            organization=self.organization,
            api_key=self.api_key,
            timestamp=self.now,
            latency_ms=200,
            tokens_input=0,
            tokens_output=0,
            cost=Decimal('0.000'),
            status='ERROR',
            error_type='RateLimitError',
            error_message='Rate limit exceeded'
        )
        
        # Another organization's metrics
        self.other_organization = Organization.objects.create(
            name='Other Organization',
            slug='other-org'
        )
        self.other_metrics = ModelMetrics.objects.create(
            model=self.text_model,
            organization=self.other_organization,
            timestamp=self.now,
            latency_ms=110,
            tokens_input=1200,
            tokens_output=600,
            cost=Decimal('0.0025'),
            status='SUCCESS'
        )
        
        # URL for model metrics endpoints
        self.metrics_list_url = reverse('modelmetrics-list')
        self.text_model_metrics_detail_url = reverse('modelmetrics-detail', args=[self.text_model_metrics.id])
        self.code_model_metrics_detail_url = reverse('modelmetrics-detail', args=[self.code_model_metrics.id])
        self.cost_summary_url = reverse('modelmetrics-cost-summary')
        self.optimization_stats_url = reverse('modelmetrics-optimization-stats')
        self.dashboard_summary_url = reverse('modelmetrics-dashboard-summary')

    def test_list_model_metrics(self):
        """Test listing model metrics."""
        response = self.client.get(self.metrics_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return user's organization metrics only
        self.assertEqual(len(response.data), 5)  # 5 metrics for user's organization
        
        # Check that other organization's metrics are not included
        metric_ids = [metric['id'] for metric in response.data]
        self.assertNotIn(str(self.other_metrics.id), metric_ids)
    
    def test_retrieve_model_metrics(self):
        """Test retrieving model metrics."""
        # User's own metrics
        response = self.client.get(self.text_model_metrics_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['model'], str(self.text_model.id))
        self.assertEqual(response.data['model_name'], 'Text Model')
        self.assertEqual(response.data['provider_name'], 'Test Provider')
        self.assertEqual(response.data['organization'], str(self.organization.id))
        self.assertEqual(response.data['organization_name'], 'Test Organization')
        self.assertEqual(response.data['latency_ms'], 100)
        self.assertEqual(response.data['tokens_input'], 1000)
        self.assertEqual(response.data['tokens_output'], 500)
        self.assertEqual(Decimal(response.data['cost']), Decimal('0.002'))
        self.assertEqual(response.data['status'], 'SUCCESS')
        self.assertEqual(response.data['optimization_metadata'], {'strategy': 'cost_optimized'})
        
        # Check calculated fields
        self.assertIn('cost_per_token', response.data)
        self.assertIn('efficiency_score', response.data)
        
        # Other organization's metrics
        other_metrics_url = reverse('modelmetrics-detail', args=[self.other_metrics.id])
        response = self.client.get(other_metrics_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_create_model_metrics(self):
        """Test creating model metrics."""
        data = {
            'model': self.text_model.id,
            'latency_ms': 140,
            'tokens_input': 2200,
            'tokens_output': 900,
            'cost': '0.004',
            'status': 'SUCCESS',
            'optimization_metadata': {'strategy': 'balanced'}
        }
        response = self.client.post(self.metrics_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that the metrics were created correctly
        new_metrics = ModelMetrics.objects.get(id=response.data['id'])
        self.assertEqual(new_metrics.model, self.text_model)
        self.assertEqual(new_metrics.organization, self.organization)  # Should be set automatically
        self.assertEqual(new_metrics.latency_ms, 140)
        self.assertEqual(new_metrics.tokens_input, 2200)
        self.assertEqual(new_metrics.tokens_output, 900)
        self.assertEqual(new_metrics.cost, Decimal('0.004'))
        self.assertEqual(new_metrics.status, 'SUCCESS')
        self.assertEqual(new_metrics.optimization_metadata, {'strategy': 'balanced'})
    
    def test_update_model_metrics(self):
        """Test updating model metrics."""
        data = {
            'model': self.text_model.id,
            'organization': self.organization.id,
            'latency_ms': 160,
            'tokens_input': 2500,
            'tokens_output': 1100,
            'cost': '0.005',
            'status': 'SUCCESS',
            'optimization_metadata': {'strategy': 'updated'}
        }
        response = self.client.put(self.text_model_metrics_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.text_model_metrics.refresh_from_db()
        self.assertEqual(self.text_model_metrics.latency_ms, 160)
        self.assertEqual(self.text_model_metrics.tokens_input, 2500)
        self.assertEqual(self.text_model_metrics.tokens_output, 1100)
        self.assertEqual(self.text_model_metrics.cost, Decimal('0.005'))
        self.assertEqual(self.text_model_metrics.optimization_metadata, {'strategy': 'updated'})
    
    def test_partial_update_model_metrics(self):
        """Test partially updating model metrics."""
        data = {
            'latency_ms': 180,
            'optimization_metadata': {'strategy': 'partially_updated'}
        }
        response = self.client.patch(self.text_model_metrics_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.text_model_metrics.refresh_from_db()
        self.assertEqual(self.text_model_metrics.latency_ms, 180)  # Changed
        self.assertEqual(self.text_model_metrics.tokens_input, 1000)  # Unchanged
        self.assertEqual(self.text_model_metrics.tokens_output, 500)  # Unchanged
        self.assertEqual(self.text_model_metrics.optimization_metadata, {'strategy': 'partially_updated'})  # Changed
    
    def test_delete_model_metrics(self):
        """Test deleting model metrics."""
        response = self.client.delete(self.text_model_metrics_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # The metrics should be deleted
        with self.assertRaises(ModelMetrics.DoesNotExist):
            ModelMetrics.objects.get(id=self.text_model_metrics.id)
    
    def test_cost_summary(self):
        """Test the cost_summary action."""
        response = self.client.get(self.cost_summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the response
        self.assertIn('total_cost', response.data)
        self.assertIn('total_requests', response.data)
        self.assertIn('successful_requests', response.data)
        self.assertIn('failed_requests', response.data)
        self.assertIn('total_tokens_input', response.data)
        self.assertIn('total_tokens_output', response.data)
        self.assertIn('daily_costs', response.data)
        self.assertIn('model_costs', response.data)
        
        # Check the values
        self.assertEqual(response.data['total_requests'], 5)  # 5 metrics for user's organization
        self.assertEqual(response.data['successful_requests'], 4)  # 4 success, 1 error
        self.assertEqual(response.data['failed_requests'], 1)  # 1 error
        
        # Calculate expected total cost
        expected_cost = Decimal('0.002') + Decimal('0.005') + Decimal('0.003') + Decimal('0.0035') + Decimal('0.000')
        self.assertEqual(Decimal(response.data['total_cost']), expected_cost)
        
        # Calculate expected total tokens
        expected_tokens_input = 1000 + 2000 + 1500 + 1800 + 0
        expected_tokens_output = 500 + 1000 + 700 + 800 + 0
        self.assertEqual(response.data['total_tokens_input'], expected_tokens_input)
        self.assertEqual(response.data['total_tokens_output'], expected_tokens_output)
        
        # Check daily costs
        self.assertEqual(len(response.data['daily_costs']), 3)  # Today, yesterday, last week
        
        # Check model costs
        self.assertEqual(len(response.data['model_costs']), 2)  # Text Model and Code Model
        
        # Check date range filtering
        yesterday_str = self.yesterday.strftime('%Y-%m-%d')
        response = self.client.get(f"{self.cost_summary_url}?start_date={yesterday_str}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_requests'], 4)  # Excluding last week's metrics
        
        # Check model filtering
        response = self.client.get(f"{self.cost_summary_url}?model_id={self.text_model.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_requests'], 4)  # Excluding code model metrics
    
    def test_optimization_stats(self):
        """Test the optimization_stats action."""
        response = self.client.get(self.optimization_stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the response
        self.assertIn('total_optimized_requests', response.data)
        self.assertIn('total_savings', response.data)
        self.assertIn('optimization_strategies', response.data)
        self.assertIn('optimization_trends', response.data)
        self.assertIn('potential_savings', response.data)
        self.assertIn('recommendations', response.data)
        
        # Check the values
        self.assertEqual(response.data['total_optimized_requests'], 2)  # 2 metrics with optimization_metadata
        
        # Check optimization strategies
        strategies = response.data['optimization_strategies']
        self.assertEqual(len(strategies), 2)  # cost_optimized and performance_optimized
        
        # Check recommendations
        self.assertTrue(len(response.data['recommendations']) > 0)
    
    def test_dashboard_summary(self):
        """Test the dashboard_summary action."""
        response = self.client.get(self.dashboard_summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the response
        self.assertIn('cost_summary', response.data)
        self.assertIn('recent_requests', response.data)
        self.assertIn('models', response.data)
        self.assertIn('daily_usage', response.data)
        self.assertIn('error_rate', response.data)
        self.assertIn('top_models', response.data)
        
        # Check cost summary
        self.assertEqual(response.data['cost_summary']['total_requests'], 5)
        
        # Check recent requests
        self.assertEqual(len(response.data['recent_requests']), 5)
        
        # Check models
        self.assertEqual(len(response.data['models']), 2)  # Text Model and Code Model
        
        # Check daily usage
        self.assertTrue(len(response.data['daily_usage']) > 0)
        
        # Check error rate
        self.assertEqual(response.data['error_rate']['total_errors'], 1)
        self.assertEqual(response.data['error_rate']['total_requests'], 5)
        self.assertEqual(response.data['error_rate']['error_percentage'], 20.0)  # 1/5 = 20%
        
        # Check top models
        self.assertEqual(len(response.data['top_models']), 2)  # Text Model and Code Model
    
    def test_search_model_metrics(self):
        """Test searching for model metrics."""
        # Search by model name
        response = self.client.get(f"{self.metrics_list_url}?search=Text")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)  # 4 metrics for Text Model
        
        # Search by provider name
        response = self.client.get(f"{self.metrics_list_url}?search=Test Provider")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)  # All 5 metrics
    
    def test_ordering_model_metrics(self):
        """Test ordering model metrics."""
        # Order by timestamp ascending
        response = self.client.get(f"{self.metrics_list_url}?ordering=timestamp")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        # First should be the oldest (last week)
        self.assertEqual(response.data[0]['id'], str(self.last_week_metrics.id))
        
        # Order by timestamp descending (default)
        response = self.client.get(self.metrics_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        # First should be the newest (today)
        newest_ids = [str(self.text_model_metrics.id), str(self.code_model_metrics.id), str(self.error_metrics.id)]
        self.assertIn(response.data[0]['id'], newest_ids)
        
        # Order by latency_ms
        response = self.client.get(f"{self.metrics_list_url}?ordering=latency_ms")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        # First should be the lowest latency
        self.assertEqual(response.data[0]['latency_ms'], 100)
        
        # Order by cost
        response = self.client.get(f"{self.metrics_list_url}?ordering=cost")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        # First should be the lowest cost
        self.assertEqual(Decimal(response.data[0]['cost']), Decimal('0.000'))  # Error metrics
    
    def test_user_without_organization(self):
        """Test that a user without a default organization gets no metrics."""
        # Create a user without a default organization
        user_without_org = User.objects.create_user(
            email='no-org@example.com',
            password='testpassword'
        )
        
        # Set up authentication
        self.client.force_authenticate(user=user_without_org)
        
        # Try to list metrics
        response = self.client.get(self.metrics_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # No metrics
        
        # Try to get cost summary
        response = self.client.get(self.cost_summary_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Try to get dashboard summary
        response = self.client.get(self.dashboard_summary_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the API."""
        # Log out
        self.client.force_authenticate(user=None)
        
        # Try to access the API
        response = self.client.get(self.metrics_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
