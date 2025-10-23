from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from core.models import Organization, Workspace
from prompt.models import PromptSession
from modelhub.models import RoutingRule, Model, Provider
from .models import Agent, AgentTool, AgentParameter, AgentExecution
from .services import AgentService

User = get_user_model()


class AgentModelTest(TestCase):
    """Test the Agent model"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create test organization
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            creator=self.user
        )
        self.organization.members.add(self.user)
        
        # Create test workspace
        self.workspace = Workspace.objects.create(
            name='Test Workspace',
            description='A test workspace',
            organization=self.organization,
            creator=self.user
        )
        
        # Create test routing rule
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider'
        )
        
        self.model = Model.objects.create(
            name='Test Model',
            provider=self.provider,
            model_id='test-model',
            is_active=True
        )
        
        self.routing_rule = RoutingRule.objects.create(
            name='Test Rule',
            organization=self.organization,
            creator=self.user,
            is_active=True
        )
        
        # Create test prompt session
        self.prompt_session = PromptSession.objects.create(
            title='Test Session',
            workspace=self.workspace,
            creator=self.user,
            prompt='Test prompt'
        )
        
    def test_create_agent(self):
        """Test creating an agent"""
        agent = Agent.objects.create(
            name='Test Agent',
            description='A test agent',
            instructions='Do test things',
            organization=self.organization,
            workspace=self.workspace,
            creator=self.user,
            prompt_session=self.prompt_session,
            routing_rule=self.routing_rule
        )
        
        self.assertEqual(agent.name, 'Test Agent')
        self.assertEqual(agent.description, 'A test agent')
        self.assertEqual(agent.instructions, 'Do test things')
        self.assertEqual(agent.organization, self.organization)
        self.assertEqual(agent.workspace, self.workspace)
        self.assertEqual(agent.creator, self.user)
        self.assertEqual(agent.prompt_session, self.prompt_session)
        self.assertEqual(agent.routing_rule, self.routing_rule)
        self.assertEqual(agent.status, 'DRAFT')
        self.assertEqual(agent.category, 'GENERAL')
        self.assertFalse(agent.is_public)
        self.assertFalse(agent.is_template)
        
    def test_agent_tool(self):
        """Test creating an agent tool"""
        agent = Agent.objects.create(
            name='Test Agent',
            description='A test agent',
            instructions='Do test things',
            organization=self.organization,
            workspace=self.workspace,
            creator=self.user,
            prompt_session=self.prompt_session,
            routing_rule=self.routing_rule
        )
        
        tool = AgentTool.objects.create(
            agent=agent,
            name='Test Tool',
            description='A test tool',
            tool_type='API',
            configuration={'url': 'https://api.example.com'}
        )
        
        self.assertEqual(tool.agent, agent)
        self.assertEqual(tool.name, 'Test Tool')
        self.assertEqual(tool.description, 'A test tool')
        self.assertEqual(tool.tool_type, 'API')
        self.assertEqual(tool.configuration, {'url': 'https://api.example.com'})
        
    def test_agent_parameter(self):
        """Test creating an agent parameter"""
        agent = Agent.objects.create(
            name='Test Agent',
            description='A test agent',
            instructions='Do test things',
            organization=self.organization,
            workspace=self.workspace,
            creator=self.user,
            prompt_session=self.prompt_session,
            routing_rule=self.routing_rule
        )
        
        param = AgentParameter.objects.create(
            agent=agent,
            name='Test Param',
            description='A test parameter',
            param_type='STRING',
            default_value='default',
            is_required=True
        )
        
        self.assertEqual(param.agent, agent)
        self.assertEqual(param.name, 'Test Param')
        self.assertEqual(param.description, 'A test parameter')
        self.assertEqual(param.param_type, 'STRING')
        self.assertEqual(param.default_value, 'default')
        self.assertTrue(param.is_required)
        

class AgentServiceTest(TestCase):
    """Test the AgentService"""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create test organization
        self.organization = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            creator=self.user
        )
        self.organization.members.add(self.user)
        
        # Create test workspace
        self.workspace = Workspace.objects.create(
            name='Test Workspace',
            description='A test workspace',
            organization=self.organization,
            creator=self.user
        )
        
        # Create test routing rule
        self.provider = Provider.objects.create(
            name='Test Provider',
            slug='test-provider'
        )
        
        self.model = Model.objects.create(
            name='Test Model',
            provider=self.provider,
            model_id='test-model',
            is_active=True
        )
        
        self.routing_rule = RoutingRule.objects.create(
            name='Test Rule',
            organization=self.organization,
            creator=self.user,
            is_active=True
        )
        
        self.agent_service = AgentService()
        
    def test_create_agent(self):
        """Test creating an agent through the service"""
        agent = self.agent_service.create_agent(
            name='Service Agent',
            description='An agent created through the service',
            instructions='Do service things',
            organization=self.organization,
            workspace=self.workspace,
            creator=self.user,
            routing_rule=self.routing_rule
        )
        
        self.assertEqual(agent.name, 'Service Agent')
        self.assertEqual(agent.description, 'An agent created through the service')
        self.assertEqual(agent.instructions, 'Do service things')
        self.assertEqual(agent.organization, self.organization)
        self.assertEqual(agent.workspace, self.workspace)
        self.assertEqual(agent.creator, self.user)
        self.assertEqual(agent.routing_rule, self.routing_rule)
        self.assertIsNotNone(agent.prompt_session)
        
    def test_clone_agent(self):
        """Test cloning an agent through the service"""
        # Create an original agent
        original_agent = self.agent_service.create_agent(
            name='Original Agent',
            description='An original agent',
            instructions='Do original things',
            organization=self.organization,
            workspace=self.workspace,
            creator=self.user,
            routing_rule=self.routing_rule
        )
        
        # Create a tool for the original agent
        AgentTool.objects.create(
            agent=original_agent,
            name='Original Tool',
            description='An original tool',
            tool_type='API',
            configuration={'url': 'https://api.example.com'}
        )
        
        # Create a parameter for the original agent
        AgentParameter.objects.create(
            agent=original_agent,
            name='Original Param',
            description='An original parameter',
            param_type='STRING',
            default_value='original',
            is_required=True
        )
        
        # Create a new user to clone to
        new_user = User.objects.create_user(
            email='new@example.com',
            password='newpass123',
            first_name='New',
            last_name='User'
        )
        
        # Create a new organization
        new_organization = Organization.objects.create(
            name='New Org',
            slug='new-org',
            creator=new_user
        )
        new_organization.members.add(new_user)
        
        # Clone the agent
        cloned_agent = self.agent_service.clone_agent(
            agent=original_agent,
            new_creator=new_user,
            new_organization=new_organization,
            new_name='Cloned Agent'
        )
        
        self.assertEqual(cloned_agent.name, 'Cloned Agent')
        self.assertEqual(cloned_agent.description, original_agent.description)
        self.assertEqual(cloned_agent.instructions, original_agent.instructions)
        self.assertEqual(cloned_agent.organization, new_organization)
        self.assertEqual(cloned_agent.creator, new_user)
        self.assertEqual(cloned_agent.routing_rule, original_agent.routing_rule)
        self.assertIsNotNone(cloned_agent.prompt_session)
        self.assertNotEqual(cloned_agent.prompt_session, original_agent.prompt_session)
        
        # Check that tools were cloned
        self.assertEqual(cloned_agent.tools.count(), original_agent.tools.count())
        
        # Check that parameters were cloned
        self.assertEqual(cloned_agent.parameters.count(), original_agent.parameters.count())
