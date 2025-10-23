import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from .models import AgentExecution, AgentToolExecution

logger = logging.getLogger(__name__)

class AgentExecutionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for agent execution updates.
    
    This consumer allows clients to subscribe to real-time updates for a specific
    agent execution. It provides information about execution status, progress,
    and tool execution results.
    """
    
    def send_execution_update(self, execution_id, status, progress):
        """
        Send an execution update to the WebSocket.
        
        Args:
            execution_id (str): The ID of the execution to update
            status (str): The new status of the execution
            progress (int): The progress percentage (0-100)
        """
        # Format the update data
        update_data = {
            'id': str(execution_id),
            'status': status,
            'progress': progress
        }
        
        # Get the status display name if possible
        try:
            from .models import AgentExecution
            update_data['status_display'] = dict(AgentExecution.STATUS_CHOICES).get(status, status)
        except Exception:
            update_data['status_display'] = status
        
        # Send the update to the WebSocket
        self.send(text_data=json.dumps({
            'type': 'execution_update',
            'data': update_data
        }))
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Get the execution_id from the URL route
        self.execution_id = self.scope['url_route']['kwargs'].get('execution_id')
        
        if not self.execution_id:
            logger.error("No execution_id provided in WebSocket connection")
            await self.close()
            return
            
        # Verify the user has access to this execution
        has_access = await self.check_execution_access()
        if not has_access:
            logger.warning(f"User {self.user.email} attempted to access unauthorized execution {self.execution_id}")
            await self.close()
            return
        
        # Create a unique group name for this execution
        self.execution_group_name = f"agent_execution_{self.execution_id}"
        
        # Join the execution group
        await self.channel_layer.group_add(
            self.execution_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        logger.info(f"WebSocket connection accepted for user {self.user.email}, execution {self.execution_id}")
        
        # Send initial execution state
        await self.send_initial_state()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'execution_group_name'):
            # Leave the execution group
            await self.channel_layer.group_discard(
                self.execution_group_name,
                self.channel_name
            )
        
        user_identifier = getattr(self.user, 'email', getattr(self.user, 'username', 'Unknown')) if hasattr(self, 'user') else 'Unknown'
        logger.info(f"WebSocket disconnected for user {user_identifier}, execution {getattr(self, 'execution_id', 'Unknown')}, code: {close_code}")
    
    async def receive(self, text_data):
        """Handle incoming messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            else:
                logger.warning(f"Received unsupported message type: {message_type}")
        
        except json.JSONDecodeError:
            logger.error(f"Received invalid JSON: {text_data}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    @database_sync_to_async
    def check_execution_access(self):
        """Check if the user has access to this execution"""
        try:
            # Get the execution and check if it belongs to the user's organization
            execution = AgentExecution.objects.get(id=self.execution_id)
            return execution.agent.organization == self.user.organization
        except ObjectDoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error checking execution access: {str(e)}")
            return False
    
    @database_sync_to_async
    def get_execution_data(self):
        """Get the current execution data"""
        try:
            execution = AgentExecution.objects.get(id=self.execution_id)
            
            # Get the latest tool executions
            tool_executions = AgentToolExecution.objects.filter(
                agent_execution_id=self.execution_id
            ).order_by('-created_at')[:10]  # Get the 10 most recent tool executions
            
            # Format the tool executions data
            tool_executions_data = []
            for tool_exec in tool_executions:
                tool_executions_data.append({
                    'id': str(tool_exec.id),
                    'tool_name': tool_exec.tool_name,
                    'status': tool_exec.status,
                    'created_at': tool_exec.created_at.isoformat(),
                    'execution_time': tool_exec.execution_time
                })
            
            # Calculate progress percentage based on completed steps
            total_steps = execution.total_steps or 1  # Avoid division by zero
            completed_steps = execution.completed_steps or 0
            progress = min(100, int((completed_steps / total_steps) * 100))
            
            return {
                'id': str(execution.id),
                'status': execution.status,
                'status_display': execution.get_status_display(),
                'progress': progress,
                'start_time': execution.start_time.isoformat() if execution.start_time else None,
                'end_time': execution.end_time.isoformat() if execution.end_time else None,
                'error_message': execution.error_message,
                'tool_executions': tool_executions_data
            }
        except ObjectDoesNotExist:
            logger.error(f"Execution {self.execution_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting execution data: {str(e)}")
            return None
    
    async def send_initial_state(self):
        """Send the initial execution state to the client"""
        execution_data = await self.get_execution_data()
        if execution_data:
            await self.send(text_data=json.dumps({
                'type': 'execution_update',
                'data': execution_data
            }))
    
    async def execution_update(self, event):
        """Handle execution update events and forward to the WebSocket"""
        # Forward the update to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'execution_update',
            'data': event['data']
        }))
    
    async def tool_execution_update(self, event):
        """Handle tool execution update events and forward to the WebSocket"""
        # Forward the update to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'tool_execution_update',
            'data': event['data']
        }))

# Helper function to send execution updates from anywhere in the code
def send_execution_update(execution_id, status=None, progress=None, error_message=None):
    """
    Send an execution update to all connected clients for a specific execution.
    
    This function can be called from anywhere in the code to broadcast updates
    about an agent execution to all connected WebSocket clients.
    
    Args:
        execution_id (str): The ID of the execution to update
        status (str, optional): The new status of the execution
        progress (int, optional): The progress percentage (0-100)
        error_message (str, optional): Error message if any
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # Prepare the update data
        update_data = {
            'id': str(execution_id)
        }
        
        if status is not None:
            update_data['status'] = status
            
            # Get the display name for the status if possible
            try:
                from .models import AgentExecution
                update_data['status_display'] = dict(AgentExecution.STATUS_CHOICES).get(status, status)
            except Exception:
                update_data['status_display'] = status
        
        if progress is not None:
            update_data['progress'] = min(100, max(0, progress))  # Ensure progress is between 0-100
            
        if error_message is not None:
            update_data['error_message'] = error_message
        
        # Send the update to the group
        async_to_sync(channel_layer.group_send)(
            f"agent_execution_{execution_id}",
            {
                'type': 'execution_update',
                'data': update_data
            }
        )
    except Exception as e:
        logger.error(f"Error sending execution update: {str(e)}")

# Helper function to send tool execution updates
def send_tool_execution_update(execution_id, tool_execution):
    """
    Send a tool execution update to all connected clients for a specific execution.
    
    Args:
        execution_id (str): The ID of the parent execution
        tool_execution (AgentToolExecution): The tool execution instance
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    try:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # Prepare the tool execution data
        tool_data = {
            'id': str(tool_execution.id),
            'tool_name': tool_execution.tool_name,
            'tool_type': tool_execution.tool_type,
            'status': tool_execution.status,
            'created_at': tool_execution.created_at.isoformat(),
            'execution_time': tool_execution.execution_time,
            'error_message': tool_execution.error_message
        }
        
        # Send the update to the group
        async_to_sync(channel_layer.group_send)(
            f"agent_execution_{execution_id}",
            {
                'type': 'tool_execution_update',
                'data': tool_data
            }
        )
    except Exception as e:
        logger.error(f"Error sending tool execution update: {str(e)}")
