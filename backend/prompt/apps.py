from django.apps import AppConfig


class PromptConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prompt'

    def ready(self):
        """
        Register the prompt app's context session ID update function
        when Django starts up.
        """
        try:
            from context_manager.services.entity_registry import EntityContextRegistry, update_prompt_session_context_id
            
            # Register the update function for prompt_session entity type
            EntityContextRegistry.register('prompt_session', update_prompt_session_context_id)
            
        except ImportError:
            # Handle case where context_manager app is not available
            pass
