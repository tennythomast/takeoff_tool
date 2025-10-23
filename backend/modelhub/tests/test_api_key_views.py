import json
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch

from modelhub.models import Provider, Model, APIKey, ModelMetrics
from modelhub.services.api_key_manager import APIKeyManager
from core.models import Organization, User


class APIKeyViewSetTest(APITestCase):
    """Test cases for the APIKeyViewSet."""

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
        
        # Create API keys
        self.api_key = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider,
            label='Test API Key',
            key='sk-test-api-key-12345',
            is_default=True,
            is_active=True,
            daily_quota=Decimal('10.00'),
            monthly_quota=Decimal('200.00')
        )
        
        self.inactive_api_key = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider,
            label='Inactive API Key',
            key='sk-inactive-api-key-12345',
            is_default=False,
            is_active=False,
            daily_quota=Decimal('5.00'),
            monthly_quota=Decimal('100.00')
        )
        
        # Create system-wide API key (no organization)
        self.system_api_key = APIKey.objects.create(
            organization=None,
            provider=self.provider,
            label='System API Key',
            key='sk-system-api-key-12345',
            is_default=True,
            is_active=True
        )
        
        # Create another organization's API key
        self.other_organization = Organization.objects.create(
            name='Other Organization',
            slug='other-org'
        )
        self.other_api_key = APIKey.objects.create(
            organization=self.other_organization,
            provider=self.provider,
            label='Other API Key',
            key='sk-other-api-key-12345',
            is_default=True,
            is_active=True
        )
        
        # URL for API key endpoints
        self.api_key_list_url = reverse('apikey-list')
        self.api_key_detail_url = reverse('apikey-detail', args=[self.api_key.id])
        self.inactive_api_key_detail_url = reverse('apikey-detail', args=[self.inactive_api_key.id])
        self.system_api_key_detail_url = reverse('apikey-detail', args=[self.system_api_key.id])
        self.other_api_key_detail_url = reverse('apikey-detail', args=[self.other_api_key.id])
        self.usage_summary_url = reverse('apikey-usage-summary')
        self.health_status_url = reverse('apikey-health-status')
        self.quota_status_url = reverse('apikey-quota-status', args=[self.api_key.id])

    def test_list_api_keys(self):
        """Test listing API keys."""
        response = self.client.get(self.api_key_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return user's organization API keys (active only) and system-wide API keys
        self.assertEqual(len(response.data), 2)
        
        api_key_labels = [api_key['label'] for api_key in response.data]
        self.assertIn('Test API Key', api_key_labels)  # User's active API key
        self.assertIn('System API Key', api_key_labels)  # System-wide API key
        self.assertNotIn('Inactive API Key', api_key_labels)  # User's inactive API key
        self.assertNotIn('Other API Key', api_key_labels)  # Other organization's API key
    
    def test_retrieve_api_key(self):
        """Test retrieving an API key."""
        # User's own API key
        response = self.client.get(self.api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['label'], 'Test API Key')
        
        # System-wide API key
        response = self.client.get(self.system_api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['label'], 'System API Key')
        
        # Other organization's API key
        response = self.client.get(self.other_api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Inactive API key
        response = self.client.get(self.inactive_api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_create_api_key(self):
        """Test creating an API key."""
        data = {
            'provider': self.provider.id,
            'label': 'New API Key',
            'key': 'sk-new-api-key-12345',
            'is_default': False,
            'is_active': True,
            'daily_quota': '15.00',
            'monthly_quota': '300.00'
        }
        response = self.client.post(self.api_key_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that the API key was created correctly
        new_api_key = APIKey.objects.get(label='New API Key')
        self.assertEqual(new_api_key.organization, self.organization)
        self.assertEqual(new_api_key.provider, self.provider)
        self.assertEqual(new_api_key.key, 'sk-new-api-key-12345')
        self.assertEqual(new_api_key.daily_quota, Decimal('15.00'))
    
    def test_update_api_key(self):
        """Test updating an API key."""
        data = {
            'provider': self.provider.id,
            'label': 'Updated API Key',
            'key': 'sk-updated-api-key-12345',
            'is_default': True,
            'is_active': True,
            'daily_quota': '20.00',
            'monthly_quota': '400.00'
        }
        response = self.client.put(self.api_key_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.label, 'Updated API Key')
        self.assertEqual(self.api_key.key, 'sk-updated-api-key-12345')
        self.assertEqual(self.api_key.daily_quota, Decimal('20.00'))
        self.assertEqual(self.api_key.monthly_quota, Decimal('400.00'))
    
    def test_partial_update_api_key(self):
        """Test partially updating an API key."""
        data = {
            'label': 'Partially Updated API Key',
            'daily_quota': '25.00'
        }
        response = self.client.patch(self.api_key_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.label, 'Partially Updated API Key')
        self.assertEqual(self.api_key.daily_quota, Decimal('25.00'))
        self.assertEqual(self.api_key.monthly_quota, Decimal('200.00'))  # Unchanged
    
    def test_delete_api_key(self):
        """Test deleting an API key."""
        response = self.client.delete(self.api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # The API key should be deleted
        with self.assertRaises(APIKey.DoesNotExist):
            APIKey.objects.get(id=self.api_key.id)
    
    @patch.object(APIKeyManager, 'get_usage_summary')
    def test_usage_summary(self, mock_get_usage_summary):
        """Test the usage_summary action."""
        # Mock the APIKeyManager.get_usage_summary method
        mock_get_usage_summary.return_value = {
            'total_cost': 50.0,
            'total_requests': 100,
            'daily_usage': [{'date': '2023-01-01', 'cost': 10.0}],
            'provider_usage': [{'provider': 'Test Provider', 'cost': 50.0}]
        }
        
        response = self.client.get(self.usage_summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the APIKeyManager.get_usage_summary method was called
        mock_get_usage_summary.assert_called_once_with(self.organization)
        
        # Check the response
        self.assertEqual(response.data['total_cost'], 50.0)
        self.assertEqual(response.data['total_requests'], 100)
        self.assertEqual(len(response.data['daily_usage']), 1)
        self.assertEqual(len(response.data['provider_usage']), 1)
    
    @patch.object(APIKeyManager, 'get_key_health')
    def test_health_status(self, mock_get_key_health):
        """Test the health_status action."""
        # Mock the APIKeyManager.get_key_health method
        mock_get_key_health.return_value = {
            'healthy_keys': 1,
            'warning_keys': 0,
            'unhealthy_keys': 0,
            'key_statuses': [
                {
                    'key_id': str(self.api_key.id),
                    'label': 'Test API Key',
                    'provider': 'Test Provider',
                    'status': 'healthy',
                    'error_rate': 0.0
                }
            ]
        }
        
        response = self.client.get(self.health_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the APIKeyManager.get_key_health method was called
        mock_get_key_health.assert_called_once_with(self.organization)
        
        # Check the response
        self.assertEqual(response.data['healthy_keys'], 1)
        self.assertEqual(response.data['warning_keys'], 0)
        self.assertEqual(response.data['unhealthy_keys'], 0)
        self.assertEqual(len(response.data['key_statuses']), 1)
        self.assertEqual(response.data['key_statuses'][0]['label'], 'Test API Key')
    
    def test_quota_status(self):
        """Test the quota_status action."""
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
        
        # Create model metrics for today
        ModelMetrics.objects.create(
            model=model,
            organization=self.organization,
            api_key=self.api_key,
            latency_ms=100,
            tokens_input=1000,
            tokens_output=500,
            cost=Decimal('2.00'),
            status='SUCCESS'
        )
        
        response = self.client.get(self.quota_status_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the response
        self.assertEqual(response.data['key_id'], str(self.api_key.id))
        self.assertEqual(response.data['label'], 'Test API Key')
        self.assertEqual(response.data['provider'], 'Test Provider')
        
        # Check quota information
        self.assertIn('daily_usage', response.data)
        self.assertIn('monthly_usage', response.data)
        self.assertIn('daily_remaining', response.data)
        self.assertIn('monthly_remaining', response.data)
        self.assertIn('daily_percent_used', response.data)
        self.assertIn('monthly_percent_used', response.data)
    
    def test_search_api_keys(self):
        """Test searching for API keys."""
        # Create another API key
        APIKey.objects.create(
            organization=self.organization,
            provider=self.provider,
            label='Searchable API Key',
            key='sk-searchable-api-key-12345',
            is_default=False,
            is_active=True
        )
        
        # Search by label
        response = self.client.get(f"{self.api_key_list_url}?search=Searchable")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['label'], 'Searchable API Key')
        
        # Search by provider name
        response = self.client.get(f"{self.api_key_list_url}?search=Test Provider")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # All active API keys for this provider
    
    def test_ordering_api_keys(self):
        """Test ordering API keys."""
        # Create another API key with a name that comes before 'Test API Key' alphabetically
        APIKey.objects.create(
            organization=self.organization,
            provider=self.provider,
            label='AAA API Key',
            key='sk-aaa-api-key-12345',
            is_default=False,
            is_active=True
        )
        
        # Order by label ascending
        response = self.client.get(f"{self.api_key_list_url}?ordering=label")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # All active API keys
        self.assertEqual(response.data[0]['label'], 'AAA API Key')
        
        # Order by label descending
        response = self.client.get(f"{self.api_key_list_url}?ordering=-label")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # All active API keys
        self.assertEqual(response.data[0]['label'], 'Test API Key')
        
        # Order by provider name
        response = self.client.get(f"{self.api_key_list_url}?ordering=provider__name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # All active API keys
        # All have the same provider, so order should be by ID
        
        # Order by is_default
        response = self.client.get(f"{self.api_key_list_url}?ordering=-is_default")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # All active API keys
        # Default keys should come first
        default_keys = [key for key in response.data if key['is_default']]
        non_default_keys = [key for key in response.data if not key['is_default']]
        self.assertEqual(len(default_keys), 2)  # User's default key and system default key
        self.assertEqual(len(non_default_keys), 1)  # AAA API Key
    
    def test_user_without_organization(self):
        """Test that a user without a default organization gets no API keys."""
        # Create a user without a default organization
        user_without_org = User.objects.create_user(
            email='no-org@example.com',
            password='testpassword'
        )
        
        # Set up authentication
        self.client.force_authenticate(user=user_without_org)
        
        # Try to list API keys
        response = self.client.get(self.api_key_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # No API keys
        
        # Try to get usage summary
        response = self.client.get(self.usage_summary_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Try to get health status
        response = self.client.get(self.health_status_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the API."""
        # Log out
        self.client.force_authenticate(user=None)
        
        # Try to access the API
        response = self.client.get(self.api_key_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
