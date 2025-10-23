"""
WebSocket integration for agent execution updates.

This module provides functions to integrate WebSocket updates with agent execution
and tool execution processes, allowing real-time updates to be sent to connected clients.
"""

import logging
from .consumers import send_execution_update, send_tool_execution_update

logger = logging.getLogger(__name__)

def update_agent_execution_status(execution, status=None, progress=None, error_message=None):
    """
    Update an agent execution status and send WebSocket updates to connected clients.
    
    Args:
        execution: The AgentExecution instance
        status: The new status (optional)
        progress: The progress percentage (optional)
        error_message: Error message if any (optional)
    """
    try:
        # Send WebSocket update
        send_execution_update(
            execution_id=str(execution.id),
            status=status or execution.status,
            progress=progress,
            error_message=error_message or execution.error_message
        )
        logger.debug(f"Sent WebSocket update for execution {execution.id}, status: {status}")
    except Exception as e:
        logger.error(f"Error sending WebSocket update for execution {execution.id}: {str(e)}")

def update_tool_execution_status(tool_execution):
    """
    Send WebSocket updates for tool execution status changes.
    
    Args:
        tool_execution: The AgentToolExecution instance
    """
    try:
        # Send WebSocket update
        send_tool_execution_update(tool_execution)
        logger.debug(f"Sent WebSocket update for tool execution {tool_execution.id}")
    except Exception as e:
        logger.error(f"Error sending WebSocket update for tool execution {tool_execution.id}: {str(e)}")


def send_cache_notification(execution_id, cache_hit=True, cost_saved=None):
    """Send a cache notification via WebSocket"""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    import json
    
    channel_layer = get_channel_layer()
    group_name = f"execution_{execution_id}"
    
    # Prepare notification data
    notification_data = {
        'execution_id': str(execution_id),
        'cache_hit': cache_hit,
        'cost_saved': str(cost_saved) if cost_saved else '0.0'
    }
    
    # Send to group
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_execution_update',
            'message': {
                'type': 'cache_notification',
                'data': notification_data
            }
        }
    )
