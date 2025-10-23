from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import User, Organization
from projects.models import Project
from ..models import PromptSession, Prompt, ModelExecutionLog


class PromptSessionViewSetTests(APITestCase):
    """Test cases for PromptSessionViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create users and their organizations
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.owner_org = Organization.objects.create(
            name='Owner Org',
            slug='owner-org',
            org_type=Organization.OrgType.SOLO
        )
        self.owner.default_org = self.owner_org
        self.owner.save()

        self.collaborator = User.objects.create_user(
            email='collaborator@example.com',
            password='testpass123'
        )
        self.collaborator_org = Organization.objects.create(
            name='Collaborator Org',
            slug='collaborator-org',
            org_type=Organization.OrgType.SOLO
        )
        self.collaborator.default_org = self.collaborator_org
        self.collaborator.save()

        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        self.other_org = Organization.objects.create(
            name='Other Org',
            slug='other-org',
            org_type=Organization.OrgType.SOLO
        )
        self.other_user.default_org = self.other_org
        self.other_user.save()

        # Create project
        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            owner=self.owner,
            organization=self.owner_org,
            is_active=True
        )
        self.project.collaborators.add(self.collaborator)
        
        # Create sessions
        self.session = PromptSession.objects.create(
            title='Test Session',
            description='Test Description',
            project=self.project,
            creator=self.owner,
            model_type=PromptSession.ModelType.TEXT,
            status=PromptSession.Status.DRAFT,
            prompt='Test prompt',
            is_active=True,
            cost=Decimal('0.00')
        )
        
        # URLs
        self.list_url = f'/api/v1/projects/{self.project.pk}/prompt-sessions/'
        self.detail_url = f'/api/v1/projects/{self.project.pk}/prompt-sessions/{self.session.pk}/'
        
        # Authenticate
        self.client.force_authenticate(user=self.owner)
    
    def test_list_sessions(self):
        """Test listing prompt sessions."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Test Session')
    
    def test_create_session(self):
        """Test creating a prompt session."""
        data = {
            'title': 'New Session',
            'description': 'New Description',
            'project': self.project.pk,
            'model_type': PromptSession.ModelType.TEXT,
            'prompt': 'New prompt'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PromptSession.objects.count(), 2)
        self.assertEqual(response.data['title'], 'New Session')
    
    def test_retrieve_session(self):
        """Test retrieving a prompt session."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Session')
    
    def test_update_session(self):
        """Test updating a prompt session."""
        data = {
            'title': 'Updated Session',
            'description': 'Updated Description',
            'project': self.project.pk,
            'model_type': PromptSession.ModelType.TEXT,
            'prompt': 'Updated prompt'
        }
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Session')
    
    def test_delete_session(self):
        """Test deleting a prompt session."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PromptSession.objects.filter(is_active=True).count(), 0)
    
    def test_collaborator_access(self):
        """Test collaborator access to prompt sessions."""
        self.client.force_authenticate(user=self.collaborator)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_other_user_no_access(self):
        """Test that other users cannot access prompt sessions."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class PromptViewSetTests(APITestCase):
    """Test cases for PromptViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create user and organization
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.owner_org = Organization.objects.create(
            name='Owner Org',
            slug='owner-org',
            org_type=Organization.OrgType.SOLO
        )
        self.owner.default_org = self.owner_org
        self.owner.save()
        
        # Create project and session
        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            owner=self.owner,
            organization=self.owner_org,
            is_active=True
        )
        self.session = PromptSession.objects.create(
            title='Test Session',
            description='Test Description',
            project=self.project,
            creator=self.owner,
            model_type=PromptSession.ModelType.TEXT,
            status=PromptSession.Status.DRAFT,
            prompt='Test prompt',
            is_active=True
        )
        
        # Create prompt
        self.prompt = Prompt.objects.create(
            session=self.session,
            user=self.owner,
            input_text='Test input',
            is_active=True
        )
        
        # URLs
        self.list_url = f'/api/v1/projects/{self.project.pk}/prompt-sessions/{self.session.pk}/prompts/'
        self.detail_url = f'/api/v1/projects/{self.project.pk}/prompt-sessions/{self.session.pk}/prompts/{self.prompt.pk}/'
        self.execute_url = f'/api/v1/projects/{self.project.pk}/prompt-sessions/{self.session.pk}/prompts/{self.prompt.pk}/execute/'
        
        # Authenticate
        self.client.force_authenticate(user=self.owner)
    
    def test_list_prompts(self):
        """Test listing prompts."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['input_text'], 'Test input')
    
    def test_create_prompt(self):
        """Test creating a prompt."""
        data = {
            'input_text': 'New input',
            'context': {'key': 'value'},
            'metadata': {'tag': 'test'}
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Prompt.objects.count(), 2)
        self.assertEqual(response.data['input_text'], 'New input')
    
    def test_execute_prompt(self):
        """Test executing a prompt."""
        data = {
            'model_name': 'gpt-4',
            'provider': ModelExecutionLog.Provider.OPENAI
        }
        response = self.client.post(self.execute_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ModelExecutionLog.objects.count(), 1)
        self.assertEqual(
            ModelExecutionLog.objects.first().status,
            ModelExecutionLog.Status.SUCCESS
        )
    
    def test_execute_prompt_wrong_model_type(self):
        """Test executing a prompt with wrong model type."""
        # Change session type to IMAGE
        self.session.model_type = PromptSession.ModelType.IMAGE
        self.session.save()
        
        data = {
            'model_name': 'gpt-4',  # Text model for image session
            'provider': ModelExecutionLog.Provider.OPENAI
        }
        response = self.client.post(self.execute_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ModelExecutionLogViewSetTests(APITestCase):
    """Test cases for ModelExecutionLogViewSet."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create user and organization
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.owner_org = Organization.objects.create(
            name='Owner Org',
            slug='owner-org',
            org_type=Organization.OrgType.SOLO
        )
        self.owner.default_org = self.owner_org
        self.owner.save()
        
        # Create project, session, and prompt
        self.project = Project.objects.create(
            name='Test Project',
            description='Test Description',
            owner=self.owner,
            organization=self.owner_org,
            is_active=True
        )
        self.session = PromptSession.objects.create(
            title='Test Session',
            description='Test Description',
            project=self.project,
            creator=self.owner,
            model_type=PromptSession.ModelType.TEXT,
            status=PromptSession.Status.DRAFT,
            prompt='Test prompt',
            is_active=True
        )
        self.prompt = Prompt.objects.create(
            session=self.session,
            user=self.owner,
            input_text='Test input',
            is_active=True
        )
        
        # Create execution log
        self.execution = ModelExecutionLog.objects.create(
            prompt=self.prompt,
            model_name='gpt-4',
            provider=ModelExecutionLog.Provider.OPENAI,
            response_type=ModelExecutionLog.ResponseType.TEXT,
            output={'text': 'Test output'},
            token_input=10,
            token_output=20,
            cost_usd=Decimal('0.001'),
            latency_ms=100,
            status=ModelExecutionLog.Status.SUCCESS,
            is_active=True
        )
        
        # URLs
        self.list_url = f'/api/v1/projects/{self.project.pk}/prompt-sessions/{self.session.pk}/prompts/{self.prompt.pk}/executions/'
        self.detail_url = f'/api/v1/projects/{self.project.pk}/prompt-sessions/{self.session.pk}/prompts/{self.prompt.pk}/executions/{self.execution.pk}/'
        
        # Authenticate
        self.client.force_authenticate(user=self.owner)
    
    def test_list_executions(self):
        """Test listing execution logs."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['model_name'], 'gpt-4')
    
    def test_create_execution(self):
        """Test creating an execution log."""
        data = {
            'model_name': 'gpt-3.5-turbo',
            'provider': ModelExecutionLog.Provider.OPENAI
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ModelExecutionLog.objects.count(), 2)
        self.assertEqual(response.data['model_name'], 'gpt-3.5-turbo')
    
    def test_retrieve_execution(self):
        """Test retrieving an execution log."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['model_name'], 'gpt-4')
        self.assertEqual(response.data['status'], ModelExecutionLog.Status.SUCCESS)
