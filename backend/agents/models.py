from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel, SoftDeletableMixin, SoftDeletableManager


class Agent(SoftDeletableMixin, BaseModel):
    """Model for AI agents that can be configured and executed."""
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active')
        PAUSED = 'PAUSED', _('Paused')
        ARCHIVED = 'ARCHIVED', _('Archived')
    
    class Category(models.TextChoices):
        PRODUCTIVITY = 'PRODUCTIVITY', _('Productivity')
        ANALYSIS = 'ANALYSIS', _('Analysis')
        COMPLIANCE = 'COMPLIANCE', _('Compliance')
        RESEARCH = 'RESEARCH', _('Research')
        CUSTOMER_SERVICE = 'CUSTOMER_SERVICE', _('Customer Service')
        DEVELOPMENT = 'DEVELOPMENT', _('Development')
        GENERAL = 'GENERAL', _('General')
        
    class CommunicationStyle(models.TextChoices):
        PROFESSIONAL = 'PROFESSIONAL', _('Professional')
        FRIENDLY = 'FRIENDLY', _('Friendly')
        TECHNICAL = 'TECHNICAL', _('Technical')
        CONCISE = 'CONCISE', _('Concise')
        CONVERSATIONAL = 'CONVERSATIONAL', _('Conversational')
        
    class OutputFormat(models.TextChoices):
        FREE_TEXT = 'FREE_TEXT', _('Free Text')
        STRUCTURED = 'STRUCTURED', _('Structured')
        MARKDOWN = 'MARKDOWN', _('Markdown')
        JSON = 'JSON', _('JSON')
        HTML = 'HTML', _('HTML')
    
    class MemoryType(models.TextChoices):
        NONE = 'NONE', _('No Memory')
        SHORT_TERM = 'SHORT_TERM', _('Short-term Memory')
        LONG_TERM = 'LONG_TERM', _('Long-term Memory')
        HYBRID = 'HYBRID', _('Hybrid Memory')
        
    class CapabilityLevel(models.TextChoices):
        BASIC = 'BASIC', _('Basic')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermediate')
        ADVANCED = 'ADVANCED', _('Advanced')
        EXPERT = 'EXPERT', _('Expert')
    
    name = models.CharField(_('name'), max_length=255, db_index=True)
    description = models.TextField(_('description'), blank=True)
    instructions = models.TextField(_('instructions'), help_text=_('System instructions for the agent'))
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GENERAL,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    icon = models.CharField(max_length=50, default='bot', help_text=_('Icon identifier'))
    routing_rule = models.ForeignKey(
        'modelhub.RoutingRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        help_text=_('LLM routing rule to determine which model to use')
    )
    prompt_session = models.ForeignKey(
        'prompt.PromptSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents',
        help_text=_('Associated prompt session for this agent')
    )
    creator = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='created_agents',
        verbose_name=_('creator')
    )
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='agents',
        verbose_name=_('organization')
    )
    
    # Smart configuration fields
    primary_role = models.CharField(
        max_length=255, 
        blank=True,
        help_text=_('Primary role of this agent (e.g., "Customer Support Assistant")')
    )
    target_users = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of target user types for this agent')
    )
    problem_statement = models.TextField(
        blank=True,
        help_text=_('Clear statement of the problem this agent solves')
    )
    communication_style = models.CharField(
        max_length=20,
        choices=CommunicationStyle.choices,
        default=CommunicationStyle.PROFESSIONAL,
        help_text=_('Preferred communication style for this agent')
    )
    output_format = models.CharField(
        max_length=20,
        choices=OutputFormat.choices,
        default=OutputFormat.MARKDOWN,
        help_text=_('Preferred output format for this agent')
    )
    quality_preference = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text=_('Quality preference: 1=Speed, 2=Balanced, 3=Quality')
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='agents',
        verbose_name=_('workspace'),
        null=True,
        blank=True
    )
    is_public = models.BooleanField(
        default=False,
        help_text=_('Whether this agent can be cloned by other users')
    )
    is_template = models.BooleanField(
        default=False,
        help_text=_('Whether this agent serves as a template for new agents')
    )
    parent_agent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_agents',
        help_text=_('Original agent this was cloned from')
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional configuration options')
    )
    
    # Smart configuration fields
    primary_role = models.CharField(
        max_length=50,
        choices=[
            ('ANALYZER', _('Analyzer')),
            ('ASSISTANT', _('Assistant')),
            ('CLASSIFIER', _('Classifier')),
            ('GENERATOR', _('Generator')),
            ('MONITOR', _('Monitor')),
            ('CUSTOM', _('Custom')),
        ],
        default='ASSISTANT',
        help_text=_('Primary role for AI-generated instructions')
    )
    
    target_users = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Target user types for this agent (e.g., ["workspace Managers", "Developers"])')
    )
    
    problem_statement = models.TextField(
        blank=True,
        help_text=_('Specific problem this agent solves - used for instruction generation')
    )
    
    communication_style = models.CharField(
        max_length=20,
        choices=[
            ('PROFESSIONAL', _('Professional')),
            ('FRIENDLY', _('Friendly')),
            ('TECHNICAL', _('Technical')),
            ('CONCISE', _('Concise')),
        ],
        default='PROFESSIONAL',
        help_text=_('Communication style for responses')
    )
    
    output_format = models.CharField(
        max_length=30,
        choices=[
            ('STRUCTURED_SUMMARY', _('Structured Summary')),
            ('BULLET_POINTS', _('Bullet Points')),
            ('DETAILED_REPORT', _('Detailed Report')),
            ('JSON_FORMAT', _('JSON Format')),
            ('MARKDOWN', _('Markdown Document')),
        ],
        default='STRUCTURED_SUMMARY',
        help_text=_('Preferred output format')
    )
    
    quality_preference = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text=_('Quality vs Speed preference: 1=Fast, 2=Balanced, 3=Quality')
    )
    
    # Performance prediction fields
    predicted_accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text=_('AI-predicted accuracy percentage')
    )
    
    predicted_response_time = models.FloatField(
        null=True,
        blank=True,
        help_text=_('AI-predicted average response time in seconds')
    )
    
    predicted_cost_per_1k = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('AI-predicted cost per 1000 executions')
    )
    
    # Capability settings
    capabilities = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Specific capabilities this agent has (e.g., code generation, data analysis)')
    )
    
    capability_level = models.CharField(
        max_length=20,
        choices=CapabilityLevel.choices,
        default=CapabilityLevel.BASIC,
        help_text=_('Overall capability level of this agent')
    )
    
    # Memory settings
    memory_type = models.CharField(
        max_length=20,
        choices=MemoryType.choices,
        default=MemoryType.SHORT_TERM,
        help_text=_('Type of memory this agent uses')
    )
    
    memory_window = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Number of previous interactions to remember (0-100)')
    )
    
    memory_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional memory configuration options')
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Metadata about agent usage and performance')
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('agent')
        verbose_name_plural = _('agents')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['is_public']),
            models.Index(fields=['is_template']),
        ]
    
    def __str__(self):
        return self.name
    
    def clone(self, new_creator, new_organization, new_workspace=None, new_name=None):
        """Create a copy of this agent for another user
        
        Args:
            new_creator (User): The user who will own the cloned agent
            new_organization (Organization): The organization the cloned agent will belong to
            new_workspace (Workspace, optional): The workspace the cloned agent will belong to. Defaults to None.
            new_name (str, optional): A new name for the cloned agent. Defaults to None.
            
        Returns:
            Agent: The newly created agent clone
        """
        from prompt.models import PromptSession
        
        # Create a new prompt session for the clone
        new_prompt_session = None
        if self.prompt_session:
            new_prompt_session = PromptSession.objects.create(
                title=new_name or f"Clone of {self.name}",
                description=self.prompt_session.description,
                workspace=new_workspace or self.workspace,
                creator=new_creator,
                prompt=self.prompt_session.prompt,
                context=self.prompt_session.context.copy() if self.prompt_session.context else {},
                metadata=self.prompt_session.metadata.copy() if self.prompt_session.metadata else {}
            )
            
            # Copy system prompt if it exists
            system_prompt = self.prompt_session.prompts.filter(metadata__role='system').first()
            if system_prompt:
                from prompt.models import Prompt
                Prompt.objects.create(
                    session=new_prompt_session,
                    input_text=system_prompt.input_text,
                    user=new_creator,
                    metadata={'role': 'system'}
                )
        
        # Create the cloned agent
        clone = Agent.objects.create(
            name=new_name or f"Clone of {self.name}",
            description=self.description,
            instructions=self.instructions,
            organization=new_organization,
            workspace=new_workspace or self.workspace,
            creator=new_creator,
            prompt_session=new_prompt_session,
            routing_rule=self.routing_rule,
            category=self.category,
            status='DRAFT',  # Always start as draft
            is_public=False,  # Always start as private
            is_template=False,  # Never clone as template
            metadata=self.metadata.copy() if self.metadata else {},
            # Copy smart configuration fields
            primary_role=self.primary_role,
            target_users=self.target_users.copy() if self.target_users else [],
            problem_statement=self.problem_statement,
            communication_style=self.communication_style,
            output_format=self.output_format,
            quality_preference=self.quality_preference,
            # Copy capability settings
            capabilities=self.capabilities.copy() if self.capabilities else {},
            capability_level=self.capability_level,
            # Copy memory settings
            memory_type=self.memory_type,
            memory_window=self.memory_window,
            memory_config=self.memory_config.copy() if self.memory_config else {},
            # Reset performance prediction fields
            predicted_accuracy=None,
            predicted_response_time=None,
            predicted_cost_per_1k=None
        )
        
        # Clone all tools
        for tool in self.tools.all():
            AgentTool.objects.create(
                agent=clone,
                name=tool.name,
                description=tool.description,
                tool_type=tool.tool_type,
                configuration=tool.configuration.copy() if tool.configuration else {},
                metadata=tool.metadata.copy() if tool.metadata else {}
            )
        
        # Clone all parameters
        for param in self.parameters.all():
            AgentParameter.objects.create(
                agent=clone,
                name=param.name,
                description=param.description,
                param_type=param.param_type,
                default_value=param.default_value,
                is_required=param.is_required,
                validation_rules=param.validation_rules.copy() if param.validation_rules else {},
                metadata=param.metadata.copy() if param.metadata else {}
            )
        
        return clone
    
    def get_execution_count(self):
        """Get the number of times this agent has been executed"""
        return self.executions.count()
    
    def get_average_execution_time(self):
        """Get the average execution time in seconds"""
        executions = self.executions.filter(status='COMPLETED')
        if not executions.exists():
            return 0
        
        # Calculate average execution time
        total_time = 0
        count = 0
        
        for execution in executions:
            if execution.started_at and execution.completed_at:
                duration = (execution.completed_at - execution.started_at).total_seconds()
                total_time += duration
                count += 1
                
        if count == 0:
            return 0
            
        return total_time / count
        
    def get_success_rate(self):
        """Calculate success rate percentage"""
        total = self.executions.count()
        if total == 0:
            return 0
        successful = self.executions.filter(status='COMPLETED').count()
        return (successful / total) * 100
    
    def get_average_cost(self):
        """Get average cost per execution"""
        executions = self.executions.filter(status='COMPLETED')
        if not executions.exists():
            return 0
        return executions.aggregate(avg_cost=models.Avg('cost'))['avg_cost'] or 0
    
    def get_config(self):
        """Get agent configuration"""
        return self.config or {}
        
    def generate_instructions_from_config(self):
        """Generate optimized instructions based on smart config"""
        from modelhub.services import ModelHubService
        
        # Skip if required fields are not filled
        if not self.primary_role or not self.problem_statement:
            return None
            
        # Get available tools
        tool_names = list(self.tools.values_list('name', flat=True))
        
        # Format target users as comma-separated string
        target_users_str = ', '.join(self.target_users) if self.target_users else 'All users'
        
        generation_prompt = f"""
        Generate optimized AI agent instructions based on this configuration:
        
        Role: {self.primary_role}
        Target Users: {target_users_str}
        Problem Statement: {self.problem_statement}
        Communication Style: {self.get_communication_style_display()}
        Output Format: {self.get_output_format_display()}
        Quality Preference: {self.quality_preference}/3
        
        Available Tools: {tool_names}
        
        Generate clear, specific instructions that:
        1. Define the agent's role and personality
        2. Specify how to use available tools
        3. Set output formatting rules
        4. Include error handling guidance
        5. Match the communication style
        
        Make instructions concise but complete (max 300 words).
        """
        
        # Use modelhub to generate instructions
        modelhub_service = ModelHubService()
        
        # Select model based on quality preference
        model_preference = 'fast'
        if self.quality_preference == 3:
            model_preference = 'smart'
        elif self.quality_preference == 2:
            model_preference = 'balanced'
            
        response = modelhub_service.generate_text(
            prompt=generation_prompt,
            model_preference=model_preference,
            max_tokens=600
        )
        
        # Update the instructions field
        if response and hasattr(response, 'content'):
            return response.content
            
        return None
    
    def update_performance_predictions(self):
        """Update AI predictions based on actual performance"""
        if self.executions.filter(status='COMPLETED').count() >= 10:
            # Update predictions based on actual data
            self.predicted_accuracy = self.get_success_rate()
            self.predicted_response_time = self.get_average_execution_time()
            self.predicted_cost_per_1k = self.get_average_cost() * 1000
            self.save()
    
    def generate_optimization_suggestions(self):
        """Generate AI-powered optimization suggestions"""
        # This would integrate with your AI system to analyze
        # performance and suggest improvements
        pass


class AgentTool(BaseModel):
    """Tools that can be used by agents"""
    class ToolType(models.TextChoices):
        API = 'API', _('API')
        WEBHOOK = 'WEBHOOK', _('Webhook')
        DATABASE = 'DATABASE', _('Database')
        FILE = 'FILE', _('File')
        FUNCTION = 'FUNCTION', _('Function')
        OTHER = 'OTHER', _('Other')
    
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='tools',
        verbose_name=_('agent')
    )
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    tool_type = models.CharField(
        _('tool type'),
        max_length=50,
        choices=ToolType.choices,
        default=ToolType.FUNCTION
    )
    config = models.JSONField(_('configuration'), default=dict, blank=True)
    is_required = models.BooleanField(_('required'), default=False)
    
    # Webhook specific fields
    webhook_url = models.URLField(_('webhook URL'), blank=True, null=True, 
                               help_text=_('URL to call when executing this tool'))
    webhook_method = models.CharField(
        _('webhook method'),
        max_length=10,
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('PATCH', 'PATCH'),
            ('DELETE', 'DELETE')
        ],
        default='POST',
        blank=True,
        null=True
    )
    webhook_headers = models.JSONField(
        _('webhook headers'),
        default=dict,
        blank=True,
        help_text=_('Headers to send with webhook request')
    )
    webhook_auth_type = models.CharField(
        _('webhook authentication type'),
        max_length=20,
        choices=[
            ('NONE', _('None')),
            ('BASIC', _('Basic Auth')),
            ('BEARER', _('Bearer Token')),
            ('API_KEY', _('API Key')),
            ('CUSTOM', _('Custom'))
        ],
        default='NONE',
        blank=True
    )
    webhook_auth_config = models.JSONField(
        _('webhook authentication config'),
        default=dict,
        blank=True,
        help_text=_('Authentication configuration for webhook')
    )
    
    # Tool schema for validation
    input_schema = models.JSONField(
        _('input schema'),
        default=dict,
        blank=True,
        help_text=_('JSON Schema for tool input validation')
    )
    output_schema = models.JSONField(
        _('output schema'),
        default=dict,
        blank=True,
        help_text=_('JSON Schema for tool output validation')
    )
    
    # Smart recommendation fields
    match_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('AI-calculated match percentage for agent use case')
    )
    
    performance_impact = models.CharField(
        max_length=20,
        choices=[
            ('HIGH', _('High Impact')),
            ('MEDIUM', _('Medium Impact')),
            ('LOW', _('Low Impact')),
        ],
        default='MEDIUM',
        help_text=_('Expected performance impact')
    )
    
    recommendation_reason = models.TextField(
        blank=True,
        help_text=_('AI-generated reason for recommending this tool')
    )
    
    class Meta:
        verbose_name = _('agent tool')
        verbose_name_plural = _('agent tools')
        unique_together = ('agent', 'name')
    
    def __str__(self):
        return f"{self.agent.name} - {self.name}"
    
    def execute_tool(self, input_data):
        """
        Execute this tool with the given input data
        
        Args:
            input_data (dict): Input data for the tool
            
        Returns:
            dict: Tool execution result
        """
        import requests
        import json
        import logging
        import jsonschema
        from django.conf import settings
        
        logger = logging.getLogger(__name__)
        
        # Validate input against schema if provided
        if self.input_schema:
            try:
                jsonschema.validate(instance=input_data, schema=self.input_schema)
            except jsonschema.exceptions.ValidationError as e:
                logger.error(f"Tool input validation failed: {str(e)}")
                return {
                    'status': 'error',
                    'error': f"Input validation failed: {str(e)}",
                    'code': 'VALIDATION_ERROR'
                }
        
        # Execute tool based on type
        try:
            if self.tool_type == self.ToolType.WEBHOOK:
                return self._execute_webhook(input_data)
            elif self.tool_type == self.ToolType.API:
                return self._execute_api(input_data)
            elif self.tool_type == self.ToolType.FUNCTION:
                return self._execute_function(input_data)
            else:
                return {
                    'status': 'error',
                    'error': f"Tool type {self.tool_type} not implemented",
                    'code': 'NOT_IMPLEMENTED'
                }
        except Exception as e:
            logger.exception(f"Error executing tool {self.name}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'code': 'EXECUTION_ERROR'
            }
    
    def _execute_webhook(self, input_data):
        """
        Execute a webhook tool
        
        Args:
            input_data (dict): Input data for the webhook
            
        Returns:
            dict: Webhook response
        """
        import requests
        import json
        
        if not self.webhook_url:
            raise ValueError("Webhook URL not configured for this tool")
        
        # Prepare headers
        headers = self.webhook_headers.copy() if self.webhook_headers else {}
        
        # Add authentication if configured
        if self.webhook_auth_type == 'BASIC':
            import base64
            auth_config = self.webhook_auth_config or {}
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers['Authorization'] = f"Basic {encoded_auth}"
        elif self.webhook_auth_type == 'BEARER':
            auth_config = self.webhook_auth_config or {}
            token = auth_config.get('token', '')
            headers['Authorization'] = f"Bearer {token}"
        elif self.webhook_auth_type == 'API_KEY':
            auth_config = self.webhook_auth_config or {}
            key_name = auth_config.get('key_name', 'api_key')
            key_value = auth_config.get('key_value', '')
            key_location = auth_config.get('key_location', 'header')
            
            if key_location == 'header':
                headers[key_name] = key_value
            # For query params, we'll handle in the request itself
        
        # Default to JSON content type if not specified
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        # Prepare request
        method = self.webhook_method or 'POST'
        url = self.webhook_url
        
        # Handle API key in query params
        if self.webhook_auth_type == 'API_KEY':
            auth_config = self.webhook_auth_config or {}
            key_location = auth_config.get('key_location', 'header')
            if key_location == 'query':
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                parsed_url = urlparse(url)
                params = parse_qs(parsed_url.query)
                params[auth_config.get('key_name', 'api_key')] = [auth_config.get('key_value', '')]
                parsed_url = parsed_url._replace(query=urlencode(params, doseq=True))
                url = urlunparse(parsed_url)
        
        # Execute request based on method
        response = None
        if method == 'GET':
            # For GET, convert input_data to query params
            response = requests.get(url, params=input_data, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=input_data, headers=headers)
        elif method == 'PUT':
            response = requests.put(url, json=input_data, headers=headers)
        elif method == 'PATCH':
            response = requests.patch(url, json=input_data, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, json=input_data, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Process response
        try:
            response_data = response.json()
        except ValueError:
            # Not JSON, return text
            response_data = {'text': response.text}
        
        result = {
            'status': 'success' if response.ok else 'error',
            'status_code': response.status_code,
            'data': response_data
        }
        
        # Validate output against schema if provided
        if self.output_schema and response.ok:
            try:
                import jsonschema
                jsonschema.validate(instance=response_data, schema=self.output_schema)
            except jsonschema.exceptions.ValidationError as e:
                result['status'] = 'warning'
                result['validation_error'] = str(e)
        
        return result
    
    def _execute_api(self, input_data):
        """
        Execute an API tool (similar to webhook but with more configuration)
        
        Args:
            input_data (dict): Input data for the API
            
        Returns:
            dict: API response
        """
        # For now, API tools use the same implementation as webhooks
        return self._execute_webhook(input_data)
    
    def _execute_function(self, input_data):
        """
        Execute a function tool
        
        Args:
            input_data (dict): Input data for the function
            
        Returns:
            dict: Function result
        """
        # Function tools are defined in the config
        function_config = self.config or {}
        function_type = function_config.get('function_type', 'python_code')
        
        if function_type == 'python_code':
            # Execute Python code (with appropriate sandboxing)
            # This is a simplified implementation - in production you would want
            # much more robust sandboxing and security measures
            try:
                code = function_config.get('code', '')
                if not code:
                    return {
                        'status': 'error',
                        'error': 'No code provided for function tool',
                        'code': 'NO_CODE'
                    }
                
                # Create a restricted globals dictionary
                restricted_globals = {
                    '__builtins__': {
                        'abs': abs, 'all': all, 'any': any, 'bool': bool,
                        'dict': dict, 'float': float, 'int': int, 'len': len,
                        'list': list, 'max': max, 'min': min, 'range': range,
                        'round': round, 'sorted': sorted, 'str': str, 'sum': sum,
                        'tuple': tuple, 'type': type,
                        # Add other safe builtins as needed
                    }
                }
                
                # Create locals with input data
                locals_dict = {'input': input_data, 'result': None}
                
                # Execute the code
                exec(code, restricted_globals, locals_dict)
                
                # Get the result
                result = locals_dict.get('result')
                
                return {
                    'status': 'success',
                    'data': result
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'error': f"Function execution error: {str(e)}",
                    'code': 'EXECUTION_ERROR'
                }
        else:
            return {
                'status': 'error',
                'error': f"Function type {function_type} not supported",
                'code': 'UNSUPPORTED_FUNCTION_TYPE'
            }
    
    def get_tool_definition(self):
        """
        Get the tool definition in a format suitable for LLM function calling
        
        Returns:
            dict: Tool definition for LLM
        """
        return {
            'name': self.name,
            'description': self.description,
            'parameters': self.input_schema or {
                'type': 'object',
                'properties': {}
            }
        }


class AgentParameter(BaseModel):
    """Configurable parameters for agents"""
    class ParameterType(models.TextChoices):
        STRING = 'STRING', _('String')
        NUMBER = 'NUMBER', _('Number')
        BOOLEAN = 'BOOLEAN', _('Boolean')
        ENUM = 'ENUM', _('Enumeration')
        JSON = 'JSON', _('JSON')
    
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='parameters',
        verbose_name=_('agent')
    )
    name = models.CharField(_('name'), max_length=255)
    description = models.TextField(_('description'))
    parameter_type = models.CharField(
        max_length=20,
        choices=ParameterType.choices,
        default=ParameterType.STRING
    )
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text=_('Default value for this parameter')
    )
    is_required = models.BooleanField(
        default=False,
        help_text=_('Whether this parameter is required')
    )
    options = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Available options for ENUM type parameters')
    )
    validation = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Validation rules for this parameter')
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = _('agent parameter')
        verbose_name_plural = _('agent parameters')
        unique_together = ['agent', 'name']
    
    def __str__(self):
        return f"{self.agent.name} - {self.name}"


class AgentConfigurationStep(BaseModel):
    """Track completion of configuration wizard steps"""
    agent = models.OneToOneField(
        Agent,
        on_delete=models.CASCADE,
        related_name='config_progress'
    )
    
    step_1_completed = models.BooleanField(default=False)  # Purpose & Role
    step_2_completed = models.BooleanField(default=False)  # Intelligence & Tools  
    step_3_completed = models.BooleanField(default=False)  # Behavior & Rules
    step_4_completed = models.BooleanField(default=False)  # Performance & Testing
    
    wizard_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('agent configuration step')
        verbose_name_plural = _('agent configuration steps')
        
    def __str__(self):
        return f"Configuration progress for {self.agent.name}"
        
    def update_completion_status(self):
        """Update the wizard_completed flag based on step completion"""
        if all([self.step_1_completed, self.step_2_completed, 
                self.step_3_completed, self.step_4_completed]):
            self.wizard_completed = True
            self.completed_at = timezone.now()
        else:
            self.wizard_completed = False
            self.completed_at = None
        self.save()


class AgentOptimization(BaseModel):
    """Track optimization suggestions and their impacts"""
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='optimizations'
    )
    
    suggestion_type = models.CharField(
        max_length=50,
        choices=[
            ('TOOL_ADDITION', _('Add Tool')),
            ('MODEL_ROUTING', _('Improve Routing')),
            ('PROMPT_OPTIMIZATION', _('Optimize Prompt')),
            ('CACHING', _('Enable Caching')),
        ]
    )
    
    suggestion_text = models.TextField()
    estimated_impact = models.CharField(max_length=100)  # e.g., "+5% accuracy"
    applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    
    # Track actual impact after application
    actual_impact = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('agent optimization')
        verbose_name_plural = _('agent optimizations')
        
    def __str__(self):
        return f"{self.get_suggestion_type_display()} for {self.agent.name}"
        
    def apply_optimization(self):
        """Mark this optimization as applied"""
        self.applied = True
        self.applied_at = timezone.now()
        self.save()


class AgentExecution(BaseModel):
    """Record of agent execution instances"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        RUNNING = 'RUNNING', _('Running')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    agent = models.ForeignKey(
        Agent,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name=_('agent')
    )
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='agent_executions',
        verbose_name=_('user')
    )
    prompt_session = models.ForeignKey(
        'prompt.PromptSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_executions',
        help_text=_('Associated prompt session for this execution')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    execution_time = models.FloatField(
        null=True,
        blank=True,
        help_text=_('Execution time in seconds')
    )
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Input data for this execution')
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Output data from this execution')
    )
    error_message = models.TextField(blank=True)
    model_used = models.ForeignKey(
        'modelhub.Model',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_executions',
        help_text=_('The LLM model used for this execution')
    )
    tokens_used = models.IntegerField(default=0)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        help_text=_('Cost of this execution in USD')
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('agent execution')
        verbose_name_plural = _('agent executions')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
        ]
        
    def __str__(self):
        return f"{self.agent.name} execution {self.id} - {self.created_at}"


class AgentToolExecution(BaseModel):
    """Records of agent tool executions"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        RUNNING = 'RUNNING', _('Running')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
    
    agent_execution = models.ForeignKey(
        AgentExecution,
        on_delete=models.CASCADE,
        related_name='tool_executions',
        verbose_name=_('agent execution')
    )
    tool = models.ForeignKey(
        AgentTool,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name=_('tool')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    execution_time = models.FloatField(
        null=True,
        blank=True,
        help_text=_('Execution time in seconds')
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional metadata about this tool execution')
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('agent tool execution')
        verbose_name_plural = _('agent tool executions')
    
    def __str__(self):
        return f"{self.tool.name} execution for {self.agent_execution}"


class AgentResponseCache(models.Model):
    """Cache for agent responses to avoid redundant LLM calls"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='response_cache')
    input_hash = models.CharField(max_length=64, db_index=True)  # SHA256 of input
    response_data = models.JSONField()
    cost_saved = models.DecimalField(max_digits=8, decimal_places=4)
    hit_count = models.IntegerField(default=1)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('agent', 'input_hash')
        indexes = [
            models.Index(fields=['agent', 'input_hash']),
            models.Index(fields=['expires_at']),
        ]
    
    @classmethod
    def get_or_create_response(cls, agent, input_text, ttl_hours=24):
        """
        Get a cached response or return None if not found.
        
        Args:
            agent (Agent): The agent to check cache for
            input_text (str): The input text to check
            ttl_hours (int): Time-to-live in hours for new cache entries
            
        Returns:
            tuple: (response_data, cost_saved) or (None, 0) if not found
        """
        import hashlib
        from datetime import timedelta
        
        # Create hash of input (normalize first)
        normalized_input = input_text.strip().lower()
        input_hash = hashlib.sha256(normalized_input.encode()).hexdigest()
        
        # Check for existing cache
        try:
            cache_entry = cls.objects.get(
                agent=agent,
                input_hash=input_hash,
                expires_at__gt=timezone.now()
            )
            cache_entry.hit_count += 1
            cache_entry.save(update_fields=['hit_count'])
            return cache_entry.response_data, cache_entry.cost_saved
        except cls.DoesNotExist:
            return None, 0
    
    @classmethod
    def create_cache_entry(cls, agent, input_text, response_data, cost_saved, ttl_hours=24):
        """
        Create a new cache entry for an agent response.
        
        Args:
            agent (Agent): The agent the response is for
            input_text (str): The input text that generated this response
            response_data (dict): The response data to cache
            cost_saved (Decimal): The cost that will be saved on future hits
            ttl_hours (int): Time-to-live in hours
            
        Returns:
            AgentResponseCache: The created cache entry
        """
        import hashlib
        from datetime import timedelta
        
        # Create hash of input (normalize first)
        normalized_input = input_text.strip().lower()
        input_hash = hashlib.sha256(normalized_input.encode()).hexdigest()
        
        # Calculate expiry time
        expires_at = timezone.now() + timedelta(hours=ttl_hours)
        
        # Create or update cache entry
        cache_entry, created = cls.objects.update_or_create(
            agent=agent,
            input_hash=input_hash,
            defaults={
                'response_data': response_data,
                'cost_saved': cost_saved,
                'expires_at': expires_at,
                'hit_count': 1 if created else models.F('hit_count') + 1
            }
        )
        
        return cache_entry


class AgentCacheAnalytics(models.Model):
    """Analytics for agent response cache performance"""
    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name='cache_analytics')
    total_requests = models.IntegerField(default=0)
    cache_hits = models.IntegerField(default=0)
    cache_misses = models.IntegerField(default=0)
    total_cost_saved = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('agent cache analytics')
        verbose_name_plural = _('agent cache analytics')
    
    def __str__(self):
        return f"Cache analytics for {self.agent.name}"
    
    def hit_rate(self):
        """Calculate the cache hit rate as a percentage"""
        if self.total_requests == 0:
            return 0
        return (self.cache_hits / self.total_requests) * 100
    
    def record_hit(self, cost_saved):
        """Record a cache hit and update analytics"""
        self.total_requests += 1
        self.cache_hits += 1
        self.total_cost_saved += cost_saved
        self.save(update_fields=['total_requests', 'cache_hits', 'total_cost_saved', 'last_updated'])
    
    def record_miss(self):
        """Record a cache miss and update analytics"""
        self.total_requests += 1
        self.cache_misses += 1
        self.save(update_fields=['total_requests', 'cache_misses', 'last_updated'])
    
    @classmethod
    def get_or_create_for_agent(cls, agent):
        """Get or create analytics for an agent"""
        analytics, created = cls.objects.get_or_create(agent=agent)
        return analytics
