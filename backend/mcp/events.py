import json
import logging
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

def broadcast_resource_update(resource):
    """
    Broadcast resource update to all connected clients
    
    Args:
        resource: MCPResourceDiscovery instance that was updated
    """
    try:
        channel_layer = get_channel_layer()
        
        # Create a serializable representation of the resource
        resource_data = {
            'id': resource.id,
            'resource_name': resource.resource_name,
            'resource_type': resource.resource_type,
            'resource_uri': resource.resource_uri,
            'is_available': resource.is_available,
            'last_verified': resource.last_verified.isoformat() if resource.last_verified else None
        }
        
        # Send to connection group
        connection_group = f"mcp_resources_{resource.connection_id}"
        async_to_sync(channel_layer.group_send)(
            connection_group,
            {
                'type': 'resource_updated',
                'resource': resource_data
            }
        )
        
        # Send to resource-specific group
        resource_group = f"mcp_resource_{resource.id}"
        async_to_sync(channel_layer.group_send)(
            resource_group,
            {
                'type': 'resource_updated',
                'resource': resource_data
            }
        )
        
        logger.info(f"Broadcast resource update for {resource.resource_name} (ID: {resource.id})")
        
    except Exception as e:
        logger.exception(f"Error broadcasting resource update: {str(e)}")


def broadcast_connection_status(connection_id, status):
    """
    Broadcast connection status update to all connected clients
    
    Args:
        connection_id: ID of the MCPServerConnection
        status: Status string (e.g., 'connected', 'disconnected', 'error')
    """
    try:
        channel_layer = get_channel_layer()
        
        # Send to connection group
        connection_group = f"mcp_resources_{connection_id}"
        async_to_sync(channel_layer.group_send)(
            connection_group,
            {
                'type': 'connection_status',
                'connection_id': str(connection_id),
                'status': status,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Broadcast connection status update for connection {connection_id}: {status}")
        
    except Exception as e:
        logger.exception(f"Error broadcasting connection status: {str(e)}")
