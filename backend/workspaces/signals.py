from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Workspace, WorkspaceCollaborator, PromptSession


@receiver(post_save, sender=Workspace)
def create_workspace_owner_collaborator(sender, instance, created, **kwargs):
    """Automatically create a WorkspaceCollaborator for the workspace owner with ADMIN role."""
    if created:
        WorkspaceCollaborator.objects.create(
            workspace=instance,
            user=instance.owner,
            role=WorkspaceCollaborator.Role.ADMIN
        )


@receiver(pre_save, sender=PromptSession)
def update_prompt_session_timestamps(sender, instance, **kwargs):
    """Update timestamps based on status changes."""
    if not instance.pk:  # New instance
        return

    old_instance = PromptSession.objects.get(pk=instance.pk)
    
    # Status transitions
    if old_instance.status != instance.status:
        if instance.status == PromptSession.Status.ACTIVE and not instance.started_at:
            instance.started_at = timezone.now()
        elif instance.status in [PromptSession.Status.COMPLETED, PromptSession.Status.FAILED]:
            instance.completed_at = timezone.now()
