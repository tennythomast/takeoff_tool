import json
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from modelhub.models import Provider, Model, RoutingRule, RoutingRuleModel
from core.models import Organization, User


class RoutingRuleViewSetTest(APITestCase):
    """Test cases for the RoutingRuleViewSet."""

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
        
        # Create provider and models
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        
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
        
        # Create routing rules
        self.text_rule = RoutingRule.objects.create(
            organization=self.organization,
            name='Text Rule',
            description='A rule for text models',
            priority=1,
            model_type='TEXT',
            conditions={
                'input_tokens': {'min': 0, 'max': 1000},
                'tags': ['text', 'general']
            }
        )
        
        self.code_rule = RoutingRule.objects.create(
            organization=self.organization,
            name='Code Rule',
            description='A rule for code models',
            priority=2,
            model_type='CODE',
            conditions={
                'input_tokens': {'min': 0, 'max': 2000},
                'tags': ['code', 'programming']
            }
        )
        
        # Create system-wide rule (no organization)
        self.system_rule = RoutingRule.objects.create(
            organization=None,
            name='System Rule',
            description='A system-wide rule',
            priority=100,
            model_type='TEXT',
            conditions={
                'input_tokens': {'min': 0, 'max': 4000},
                'tags': ['system']
            }
        )
        
        # Create another organization's rule
        self.other_organization = Organization.objects.create(
            name='Other Organization',
            slug='other-org'
        )
        self.other_rule = RoutingRule.objects.create(
            organization=self.other_organization,
            name='Other Rule',
            description='Another organization\'s rule',
            priority=1,
            model_type='TEXT',
            conditions={
                'input_tokens': {'min': 0, 'max': 1000},
                'tags': ['other']
            }
        )
        
        # Add models to rules
        self.text_rule_model = RoutingRuleModel.objects.create(
            rule=self.text_rule,
            model=self.text_model,
            weight=10,
            notes='Primary text model',
            tags=['primary']
        )
        
        self.code_rule_model = RoutingRuleModel.objects.create(
            rule=self.code_rule,
            model=self.code_model,
            weight=10,
            notes='Primary code model',
            tags=['primary']
        )
        
        # URL for routing rule endpoints
        self.rule_list_url = reverse('routingrule-list')
        self.text_rule_detail_url = reverse('routingrule-detail', args=[self.text_rule.id])
        self.code_rule_detail_url = reverse('routingrule-detail', args=[self.code_rule.id])
        self.system_rule_detail_url = reverse('routingrule-detail', args=[self.system_rule.id])
        self.other_rule_detail_url = reverse('routingrule-detail', args=[self.other_rule.id])

    def test_list_routing_rules(self):
        """Test listing routing rules."""
        response = self.client.get(self.rule_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return user's organization rules and system-wide rules
        self.assertEqual(len(response.data), 3)
        
        rule_names = [rule['name'] for rule in response.data]
        self.assertIn('Text Rule', rule_names)  # User's rule
        self.assertIn('Code Rule', rule_names)  # User's rule
        self.assertIn('System Rule', rule_names)  # System-wide rule
        self.assertNotIn('Other Rule', rule_names)  # Other organization's rule
    
    def test_retrieve_routing_rule(self):
        """Test retrieving a routing rule."""
        # User's own rule
        response = self.client.get(self.text_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Text Rule')
        
        # System-wide rule
        response = self.client.get(self.system_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'System Rule')
        
        # Other organization's rule
        response = self.client.get(self.other_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_create_routing_rule(self):
        """Test creating a routing rule."""
        data = {
            'name': 'New Rule',
            'description': 'A new routing rule',
            'priority': 3,
            'model_type': 'IMAGE',
            'conditions': {
                'input_tokens': {'min': 0, 'max': 500},
                'tags': ['image', 'generation']
            }
        }
        response = self.client.post(self.rule_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that the rule was created correctly
        new_rule = RoutingRule.objects.get(name='New Rule')
        self.assertEqual(new_rule.organization, self.organization)
        self.assertEqual(new_rule.priority, 3)
        self.assertEqual(new_rule.model_type, 'IMAGE')
        self.assertEqual(new_rule.conditions['tags'], ['image', 'generation'])
    
    def test_update_routing_rule(self):
        """Test updating a routing rule."""
        data = {
            'name': 'Updated Text Rule',
            'description': 'An updated text rule',
            'priority': 5,
            'model_type': 'TEXT',
            'conditions': {
                'input_tokens': {'min': 0, 'max': 2000},
                'tags': ['text', 'updated']
            }
        }
        response = self.client.put(self.text_rule_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.text_rule.refresh_from_db()
        self.assertEqual(self.text_rule.name, 'Updated Text Rule')
        self.assertEqual(self.text_rule.description, 'An updated text rule')
        self.assertEqual(self.text_rule.priority, 5)
        self.assertEqual(self.text_rule.conditions['tags'], ['text', 'updated'])
    
    def test_partial_update_routing_rule(self):
        """Test partially updating a routing rule."""
        data = {
            'priority': 10,
            'conditions': {
                'input_tokens': {'min': 0, 'max': 3000},
                'tags': ['text', 'general']
            }
        }
        response = self.client.patch(self.text_rule_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.text_rule.refresh_from_db()
        self.assertEqual(self.text_rule.name, 'Text Rule')  # Unchanged
        self.assertEqual(self.text_rule.priority, 10)  # Changed
        self.assertEqual(self.text_rule.conditions['input_tokens']['max'], 3000)  # Changed
    
    def test_delete_routing_rule(self):
        """Test deleting a routing rule."""
        response = self.client.delete(self.text_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # The rule should be deleted
        with self.assertRaises(RoutingRule.DoesNotExist):
            RoutingRule.objects.get(id=self.text_rule.id)
        
        # The rule model should also be deleted (cascade)
        with self.assertRaises(RoutingRuleModel.DoesNotExist):
            RoutingRuleModel.objects.get(id=self.text_rule_model.id)
    
    def test_search_routing_rules(self):
        """Test searching for routing rules."""
        # Search by name
        response = self.client.get(f"{self.rule_list_url}?search=Code")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Code Rule')
        
        # Search by description
        response = self.client.get(f"{self.rule_list_url}?search=system-wide")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'System Rule')
    
    def test_ordering_routing_rules(self):
        """Test ordering routing rules."""
        # Order by name ascending
        response = self.client.get(f"{self.rule_list_url}?ordering=name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Code Rule')
        self.assertEqual(response.data[1]['name'], 'System Rule')
        self.assertEqual(response.data[2]['name'], 'Text Rule')
        
        # Order by name descending
        response = self.client.get(f"{self.rule_list_url}?ordering=-name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Text Rule')
        self.assertEqual(response.data[1]['name'], 'System Rule')
        self.assertEqual(response.data[2]['name'], 'Code Rule')
        
        # Order by priority (default)
        response = self.client.get(self.rule_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # Priority order: 1 (Text Rule), 2 (Code Rule), 100 (System Rule)
        self.assertEqual(response.data[0]['name'], 'Text Rule')
        self.assertEqual(response.data[1]['name'], 'Code Rule')
        self.assertEqual(response.data[2]['name'], 'System Rule')
        
        # Order by model_type
        response = self.client.get(f"{self.rule_list_url}?ordering=model_type")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # Alphabetical order of model_type: CODE, TEXT, TEXT
        self.assertEqual(response.data[0]['model_type'], 'CODE')
        self.assertEqual(response.data[1]['model_type'], 'TEXT')
        self.assertEqual(response.data[2]['model_type'], 'TEXT')
    
    def test_models_field_in_response(self):
        """Test that the models field is included in the response."""
        response = self.client.get(self.text_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the models field is included
        self.assertIn('models', response.data)
        self.assertEqual(len(response.data['models']), 1)
        
        # Check the model data
        model_data = response.data['models'][0]
        self.assertEqual(model_data['model'], str(self.text_model.id))
        self.assertEqual(model_data['model_name'], 'Text Model')
        self.assertEqual(model_data['provider_name'], 'Test Provider')
        self.assertEqual(model_data['weight'], 10)
        self.assertEqual(model_data['notes'], 'Primary text model')
        self.assertEqual(model_data['tags'], ['primary'])
    
    def test_model_count_field_in_response(self):
        """Test that the model_count field is included in the response."""
        response = self.client.get(self.text_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the model_count field is included
        self.assertIn('model_count', response.data)
        self.assertEqual(response.data['model_count'], 1)
    
    def test_cheapest_model_cost_field_in_response(self):
        """Test that the cheapest_model_cost field is included in the response."""
        response = self.client.get(self.text_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the cheapest_model_cost field is included
        self.assertIn('cheapest_model_cost', response.data)
        
        # Check the cheapest model cost data
        cheapest_cost = response.data['cheapest_model_cost']
        self.assertEqual(cheapest_cost['model_name'], 'Text Model')
        self.assertEqual(cheapest_cost['tokens_input'], 1000)
        self.assertEqual(cheapest_cost['tokens_output'], 500)
        
        # Calculate expected cost
        expected_cost = float(self.text_model.estimate_cost(1000, 500))
        self.assertEqual(cheapest_cost['cost'], expected_cost)
    
    def test_user_without_organization(self):
        """Test that a user without a default organization gets only system rules."""
        # Create a user without a default organization
        user_without_org = User.objects.create_user(
            email='no-org@example.com',
            password='testpassword'
        )
        
        # Set up authentication
        self.client.force_authenticate(user=user_without_org)
        
        # Try to list routing rules
        response = self.client.get(self.rule_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only system rule
        self.assertEqual(response.data[0]['name'], 'System Rule')
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access the API."""
        # Log out
        self.client.force_authenticate(user=None)
        
        # Try to access the API
        response = self.client.get(self.rule_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
