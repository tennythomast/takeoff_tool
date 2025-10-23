from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import MCPResourceDiscovery, MCPServerConnection
from .events import broadcast_resource_update, broadcast_connection_status


@receiver(post_save, sender=MCPResourceDiscovery)
def resource_saved(sender, instance, created, **kwargs):
    """
    Signal handler for resource save events
    
    Args:
        sender: The model class (MCPResourceDiscovery)
        instance: The actual instance being saved
        created: Boolean, True if a new record was created
    """
    # Only broadcast for updates, not new resources
    # New resources will be discovered through the connection's discover_resources action
    if not created:
        broadcast_resource_update(instance)


@receiver(post_delete, sender=MCPResourceDiscovery)
def resource_deleted(sender, instance, **kwargs):
    """
    Signal handler for resource delete events
    
    Args:
        sender: The model class (MCPResourceDiscovery)
        instance: The actual instance being deleted
    """
    # Broadcast the resource as unavailable
    instance.is_available = False
    broadcast_resource_update(instance)


@receiver(post_save, sender=MCPServerConnection)
def connection_status_changed(sender, instance, **kwargs):
    """
    Signal handler for connection status changes
    
    Args:
        sender: The model class (MCPServerConnection)
        instance: The actual instance being saved
    """
    # Broadcast connection status
    status = 'connected' if instance.is_connected else 'disconnected'
    if not instance.is_active:
        status = 'disabled'
    elif instance.health_status == 'error':
        status = 'error'
        
    broadcast_connection_status(instance.id, status)
