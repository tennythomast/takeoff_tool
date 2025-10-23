import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json
from django.test import TestCase

from modelhub.models import Provider, Model, APIKey, RoutingRule
from core.models import Organization, User
from modelhub.utils import (
    select_model_for_request,
    estimate_tokens,
    calculate_cost,
    get_available_models,
    validate_api_key,
    log_model_usage,
    format_prompt_template
)


class TestModelSelection(TestCase):
    """Test cases for model selection utilities."""

    def setUp(self):
        """Set up test data."""
        # Create organizations
        self.organization = Organization.objects.create(
            name='Test Organization',
            slug='test-org'
        )
        
        # Create user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword'
        )
        self.user.default_org = self.organization
        self.user.save()
        
        # Create providers
        self.provider1 = Provider.objects.create(
            name='Provider 1',
            slug='provider1',
            status='ACTIVE',
            config={'api_base': 'https://api.provider1.com'}
        )
        
        self.provider2 = Provider.objects.create(
            name='Provider 2',
            slug='provider2',
            status='ACTIVE',
            config={'api_base': 'https://api.provider2.com'}
        )
        
        # Create models
        self.text_model1 = Model.objects.create(
            provider=self.provider1,
            name='Text Model 1',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='ACTIVE',
            capabilities=['general', 'summarization']
        )
        
        self.text_model2 = Model.objects.create(
            provider=self.provider2,
            name='Text Model 2',
            model_type='TEXT',
            cost_input=Decimal('0.0015'),
            cost_output=Decimal('0.0025'),
            context_window=8192,
            status='ACTIVE',
            capabilities=['general', 'summarization', 'translation']
        )
        
        self.code_model = Model.objects.create(
            provider=self.provider1,
            name='Code Model',
            model_type='CODE',
            cost_input=Decimal('0.002'),
            cost_output=Decimal('0.003'),
            context_window=8192,
            status='ACTIVE',
            capabilities=['code_generation', 'code_explanation']
        )
        
        self.inactive_model = Model.objects.create(
            provider=self.provider1,
            name='Inactive Model',
            model_type='TEXT',
            cost_input=Decimal('0.001'),
            cost_output=Decimal('0.002'),
            context_window=4096,
            status='INACTIVE',
            capabilities=['general']
        )
        
        # Create API keys
        self.api_key1 = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider1,
            label='API Key 1',
            key='sk-test-key1',
            is_default=True,
            is_active=True
        )
        
        self.api_key2 = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider2,
            label='API Key 2',
            key='sk-test-key2',
            is_default=False,
            is_active=True
        )
        
        self.inactive_api_key = APIKey.objects.create(
            organization=self.organization,
            provider=self.provider1,
            label='Inactive API Key',
            key='sk-test-key-inactive',
            is_default=False,
            is_active=False
        )
        
        # Create routing rules
        self.routing_rule1 = RoutingRule.objects.create(
            organization=self.organization,
            name='Code Rule',
            priority=10,
            model=self.code_model,
            conditions={
                'task_type': 'code_generation',
                'min_tokens': 0,
                'max_tokens': 4000
            },
            is_active=True
        )
        
        self.routing_rule2 = RoutingRule.objects.create(
            organization=self.organization,
            name='Long Text Rule',
            priority=20,
            model=self.text_model2,
            conditions={
                'task_type': 'general',
                'min_tokens': 2000,
                'max_tokens': 8000
            },
            is_active=True
        )
        
        self.routing_rule3 = RoutingRule.objects.create(
            organization=self.organization,
            name='Default Text Rule',
            priority=30,
            model=self.text_model1,
            conditions={
                'task_type': 'general',
                'min_tokens': 0,
                'max_tokens': 4000
            },
            is_active=True
        )
        
        self.inactive_rule = RoutingRule.objects.create(
            organization=self.organization,
            name='Inactive Rule',
            priority=5,
            model=self.text_model1,
            conditions={
                'task_type': 'general',
                'min_tokens': 0,
                'max_tokens': 4000
            },
            is_active=False
        )

    @patch('modelhub.utils.estimate_tokens')
    def test_select_model_for_request(self, mock_estimate_tokens):
        """Test selecting a model based on request parameters and routing rules."""
        # Mock the token estimation
        mock_estimate_tokens.return_value = 1000
        
        # Test code generation request
        request_params = {
            'task_type': 'code_generation',
            'prompt': 'Write a Python function to calculate Fibonacci numbers'
        }
        selected_model, api_key = select_model_for_request(self.organization, request_params)
        self.assertEqual(selected_model, self.code_model)
        self.assertEqual(api_key, self.api_key1)
        
        # Test long text request
        mock_estimate_tokens.return_value = 3000
        request_params = {
            'task_type': 'general',
            'prompt': 'A very long text...'
        }
        selected_model, api_key = select_model_for_request(self.organization, request_params)
        self.assertEqual(selected_model, self.text_model2)
        self.assertEqual(api_key, self.api_key2)
        
        # Test default text request
        mock_estimate_tokens.return_value = 1000
        request_params = {
            'task_type': 'general',
            'prompt': 'A short text'
        }
        selected_model, api_key = select_model_for_request(self.organization, request_params)
        self.assertEqual(selected_model, self.text_model1)
        self.assertEqual(api_key, self.api_key1)
        
        # Test explicit model selection
        request_params = {
            'task_type': 'general',
            'prompt': 'A short text',
            'model_id': str(self.text_model2.id)
        }
        selected_model, api_key = select_model_for_request(self.organization, request_params)
        self.assertEqual(selected_model, self.text_model2)
        self.assertEqual(api_key, self.api_key2)
        
        # Test explicit API key selection
        request_params = {
            'task_type': 'general',
            'prompt': 'A short text',
            'api_key_id': str(self.api_key2.id)
        }
        selected_model, api_key = select_model_for_request(self.organization, request_params)
        self.assertEqual(selected_model, self.text_model1)  # Should still follow routing rules
        self.assertEqual(api_key, self.api_key2)  # But use the specified API key
        
        # Test no matching rules
        request_params = {
            'task_type': 'unknown_task',
            'prompt': 'A short text'
        }
        with self.assertRaises(ValueError):
            select_model_for_request(self.organization, request_params)
        
        # Test inactive model in rule
        self.routing_rule3.model = self.inactive_model
        self.routing_rule3.save()
        request_params = {
            'task_type': 'general',
            'prompt': 'A short text'
        }
        with self.assertRaises(ValueError):
            select_model_for_request(self.organization, request_params)
        
        # Reset for other tests
        self.routing_rule3.model = self.text_model1
        self.routing_rule3.save()

    def test_estimate_tokens(self):
        """Test token estimation for different text inputs."""
        # Test with a simple text
        text = "This is a simple text with about 10 tokens."
        tokens = estimate_tokens(text)
        self.assertGreater(tokens, 0)
        
        # Test with a longer text
        long_text = "This is a longer text " * 100
        long_tokens = estimate_tokens(long_text)
        self.assertGreater(long_tokens, tokens)
        
        # Test with empty text
        empty_tokens = estimate_tokens("")
        self.assertEqual(empty_tokens, 0)
        
        # Test with non-string input
        with self.assertRaises(TypeError):
            estimate_tokens(123)

    def test_calculate_cost(self):
        """Test cost calculation based on token counts and model rates."""
        # Test with text model 1
        cost = calculate_cost(self.text_model1, 1000, 500)
        expected_cost = (Decimal('0.001') * 1000 / 1000) + (Decimal('0.002') * 500 / 1000)
        self.assertEqual(cost, expected_cost)
        
        # Test with code model
        cost = calculate_cost(self.code_model, 2000, 1000)
        expected_cost = (Decimal('0.002') * 2000 / 1000) + (Decimal('0.003') * 1000 / 1000)
        self.assertEqual(cost, expected_cost)
        
        # Test with zero tokens
        cost = calculate_cost(self.text_model1, 0, 0)
        self.assertEqual(cost, Decimal('0'))
        
        # Test with non-model input
        with self.assertRaises(AttributeError):
            calculate_cost("not a model", 1000, 500)

    def test_get_available_models(self):
        """Test retrieving available models for an organization."""
        # Test getting all available models
        models = get_available_models(self.organization)
        self.assertEqual(len(models), 3)  # 3 active models
        self.assertIn(self.text_model1, models)
        self.assertIn(self.text_model2, models)
        self.assertIn(self.code_model, models)
        self.assertNotIn(self.inactive_model, models)
        
        # Test filtering by model type
        text_models = get_available_models(self.organization, model_type='TEXT')
        self.assertEqual(len(text_models), 2)  # 2 active text models
        self.assertIn(self.text_model1, text_models)
        self.assertIn(self.text_model2, text_models)
        self.assertNotIn(self.code_model, text_models)
        
        # Test filtering by capability
        translation_models = get_available_models(self.organization, capability='translation')
        self.assertEqual(len(translation_models), 1)
        self.assertIn(self.text_model2, translation_models)
        
        # Test filtering by provider
        provider1_models = get_available_models(self.organization, provider=self.provider1)
        self.assertEqual(len(provider1_models), 2)  # 2 active models from provider1
        self.assertIn(self.text_model1, provider1_models)
        self.assertIn(self.code_model, provider1_models)
        
        # Test with no active models
        Model.objects.update(status='INACTIVE')
        no_models = get_available_models(self.organization)
        self.assertEqual(len(no_models), 0)

    def test_validate_api_key(self):
        """Test API key validation."""
        # Test valid API key
        is_valid = validate_api_key(self.api_key1)
        self.assertTrue(is_valid)
        
        # Test inactive API key
        is_valid = validate_api_key(self.inactive_api_key)
        self.assertFalse(is_valid)
        
        # Test with invalid API key format
        with patch('modelhub.utils.validate_api_key_format') as mock_validate_format:
            mock_validate_format.return_value = False
            is_valid = validate_api_key(self.api_key1)
            self.assertFalse(is_valid)
        
        # Test with API key that doesn't belong to any provider
        self.api_key1.provider = None
        self.api_key1.save()
        is_valid = validate_api_key(self.api_key1)
        self.assertFalse(is_valid)
        
        # Reset for other tests
        self.api_key1.provider = self.provider1
        self.api_key1.save()

    @patch('modelhub.utils.ModelMetrics.objects.create')
    def test_log_model_usage(self, mock_create):
        """Test logging model usage."""
        # Test successful logging
        log_model_usage(
            model=self.text_model1,
            organization=self.organization,
            api_key=self.api_key1,
            tokens_input=1000,
            tokens_output=500,
            latency_ms=150,
            cost=Decimal('0.003'),
            status='SUCCESS'
        )
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs['model'], self.text_model1)
        self.assertEqual(call_kwargs['organization'], self.organization)
        self.assertEqual(call_kwargs['api_key'], self.api_key1)
        self.assertEqual(call_kwargs['tokens_input'], 1000)
        self.assertEqual(call_kwargs['tokens_output'], 500)
        self.assertEqual(call_kwargs['latency_ms'], 150)
        self.assertEqual(call_kwargs['cost'], Decimal('0.003'))
        self.assertEqual(call_kwargs['status'], 'SUCCESS')
        
        # Test logging with error
        mock_create.reset_mock()
        log_model_usage(
            model=self.text_model1,
            organization=self.organization,
            api_key=self.api_key1,
            tokens_input=0,
            tokens_output=0,
            latency_ms=50,
            cost=Decimal('0.000'),
            status='ERROR',
            error_type='RateLimitError',
            error_message='Rate limit exceeded'
        )
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs['status'], 'ERROR')
        self.assertEqual(call_kwargs['error_type'], 'RateLimitError')
        self.assertEqual(call_kwargs['error_message'], 'Rate limit exceeded')

    def test_format_prompt_template(self):
        """Test formatting prompt templates with variables."""
        # Test simple template
        template = "Hello, {name}!"
        variables = {'name': 'World'}
        formatted = format_prompt_template(template, variables)
        self.assertEqual(formatted, "Hello, World!")
        
        # Test template with multiple variables
        template = "Hello, {name}! Today is {day}."
        variables = {'name': 'World', 'day': 'Monday'}
        formatted = format_prompt_template(template, variables)
        self.assertEqual(formatted, "Hello, World! Today is Monday.")
        
        # Test template with missing variables
        template = "Hello, {name}! Today is {day}."
        variables = {'name': 'World'}
        with self.assertRaises(KeyError):
            format_prompt_template(template, variables)
        
        # Test template with default values
        template = "Hello, {name}! Today is {day:Tuesday}."
        variables = {'name': 'World'}
        formatted = format_prompt_template(template, variables, use_defaults=True)
        self.assertEqual(formatted, "Hello, World! Today is Tuesday.")
        
        # Test template with overridden default values
        template = "Hello, {name:User}! Today is {day:Tuesday}."
        variables = {'name': 'World', 'day': 'Monday'}
        formatted = format_prompt_template(template, variables, use_defaults=True)
        self.assertEqual(formatted, "Hello, World! Today is Monday.")
        
        # Test with non-string template
        with self.assertRaises(TypeError):
            format_prompt_template(123, {})


if __name__ == '__main__':
    unittest.main()
