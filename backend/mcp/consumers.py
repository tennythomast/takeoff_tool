import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from .models import MCPServerConnection, MCPResourceDiscovery, MCPWorkspaceAccess

User = get_user_model()
logger = logging.getLogger(__name__)


class MCPResourceConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time MCP resource updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get connection ID from URL route
        self.connection_id = self.scope['url_route']['kwargs']['connection_id']
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            logger.warning(f"Unauthenticated connection attempt to MCP resource stream")
            await self.close()
            return
        
        # Check if connection exists and user has access
        connection_exists = await self.connection_exists_and_accessible()
        if not connection_exists:
            logger.warning(f"User {self.user.username} attempted to access unauthorized MCP connection {self.connection_id}")
            await self.close()
            return
        
        # Create a unique group name for this connection
        self.group_name = f"mcp_resources_{self.connection_id}"
        
        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Send initial connection status
        await self.send_connection_status("connected")
        
        logger.info(f"User {self.user.username} connected to MCP resource stream for connection {self.connection_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave the group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        
        logger.info(f"User {self.user.username} disconnected from MCP resource stream (code: {close_code})")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_resource':
                # Subscribe to updates for a specific resource
                resource_id = data.get('resource_id')
                if resource_id:
                    can_access = await self.can_access_resource(resource_id)
                    if can_access:
                        # Add resource-specific group
                        resource_group = f"mcp_resource_{resource_id}"
                        await self.channel_layer.group_add(
                            resource_group,
                            self.channel_name
                        )
                        await self.send(text_data=json.dumps({
                            'type': 'subscription_success',
                            'resource_id': resource_id
                        }))
                    else:
                        await self.send(text_data=json.dumps({
                            'type': 'error',
                            'message': 'Access denied to resource',
                            'resource_id': resource_id
                        }))
            
            elif message_type == 'unsubscribe_resource':
                # Unsubscribe from updates for a specific resource
                resource_id = data.get('resource_id')
                if resource_id:
                    resource_group = f"mcp_resource_{resource_id}"
                    await self.channel_layer.group_discard(
                        resource_group,
                        self.channel_name
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'unsubscription_success',
                        'resource_id': resource_id
                    }))
            
            elif message_type == 'ping':
                # Simple ping to keep connection alive
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            
            else:
                logger.warning(f"Unknown message type received: {message_type}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unknown message type'
                }))
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.exception(f"Error processing WebSocket message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def resource_updated(self, event):
        """Handle resource update event"""
        # For MVP, only forward updates for resources the user can access
        resource = event['resource']
        resource_id = resource.get('id')
        
        # Skip resource check for connection-wide updates
        if not resource_id:
            await self.send(text_data=json.dumps({
                'type': 'resource_updated',
                'resource': resource
            }))
            return
            
        # Check if user can access this resource using our MVP approach
        can_access = await self.can_access_resource(resource_id)
        if can_access:
            # Forward the resource update to the client
            await self.send(text_data=json.dumps({
                'type': 'resource_updated',
                'resource': resource
            }))
        else:
            # Log that we're filtering this update
            logger.debug(f"Filtered resource update for resource {resource_id} - user {self.user.id} doesn't have access")
    
    async def connection_status(self, event):
        """Handle connection status event"""
        # Forward the connection status to the client
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'connection_id': event['connection_id'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))
    
    async def send_connection_status(self, status):
        """Send connection status update"""
        from datetime import datetime
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'connection_id': self.connection_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }))
    
    @database_sync_to_async
    def connection_exists_and_accessible_mvp(self):
        """Simplified connection access check for MVP"""
        try:
            # Check if connection exists
            connection = MCPServerConnection.objects.get(id=self.connection_id)
            
            # Check if user is a member of the organization
            if not self.user.organizations.filter(id=connection.organization.id).exists():
                return False
                
            # For MVP, also check if there's at least one active workspace access for this connection
            # This ensures we don't create WebSocket connections for connections that have no workspace access
            user_workspaces = self.user.workspaces.all()
            has_workspace_access = MCPWorkspaceAccess.objects.filter(
                workspace__in=user_workspaces,
                connection=connection,
                is_active=True
            ).exists()
            
            return has_workspace_access
        except ObjectDoesNotExist:
            return False
        except Exception as e:
            logger.exception(f"Error checking connection access: {str(e)}")
            return False
    
    @database_sync_to_async
    def connection_exists_and_accessible(self):
        """Check if connection exists and user has access"""
        # For MVP, use the simplified version
        return self.connection_exists_and_accessible_mvp()
        
        # Note: Full implementation with more complex access checks
        # will be added after MVP
    
    @database_sync_to_async
    def can_access_resource_mvp(self, resource_id):
        """Simplified resource access check for MVP"""
        try:
            # Get the resource
            resource = MCPResourceDiscovery.objects.get(id=resource_id)
            
            # Check if resource belongs to the connection
            if str(resource.connection.id) != self.connection_id:
                return False
            
            # Check if user has workspace access to this resource
            user_workspaces = self.user.workspaces.all()
            
            # For MVP, just check if the resource is explicitly allowed in any workspace
            return MCPWorkspaceAccess.objects.filter(
                workspace__in=user_workspaces,
                connection=resource.connection,
                is_active=True,
                allowed_resources=resource
            ).exists()
            
        except ObjectDoesNotExist:
            return False
        except Exception as e:
            logger.exception(f"Error checking resource access: {str(e)}")
            return False
    
    @database_sync_to_async
    def can_access_resource(self, resource_id):
        """Check if user can access a specific resource"""
        # For MVP, use the simplified version
        return self.can_access_resource_mvp(resource_id)
        
        # Note: Full implementation with hierarchical access and complex filtering
        # will be added after MVP

