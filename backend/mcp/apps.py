from django.apps import AppConfig


class MCPConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mcp'
    
    def ready(self):
        """Import signals when app is ready"""
        import mcp.signals
