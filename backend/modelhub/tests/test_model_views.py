import json
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from modelhub.models import Provider, Model
from core.models import Organization, User


class ModelViewSetTest(APITestCase):
    """Test cases for the ModelViewSet."""

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
            version='1.0',
            model_type='TEXT',
            capabilities=['completion', 'chat'],
            config={'temperature': 0.7},
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )
        
        self.code_model = Model.objects.create(
            provider=self.provider,
            name='Code Model',
            version='1.0',
            model_type='CODE',
            capabilities=['completion', 'chat', 'function_calling'],
            config={'temperature': 0.5},
            cost_input=Decimal('0.002'),
            cost_output=Decimal('0.003'),
            context_window=8192,
            status='ACTIVE'
        )
        
        self.inactive_model = Model.objects.create(
            provider=self.provider,
            name='Inactive Model',
            version='1.0',
            model_type='TEXT',
            capabilities=['completion'],
            config={'temperature': 0.7},
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='INACTIVE'
        )
        
        # URL for model endpoints
        self.model_list_url = reverse('model-list')
        self.text_model_detail_url = reverse('model-detail', args=[self.text_model.id])
        self.code_model_detail_url = reverse('model-detail', args=[self.code_model.id])
        self.inactive_model_detail_url = reverse('model-detail', args=[self.inactive_model.id])
        self.text_model_estimate_cost_url = reverse('model-estimate-cost', args=[self.text_model.id])

    def test_list_models(self):
        """Test that only active models are listed."""
        response = self.client.get(self.model_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Only active models should be returned
        self.assertEqual(len(response.data), 2)
        model_names = [model['name'] for model in response.data]
        self.assertIn('Text Model', model_names)
        self.assertIn('Code Model', model_names)
        self.assertNotIn('Inactive Model', model_names)
    
    def test_filter_models_by_type(self):
        """Test filtering models by type."""
        response = self.client.get(f"{self.model_list_url}?model_type=TEXT")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Text Model')
        
        response = self.client.get(f"{self.model_list_url}?model_type=CODE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Code Model')
    
    def test_retrieve_active_model(self):
        """Test retrieving an active model."""
        response = self.client.get(self.text_model_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Text Model')
        self.assertEqual(response.data['model_type'], 'TEXT')
        self.assertEqual(response.data['status'], 'ACTIVE')
        
        # Check that cost_display is included
        self.assertIn('cost_display', response.data)
        self.assertEqual(response.data['cost_display']['input_per_1k'], f"${self.text_model.cost_input:.4f}")
        
        # Check that cost_examples is included
        self.assertIn('cost_examples', response.data)
        self.assertTrue(len(response.data['cost_examples']) > 0)
    
    def test_retrieve_inactive_model(self):
        """Test retrieving an inactive model."""
        response = self.client.get(self.inactive_model_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_create_model(self):
        """Test creating a model."""
        data = {
            'provider': self.provider.id,
            'name': 'New Model',
            'version': '1.0',
            'model_type': 'IMAGE',
            'capabilities': ['generation', 'editing'],
            'config': {'quality': 'high'},
            'cost_input': '0.005',
            'cost_output': '0.010',
            'context_window': 1024,
            'status': 'ACTIVE'
        }
        response = self.client.post(self.model_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Model.objects.count(), 4)
        
        # Check that the model was created correctly
        new_model = Model.objects.get(name='New Model')
        self.assertEqual(new_model.model_type, 'IMAGE')
        self.assertEqual(new_model.capabilities, ['generation', 'editing'])
        self.assertEqual(new_model.cost_input, Decimal('0.005'))
    
    def test_update_model(self):
        """Test updating a model."""
        data = {
            'provider': self.provider.id,
            'name': 'Updated Text Model',
            'version': '1.1',
            'model_type': 'TEXT',
            'capabilities': ['completion', 'chat', 'summarization'],
            'config': {'temperature': 0.8},
            'cost_input': '0.0015',
            'cost_output': '0.0025',
            'context_window': 8192,
            'status': 'ACTIVE'
        }
        response = self.client.put(self.text_model_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.text_model.refresh_from_db()
        self.assertEqual(self.text_model.name, 'Updated Text Model')
        self.assertEqual(self.text_model.version, '1.1')
        self.assertEqual(self.text_model.capabilities, ['completion', 'chat', 'summarization'])
        self.assertEqual(self.text_model.cost_input, Decimal('0.0015'))
        self.assertEqual(self.text_model.context_window, 8192)
    
    def test_partial_update_model(self):
        """Test partially updating a model."""
        data = {
            'capabilities': ['completion', 'chat', 'function_calling'],
            'cost_input': '0.0015'
        }
        response = self.client.patch(self.text_model_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.text_model.refresh_from_db()
        self.assertEqual(self.text_model.name, 'Text Model')  # Unchanged
        self.assertEqual(self.text_model.capabilities, ['completion', 'chat', 'function_calling'])  # Changed
        self.assertEqual(self.text_model.cost_input, Decimal('0.0015'))  # Changed
    
    def test_delete_model(self):
        """Test deleting a model."""
        response = self.client.delete(self.text_model_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # The model should be deleted
        with self.assertRaises(Model.DoesNotExist):
            Model.objects.get(id=self.text_model.id)
    
    def test_estimate_cost(self):
        """Test the estimate_cost action."""
        data = {
            'input_tokens': 1000,
            'output_tokens': 500
        }
        response = self.client.post(self.text_model_estimate_cost_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the response
        self.assertEqual(response.data['model_id'], str(self.text_model.id))
        self.assertEqual(response.data['model_name'], 'Text Model')
        self.assertEqual(response.data['provider'], 'Test Provider')
        self.assertEqual(response.data['input_tokens'], 1000)
        self.assertEqual(response.data['output_tokens'], 500)
        
        # Calculate expected cost
        expected_cost = float(self.text_model.estimate_cost(1000, 500))
        self.assertEqual(response.data['estimated_cost'], expected_cost)
        
        # Cost details should be included
        self.assertIn('cost_details', response.data)
        self.assertEqual(response.data['cost_details'], self.text_model.cost_display)
    
    def test_estimate_cost_validation(self):
        """Test validation in the estimate_cost action."""
        # Invalid input (negative tokens)
        data = {
            'input_tokens': -1000,
            'output_tokens': 500
        }
        response = self.client.post(self.text_model_estimate_cost_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Invalid input (non-numeric tokens)
        data = {
            'input_tokens': 'not-a-number',
            'output_tokens': 500
        }
        response = self.client.post(self.text_model_estimate_cost_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_search_models(self):
        """Test searching for models."""
        # Search by name
        response = self.client.get(f"{self.model_list_url}?search=Code")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Code Model')
        
        # Search by provider name
        response = self.client.get(f"{self.model_list_url}?search=Test Provider")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Both active models
    
    def test_ordering_models(self):
        """Test ordering models."""
        # Order by name ascending
        response = self.client.get(f"{self.model_list_url}?ordering=name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'Code Model')
        self.assertEqual(response.data[1]['name'], 'Text Model')
        
        # Order by name descending
        response = self.client.get(f"{self.model_list_url}?ordering=-name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'Text Model')
        self.assertEqual(response.data[1]['name'], 'Code Model')
        
        # Order by provider name
        response = self.client.get(f"{self.model_list_url}?ordering=provider__name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Both have the same provider, so order should be by ID
        
        # Order by status
        response = self.client.get(f"{self.model_list_url}?ordering=status")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Both are active, so order should be by ID
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the API."""
        # Log out
        self.client.force_authenticate(user=None)
        
        # Try to access the API
        response = self.client.get(self.model_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
