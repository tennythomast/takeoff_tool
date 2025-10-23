import logging
import time
import asyncio
import json
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from modelhub.models import RoutingRule, Model
from modelhub.services.llm_router import OptimizationStrategy
from prompt.models import PromptSession, Prompt
from .models import Agent, AgentExecution, AgentOptimization, AgentToolExecution
from .websocket_integration import update_agent_execution_status, update_tool_execution_status
from modelhub.services.llm_router import execute_with_cost_optimization, RequestContext


logger = logging.getLogger(__name__)


class AgentService:
    """Service for handling agent operations"""
    
    @staticmethod
    def create_agent(name, description, instructions, creator, organization, 
                    category=Agent.Category.GENERAL, workspace=None, routing_rule=None,
                    is_public=False, is_template=False, parent_agent=None,
                    config=None, tools=None, parameters=None,
                    capabilities=None, capability_level=Agent.CapabilityLevel.BASIC,
                    memory_type=Agent.MemoryType.SHORT_TERM, memory_window=10,
                    memory_config=None):
        """
        Create a new agent with optional tools and parameters
        
        Args:
            name (str): Agent name
            description (str): Agent description
            instructions (str): System instructions for the agent
            creator (User): User creating the agent
            organization (Organization): Organization the agent belongs to
            category (str): Agent category
            workspace (Workspace, optional): Workspace the agent belongs to
            routing_rule (RoutingRule, optional): LLM routing rule to use
            is_public (bool): Whether the agent can be cloned by others
            is_template (bool): Whether this is a template agent
            parent_agent (Agent, optional): Original agent this was cloned from
            config (dict, optional): Additional configuration
            tools (list, optional): List of tools to add to the agent
            parameters (list, optional): List of parameters to add to the agent
            capabilities (dict, optional): Specific capabilities this agent has
            capability_level (str): Overall capability level of this agent
            memory_type (str): Type of memory this agent uses
            memory_window (int): Number of previous interactions to remember
            memory_config (dict, optional): Additional memory configuration options
            
        Returns:
            Agent: The created agent
        """
        with transaction.atomic():
            # Create prompt session for this agent
            prompt_session = PromptSession.objects.create(
                title=name,
                description=description,
                workspace=workspace,
                creator=creator,
                model_type=PromptSession.ModelType.TEXT,
                status=PromptSession.Status.ACTIVE
            )
            
            # Create system prompt with instructions
            Prompt.objects.create(
                session=prompt_session,
                input_text=instructions,
                user=creator,
                metadata={'role': 'system'}
            )
            
            # Create the agent
            agent = Agent.objects.create(
                name=name,
                description=description,
                instructions=instructions,
                category=category,
                creator=creator,
                organization=organization,
                workspace=workspace,
                routing_rule=routing_rule,
                prompt_session=prompt_session,
                is_public=is_public,
                is_template=is_template,
                parent_agent=parent_agent,
                config=config or {},
                # Capability settings
                capabilities=capabilities or {},
                capability_level=capability_level,
                # Memory settings
                memory_type=memory_type,
                memory_window=memory_window,
                memory_config=memory_config or {}
            )
            
            # Add tools if provided
            if tools:
                for tool_data in tools:
                    agent.tools.create(
                        name=tool_data['name'],
                        description=tool_data.get('description', ''),
                        tool_type=tool_data.get('tool_type', 'FUNCTION'),
                        config=tool_data.get('config', {}),
                        is_required=tool_data.get('is_required', False)
                    )
            
            # Add parameters if provided
            if parameters:
                for param_data in parameters:
                    agent.parameters.create(
                        name=param_data['name'],
                        description=param_data.get('description', ''),
                        parameter_type=param_data.get('parameter_type', 'STRING'),
                        default_value=param_data.get('default_value'),
                        is_required=param_data.get('is_required', False),
                        options=param_data.get('options', []),
                        validation=param_data.get('validation', {})
                    )
            
            return agent
    
    @staticmethod
    def clone_agent(agent, new_creator, new_organization, new_workspace=None, new_name=None):
        """
        Clone an existing agent for another user/organization
        
        Args:
            agent (Agent): Agent to clone
            new_creator (User): User creating the clone
            new_organization (Organization): Organization the clone belongs to
            new_workspace (Workspace, optional): Workspace the clone belongs to
            new_name (str, optional): New name for the cloned agent
            
        Returns:
            Agent: The cloned agent
        """
        with transaction.atomic():
            # Clone the agent
            clone_name = new_name or f"{agent.name} (Clone)"
            
            # Create new prompt session for the clone
            prompt_session = PromptSession.objects.create(
                title=clone_name,
                description=agent.description,
                workspace=new_workspace,
                creator=new_creator,
                model_type=PromptSession.ModelType.TEXT,
                status=PromptSession.Status.ACTIVE
            )
            
            # Copy system message with instructions
            if agent.prompt_session:
                # Find system prompt from original agent
                system_prompt = agent.prompt_session.prompts.filter(metadata__role='system').first()
                if system_prompt:
                    Prompt.objects.create(
                        session=prompt_session,
                        input_text=system_prompt.input_text,
                        user=new_creator,
                        metadata={'role': 'system'}
                    )
            
            # Create the cloned agent
            cloned_agent = Agent.objects.create(
                name=clone_name,
                description=agent.description,
                instructions=agent.instructions,
                category=agent.category,
                creator=new_creator,
                organization=new_organization,
                workspace=new_workspace,
                routing_rule=agent.routing_rule,  # Use same routing rule
                prompt_session=prompt_session,
                is_public=False,  # Default to private for clones
                is_template=False,  # Default to not a template for clones
                parent_agent=agent,  # Reference original agent
                config=agent.config.copy(),
                metadata={}  # Reset metadata for the clone
            )
            
            # Clone tools
            for tool in agent.tools.all():
                cloned_agent.tools.create(
                    name=tool.name,
                    description=tool.description,
                    tool_type=tool.tool_type,
                    config=tool.config.copy(),
                    is_required=tool.is_required
                )
            
            # Clone parameters
            for param in agent.parameters.all():
                cloned_agent.parameters.create(
                    name=param.name,
                    description=param.description,
                    parameter_type=param.parameter_type,
                    default_value=param.default_value,
                    is_required=param.is_required,
                    options=param.options.copy() if param.options else [],
                    validation=param.validation.copy() if param.validation else {}
                )
            
            return cloned_agent
    
    @staticmethod
    def select_model(agent, input_data=None):
        """
        Select the appropriate LLM model for this agent using the routing rule
        
        Args:
            agent (Agent): The agent to select a model for
            input_data (dict, optional): Input data that might influence model selection
            
        Returns:
            Model: The selected model
        """
        # If agent has a specific routing rule, use it
        if agent.routing_rule:
            routing_rule = agent.routing_rule
        else:
            # Otherwise, find an appropriate rule based on the agent's category and organization
            routing_rules = RoutingRule.objects.filter(
                model_type='TEXT',  # Assuming agents use text models
                organization=agent.organization
            ).order_by('priority')
            
            # If no org-specific rules, fall back to system-wide rules
            if not routing_rules.exists():
                routing_rules = RoutingRule.objects.filter(
                    model_type='TEXT',
                    organization__isnull=True
                ).order_by('priority')
            
            if not routing_rules.exists():
                raise ValueError("No suitable routing rules found")
            
            # Use the highest priority rule (lowest number)
            routing_rule = routing_rules.first()
        
        # Get models associated with the rule
        rule_models = routing_rule.models.all()
        if not rule_models.exists():
            raise ValueError(f"Routing rule {routing_rule.name} has no associated models")
        
        # For now, just use the first model (in a real implementation, you'd use weights and conditions)
        # A more sophisticated implementation would evaluate conditions in the routing rule
        return rule_models.first()
    
    @staticmethod
    def execute_agent(agent, user, input_data=None, async_execution=False, stream=False, enable_tools=True, use_cache=True):
        """
        Execute an agent with the given input data using the LLM Router
        
        Args:
            agent (Agent): The agent to execute
            user (User): The user executing the agent
            input_data (dict, optional): Input data for the agent
            async_execution (bool): Whether to execute asynchronously
            stream (bool): Whether to stream the response
            enable_tools (bool): Whether to enable tools for this execution
            use_cache (bool): Whether to use response caching
        """
        
        # Import necessary modules
        from modelhub.services.llm_router import execute_with_cost_optimization, RequestContext
        from .models import AgentResponseCache, AgentCacheAnalytics
        
        # Create request context
        request_context = RequestContext(
            complexity='medium',  # Default complexity
            max_tokens=1024,
            session_id=str(agent.prompt_session.id) if agent.prompt_session else None,
            prompt_id=None,
            user_preferences=agent.config.get('quality_preference', {}),
            conversation_history=None,
            entity_type='agent_session'  # Explicitly set entity_type for agent calls
        )
        
        # Determine optimization strategy based on agent config
        quality_preference = agent.config.get('quality_preference', 'BALANCED')
        strategy = OptimizationStrategy.BALANCED
        if quality_preference == 'COST':
            strategy = OptimizationStrategy.COST_FIRST
        elif quality_preference == 'QUALITY':
            strategy = OptimizationStrategy.QUALITY_FIRST
        elif quality_preference == 'SPEED':
            strategy = OptimizationStrategy.PERFORMANCE_FIRST
            return execution
        
        # Otherwise, execute synchronously
        try:
            # Update status to running
            execution.status = AgentExecution.Status.RUNNING
            execution.started_at = timezone.now()
            execution.save(update_fields=['status', 'started_at'])
            
            # Get user input from input_data
            user_input = input_data.get('prompt', '') if input_data else ''
            
            # Create a new prompt for the user input
            user_prompt = None
            if agent.prompt_session:
                user_prompt = Prompt.objects.create(
                    session=agent.prompt_session,
                    input_text=user_input,
                    user=user,
                    metadata={'role': 'user'}
                )
            
            # Prepare messages for the LLM call
            messages = []
            
            # Add system instructions
            messages.append({
                'role': 'system',
                'content': agent.instructions
            })
            
            # Add conversation history if available
            if agent.prompt_session:
                # Get previous messages, excluding the one we just created
                previous_prompts = agent.prompt_session.prompts.exclude(id=user_prompt.id).order_by('created_at')
                for prompt in previous_prompts:
                    role = prompt.metadata.get('role', 'user')
                    messages.append({
                        'role': role,
                        'content': prompt.input_text
                    })
            
            # Add current user input
            messages.append({
                'role': 'user',
                'content': user_input
            })
            
            # Prepare parameters based on agent configuration
            llm_params = {}
            
            # Add any agent parameters as LLM parameters
            for param in agent.parameters.all():
                # Only include parameters that are meant to be passed to the LLM
                if param.parameter_type in ['TEMPERATURE', 'TOP_P', 'MAX_TOKENS', 'FREQUENCY_PENALTY', 'PRESENCE_PENALTY']:
                    param_key = param.name.lower()
                    param_value = input_data.get(param.name, param.default_value)
                    if param_value is not None:
                        llm_params[param_key] = param_value
            
            # Set default max_tokens if not specified
            if 'max_tokens' not in llm_params:
                llm_params['max_tokens'] = 1024
                
            # Add tools if enabled
            tools = []
            if enable_tools:
                # Get all active tools for this agent
                agent_tools = agent.tools.all()
                
                # Convert tools to the format expected by the LLM
                for tool in agent_tools:
                    tools.append(tool.get_tool_definition())
            
            # Import the LLM Router here to avoid circular imports
            from modelhub.services.llm_router import execute_with_cost_optimization, RequestContext
            
            # Create request context
            request_context = RequestContext(
                complexity='medium',  # Default complexity
                max_tokens=llm_params.get('max_tokens', 1024),
                session_id=str(agent.prompt_session.id) if agent.prompt_session else None,
                prompt_id=str(user_prompt.id) if user_prompt else None,
                user_preferences=agent.config.get('quality_preference', {}),
                conversation_history=messages[:-1] if len(messages) > 1 else None,
                entity_type='agent_session'  # Explicitly set entity_type for agent calls
            )
            
            # Determine optimization strategy based on agent config
            quality_preference = agent.config.get('quality_preference', 'BALANCED')
            strategy = OptimizationStrategy.BALANCED
            if quality_preference == 'COST':
                strategy = OptimizationStrategy.COST_FIRST
            elif quality_preference == 'QUALITY':
                strategy = OptimizationStrategy.QUALITY_FIRST
            elif quality_preference == 'SPEED':
                strategy = OptimizationStrategy.PERFORMANCE_FIRST
            
            # Start timing
            start_time = time.time()
            
            # Check cache if enabled and not using tools (caching with tools is more complex)
            cached_response = None
            cached_cost = Decimal('0')
            user_input = input_data.get('prompt', '') if input_data else ''
            
            if use_cache and not enable_tools and agent.config.get('enable_caching', True):
                try:
                    # Get or create analytics tracker
                    analytics = AgentCacheAnalytics.get_or_create_for_agent(agent)
                    
                    logger.debug(f"Checking cache for agent {agent.id} with input: {user_input[:50]}...")
                    cached_response, cached_cost = AgentResponseCache.get_or_create_response(
                        agent=agent,
                        input_text=user_input,
                        ttl_hours=agent.config.get('cache_ttl_hours', 24)
                    )
                    
                    if cached_response:
                        # Record cache hit in analytics
                        analytics.record_hit(cached_cost)
                        logger.info(f"Cache hit for agent {agent.id}, saved ${cached_cost}")
                        
                        # Send WebSocket notification about cache hit
                        from .websocket_integration import send_cache_notification
                        send_cache_notification(
                            execution_id=str(execution.id),
                            cache_hit=True,
                            cost_saved=cached_cost
                        )
                        
                        # Use cached response and skip LLM call
                        response_content = cached_response.get('response', '')
                        metadata = cached_response.get('metadata', {})
                        
                        # Update execution record
                        execution.status = AgentExecution.Status.COMPLETED
                        execution.completed_at = timezone.now()
                        execution.execution_time = time.time() - start_time
                        execution.output_data = cached_response
                        execution.tokens_used = metadata.get('tokens_used', 0)
                        execution.cost = Decimal('0')  # No cost for cached responses
                        execution.save()
                        
                        # Add model response to prompt session with cache metadata
                        if agent.prompt_session:
                            prompt_metadata = {
                                'role': 'assistant',
                                'parent_id': user_prompt.id if user_prompt else None,
                                'llm_metadata': metadata,
                                'from_cache': True,
                                'cost_saved': str(cached_cost)
                            }
                            
                            Prompt.objects.create(
                                session=agent.prompt_session,
                                input_text=response_content,
                                user=user,
                                metadata=prompt_metadata
                            )
                        
                        # Update agent metrics
                        agent.update_metrics_with_execution(execution)
                        
                        return execution
                        
                    else:
                        # Record cache miss in analytics
                        analytics.record_miss()
                        
                        # Send WebSocket notification about cache miss
                        from .websocket_integration import send_cache_notification
                        send_cache_notification(
                            execution_id=str(execution.id),
                            cache_hit=False,
                            cost_saved=None
                        )
                except Exception as cache_error:
                    logger.warning(f"Error checking cache for agent {agent.id}: {str(cache_error)}")
            
            # Execute the LLM call using the LLM Router
            # We need to run the async function in a synchronous context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Add tools to the LLM call if enabled and available
                if enable_tools and tools:
                    llm_params['tools'] = tools
                    llm_params['tool_choice'] = 'auto'  # Let the model decide when to use tools
                
                response, metadata = loop.run_until_complete(
                    execute_with_cost_optimization(
                        organization=agent.organization,
                        model_type='TEXT',
                        request_context=request_context,
                        strategy=strategy,
                        messages=messages,
                        stream=stream,
                        **llm_params
                    )
                )
            finally:
                loop.close()
            
            # Process the response, handling any tool calls
            response_content = response.content
            tool_calls = getattr(response, 'tool_calls', None)
            tool_results = []
            
            # Handle tool calls if present
            if enable_tools and tool_calls:
                # Process each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call.get('name')
                    tool_args = tool_call.get('arguments', {})
                    tool_id = tool_call.get('id')
                    
                    logger.info(f"Agent {agent.id} is calling tool {tool_name} with args: {tool_args}")
                    
                    try:
                        # Find the tool by name
                        tool = agent.tools.filter(name=tool_name).first()
                        if not tool:
                            raise ValueError(f"Tool {tool_name} not found for agent {agent.id}")
                        
                        # Create a tool execution record
                        tool_execution = AgentToolExecution.objects.create(
                            agent_execution=execution,
                            tool=tool,
                            status=AgentToolExecution.Status.RUNNING,
                            input_data=tool_args
                        )
                        
                        # Execute the tool
                        start_tool_time = time.time()
                        tool_result = tool.execute_tool(tool_args)
                        tool_execution_time = time.time() - start_tool_time
                        
                        # Update the tool execution record
                        tool_execution.status = AgentToolExecution.Status.COMPLETED
                        tool_execution.output_data = tool_result
                        tool_execution.execution_time = tool_execution_time
                        tool_execution.save()
                        
                        # Add to tool results
                        tool_results.append({
                            'tool_call_id': tool_id,
                            'name': tool_name,
                            'result': tool_result
                        })
                        
                    except Exception as e:
                        logger.exception(f"Error executing tool {tool_name}: {str(e)}")
                        
                        # Update the tool execution record with error
                        if 'tool_execution' in locals():
                            tool_execution.status = AgentToolExecution.Status.FAILED
                            tool_execution.error_message = str(e)
                            tool_execution.save()
                        
                        # Add error to tool results
                        tool_results.append({
                            'tool_call_id': tool_id,
                            'name': tool_name,
                            'error': str(e)
                        })
                
                # If we have tool results, we need to call the LLM again with the results
                if tool_results:
                    # Add the assistant's response with tool calls to messages
                    messages.append({
                        'role': 'assistant',
                        'content': response_content,
                        'tool_calls': tool_calls
                    })
                    
                    # Add tool results to messages
                    for result in tool_results:
                        messages.append({
                            'role': 'tool',
                            'tool_call_id': result.get('tool_call_id'),
                            'name': result.get('name'),
                            'content': json.dumps(result.get('result', {}) if 'result' in result else {'error': result.get('error')})
                        })
                    
                    # Call the LLM again with tool results
                    try:
                        # We don't need to pass tools again since we're just getting the final response
                        if 'tools' in llm_params:
                            del llm_params['tools']
                        if 'tool_choice' in llm_params:
                            del llm_params['tool_choice']
                        
                        # Make the second LLM call
                        second_response, second_metadata = loop.run_until_complete(
                            execute_with_cost_optimization(
                                organization=agent.organization,
                                model_type='TEXT',
                                request_context=request_context,
                                strategy=strategy,
                                messages=messages,
                                stream=stream,
                                **llm_params
                            )
                        )
                        
                        # Update response and metadata with the second call
                        response_content = second_response.content
                        
                        # Merge metadata from both calls
                        metadata['second_call'] = second_metadata
                        metadata['tokens_used'] = (metadata.get('tokens_used', 0) or 0) + (second_metadata.get('tokens_used', 0) or 0)
                        metadata['cost'] = (metadata.get('cost', 0) or 0) + (second_metadata.get('cost', 0) or 0)
                        
                    except Exception as e:
                        logger.exception(f"Error in second LLM call after tool execution: {str(e)}")
                        # Continue with the original response if the second call fails
            
            # Add model response to prompt session
            if agent.prompt_session:
                # Create metadata with tool calls and results if applicable
                prompt_metadata = {
                    'role': 'assistant',
                    'parent_id': user_prompt.id if user_prompt else None,
                    'llm_metadata': metadata
                }
                
                if tool_calls:
                    prompt_metadata['tool_calls'] = tool_calls
                    prompt_metadata['tool_results'] = tool_results
                
                Prompt.objects.create(
                    session=agent.prompt_session,
                    input_text=response_content,
                    user=user,
                    metadata=prompt_metadata
                )
            
            # Get model used from metadata
            model_name = metadata.get('selected_model')
            provider_name = metadata.get('selected_provider')
            
            # Try to find the model in the database
            try:
                model = Model.objects.filter(name=model_name, provider__slug=provider_name).first()
                if model:
                    execution.model_used = model
            except Exception as model_error:
                logger.warning(f"Could not find model {provider_name}/{model_name}: {str(model_error)}")
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Update execution record
            execution.status = AgentExecution.Status.COMPLETED
            execution.completed_at = timezone.now()
            execution.execution_time = execution_time
            
            # Include tool calls and results in the output data if applicable
            output_data = {
                'response': response_content,
                'metadata': metadata
            }
            
            if tool_calls:
                output_data['tool_calls'] = tool_calls
                output_data['tool_results'] = tool_results
                
                # Add summary of tools used
                tool_summary = []
                for tool_result in tool_results:
                    tool_summary.append({
                        'name': tool_result.get('name'),
                        'success': 'result' in tool_result and tool_result.get('result', {}).get('status') == 'success',
                        'execution_time': next(
                            (te.execution_time for te in execution.tool_executions.all() 
                             if te.tool.name == tool_result.get('name')),
                            None
                        )
                    })
                output_data['tool_summary'] = tool_summary
            
            execution.output_data = output_data
            execution.tokens_used = response.total_tokens if hasattr(response, 'total_tokens') else 0
            execution.cost = response.cost if hasattr(response, 'cost') else Decimal('0.0')
            execution.save()
            
            # Update agent metrics with this execution
            agent.update_metrics_with_execution(execution)
            
            # Store response in cache if enabled and not using tools
            if use_cache and not enable_tools and agent.config.get('enable_caching', True) and not stream:
                try:
                    # Only cache successful responses
                    if execution.status == AgentExecution.Status.COMPLETED:
                        # Prepare cache data
                        cache_data = {
                            'response': response_content,
                            'metadata': metadata,
                            'execution_id': str(execution.id),
                            'created_at': execution.created_at.isoformat() if execution.created_at else None
                        }
                        
                        # Calculate cost saved for future cache hits
                        cost_saved = execution.cost or Decimal('0')
                        
                        # Store in cache
                        AgentResponseCache.create_cache_entry(
                            agent=agent,
                            input_text=user_input,
                            response_data=cache_data,
                            cost_saved=cost_saved,
                            ttl_hours=agent.config.get('cache_ttl_hours', 24)
                        )
                        logger.info(f"Cached response for agent {agent.id} with input: {user_input[:50]}...")
                except Exception as cache_error:
                    logger.warning(f"Error caching response for agent {agent.id}: {str(cache_error)}")
            
            return execution
            
        except Exception as e:
            logger.exception(f"Error executing agent {agent.id}: {str(e)}")
            execution.status = AgentExecution.Status.FAILED
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            raise
    
    @staticmethod
    def generate_agent_instructions(purpose, role, context='', routing_preference='balanced', user=None):
        """
        Generate optimized instructions for an agent using the proper LLM router
        
        Args:
            purpose (str): The purpose of the agent
            role (str): The role of the agent
            context (str): Additional context for the agent
            routing_preference (str): Model routing preference (balanced, quality, speed, cost)
            user (User): The user requesting the instructions
            
        Returns:
            str: The generated instructions
        """
        try:
            logger.info(f"Generating agent instructions for role: {role}, routing: {routing_preference}")
            
            # Import the LLM router components
            from modelhub.services.llm_router import (
                execute_with_cost_optimization, 
                OptimizationStrategy, 
                RequestContext
            )
            
            # Map routing preferences to correct OptimizationStrategy values
            strategy_mapping = {
                'balanced': OptimizationStrategy.BALANCED,
                'quality': OptimizationStrategy.QUALITY_FIRST,
                'speed': OptimizationStrategy.PERFORMANCE_FIRST,
                'cost': OptimizationStrategy.COST_FIRST
            }
            
            strategy = strategy_mapping.get(routing_preference.lower(), OptimizationStrategy.BALANCED)
            logger.info(f"Using optimization strategy: {strategy.value}")
            
            # Build comprehensive prompt for instruction generation
            enhanced_prompt = f"""You are an expert AI system architect. Create comprehensive, professional instructions for an AI agent.

AGENT SPECIFICATIONS:
- Name: AI Assistant
- Role: {role}
- Purpose: {purpose}
- Context: {context if context else 'General AI assistant for professional use'}

Create detailed, actionable instructions that include:

## 1. Identity & Mission Statement
Define the agent's core identity, purpose, and primary objectives in clear terms.

## 2. Role Definition & Scope
- Specific responsibilities and duties
- Areas of expertise and focus
- Professional boundaries and limitations

## 3. Communication Excellence
- Professional tone and communication style
- How to engage with users effectively
- Response formatting and structure guidelines

## 4. Operational Procedures
- How to handle different types of requests
- Problem-solving approaches and methodologies
- When and how to ask clarifying questions

## 5. Quality Standards & Best Practices
- Accuracy and reliability requirements
- How to handle uncertainty and limitations
- Error acknowledgment and correction procedures

## 6. User Experience Guidelines
- How to provide exceptional service
- Techniques for understanding user needs
- Methods for ensuring user satisfaction

## 7. Professional Conduct
- Ethical guidelines and principles
- Confidentiality and privacy standards
- When to escalate or refer to human experts

## 8. Continuous Improvement
- How to learn from interactions
- Adaptation strategies for different users
- Performance optimization approaches

The instructions should be comprehensive (1500-2000 words), specific to the role of {role}, 
and focused on enabling excellent performance in {purpose}.

Format the response as a detailed operational manual that would enable an AI system to excel in this role."""

            # Create request context
            request_context = RequestContext(
                complexity='medium',  # Agent instruction generation is moderately complex
                max_tokens=2048,      # Allow for comprehensive instructions
                session_id=f"agent_instruction_{user.id if user else 'system'}_{hash(role)}",
                user_preferences={'quality': 'high', 'detailed': True},
                conversation_history=None,
                entity_type='agent_session'  # Explicitly set entity_type for agent calls
            )
            
            # Prepare messages for the LLM call
            messages = [
                {
                    'role': 'system',
                    'content': 'You are an expert AI system designer specializing in creating comprehensive, professional agent instructions. Your instructions should be detailed, actionable, and enable AI agents to perform excellently in their designated roles.'
                },
                {
                    'role': 'user',
                    'content': enhanced_prompt
                }
            ]
            
            # Get organization for the user (if available)
            organization = getattr(user, 'organization', None) if user else None
            
            logger.info(f"Calling LLM router with strategy: {strategy.value}, organization: {organization}")
            
            # Execute the LLM call using your router
           
            from asgiref.sync import sync_to_async
            try:
                # Check if we're already in an async context
                current_loop = asyncio.get_running_loop()
                logger.warning("Already in async context, using sync_to_async wrapper")
                
                # Create async wrapper function
                async def _execute_optimization():
                    return await execute_with_cost_optimization(
                        organization=organization,
                        model_type='TEXT',
                        request_context=request_context,
                        strategy=strategy,
                        messages=messages,
                        max_tokens=2048,
                        temperature=0.7
                    )
                
                # Execute using Django's async utilities
                response, metadata = sync_to_async(_execute_optimization)()
                
            except RuntimeError:
                # No running event loop - safe to create one
                logger.info("No existing event loop, creating new one")
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    response, metadata = loop.run_until_complete(
                        execute_with_cost_optimization(
                            organization=organization,
                            model_type='TEXT',
                            request_context=request_context,
                            strategy=strategy,
                            messages=messages,
                            max_tokens=2048,
                            temperature=0.7
                        )
                    )
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)

            # Extract the generated instructions (keep this part the same)
            instructions = response.content if hasattr(response, 'content') else str(response)
            instructions = instructions.strip()

            if not instructions or len(instructions) < 100:
                logger.warning("LLM router returned empty or too short instructions")
                return None

            # Log success with metadata (keep this part the same)
            logger.info(f"Successfully generated {len(instructions)} character instructions")
            logger.info(f"Used model: {metadata.get('selected_model', 'unknown')} from {metadata.get('selected_provider', 'unknown')}")
            logger.info(f"Estimated cost: ${metadata.get('optimization', {}).get('estimated_cost', 0):.6f}")

            return instructions
            
        except ImportError as e:
            logger.error(f"Failed to import LLM router components: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error generating agent instructions with LLM router: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    def get_model_for_routing(routing_preference):
        """
        Get the appropriate model based on routing preference
        """
        try:
            # Try to use your routing rules from the database
            from modelhub.models import RoutingRule
            
            # Map routing preferences to rule names (based on your screenshot)
            rule_name_mapping = {
                'cost': 'Cost-First Simple Queries',
                'balanced': 'Balanced Medium Complexity', 
                'quality': 'Quality-First Complex Tasks',
                'speed': 'Performance-First Fast Response'
            }
            
            rule_name = rule_name_mapping.get(routing_preference.lower())
            if rule_name:
                # Find the rule by name
                rule = RoutingRule.objects.filter(
                    name=rule_name,
                    is_active=True,
                    model_type='TEXT'
                ).first()
                
                if rule:
                    # Get the first model from the rule
                    rule_model = rule.routingrulemodel_set.first()
                    if rule_model and rule_model.model:
                        logger.info(f"Found model from rule '{rule_name}': {rule_model.model.name}")
                        return rule_model.model.name
            
            # Fallback to simple name-based lookup
            routing_rules = RoutingRule.objects.filter(
                model_type='TEXT',
                is_active=True
            ).order_by('priority')
            
            # Try to find a rule that matches our preference by name content
            preference_keywords = {
                'quality': ['quality', 'complex', 'high'],
                'speed': ['speed', 'fast', 'performance'],
                'cost': ['cost', 'cheap', 'economy', 'simple'],
                'balanced': ['balanced', 'medium', 'default']
            }
            
            keywords = preference_keywords.get(routing_preference.lower(), ['balanced'])
            
            for rule in routing_rules:
                rule_name_lower = rule.name.lower()
                if any(keyword in rule_name_lower for keyword in keywords):
                    rule_model = rule.routingrulemodel_set.first()
                    if rule_model and rule_model.model:
                        logger.info(f"Selected model from rule '{rule.name}': {rule_model.model.name}")
                        return rule_model.model.name
            
            # If no specific rule found, use the first available rule
            if routing_rules.exists():
                first_rule = routing_rules.first()
                rule_model = first_rule.routingrulemodel_set.first()
                if rule_model and rule_model.model:
                    logger.info(f"Using default model from rule '{first_rule.name}': {rule_model.model.name}")
                    return rule_model.model.name
                    
        except Exception as e:
            logger.warning(f"Error getting model from routing rules: {str(e)}")
        
        # Final fallback to hardcoded models
        default_models = {
            'balanced': 'gpt-4',
            'quality': 'gpt-4-turbo',
            'speed': 'gpt-3.5-turbo',
            'cost': 'gpt-3.5-turbo'
        }
        
        model = default_models.get(routing_preference.lower(), 'gpt-4')
        logger.info(f"Using fallback model {model} for routing preference {routing_preference}")
        return model
