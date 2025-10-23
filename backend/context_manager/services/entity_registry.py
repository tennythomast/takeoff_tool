import logging
from typing import Dict, Callable, Awaitable
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class EntityContextRegistry:
    """
    Registry for domain entities to register context session ID update functions.
    
    This allows each domain (prompts, agents, workflows, etc.) to register their own
    logic for updating their entity's context_session_id field when a context session
    is created or retrieved by the UniversalContextService.
    """
    
    _registry: Dict[str, Callable[[str, str], Awaitable[None]]] = {}
    
    @classmethod
    def register(cls, entity_type: str, update_function: Callable[[str, str], Awaitable[None]]):
        """
        Register an update function for a specific entity type.
        
        Args:
            entity_type: The entity type (e.g., 'prompt_session', 'agent_session')
            update_function: Async function that takes (entity_id, context_session_id)
        """
        cls._registry[entity_type] = update_function
        logger.info(f"Registered context session ID update function for entity type: {entity_type}")
    
    @classmethod
    async def update_entity_context_session_id(cls, entity_type: str, entity_id: str, context_session_id: str):
        """
        Update the context session ID for a domain entity.
        
        Args:
            entity_type: The entity type (e.g., 'prompt_session', 'agent_session')
            entity_id: The ID of the domain entity
            context_session_id: The context session ID to set
        """
        if entity_type in cls._registry:
            try:
                await cls._registry[entity_type](entity_id, context_session_id)
                logger.debug(f"Updated context session ID for {entity_type} {entity_id}")
            except Exception as e:
                logger.error(f"Failed to update context session ID for {entity_type} {entity_id}: {str(e)}", exc_info=True)
        else:
            logger.debug(f"No update function registered for entity type: {entity_type}")
    
    @classmethod
    def get_registered_types(cls) -> list:
        """Get list of registered entity types."""
        return list(cls._registry.keys())
    
    @classmethod
    def is_registered(cls, entity_type: str) -> bool:
        """Check if an entity type is registered."""
        return entity_type in cls._registry


# Update function for PromptSession entities
async def update_prompt_session_context_id(entity_id: str, context_session_id: str):
    """Update PromptSession with context session ID."""
    try:
        from prompt.models import PromptSession
        
        # Get the prompt session
        session = await PromptSession.objects.aget(id=entity_id)
        
        # Only update if not already set
        if not session.context_session_id:
            session.context_session_id = context_session_id
            await database_sync_to_async(session.save)(update_fields=['context_session_id'])
            logger.info(f"Updated PromptSession {entity_id} with context_session_id {context_session_id}")
        else:
            logger.debug(f"PromptSession {entity_id} already has context_session_id: {session.context_session_id}")
            
    except Exception as e:
        logger.error(f"Failed to update PromptSession {entity_id}: {str(e)}", exc_info=True)
        raise


# Register the prompt session update function
EntityContextRegistry.register('prompt_session', update_prompt_session_context_id)
