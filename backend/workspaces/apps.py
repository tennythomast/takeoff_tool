from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WorkspacesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workspaces'  # Updated module name to match directory name
    verbose_name = _('Workspaces')

    def ready(self):
        try:
            import workspaces.signals  # noqa: F401
        except ImportError:
            pass
