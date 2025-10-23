import json
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from modelhub.models import Provider, Model
from core.models import Organization, User


class ProviderViewSetTest(APITestCase):
    """Test cases for the ProviderViewSet."""

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
        
        # Create providers
        self.active_provider = Provider.objects.create(
            name='Active Provider',
            slug='active-provider',
            description='An active provider',
            website='https://active.example.com',
            documentation_url='https://docs.active.example.com',
            status='ACTIVE',
            config={'base_url': 'https://api.active.example.com/v1'}
        )
        
        self.inactive_provider = Provider.objects.create(
            name='Inactive Provider',
            slug='inactive-provider',
            description='An inactive provider',
            website='https://inactive.example.com',
            documentation_url='https://docs.inactive.example.com',
            status='INACTIVE',
            config={'base_url': 'https://api.inactive.example.com/v1'}
        )
        
        # URL for provider endpoints
        self.provider_list_url = reverse('provider-list')
        self.active_provider_detail_url = reverse('provider-detail', args=[self.active_provider.id])
        self.inactive_provider_detail_url = reverse('provider-detail', args=[self.inactive_provider.id])

    def test_list_providers(self):
        """Test that only active providers are listed."""
        response = self.client.get(self.provider_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Only active providers should be returned
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Active Provider')
    
    def test_retrieve_active_provider(self):
        """Test retrieving an active provider."""
        response = self.client.get(self.active_provider_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Active Provider')
        self.assertEqual(response.data['status'], 'ACTIVE')
    
    def test_retrieve_inactive_provider(self):
        """Test retrieving an inactive provider."""
        response = self.client.get(self.inactive_provider_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_create_provider(self):
        """Test creating a provider."""
        data = {
            'name': 'New Provider',
            'slug': 'new-provider',
            'description': 'A new provider',
            'website': 'https://new.example.com',
            'documentation_url': 'https://docs.new.example.com',
            'status': 'ACTIVE',
            'config': {'base_url': 'https://api.new.example.com/v1'}
        }
        response = self.client.post(self.provider_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Provider.objects.count(), 3)
        self.assertEqual(Provider.objects.get(slug='new-provider').name, 'New Provider')
    
    def test_update_provider(self):
        """Test updating a provider."""
        data = {
            'name': 'Updated Provider',
            'slug': 'active-provider',  # Keep the same slug
            'description': 'An updated provider',
            'website': 'https://updated.example.com',
            'documentation_url': 'https://docs.updated.example.com',
            'status': 'ACTIVE',
            'config': {'base_url': 'https://api.updated.example.com/v1'}
        }
        response = self.client.put(self.active_provider_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.active_provider.refresh_from_db()
        self.assertEqual(self.active_provider.name, 'Updated Provider')
        self.assertEqual(self.active_provider.description, 'An updated provider')
    
    def test_partial_update_provider(self):
        """Test partially updating a provider."""
        data = {
            'description': 'A partially updated provider'
        }
        response = self.client.patch(self.active_provider_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.active_provider.refresh_from_db()
        self.assertEqual(self.active_provider.name, 'Active Provider')  # Unchanged
        self.assertEqual(self.active_provider.description, 'A partially updated provider')  # Changed
    
    def test_delete_provider(self):
        """Test deleting a provider."""
        response = self.client.delete(self.active_provider_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Provider.objects.filter(status='ACTIVE').count(), 0)
    
    def test_search_providers(self):
        """Test searching for providers."""
        # Create another active provider
        Provider.objects.create(
            name='Another Active Provider',
            slug='another-active-provider',
            description='Another active provider for testing search',
            status='ACTIVE'
        )
        
        # Search by name
        response = self.client.get(f"{self.provider_list_url}?search=Another")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Another Active Provider')
        
        # Search by description
        response = self.client.get(f"{self.provider_list_url}?search=testing search")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Another Active Provider')
    
    def test_ordering_providers(self):
        """Test ordering providers."""
        # Create another active provider with a name that comes before 'Active Provider' alphabetically
        Provider.objects.create(
            name='AAA Provider',
            slug='aaa-provider',
            status='ACTIVE'
        )
        
        # Order by name ascending (default)
        response = self.client.get(f"{self.provider_list_url}?ordering=name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'AAA Provider')
        self.assertEqual(response.data[1]['name'], 'Active Provider')
        
        # Order by name descending
        response = self.client.get(f"{self.provider_list_url}?ordering=-name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'Active Provider')
        self.assertEqual(response.data[1]['name'], 'AAA Provider')
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the API."""
        # Log out
        self.client.force_authenticate(user=None)
        
        # Try to access the API
        response = self.client.get(self.provider_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
