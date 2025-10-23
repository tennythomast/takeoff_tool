"""
Signal handlers for agent-related models.

This module contains Django signal handlers that send WebSocket updates
when agent execution or tool execution records are created or updated.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AgentExecution, AgentToolExecution
from .websocket_integration import update_agent_execution_status, update_tool_execution_status

logger = logging.getLogger(__name__)

@receiver(post_save, sender=AgentExecution)
def agent_execution_post_save(sender, instance, created, **kwargs):
    """
    Send WebSocket updates when an AgentExecution record is created or updated.
    
    Args:
        sender: The model class (AgentExecution)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    try:
        # Calculate progress percentage based on completed steps
        total_steps = instance.total_steps or 1  # Avoid division by zero
        completed_steps = instance.completed_steps or 0
        progress = min(100, int((completed_steps / total_steps) * 100))
        
        # Send WebSocket update
        update_agent_execution_status(
            execution=instance,
            status=instance.status,
            progress=progress,
            error_message=instance.error_message
        )
        
        if created:
            logger.debug(f"Created new agent execution {instance.id}, sent WebSocket update")
        else:
            logger.debug(f"Updated agent execution {instance.id}, sent WebSocket update")
            
    except Exception as e:
        logger.error(f"Error sending WebSocket update for execution {instance.id}: {str(e)}")

@receiver(post_save, sender=AgentToolExecution)
def agent_tool_execution_post_save(sender, instance, created, **kwargs):
    """
    Send WebSocket updates when an AgentToolExecution record is created or updated.
    
    Args:
        sender: The model class (AgentToolExecution)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
    """
    try:
        # Send WebSocket update
        update_tool_execution_status(instance)
        
        if created:
            logger.debug(f"Created new tool execution {instance.id}, sent WebSocket update")
        else:
            logger.debug(f"Updated tool execution {instance.id}, sent WebSocket update")
            
    except Exception as e:
        logger.error(f"Error sending WebSocket update for tool execution {instance.id}: {str(e)}")
