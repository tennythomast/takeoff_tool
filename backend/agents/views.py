from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
import logging

from .models import (
    Agent, AgentTool, AgentParameter, AgentExecution,
    AgentConfigurationStep, AgentOptimization, AgentCacheAnalytics
)
from .serializers import (
    AgentListSerializer, AgentDetailSerializer, AgentCreateSerializer,
    AgentUpdateSerializer, AgentToolSerializer, AgentParameterSerializer,
    AgentToolCreateSerializer, AgentParameterCreateSerializer,
    AgentExecutionSerializer, AgentExecuteSerializer,
    AgentConfigurationStepSerializer, AgentOptimizationSerializer,
    AgentToolExecutionSerializer, AgentCacheAnalyticsSerializer
)
from .services import AgentService

logger = logging.getLogger(__name__)


class InstructionGenerationService:
    """Enhanced instruction generation with robust fallback strategy"""
    
    def generate_instructions(self, request_data, user=None):
        """Generate instructions with tiered fallback approach"""
        
        # Tier 1: Try primary LLM service
        try:
            return self._generate_with_primary_llm(request_data, user)
        except Exception as primary_error:
            logger.warning(f"Primary LLM failed: {str(primary_error)}")
            
            # Tier 2: Try alternative LLM provider
            try:
                return self._generate_with_alternative_llm(request_data, user)
            except Exception as alt_error:
                logger.warning(f"Alternative LLM failed: {str(alt_error)}")
                
                # Tier 3: Use intelligent template system
                try:
                    return self._generate_with_smart_template(request_data)
                except Exception as template_error:
                    logger.error(f"Smart template failed: {str(template_error)}")
                    
                    # Tier 4: Basic template (last resort)
                    return self._generate_basic_fallback(request_data)
    
    async def generate_instructions_async(self, request_data, user=None):
        """Async version that works like chat - calls LLM router directly"""
        
        # Tier 1: Try primary LLM service (async)
        try:
            return await self._generate_with_primary_llm_async(request_data, user)
        except Exception as primary_error:
            logger.warning(f"Primary LLM failed: {str(primary_error)}")
            
            # Fall back to sync template system
            try:
                return self._generate_with_smart_template(request_data)
            except Exception as template_error:
                logger.error(f"Smart template failed: {str(template_error)}")
                return self._generate_basic_fallback(request_data)

    async def _generate_with_primary_llm_async(self, data, user):
        """Async version that calls LLM router properly like chat does"""
        try:
            logger.info("Using LLM router for primary instruction generation")
            
            # Import the LLM router components
            from modelhub.services.llm_router import execute_with_cost_optimization, OptimizationStrategy, RequestContext
            
            # Build context like chat does
            purpose = data.get('problemStatement', '')
            role = data.get('primaryRole', '')
            context = self._build_enhanced_context(data)
            routing_preference = data.get('routingRule', 'balanced')
            
            # Map routing preferences
            strategy_mapping = {
                'balanced': OptimizationStrategy.BALANCED,
                'quality': OptimizationStrategy.QUALITY_FIRST,
                'speed': OptimizationStrategy.PERFORMANCE_FIRST,
                'cost': OptimizationStrategy.COST_FIRST
            }
            
            strategy = strategy_mapping.get(routing_preference.lower(), OptimizationStrategy.BALANCED)
            
            # Build comprehensive prompt
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
                complexity='medium',
                max_tokens=2048,
                session_id=f"agent_instruction_{user.id if user else 'system'}_{hash(role)}",
                user_preferences={'quality': 'high', 'detailed': True},
                conversation_history=None
            )
            
            # Prepare messages
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
            
            # Get organization for the user
            organization = getattr(user, 'organization', None) if user else None
            
            logger.info(f"Calling LLM router with strategy: {strategy.value}, organization: {organization}")
            
            # Call LLM router the same way chat does - DIRECTLY without event loop creation
            response, metadata = await execute_with_cost_optimization(
                organization=organization,
                model_type='TEXT',
                request_context=request_context,
                strategy=strategy,
                messages=messages,
                max_tokens=2048,
                temperature=0.7
            )
            
            # Extract instructions
            instructions = response.content if hasattr(response, 'content') else str(response)
            instructions = instructions.strip()
            
            if not instructions or len(instructions) < 100:
                logger.warning("LLM router returned empty or too short instructions")
                raise ValueError("Generated instructions too short or empty")
            
            logger.info(f"LLM router generated {len(instructions)} character instructions")
            
            return {
                'instructions': instructions,
                'generation_method': 'primary_llm',
                'quality_score': 'high',
                'can_enhance': False,
                'metadata': {
                    'provider': metadata.get('selected_provider', 'unknown'),
                    'model_used': metadata.get('selected_model', 'unknown'),
                    'character_count': len(instructions),
                    'source': 'dataelan_llm_router'
                }
            }
            
        except Exception as e:
            logger.error(f"LLM router generation failed: {str(e)}")
            raise
    
    def _generate_with_primary_llm(self, data, user):
        """Use your existing LLM router for primary generation"""
        try:
            logger.info("Using LLM router for primary instruction generation")
            
            # Use the enhanced AgentService method
            instructions = AgentService.generate_agent_instructions(
                purpose=data.get('problemStatement', ''),
                role=data.get('primaryRole', ''),
                context=self._build_enhanced_context(data),
                routing_preference=data.get('routingRule', 'balanced'),
                user=user
            )
            
            if not instructions or len(instructions.strip()) < 100:
                raise ValueError("Generated instructions too short or empty")
                
            logger.info(f"LLM router generated {len(instructions)} character instructions")
            
            return {
                'instructions': instructions,
                'generation_method': 'primary_llm',
                'quality_score': 'high',
                'can_enhance': False,
                'metadata': {
                    'provider': 'llm_router',
                    'model_used': data.get('routingRule', 'balanced'),
                    'character_count': len(instructions),
                    'source': 'dataelan_llm_router'
                }
            }
            
        except Exception as e:
            logger.error(f"LLM router generation failed: {str(e)}")
            raise
    
    def _generate_with_alternative_llm(self, data, user):
        """Try different routing preferences as alternatives"""
        alternative_preferences = ['balanced', 'speed', 'cost']
        original_pref = data.get('routingRule', 'balanced')
        
        for pref in alternative_preferences:
            if pref == original_pref:
                continue
                
            try:
                logger.info(f"Trying alternative LLM routing with {pref} preference")
                
                instructions = AgentService.generate_agent_instructions(
                    purpose=data.get('problemStatement', ''),
                    role=data.get('primaryRole', ''),
                    context=self._build_enhanced_context(data),
                    routing_preference=pref,
                    user=user
                )
                
                if instructions and len(instructions.strip()) >= 100:
                    logger.info(f"Alternative LLM succeeded with {pref} routing: {len(instructions)} characters")
                    
                    return {
                        'instructions': instructions,
                        'generation_method': 'alternative_llm',
                        'quality_score': 'medium-high',
                        'can_enhance': False,
                        'metadata': {
                            'provider': 'llm_router_alternative',
                            'model_used': pref,
                            'note': f'Generated using {pref} routing due to primary service issues',
                            'character_count': len(instructions)
                        }
                    }
            except Exception as e:
                logger.warning(f"Alternative LLM with {pref} routing failed: {str(e)}")
                continue
                
        raise ValueError("All LLM alternatives failed")
    
    def _generate_with_smart_template(self, data):
        """Use rule-based intelligent template system"""
        role = data.get('primaryRole', '').lower()
        problem = data.get('problemStatement', '')
        capabilities = data.get('capabilities', [])
        
        logger.info(f"Using smart template for role: {role}")
        
        # Smart templates based on role patterns
        template_library = {
            'customer support': self._get_customer_support_template(),
            'data analyst': self._get_data_analyst_template(),
            'content creator': self._get_content_creator_template(),
            'research': self._get_research_template(),
            'assistant': self._get_general_assistant_template(),
            'productivity': self._get_productivity_template()  # Add productivity template
        }
        
        # Find best matching template
        template_key = self._find_best_template(role, template_library.keys())
        base_template = template_library.get(template_key, template_library['assistant'])
        
        # Customize template with user data
        instructions = self._customize_template(base_template, data)
        
        # Add specific capabilities and constraints
        instructions = self._enhance_with_capabilities(instructions, capabilities)
        instructions = self._add_problem_specific_guidance(instructions, problem)
        
        return {
            'instructions': instructions,
            'generation_method': 'smart_template',
            'quality_score': 'medium',
            'can_enhance': True,
            'metadata': {
                'template_used': template_key,
                'character_count': len(instructions),
                'enhancement_suggestion': 'AI-generated instructions available when services are restored'
            }
        }
    
    def _generate_basic_fallback(self, data):
        """Enhanced basic fallback - better than minimal"""
        name = data.get('name', 'AI Assistant')
        role = data.get('primaryRole', 'Assistant')
        problem = data.get('problemStatement', 'general assistance')
        capabilities = data.get('capabilities', [])
        target_users = data.get('targetUsers', [])
        communication_style = data.get('communicationStyle', 'professional')
        
        logger.warning("Using enhanced basic fallback template")
        
        # Create a more comprehensive basic template
        instructions = f"""# {name} - {role}

You are {name}, an AI assistant specialized in {role}.

## Primary Mission
Your main responsibility is to {problem}

## Target Users
You serve {', '.join(target_users) if target_users else 'users'} with their specific needs.

## Communication Style
- Maintain a {communication_style.lower()} tone
- Be clear, helpful, and accurate
- Ask clarifying questions when needed
- Provide step-by-step guidance when appropriate

## Your Capabilities
{chr(10).join([f'- {cap}: Use this effectively to help users' for cap in capabilities]) if capabilities else '- General assistance and support'}

## Core Guidelines
- Always strive to be helpful and accurate
- If uncertain about something, clearly state your limitations
- Stay focused on your role as a {role}
- Provide practical, actionable advice
- Follow up to ensure user satisfaction

## Quality Standards
- Ensure responses are relevant and useful
- Maintain consistency in your approach
- Provide examples when helpful
- Acknowledge when you need more information

Always aim to provide excellent service while staying within your defined capabilities and role."""

        return {
            'instructions': instructions,
            'generation_method': 'basic_fallback',
            'quality_score': 'basic',
            'can_enhance': True,
            'metadata': {
                'is_fallback': True,
                'character_count': len(instructions),
                'enhancement_suggestion': 'Upgrade to AI-generated instructions for significantly better performance'
            }
        }
    
    def _build_enhanced_context(self, data):
        """Build comprehensive context for LLM with all user inputs"""
        name = data.get('name', 'AI Assistant')
        target_users = data.get('targetUsers', [])
        communication_style = data.get('communicationStyle', 'professional')
        output_format = data.get('outputFormat', 'markdown')
        capabilities = data.get('capabilities', [])
        quality_preference = data.get('qualityPreference', 2)
        additional_context = data.get('additionalContext', '')
        
        # Create rich context that will help the LLM generate better instructions
        context_parts = []
        
        if name != 'AI Assistant':
            context_parts.append(f"Agent Name: {name}")
        
        if target_users:
            context_parts.append(f"Target Users: {', '.join(target_users)}")
            context_parts.append(f"User Expertise Level: Varied (from beginners to experts in {', '.join(target_users)})")
        
        if communication_style:
            context_parts.append(f"Required Communication Style: {communication_style}")
            
        if output_format:
            context_parts.append(f"Preferred Output Format: {output_format}")
            
        if capabilities:
            context_parts.append(f"Required Capabilities: {', '.join(capabilities)}")
            context_parts.append(f"Integration Requirements: Must effectively utilize {len(capabilities)} different capabilities")
        
        quality_labels = {1: 'Fast/Efficient', 2: 'Balanced', 3: 'High Quality/Comprehensive'}
        context_parts.append(f"Quality Expectation: {quality_labels.get(quality_preference, 'Balanced')}")
        
        if additional_context:
            context_parts.append(f"Additional Context: {additional_context}")
        
        # Add specific guidance for the LLM
        context_parts.append("Requirements for Instructions:")
        context_parts.append("- Must be comprehensive and actionable")
        context_parts.append("- Should enable excellent performance in the specified role")
        context_parts.append("- Must include specific behavioral guidelines")
        context_parts.append("- Should address common scenarios and edge cases")
        context_parts.append("- Must maintain professional standards throughout")
        
        return "\n".join(context_parts)
    
    # Template library methods
    def _get_customer_support_template(self):
        return """You are a professional customer support AI assistant designed to provide exceptional service.

## Core Identity
- Empathetic and solution-focused
- Knowledgeable about common issues and solutions
- Committed to customer satisfaction
- Professional yet approachable

## Primary Responsibilities
- Respond to customer inquiries promptly and professionally
- Provide accurate information about products, services, and policies
- Guide customers through troubleshooting steps systematically
- Escalate complex issues to human agents when appropriate
- Maintain detailed interaction records

## Communication Protocol
- Use clear, jargon-free language appropriate for all skill levels
- Show genuine empathy for customer concerns and frustrations
- Provide step-by-step guidance with confirmation checkpoints
- Always confirm understanding before concluding interactions
- Offer multiple contact options for follow-up

## Quality Standards
- Accuracy in all information provided
- Timely responses (acknowledge immediately, resolve quickly)
- Complete resolution or clear escalation path
- Professional tone regardless of customer attitude
- Proactive suggestion of relevant resources"""

    def _get_data_analyst_template(self):
        return """You are a specialized data analysis AI assistant focused on helping users extract insights from data.

## Core Identity
- Analytical and methodical in approach
- Skilled in statistical thinking and data interpretation
- Committed to accuracy and evidence-based conclusions
- Educational in explanations

## Primary Capabilities
- Data interpretation and trend analysis
- Visualization recommendations and guidance
- Statistical analysis methodology suggestions
- Data quality assessment and improvement recommendations
- Hypothesis testing and validation approaches"""

    def _get_content_creator_template(self):
        return """You are a creative content development AI assistant specializing in high-quality content creation.

## Core Identity
- Creative and innovative in approach
- Skilled in various content formats and styles
- Audience-focused and engagement-driven
- Brand-conscious and consistent

## Primary Capabilities
- Content strategy development and planning
- Writing and editing across multiple formats
- Creative brainstorming and ideation
- Content optimization for different platforms
- Brand voice development and maintenance"""

    def _get_research_template(self):
        return """You are a research-focused AI assistant specializing in information gathering, analysis, and synthesis.

## Core Identity
- Methodical and thorough in research approach
- Committed to accuracy and source verification
- Skilled in synthesizing information from multiple sources
- Objective and evidence-based in conclusions

## Research Methodology
- Begin with clear research objectives and scope definition
- Use systematic search strategies across multiple reliable sources
- Evaluate source credibility and potential bias
- Synthesize findings into coherent, well-structured reports
- Cite sources appropriately and maintain transparency"""

    def _get_productivity_template(self):
        return """You are a productivity-focused AI assistant designed to help users optimize their efficiency and effectiveness.

## Core Identity
- Organized and systematic in approach
- Focused on practical solutions and time management
- Goal-oriented and results-driven
- Adaptable to different work styles and preferences

## Primary Capabilities
- Task planning and prioritization
- Workflow optimization and automation
- Time management strategies
- Goal setting and tracking
- Resource organization and management

## Approach
- Understand user's specific context and constraints
- Provide actionable, implementable solutions
- Break down complex workspaces into manageable steps
- Suggest tools and techniques for efficiency
- Monitor progress and adjust strategies as needed"""

    def _get_general_assistant_template(self):
        return """You are a versatile AI assistant designed to provide helpful, accurate, and reliable support across a wide range of tasks.

## Core Identity
- Helpful and responsive to user needs
- Reliable source of accurate information
- Adaptable to different communication styles and preferences
- Committed to user success and satisfaction

## Service Philosophy
- Understand user intent and provide relevant, actionable assistance
- Offer comprehensive help while respecting user autonomy
- Maintain patience and clarity in all interactions
- Provide value through knowledge, guidance, and problem-solving"""

    def _find_best_template(self, role, available_templates):
        """Find the best matching template for a given role"""
        role_lower = role.lower()
        
        # Direct matches
        for template_key in available_templates:
            if template_key in role_lower or any(word in role_lower for word in template_key.split()):
                return template_key
        
        # Keyword matching
        keyword_mapping = {
            'support': 'customer support',
            'service': 'customer support',
            'help': 'customer support',
            'customer': 'customer support',
            'data': 'data analyst',
            'analysis': 'data analyst',
            'analyst': 'data analyst',
            'content': 'content creator',
            'writing': 'content creator',
            'creator': 'content creator',
            'research': 'research',
            'productivity': 'productivity',
            'assistant': 'assistant'
        }
        
        for keyword, template_key in keyword_mapping.items():
            if keyword in role_lower and template_key in available_templates:
                return template_key
        
        return 'assistant'  # Default fallback

    def _customize_template(self, base_template, data):
        """Customize template with user-specific data"""
        name = data.get('name', 'AI Assistant')
        role = data.get('primaryRole', 'Assistant')
        problem = data.get('problemStatement', '')
        target_users = data.get('targetUsers', [])
        communication_style = data.get('communicationStyle', 'professional')
        
        customized = f"""# {name} - Specialized {role}

{base_template}

## Specialized Focus
Your primary mission is to {problem}

## Target Users
You primarily serve: {', '.join(target_users) if target_users else 'general users'}

## Communication Style
Maintain a {communication_style} tone throughout all interactions.
"""
        return customized

    def _enhance_with_capabilities(self, instructions, capabilities):
        """Add capability-specific instructions"""
        if not capabilities:
            return instructions
            
        capability_guidance = "\n\n## Available Capabilities\n"
        
        capability_instructions = {
            'Text Generation': "- Create well-structured, engaging written content\n- Adapt writing style to audience and purpose\n- Ensure clarity and coherence in all generated text",
            'Knowledge Base Access': "- Retrieve relevant information from knowledge sources\n- Cross-reference multiple sources for accuracy\n- Provide properly cited information",
            'Web Search': "- Conduct targeted searches for current information\n- Evaluate source credibility and relevance\n- Synthesize findings from multiple web sources",
            'Data Analysis': "- Process and interpret numerical data\n- Create meaningful visualizations\n- Identify trends and patterns",
            'Code Generation': "- Write clean, well-documented code\n- Follow best practices for the target language\n- Provide explanations for code functionality",
            'File Analysis': "- Process various file formats efficiently\n- Extract key information and insights\n- Maintain data security and privacy"
        }
        
        for capability in capabilities:
            if capability in capability_instructions:
                capability_guidance += f"\n### {capability}\n{capability_instructions[capability]}\n"
        
        return instructions + capability_guidance

    def _add_problem_specific_guidance(self, instructions, problem):
        """Add guidance specific to the problem domain"""
        if not problem:
            return instructions
            
        problem_guidance = f"""

## Problem-Specific Guidelines
When addressing "{problem}":
- Focus on practical, actionable solutions
- Consider the user's context and constraints
- Provide step-by-step guidance when appropriate
- Anticipate common follow-up questions
- Offer resources for further learning or support
"""
        return instructions + problem_guidance


class AgentViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing agents
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Users can see their organization's agents and public agents
        return Agent.objects.filter(
            Q(organization=user.organization) | 
            Q(is_public=True)
        ).select_related('creator', 'organization', 'workspace')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AgentListSerializer
        elif self.action == 'create':
            return AgentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AgentUpdateSerializer
        elif self.action == 'execute':
            return AgentExecuteSerializer
        elif self.action == 'configuration_progress':
            return AgentConfigurationStepSerializer
        elif self.action == 'optimizations':
            return AgentOptimizationSerializer
        elif self.action == 'performance_metrics':
            return AgentDetailSerializer
        return AgentDetailSerializer
    
    def perform_create(self, serializer):
        # Let the serializer handle organization assignment
        agent = serializer.save()
        
        # Create configuration step tracker for the new agent
        AgentConfigurationStep.objects.create(agent=agent)
        return agent
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        Execute an agent with the provided input data
        """
        agent = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        input_data = serializer.validated_data.get('input_data', {})
        async_execution = serializer.validated_data.get('async_execution', False)
        enable_tools = serializer.validated_data.get('enable_tools', True)
        use_cache = serializer.validated_data.get('use_cache', True)
        
        try:
            execution = AgentService.execute_agent(
                agent=agent,
                user=request.user,
                input_data=input_data,
                async_execution=async_execution,
                enable_tools=enable_tools,
                use_cache=use_cache
            )
            return Response(
                AgentExecutionSerializer(execution).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = self.perform_create(serializer)
        
        # Use a response serializer that includes the ID
        response_serializer = AgentDetailSerializer(agent)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class AgentInstructionsViewSet(viewsets.ViewSet):
    """ViewSet for generating AI agent instructions with enhanced LLM integration"""
    permission_classes = [permissions.IsAuthenticated]
    
    def options(self, request, *args, **kwargs):
        """Handle OPTIONS requests for CORS preflight"""
        response = Response()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate instructions using async wrapper"""
        try:
            # Extract data from request
            data = request.data
            
            primary_role = data.get('primaryRole', '')
            problem_statement = data.get('problemStatement', '')
            
            logger.info(f"Agent instruction generation request: {data.get('name', 'unnamed')} - {primary_role}")
            
            if not primary_role or not problem_statement:
                return Response({
                    'error': 'Missing required fields',
                    'details': 'Primary role and problem statement are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use ONLY async version - bypass the problematic sync method completely
            service = InstructionGenerationService()
            
            # Run the async method in a new thread to avoid threading conflicts
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            import threading
            
            def run_async_in_thread():
                """Run async code in a completely separate thread with its own event loop"""
                # Create a new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    # Run the async method
                    return new_loop.run_until_complete(
                        service._generate_with_primary_llm_async(data, request.user)
                    )
                except Exception as e:
                    logger.warning(f"Async LLM generation failed: {str(e)}")
                    # Fall back to smart template on any error
                    return service._generate_with_smart_template(data)
                finally:
                    new_loop.close()
            
            # Execute in thread pool to completely isolate from current context
            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                result = future.result(timeout=30)  # 30 second timeout
            
            # Generate suggested configuration
            suggested_config = self._generate_suggested_config(data)
            
            # Build comprehensive response
            response_data = {
                'instructions': result['instructions'],
                'generation_method': result['generation_method'],
                'quality_score': result['quality_score'],
                'can_enhance': result.get('can_enhance', False),
                'suggestedConfiguration': suggested_config,
                'metadata': result.get('metadata', {})
            }
            
            # Debug logging
            logger.info(f"Sending response with generation method: {result['generation_method']}")
            logger.info(f"Instructions length: {len(result['instructions'])}")
            logger.info(f"Can enhance: {result.get('can_enhance', False)}")
            logger.info(f"Response data keys: {list(response_data.keys())}")
            
            # Create the response with CORS headers
            response = Response(response_data, status=status.HTTP_200_OK)
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            
            return response
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error in agent instruction generation: {str(e)}\n{error_traceback}")
            
            # Emergency fallback with proper format
            try:
                emergency_instructions = f"""# {data.get('name', 'AI Assistant')} - {data.get('primaryRole', 'Assistant')}

You are an AI assistant specialized in {data.get('primaryRole', 'general assistance')}.

## Your Mission
{data.get('problemStatement', 'Help users with their requests')}

## Guidelines
- Be helpful, accurate, and professional
- Stay focused on your role
- Ask clarifying questions when needed
- Provide clear, actionable guidance

## Communication Style
Maintain a {data.get('communicationStyle', 'professional').lower()} tone in all interactions."""

                response_data = {
                    'instructions': emergency_instructions,
                    'generation_method': 'emergency_fallback',
                    'quality_score': 'minimal',
                    'can_enhance': True,
                    'suggestedConfiguration': self._generate_suggested_config(data),
                    'metadata': {
                        'is_emergency_fallback': True,
                        'error': str(e),
                        'enhancement_suggestion': 'Please try again when services are restored'
                    }
                }
                
                response = Response(response_data, status=status.HTTP_200_OK)
            except Exception as final_error:
                # Absolute last resort
                logger.error(f"Emergency fallback failed: {str(final_error)}")
                response = Response({
                    'error': 'Service temporarily unavailable',
                    'fallback_available': False,
                    'details': str(e)
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Add CORS headers to error responses as well
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            
            return response
    
    def _generate_suggested_config(self, data):
        """Generate suggested configuration based on capabilities and preferences"""
        capabilities = data.get('capabilities', [])
        quality_preference = data.get('qualityPreference', 2)
        communication_style = data.get('communicationStyle', 'professional')
        output_format = data.get('outputFormat', 'markdown')
        
        # Generate suggested tools based on capabilities
        suggested_tools = []
        capability_to_tools = {
            'Web Browsing': ['web-search', 'url-reader', 'web-browser'],
            'Data Analysis': ['data-analysis', 'chart-generator', 'file-reader'],
            'Document Processing': ['document-processor', 'document-retrieval'],
            'Knowledge Base Access': ['knowledge-base', 'document-retrieval'],
            'Text Generation': ['text-generator'],
            'Code Generation': ['code-interpreter', 'code-execution'],
            'File Analysis': ['file-analyzer', 'file-reader'],
            'Email Integration': ['email-integration'],
            'Calendar Integration': ['calendar-integration'],
            'Task Management': ['task-manager']
        }
        
        for capability in capabilities:
            if capability in capability_to_tools:
                suggested_tools.extend(capability_to_tools[capability])
        
        # Remove duplicates while preserving order
        suggested_tools = list(dict.fromkeys(suggested_tools))
        
        # Generate memory settings based on quality preference
        memory_settings = {
            'enabled': True,
            'maxTokens': 6000 if quality_preference == 3 else (3000 if quality_preference == 2 else 1500),
            'relevanceThreshold': 0.8 if quality_preference == 3 else (0.6 if quality_preference == 2 else 0.4)
        }
        
        # Generate response style based on inputs
        tone_mapping = {
            'professional': 'professional',
            'friendly': 'friendly',
            'technical': 'technical',
            'simple': 'simple',
            'casual': 'casual'
        }
        
        response_style = {
            'tone': tone_mapping.get(communication_style.lower(), 'professional'),
            'format': 'detailed' if 'detail' in output_format.lower() else 'concise',
            'creativity': 80 if quality_preference == 3 else (60 if quality_preference == 2 else 40)
        }
        
        return {
            'tools': suggested_tools,
            'memory': memory_settings,
            'responseStyle': response_style
        }


# Keep all other existing ViewSets unchanged
class AgentToolViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing agent tools
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AgentTool.objects.filter(
            agent__organization=self.request.user.organization
        )
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AgentToolCreateSerializer
        return AgentToolSerializer
    
    def perform_create(self, serializer):
        agent_id = self.kwargs.get('agent_pk')
        agent = get_object_or_404(
            Agent, 
            id=agent_id, 
            organization=self.request.user.organization
        )
        serializer.save(agent=agent)


class AgentParameterViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing agent parameters
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AgentParameter.objects.filter(
            agent__organization=self.request.user.organization
        )
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AgentParameterCreateSerializer
        return AgentParameterSerializer
    
    def perform_create(self, serializer):
        agent_id = self.kwargs.get('agent_pk')
        agent = get_object_or_404(
            Agent, 
            id=agent_id, 
            organization=self.request.user.organization
        )
        serializer.save(agent=agent)


class AgentConfigurationStepViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing agent configuration steps
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentConfigurationStepSerializer
    
    def get_queryset(self):
        user = self.request.user
        return AgentConfigurationStep.objects.filter(
            agent__organization=user.organization
        ).select_related('agent')
    
    @action(detail=True, methods=['post'])
    def complete_step(self, request, pk=None):
        """
        Mark a specific step as completed
        """
        config_step = self.get_object()
        step_number = request.data.get('step_number')
        
        if step_number not in [1, 2, 3, 4]:
            return Response(
                {'error': 'Invalid step number. Must be between 1 and 4.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the specified step
        setattr(config_step, f'step_{step_number}_completed', True)
        config_step.update_completion_status()
        
        return Response(
            self.get_serializer(config_step).data,
            status=status.HTTP_200_OK
        )


class AgentOptimizationViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing agent optimizations
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentOptimizationSerializer
    
    def get_queryset(self):
        user = self.request.user
        return AgentOptimization.objects.filter(
            agent__organization=user.organization
        ).select_related('agent')
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """
        Apply an optimization suggestion
        """
        optimization = self.get_object()
        
        if optimization.applied:
            return Response(
                {'error': 'This optimization has already been applied.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        optimization.apply_optimization()
        
        # Update the actual impact if provided
        actual_impact = request.data.get('actual_impact')
        if actual_impact:
            optimization.actual_impact = actual_impact
            optimization.save()
        
        return Response(
            self.get_serializer(optimization).data,
            status=status.HTTP_200_OK
        )


class AgentExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for viewing agent executions
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentExecutionSerializer
    
    def get_queryset(self):
        user = self.request.user
        # Users can see executions for their organization's agents
        return AgentExecution.objects.filter(
            agent__organization=user.organization
        ).select_related('agent', 'user', 'model_used')


class AgentToolExecutionViewSet(viewsets.ModelViewSet):
    """
    API endpoints for viewing agent tool executions
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentToolExecutionSerializer
    
    def get_queryset(self):
        user = self.request.user
        return AgentToolExecution.objects.filter(
            agent_execution__agent__organization=user.organization
        ).select_related('agent_execution', 'agent_execution__agent')
    
    @action(detail=False, methods=['get'])
    def by_execution(self, request):
        """
        Get all tool executions for a specific agent execution
        """
        execution_id = request.query_params.get('execution_id')
        if not execution_id:
            return Response(
                {'error': 'execution_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        execution = get_object_or_404(
            AgentExecution, 
            id=execution_id,
            agent__organization=request.user.organization
        )
        
        tool_executions = AgentToolExecution.objects.filter(agent_execution=execution)
        serializer = self.get_serializer(tool_executions, many=True)
        return Response(serializer.data)


# Additional utility functions for enhanced instruction generation
class AgentInstructionEnhancer:
    """Utility class for enhancing and refining agent instructions"""
    
    @staticmethod
    def validate_instructions(instructions):
        """Validate generated instructions for completeness and quality"""
        validation_results = {
            'is_valid': True,
            'score': 0,
            'issues': [],
            'suggestions': []
        }
        
        # Check minimum length
        if len(instructions) < 200:
            validation_results['issues'].append('Instructions are too short')
            validation_results['is_valid'] = False
        else:
            validation_results['score'] += 20
        
        # Check for key sections
        required_sections = [
            ('identity', ['identity', 'role', 'purpose']),
            ('guidelines', ['guideline', 'rule', 'protocol']),
            ('communication', ['communication', 'tone', 'style']),
            ('capabilities', ['capability', 'skill', 'function'])
        ]
        
        instructions_lower = instructions.lower()
        for section_name, keywords in required_sections:
            if any(keyword in instructions_lower for keyword in keywords):
                validation_results['score'] += 15
            else:
                validation_results['suggestions'].append(f'Consider adding {section_name} section')
        
        # Check for structure (headers, bullet points)
        if '#' in instructions or '##' in instructions:
            validation_results['score'] += 10
        if '-' in instructions or '*' in instructions:
            validation_results['score'] += 10
        
        # Check for specific directives
        directive_keywords = ['should', 'must', 'always', 'never', 'when', 'if']
        directive_count = sum(1 for keyword in directive_keywords if keyword in instructions_lower)
        if directive_count >= 5:
            validation_results['score'] += 15
        elif directive_count >= 3:
            validation_results['score'] += 10
        else:
            validation_results['suggestions'].append('Add more specific behavioral directives')
        
        # Final score assessment
        if validation_results['score'] >= 80:
            validation_results['quality'] = 'excellent'
        elif validation_results['score'] >= 60:
            validation_results['quality'] = 'good'
        elif validation_results['score'] >= 40:
            validation_results['quality'] = 'acceptable'
        else:
            validation_results['quality'] = 'needs_improvement'
            validation_results['is_valid'] = False
        
        return validation_results
    
    @staticmethod
    def enhance_instructions_with_examples(instructions, problem_domain):
        """Add domain-specific examples to instructions"""
        example_templates = {
            'customer support': """
## Example Interactions

**Typical Query**: "I'm having trouble with my account login"
**Approach**: 
1. Acknowledge the frustration
2. Gather specific details (error messages, device, browser)
3. Provide step-by-step troubleshooting
4. Offer escalation if needed

**Sample Response**: "I understand how frustrating login issues can be. Let me help you resolve this quickly. Could you tell me what error message you're seeing, and which device/browser you're using?"
""",
            'data analysis': """
## Example Analysis Workflow

**Data Request**: "Can you help me understand sales trends?"
**Approach**:
1. Clarify data scope (time period, regions, products)
2. Assess data quality and completeness
3. Recommend appropriate visualization methods
4. Identify key trends and patterns
5. Provide actionable insights

**Sample Response**: "I'd be happy to help analyze your sales trends. To provide the most relevant insights, could you specify the time period and any particular products or regions you're most interested in?"
""",
            'general': """
## Example Interactions

**Typical Query**: "Can you help me with [specific task]?"
**Approach**:
1. Understand the specific context and requirements
2. Break down complex requests into manageable steps
3. Provide clear, actionable guidance
4. Offer to clarify or expand on any points
5. Suggest related resources or next steps

**Sample Response**: "I'd be glad to help you with that. To provide the most relevant assistance, could you share a bit more context about your specific situation and what you're hoping to achieve?"
"""
        }
        
        # Determine best example set
        domain_key = 'general'
        for key in example_templates:
            if key in problem_domain.lower():
                domain_key = key
                break
        
        return instructions + example_templates.get(domain_key, example_templates['general'])
    
    @staticmethod
    def add_quality_assurance_guidelines(instructions):
        """Add quality assurance and continuous improvement guidelines"""
        qa_section = """
        ## Quality Assurance Guidelines

### Response Quality Standards
- **Accuracy**: Verify information before providing answers
- **Completeness**: Address all aspects of user queries
- **Clarity**: Use clear, understandable language
- **Relevance**: Stay focused on user needs and context
- **Timeliness**: Respond promptly and efficiently

### Continuous Improvement
- Learn from user feedback and interactions
- Adapt communication style to user preferences
- Identify knowledge gaps and areas for enhancement
- Maintain consistency in service quality
- Proactively suggest improvements and optimizations

### Error Handling
- Acknowledge mistakes openly and correct them immediately
- Apologize sincerely for any confusion or inconvenience
- Provide alternative solutions when primary approaches fail
- Learn from errors to prevent similar issues in the future
- Escalate to human oversight when necessary

### Performance Monitoring
- Track response accuracy and user satisfaction
- Monitor response times and efficiency metrics
- Identify patterns in user queries and needs
- Continuously refine approaches based on outcomes
- Maintain detailed logs for quality review and improvement
"""
        return instructions + qa_section

    def test_llm_router_connection(self, user=None):
        """Test if the LLM router is working properly"""
        try:
            logger.info("Testing LLM router connection...")
            
            test_data = {
                'name': 'Test Agent',
                'primaryRole': 'Assistant',
                'problemStatement': 'Provide helpful responses to user queries',
                'targetUsers': ['General Users'],
                'communicationStyle': 'professional',
                'outputFormat': 'markdown',
                'qualityPreference': 2,
                'capabilities': ['Text Generation'],
                'routingRule': 'balanced',
                'additionalContext': 'This is a test request to verify LLM router functionality'
            }
            
            result = self._generate_with_primary_llm(test_data, user)
            
            if result and result.get('instructions'):
                logger.info("✅ LLM router test successful")
                return True, f"Generated {len(result['instructions'])} characters"
            else:
                logger.error("❌ LLM router test failed - no instructions generated")
                return False, "No instructions generated"
                
        except Exception as e:
            logger.error(f"❌ LLM router test failed: {str(e)}")
            return False, str(e)