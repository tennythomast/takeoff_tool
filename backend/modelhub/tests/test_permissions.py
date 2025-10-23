from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from modelhub.models import Provider, Model, APIKey, RoutingRule
from modelhub.permissions import IsOrganizationMember, IsOrganizationAdmin
from core.models import Organization, User, OrganizationMembership


class ModelhubPermissionsTest(TestCase):
    """Test cases for the modelhub app permissions."""

    def setUp(self):
        """Set up test data."""
        # Create organizations
        self.organization = Organization.objects.create(
            name='Test Organization',
            slug='test-org'
        )
        
        self.other_organization = Organization.objects.create(
            name='Other Organization',
            slug='other-org'
        )
        
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpassword'
        )
        self.admin_user.default_org = self.organization
        self.admin_user.save()
        
        self.member_user = User.objects.create_user(
            email='member@example.com',
            password='memberpassword'
        )
        self.member_user.default_org = self.organization
        self.member_user.save()
        
        self.non_member_user = User.objects.create_user(
            email='nonmember@example.com',
            password='nonmemberpassword'
        )
        self.non_member_user.default_org = self.other_organization
        self.non_member_user.save()
        
        # Create organization memberships
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.admin_user,
            role='ADMIN'
        )
        
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.member_user,
            role='MEMBER'
        )
        
        OrganizationMembership.objects.create(
            organization=self.other_organization,
            user=self.non_member_user,
            role='ADMIN'
        )
        
        # Create provider
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider',
            status='ACTIVE'
        )
        
        # Create models
        self.model = Model.objects.create(
            provider=self.provider,
            name='Test Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE'
        )
        
        # Create API keys
        self.api_key = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider,
            label='Test API Key',
            key='sk-test-api-key-12345',
            is_default=True,
            is_active=True
        )
        
        # Create routing rule
        self.routing_rule = RoutingRule.objects.create(
            organization=self.organization,
            name='Test Rule',
            priority=10,
            model=self.model,
            conditions={
                'task_type': 'general',
                'min_tokens': 0,
                'max_tokens': 4000
            },
            is_active=True
        )
        
        # Set up API clients
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin_user)
        
        self.member_client = APIClient()
        self.member_client.force_authenticate(user=self.member_user)
        
        self.non_member_client = APIClient()
        self.non_member_client.force_authenticate(user=self.non_member_user)
        
        self.unauthenticated_client = APIClient()
        
        # URLs for testing
        self.provider_list_url = reverse('provider-list')
        self.provider_detail_url = reverse('provider-detail', args=[self.provider.id])
        self.model_list_url = reverse('model-list')
        self.model_detail_url = reverse('model-detail', args=[self.model.id])
        self.api_key_list_url = reverse('apikey-list')
        self.api_key_detail_url = reverse('apikey-detail', args=[self.api_key.id])
        self.routing_rule_list_url = reverse('routingrule-list')
        self.routing_rule_detail_url = reverse('routingrule-detail', args=[self.routing_rule.id])

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access any endpoints."""
        urls = [
            self.provider_list_url,
            self.provider_detail_url,
            self.model_list_url,
            self.model_detail_url,
            self.api_key_list_url,
            self.api_key_detail_url,
            self.routing_rule_list_url,
            self.routing_rule_detail_url
        ]
        
        for url in urls:
            response = self.unauthenticated_client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_provider_permissions(self):
        """Test permissions for provider endpoints."""
        # List providers
        response = self.admin_client.get(self.provider_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.member_client.get(self.provider_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.non_member_client.get(self.provider_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Create provider - only admins should be able to create
        provider_data = {
            'name': 'New Provider',
            'slug': 'new-provider',
            'status': 'ACTIVE'
        }
        
        response = self.admin_client.post(self.provider_list_url, provider_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response = self.member_client.post(self.provider_list_url, provider_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.non_member_client.post(self.provider_list_url, provider_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Update provider - only admins should be able to update
        provider_data = {
            'name': 'Updated Provider',
            'slug': 'test-provider',
            'status': 'ACTIVE'
        }
        
        response = self.admin_client.put(self.provider_detail_url, provider_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.member_client.put(self.provider_detail_url, provider_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.non_member_client.put(self.provider_detail_url, provider_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Delete provider - only admins should be able to delete
        response = self.member_client.delete(self.provider_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.non_member_client.delete(self.provider_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.admin_client.delete(self.provider_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_model_permissions(self):
        """Test permissions for model endpoints."""
        # List models
        response = self.admin_client.get(self.model_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.member_client.get(self.model_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.non_member_client.get(self.model_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Create model - only admins should be able to create
        model_data = {
            'provider': self.provider.id,
            'name': 'New Model',
            'model_type': 'TEXT',
            'cost_input': '0.001',
            'cost_output': '0.002',
            'context_window': 4096,
            'status': 'ACTIVE'
        }
        
        response = self.admin_client.post(self.model_list_url, model_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response = self.member_client.post(self.model_list_url, model_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.non_member_client.post(self.model_list_url, model_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Update model - only admins should be able to update
        model_data = {
            'provider': self.provider.id,
            'name': 'Updated Model',
            'model_type': 'TEXT',
            'cost_input': '0.001',
            'cost_output': '0.002',
            'context_window': 4096,
            'status': 'ACTIVE'
        }
        
        response = self.admin_client.put(self.model_detail_url, model_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.member_client.put(self.model_detail_url, model_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.non_member_client.put(self.model_detail_url, model_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_key_permissions(self):
        """Test permissions for API key endpoints."""
        # List API keys - only organization members should see their organization's keys
        response = self.admin_client.get(self.api_key_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        response = self.member_client.get(self.api_key_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        response = self.non_member_client.get(self.api_key_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # Should not see other organization's keys
        
        # Create API key - both admins and members should be able to create
        api_key_data = {
            'provider': self.provider.id,
            'label': 'New API Key',
            'key': 'sk-test-new-key-12345',
            'is_default': False,
            'is_active': True
        }
        
        response = self.admin_client.post(self.api_key_list_url, api_key_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        api_key_data['key'] = 'sk-test-member-key-12345'
        response = self.member_client.post(self.api_key_list_url, api_key_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Non-members should not be able to create API keys for other organizations
        api_key_data['key'] = 'sk-test-nonmember-key-12345'
        response = self.non_member_client.post(self.api_key_list_url, api_key_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Organization mismatch
        
        # Retrieve API key - only organization members should be able to retrieve their keys
        response = self.admin_client.get(self.api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.member_client.get(self.api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.non_member_client.get(self.api_key_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Should not see other organization's keys
        
        # Update API key - both admins and members should be able to update their keys
        api_key_data = {
            'provider': self.provider.id,
            'organization': self.organization.id,
            'label': 'Updated API Key',
            'key': 'sk-test-api-key-12345',
            'is_default': True,
            'is_active': True
        }
        
        response = self.admin_client.put(self.api_key_detail_url, api_key_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        api_key_data['label'] = 'Member Updated API Key'
        response = self.member_client.put(self.api_key_detail_url, api_key_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.non_member_client.put(self.api_key_detail_url, api_key_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Should not see other organization's keys

    def test_routing_rule_permissions(self):
        """Test permissions for routing rule endpoints."""
        # List routing rules - only organization members should see their organization's rules
        response = self.admin_client.get(self.routing_rule_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        response = self.member_client.get(self.routing_rule_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        response = self.non_member_client.get(self.routing_rule_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # Should not see other organization's rules
        
        # Create routing rule - only admins should be able to create
        rule_data = {
            'name': 'New Rule',
            'priority': 20,
            'model': self.model.id,
            'conditions': {
                'task_type': 'summarization',
                'min_tokens': 0,
                'max_tokens': 4000
            },
            'is_active': True
        }
        
        response = self.admin_client.post(self.routing_rule_list_url, rule_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response = self.member_client.post(self.routing_rule_list_url, rule_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.non_member_client.post(self.routing_rule_list_url, rule_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Organization mismatch
        
        # Retrieve routing rule - only organization members should be able to retrieve their rules
        response = self.admin_client.get(self.routing_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.member_client.get(self.routing_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.non_member_client.get(self.routing_rule_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Should not see other organization's rules
        
        # Update routing rule - only admins should be able to update
        rule_data = {
            'name': 'Updated Rule',
            'priority': 15,
            'model': self.model.id,
            'organization': self.organization.id,
            'conditions': {
                'task_type': 'general',
                'min_tokens': 0,
                'max_tokens': 5000
            },
            'is_active': True
        }
        
        response = self.admin_client.put(self.routing_rule_detail_url, rule_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.member_client.put(self.routing_rule_detail_url, rule_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = self.non_member_client.put(self.routing_rule_detail_url, rule_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Should not see other organization's rules

    def test_permission_classes(self):
        """Test the permission classes directly."""
        # Create mock request objects
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        admin_request = MockRequest(self.admin_user)
        member_request = MockRequest(self.member_user)
        non_member_request = MockRequest(self.non_member_user)
        
        # Test IsOrganizationMember permission
        is_org_member = IsOrganizationMember()
        self.assertTrue(is_org_member.has_permission(admin_request, None))
        self.assertTrue(is_org_member.has_permission(member_request, None))
        self.assertTrue(is_org_member.has_permission(non_member_request, None))  # Has permission for their org
        
        # Test IsOrganizationAdmin permission
        is_org_admin = IsOrganizationAdmin()
        self.assertTrue(is_org_admin.has_permission(admin_request, None))
        self.assertFalse(is_org_admin.has_permission(member_request, None))
        self.assertTrue(is_org_admin.has_permission(non_member_request, None))  # Admin in their org
        
        # Test object-level permissions
        class MockObject:
            def __init__(self, organization):
                self.organization = organization
        
        org_object = MockObject(self.organization)
        other_org_object = MockObject(self.other_organization)
        
        # IsOrganizationMember object-level permissions
        self.assertTrue(is_org_member.has_object_permission(admin_request, None, org_object))
        self.assertTrue(is_org_member.has_object_permission(member_request, None, org_object))
        self.assertFalse(is_org_member.has_object_permission(non_member_request, None, org_object))
        self.assertTrue(is_org_member.has_object_permission(non_member_request, None, other_org_object))
        
        # IsOrganizationAdmin object-level permissions
        self.assertTrue(is_org_admin.has_object_permission(admin_request, None, org_object))
        self.assertFalse(is_org_admin.has_object_permission(member_request, None, org_object))
        self.assertFalse(is_org_admin.has_object_permission(non_member_request, None, org_object))
        self.assertTrue(is_org_admin.has_object_permission(non_member_request, None, other_org_object))
