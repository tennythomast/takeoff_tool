from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agents'
    
    def ready(self):
        """Connect signal handlers when the app is ready"""
        # Import signals module to connect the signal handlers
        import agents.signals
