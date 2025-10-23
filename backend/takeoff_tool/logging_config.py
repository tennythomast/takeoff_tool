"""Custom logging configuration for the Dataelan project."""
import os
from logging.config import dictConfig

def configure_logging():
    """Configure logging for the application."""
    log_level = os.environ.get('DJANGO_LOG_LEVEL', 'INFO')
    
    # Default logging configuration
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            # Root logger
            '': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': True,
            },
            # Django
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            # Database queries (set to INFO to hide SQL queries)
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            # Django Channels
            'django.channels': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            # Daphne
            'daphne': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            # Prompt consumers
            'prompt.consumers': {
                'handlers': ['console'],
                'level': 'INFO',  # Only show INFO and above
                'propagate': False,
            },
            # MCP
            'mcp': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            # DRF
            'rest_framework': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            # Modelhub
            'modelhub': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            # Application loggers
            'core': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'workflows': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'agents': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    
    # Apply the configuration
    dictConfig(logging_config)
