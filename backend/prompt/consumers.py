# File: backend/prompt/consumers.py
# Updated to work with the new model structure and unified context management

import json
import logging
import time
import uuid
import traceback
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal
from core.utils.json_utils import safe_json_serialize
from .models import PromptSession, Prompt

# Updated imports - use the main llm_router with cost protection
from modelhub.services.llm_router import (
    execute_with_cost_optimization, 
    OptimizationStrategy, 
    RequestContext,
    ModelRouter
)
from modelhub.services.complexity.analyzer import EnhancedComplexityAnalyzer

User = get_user_model()
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat functionality"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.session_id = None
        self.connection_id = None
        self.context_type = None
        self.workspace_id = None
        # Track this consumer instance
        self.instance_id = id(self)
        logger.info(f"🏗️ [WEBSOCKET-INSTANCE] New ChatConsumer instance created: {self.instance_id}")

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Extract session_id from URL path (matches routing pattern)
        self.session_id = self.scope.get('url_route', {}).get('kwargs', {}).get('session_id')
        
        # Extract connection parameters from query string
        query_string = self.scope.get('query_string', b'').decode()
        query_params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
        
        self.connection_id = query_params.get('conn_id')
        self.context_type = query_params.get('context_type')
        self.workspace_id = query_params.get('workspace_id')
        
        logger.info(f"🔌 [WEBSOCKET-CONNECT] WebSocket connection accepted for user {self.user.email}")
        logger.info(f"🔌 [WEBSOCKET-CONNECT] Connection parameters: session_id={self.session_id}, conn_id={self.connection_id}, context_type={self.context_type}, workspace_id={self.workspace_id}")
        logger.info(f"🔌 [WEBSOCKET-CONNECT] WebSocket instance ID: {id(self)}")
        
        # Accept the connection
        await self.accept()
        
        # Send connection confirmation to frontend
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
            'connection_id': self.connection_id,
            'timestamp': time.time()
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        user_identifier = getattr(self.user, 'email', getattr(self.user, 'username', 'Unknown')) if hasattr(self, 'user') else 'Unknown'
        logger.info(f"WebSocket disconnected for user {user_identifier}, session {self.session_id}, code: {close_code}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        logger.info(f"📨 [WEBSOCKET-INSTANCE] Message received on instance {self.instance_id}: {text_data[:100]}...")
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'message':
                logger.info(f"💬 [WEBSOCKET-INSTANCE] Processing message on instance {self.instance_id}")
                await self.handle_chat_message(data)
            elif message_type == 'clear_history':
                await self.handle_clear_history(data)
            elif message_type == 'set_optimization':
                await self.handle_set_optimization_strategy(data)
            elif message_type == 'ping':
                logger.info(f"🏓 [WEBSOCKET-INSTANCE] Processing ping on instance {self.instance_id}")
                await self.send_message({'type': 'pong'})
            else:
                logger.warning(f"Unknown message type: {message_type} from user {self.user.email}")
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            await self.send_error("Internal server error")

    async def handle_chat_message(self, data):
        """Process chat messages with intelligent routing and streaming support"""
        try:
            # Extract message data using the frontend's field names
            message_text = data.get('content', '').strip()
            context = data.get('context', 'default')
            metadata = data.get('metadata', {})
            optimization_strategy = data.get('optimization_strategy', 'balanced')
            
            if not message_text:
                await self.send_error("Message cannot be empty")
                return
            
            # Generate unique message ID for this response
            message_id = str(uuid.uuid4())
            
            # Get or create session (reuse existing session for this user/context)
            session_data = await self.get_or_create_session(
                getattr(self, 'session_id', None), 
                str(self.user.id), 
                context
            )
            self.session_id = session_data['id']
            
            # CRITICAL FIX: Store the user message BEFORE execution
            # This ensures the current message is available in context preparation
            prompt_id = await self.create_prompt(self.session_id, str(self.user.id), message_text, {
                'optimization_strategy': optimization_strategy,
                'context': context,
                'metadata': metadata
            })
            
            # Get conversation history AFTER storing current message
            # This will include the current message as the last entry
            conversation_history = await self.get_conversation_history(self.session_id, limit=10)
            
            # Execute streaming request with proper context handling
            await self.execute_streaming_request(
                message_id=message_id,
                prompt_id=prompt_id,
                message_text=message_text,
                context=context,
                metadata=metadata,
                optimization_strategy=optimization_strategy,
                conversation_history=conversation_history
            )
            
        except Exception as e:
            logger.error(f"Error in handle_chat_message: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await self.send_error("Failed to process message")
    
    async def execute_streaming_request(self, message_id, prompt_id, message_text, context, metadata, optimization_strategy, conversation_history=None):
        """Execute LLM request with streaming support"""
        try:
            logger.info(f"🚀 [WEBSOCKET-INSTANCE] Starting streaming execution on instance {self.instance_id} for message_id: {message_id}")
            # Send initial processing status
            await self.send(text_data=json.dumps({
                'type': 'status',
                'message_id': message_id,
                'status': 'processing',
                'message': 'Processing your request...'
            }))
            
            # Get prompt object for execution
            prompt = await self.get_prompt_object(prompt_id)
            
            # Get user and organization for context
            user = prompt.user
            organization = prompt.session.workspace.organization
            
            # Prepare messages for LLM with proper context separation
            messages = []
            
            # Add system message with clear instructions
            system_content = """You are an AI assistant. When provided with conversation history, use it as context to inform your responses, but only respond to the CURRENT USER QUESTION.

    IMPORTANT INSTRUCTIONS:
    - The conversation history is provided for context only
    - Do NOT respond to old messages from the history
    - Focus on answering the current user's question
    - Reference previous conversation naturally when relevant
    - If asked about "what we discussed" or similar, refer to the conversation history
    - Maintain a helpful, professional tone"""

            messages.append({
                'role': 'system',
                'content': system_content
            })
            
            # Format conversation history with clear separation
            if conversation_history and len(conversation_history) > 1:
                # Separate current message from history
                historical_messages = conversation_history[:-1]  # All except last
                current_message = conversation_history[-1]      # Last message (current)
                
                # Add historical context
                if historical_messages:
                    history_content = "## CONVERSATION HISTORY (For Reference Only)\n"
                    history_content += "The following is previous conversation history. Use this as context but DO NOT respond to these old messages:\n\n"
                    
                    for msg in historical_messages:
                        role = msg['role'].title()
                        content = msg['content']
                        history_content += f"**{role}**: {content}\n"
                    
                    history_content += "\n---\n\n"
                    history_content += "## CURRENT USER QUESTION\n"
                    history_content += "Please respond to this current question, using the conversation history above for context:\n\n"
                    history_content += f"**{current_message['role'].title()}**: {current_message['content']}"
                    
                    messages.append({
                        'role': 'system',
                        'content': history_content
                    })
                
                # Add the current user message as the actual user message
                messages.append({
                    'role': 'user',
                    'content': current_message['content']
                })
            else:
                # No history or only current message, add directly
                messages.append({
                    'role': 'user',
                    'content': message_text
                })
            
            # Log the user prompt being sent to LLM
            logger.info(f"User prompt: {message_text}")
            if conversation_history and len(conversation_history) > 1:
                logger.info(f"Context: {len(conversation_history)-1} previous messages in conversation history")
            
            # Create request context with session information
            # Note: RequestContext only accepts specific parameters (see modelhub/services/llm_router.py)
            # The session_id should be the prompt session ID, not the context session ID
            request_context = RequestContext(
                session_id=str(prompt.session.id),  # Use prompt session ID as entity_id
                entity_type='platform_chat',  # Specify entity type
                prompt_id=str(prompt.id),      # Add prompt ID for context linking
                user_preferences=metadata.get('preferences', {}),
                organization_id=str(organization.id),  # Add organization ID
                max_tokens=2048,
                conversation_history=conversation_history
            )
            
            # Map optimization strategy
            strategy_mapping = {
                'cost': OptimizationStrategy.COST_FIRST,  # Corrected from COST_OPTIMIZED
                'balanced': OptimizationStrategy.BALANCED,
                'quality': OptimizationStrategy.QUALITY_FIRST,
                'speed': OptimizationStrategy.PERFORMANCE_FIRST  # Corrected from SPEED_OPTIMIZED
            }
            strategy = strategy_mapping.get(optimization_strategy, OptimizationStrategy.BALANCED)
            
            # Execute with cost optimization and streaming
            response_chunks = []
            
            async def stream_callback(chunk):
                """Handle streaming chunks"""
                nonlocal response_chunks
                
                if hasattr(chunk, 'content') and chunk.content:
                    response_chunks.append(chunk.content)
                    
                    # Send chunk to frontend
                    chunk_data = {
                        'type': 'chunk',
                        'message_id': message_id,
                        'content': chunk.content,
                        'timestamp': time.time()
                    }
                    logger.debug(f"📤 [WEBSOCKET] Sending chunk to frontend on instance {id(self)}: {chunk_data}")
                    await self.send(text_data=json.dumps(chunk_data))
                    logger.debug(f"✅ [WEBSOCKET] Chunk sent successfully from instance {id(self)}")
            
            # Execute the LLM request
            response, execution_metadata = await execute_with_cost_optimization(
                organization=organization,
                model_type='TEXT',
                request_context=request_context,
                strategy=strategy,
                messages=messages,
                stream=True,
                stream_callback=stream_callback,
                temperature=0.7,
                max_tokens=2048
            )
            
            # Get the actual cost from the response object or execution metadata
            total_cost = Decimal('0.00')
            if hasattr(response, 'cost') and response.cost:
                total_cost = response.cost
            elif 'cost_breakdown' in execution_metadata and 'total' in execution_metadata['cost_breakdown']:
                total_cost = Decimal(str(execution_metadata['cost_breakdown']['total']))
            elif 'total_cost' in execution_metadata:
                total_cost = Decimal(str(execution_metadata['total_cost']))
            
            # Combine response chunks (no filtering needed since provider fixed at source)
            if response_chunks:
                full_response = ''.join(response_chunks)
            elif hasattr(response, 'content') and response.content:
                full_response = response.content
            else:
                full_response = str(response)
            
            # Log model usage summary
            logger.debug(f"Model used: {execution_metadata.get('selected_model', 'unknown')} | "
                       f"Provider: {execution_metadata.get('provider', 'unknown')} | "
                       f"Cost: ${float(total_cost):.4f}")
            
            # Update prompt with response and metadata
            await self.update_prompt_with_response(prompt_id, full_response, execution_metadata, total_cost)
            
            # Extract token counts from execution metadata
            tokens_prompt = execution_metadata.get('tokens_prompt', 0)
            tokens_completion = execution_metadata.get('tokens_completion', 0)
            tokens_total = execution_metadata.get('tokens_used', tokens_prompt + tokens_completion)
            
            # Get provider information
            provider = execution_metadata.get('provider', 'unknown')
            
            # Send completion status with detailed metadata
            completion_data = {
                'type': 'complete',
                'message_id': message_id,
                'content': full_response,  # Include the actual response content
                'total_cost': float(total_cost),
                'model_used': execution_metadata.get('selected_model', 'unknown'),
                'tokens_used': tokens_total,
                'metadata': {
                    'provider': provider,
                    'tokens_prompt': tokens_prompt,
                    'tokens_completion': tokens_completion,
                    'execution_time': execution_metadata.get('execution_time', 0),
                    'model_details': execution_metadata.get('model_details', {})
                },
                'timestamp': time.time()
            }
            logger.debug(f"🏁 [WEBSOCKET] Sending completion to frontend on instance {id(self)}: {completion_data}")
            await self.send(text_data=json.dumps(completion_data))
            logger.debug(f"✅ [WEBSOCKET] Completion sent successfully from instance {id(self)}")
            
        except Exception as e:
            logger.error(f"Error in streaming execution: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Send error status with proper error object structure
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message_id': message_id,
                'error': {
                    'message': str(e),
                    'type': e.__class__.__name__,
                    'code': 'EXECUTION_ERROR'
                },
                'timestamp': time.time()
            }))

    async def simulate_streaming_response(self, response, message_id, prompt_id, selected_model, selected_provider, execution_metadata=None):
        """Simulate streaming response from the completed response"""
        try:
            # Extract content from response
            content = ""
            if hasattr(response, 'content') and response.content:
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = "I'm ready to help! How can I assist you today?"
            
            # Validate content
            if not content or len(content.strip()) < 5:
                logger.warning(f"Content too short: '{content}', using fallback")
                content = f"Hello! I'm your AI assistant using {selected_model}. How can I assist you today?"
            

            
            # Split content into chunks for streaming effect
            words = content.split()
            chunk_size = max(1, min(4, len(words) // 10))  # Adaptive chunk size
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                if i > 0:
                    chunk_text = " " + chunk_text
                
                # Send chunk to client
                await self.send_message({
                    'type': 'stream_chunk',
                    'message_id': message_id,
                    'content': chunk_text,
                    'is_complete': False
                })
                
                # Natural streaming delay
                await asyncio.sleep(0.05)
            
            # Calculate costs from execution metadata
            cost_breakdown = execution_metadata.get('cost_breakdown', {})
            total_cost = cost_breakdown.get('total', 0.0)
            
            # Get token counts from response
            tokens_input = getattr(response, 'tokens_input', 0)
            tokens_output = getattr(response, 'tokens_output', 0)
            
            # Send final complete message
            await self.send_complete_message(
                message_id=message_id,
                content=content,
                selected_model=selected_model,
                selected_provider=selected_provider,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                total_cost=total_cost,
                execution_metadata=execution_metadata
            )
            
        except Exception as e:
            logger.error(f"Error in streaming simulation: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Emergency fallback
            fallback_content = "I apologize, but I'm experiencing technical difficulties. Please try your question again."
            await self.send_message({
                'type': 'stream_chunk',
                'message_id': message_id,
                'content': fallback_content,
                'is_complete': True
            })

    async def send_complete_message(self, message_id, content, selected_model, selected_provider, tokens_input, tokens_output, total_cost, execution_metadata=None):
        """Send the final complete message that frontend expects"""
        
        # Get context info from metadata
        context_metadata = execution_metadata.get('context', {}) if execution_metadata else {}
        
        await self.send_message({
            'type': 'message',
            'message': {
                'id': message_id,
                'content': content,
                'role': 'assistant',
                'timestamp': time.time(),
                'model': {
                    'name': selected_model,
                    'provider': selected_provider
                },
                'tokens': {
                    'total': tokens_input + tokens_output,
                    'prompt': tokens_input,
                    'completion': tokens_output
                },
                'cost': float(total_cost),
                'optimization': {
                    'strategy_used': execution_metadata.get('optimization_strategy', 'balanced') if execution_metadata else 'balanced',
                    'context_tokens': context_metadata.get('tokens_used', 0),
                    'context_cost': float(context_metadata.get('preparation_cost', 0.0)),
                    'cache_hit': context_metadata.get('cache_hit', False)
                }
            }
        })

    async def handle_clear_history(self, data):
        """Handle clear chat history request"""
        try:
            context = data.get('context', 'default')
            
            # Clear history in database
            if self.session_id:
                await self.clear_session_prompts(self.session_id)
            
            # Notify client
            await self.send_message({
                'type': 'history_cleared'
            })
            
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            await self.send_error("Failed to clear history")

    async def handle_set_optimization_strategy(self, data):
        """Handle optimization strategy change"""
        try:
            strategy = data.get('strategy', 'balanced')

            
            # Update session metadata with new strategy
            if self.session_id:
                await self.update_session_preferences(self.session_id, {'optimization_strategy': strategy})
            
        except Exception as e:
            logger.error(f"Error setting optimization strategy: {e}")

    async def send_message(self, message_dict):
        """Send message to WebSocket client"""
        clean_message = safe_json_serialize(message_dict)
        await self.send(text_data=json.dumps(clean_message))

    async def send_error(self, error_message):
        """Send error message to client with consistent error object structure"""
        await self.send_message({
            'type': 'error',
            'message_id': str(uuid.uuid4()),  # Generate a message ID for tracking
            'error': {
                'message': error_message,
                'type': 'ServerError',
                'code': 'GENERAL_ERROR'
            },
            'timestamp': time.time()
        })

    # Method to update prompt with response and metadata
    @database_sync_to_async
    def update_prompt_with_response(self, prompt_id, response_text, execution_metadata, total_cost):
        """Update prompt with response and execution metadata"""
        try:
            from .models import Prompt
            from context_manager.models import ContextEntry
            
            # Get the prompt object
            prompt = Prompt.objects.get(id=prompt_id)
            
            # Update execution metadata
            metadata = prompt.execution_metadata or {}
            metadata.update(execution_metadata or {})
            metadata['total_cost'] = str(total_cost)  # Store as string for Decimal compatibility
            metadata['completed_at'] = timezone.now().isoformat()
            prompt.execution_metadata = metadata
            prompt.save(update_fields=['execution_metadata'])
            
            # Create response context entry
            from context_manager.models import ContextSession
            
            # Only create a context entry if we have a valid context session
            if prompt.session.context_session_id:
                # Get the context session using the ID from prompt.session
                context_session = ContextSession.objects.get(id=prompt.session.context_session_id)
                
                # Extract token counts from metadata with proper type checking
                tokens_input = 0
                tokens_output = 0
                
                # Safely extract token counts from various possible locations in metadata
                if isinstance(metadata, dict):
                    # Direct token counts
                    if 'tokens_input' in metadata and isinstance(metadata['tokens_input'], (int, float)):
                        tokens_input = metadata['tokens_input']
                    if 'tokens_output' in metadata and isinstance(metadata['tokens_output'], (int, float)):
                        tokens_output = metadata['tokens_output']
                    
                    # Token counts in cost object
                    if 'cost' in metadata and isinstance(metadata['cost'], dict):
                        if 'tokens_input' in metadata['cost'] and isinstance(metadata['cost']['tokens_input'], (int, float)):
                            tokens_input = metadata['cost']['tokens_input']
                        if 'tokens_output' in metadata['cost'] and isinstance(metadata['cost']['tokens_output'], (int, float)):
                            tokens_output = metadata['cost']['tokens_output']
                
                # Safely extract context preparation cost
                context_preparation_cost = 0
                embedding_cost = 0
                if isinstance(metadata, dict) and 'context' in metadata and isinstance(metadata['context'], dict):
                    if 'preparation_cost' in metadata['context']:
                        context_preparation_cost = metadata['context']['preparation_cost']
                    if 'embedding_cost' in metadata['context']:
                        embedding_cost = metadata['context']['embedding_cost']
                
                # Create context entry with all cost-related fields
                ContextEntry.objects.create(
                    organization_id=prompt.session.workspace.organization_id,
                    session=context_session,
                    source_entity_id=prompt_id,
                    source_entity_type='prompt',
                    content=response_text,
                    role='assistant',
                    model_used=metadata.get('selected_model', 'unknown') if isinstance(metadata, dict) else 'unknown',
                    total_cost=total_cost,
                    context_tokens_used=tokens_input + tokens_output,
                    context_preparation_cost=context_preparation_cost,
                    embedding_cost=embedding_cost,
                    execution_metadata={
                        'prompt_id': str(prompt_id),
                        'completed_at': metadata.get('completed_at'),
                        'tokens_input': tokens_input,
                        'tokens_output': tokens_output,
                        'provider': metadata.get('provider', metadata.get('selected_provider', 'unknown'))
                    }
                )
            else:
                logger.warning(f"No context_session_id found for prompt {prompt_id}, skipping context entry creation")
            
            
            return True
        except Exception as e:
            logger.error(f"Error updating prompt with response: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    @database_sync_to_async
    def get_or_create_session(self, session_id, user_id, context):
        """Get existing session or create a new one using new model structure"""
        try:
            user = User.objects.get(id=user_id)
            org = user.default_org
            
            if not org:
                raise Exception(f"User {user.email} has no organization configured")
            
            # Get or create workspace
            from workspaces.models import Workspace
            workspace = Workspace.objects.filter(organization=org, is_active=True).first()
            
            if not workspace:
                workspace = Workspace.objects.create(
                    name="Default Chat Workspace",
                    description="Auto-created workspace for AI chat sessions",
                    organization=org,
                    owner=user,
                    is_active=True
                )
            
            # Create or get session
            if session_id:
                try:
                    session = PromptSession.objects.get(id=session_id, creator=user)
                    
                    # Ensure existing session has a context session ID
                    if not session.context_session_id:
                        from context_manager.models import ContextSession
                        context_session = ContextSession.objects.create(
                            organization_id=org.id,
                            session_type='chat',
                            entity_id=session.id,
                            entity_type='prompt_session',
                            tier='starter'  # Default tier
                        )
                        session.context_session_id = context_session.id
                        session.save(update_fields=['context_session_id'])

                    
                    return {'id': str(session.id), 'title': session.title}
                except PromptSession.DoesNotExist:
                    pass
            
            # Create new session with updated model structure
            title = f"Chat - {context.capitalize()}" if context != 'default' else "New Chat"
            
            session = PromptSession.objects.create(
                creator=user,
                workspace=workspace,
                title=title,
                description=f"AI chat session in {context} context",
                model_type=PromptSession.ModelType.TEXT,
                status=PromptSession.Status.DRAFT  # Will be set to ACTIVE on first prompt
            )
            
            # Create corresponding ContextSession for conversation history
            from context_manager.models import ContextSession
            context_session = ContextSession.objects.create(
                organization_id=org.id,
                session_type='chat',
                entity_id=session.id,
                entity_type='prompt_session',
                tier='starter'  # Default tier, can be updated based on org settings
            )
            
            # Link the context session to the prompt session
            session.context_session_id = context_session.id
            session.save(update_fields=['context_session_id'])
            
            return {'id': str(session.id), 'title': session.title}
            
        except Exception as e:
            logger.error(f"Error in get_or_create_session: {str(e)}")
            raise e

    @database_sync_to_async
    def create_prompt(self, session_id, user_id, message, metadata):
        """Create a new prompt using the updated model structure"""
        try:
            session = PromptSession.objects.get(id=session_id)
            user = User.objects.get(id=user_id)
            
            prompt = Prompt.objects.create(
                session=session,
                user=user,
                input_text=message,
                execution_metadata=metadata or {},
                importance_score=1.0,  # Default importance
                is_starred=False
            )
            
            # Create user context entry for conversation history
            if session.context_session_id:
                from context_manager.models import ContextEntry, ContextSession
                context_session = ContextSession.objects.get(id=session.context_session_id)
                
                ContextEntry.objects.create(
                    organization_id=session.workspace.organization_id,
                    session=context_session,
                    source_entity_id=prompt.id,
                    source_entity_type='prompt',
                    content=message,
                    role='user',
                    execution_metadata={
                        'prompt_id': str(prompt.id),
                        'created_at': prompt.created_at.isoformat(),
                    }
                )
            
            return str(prompt.id)
            
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}")
            raise e

    @database_sync_to_async
    def get_prompt_object(self, prompt_id):
        """Get prompt object from database"""
        try:
            prompt = Prompt.objects.select_related(
                'session',
                'session__workspace',
                'session__workspace__organization',
                'user'
            ).get(id=prompt_id)
            return prompt
        except Prompt.DoesNotExist:
            logger.error(f"Prompt {prompt_id} not found")
            raise
        except Exception as e:
            logger.error(f"Error getting prompt {prompt_id}: {e}")
            raise

    @database_sync_to_async
    def get_conversation_history(self, session_id, limit=5):
        """Get recent conversation history using context entries"""
        try:
            # Get the session to access context_session_id
            session = PromptSession.objects.get(id=session_id)
            
            if not session.context_session_id:
                return []
            
            # Get conversation context from the unified system
            from context_manager.models import ContextEntry
            entries = ContextEntry.objects.filter(
                session_id=session.context_session_id
            ).order_by('-created_at')[:limit * 2]  # Get more to account for user/assistant pairs
            
            history = []
            for entry in reversed(entries):
                history.append({
                    'role': entry.role,
                    'content': entry.content,
                    'timestamp': entry.created_at.isoformat()
                })
            
            return history[-limit:] if len(history) > limit else history
            
        except Exception as e:
            logger.warning(f"Error getting conversation history: {e}")
            return []

    @database_sync_to_async
    def update_session_preferences(self, session_id, preferences):
        """Update session with optimization preferences"""
        try:
            session = PromptSession.objects.get(id=session_id)
            
            # Store preferences in a way that's compatible with the new structure
            # You might want to add a preferences field to the model, or store in description
            session.description = f"{session.description} | Preferences: {preferences}"
            session.save()
            
        except Exception as e:
            logger.error(f"Error updating session preferences: {e}")

    @database_sync_to_async
    def clear_session_prompts(self, session_id):
        """Clear all prompts in a session (soft delete)"""
        try:
            # Soft delete prompts
            Prompt.objects.filter(session_id=session_id).update(is_active=False)
            
            # Also clear context entries if needed
            session = PromptSession.objects.get(id=session_id)
            if session.context_session_id:
                from context_manager.models import ContextEntry
                ContextEntry.objects.filter(session_id=session.context_session_id).update(is_active=False)
            

            
        except Exception as e:
            logger.error(f"Error clearing session prompts: {e}")