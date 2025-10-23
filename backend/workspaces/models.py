from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, SoftDeletableMixin, SoftDeletableManager


class Workspace(SoftDeletableMixin, BaseModel):
    """Workspaces are containers for related PromptSessions and shared context."""
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        ARCHIVED = 'ARCHIVED', _('Archived')
        COMPLETED = 'COMPLETED', _('Completed')
        
    class WorkspaceType(models.TextChoices):
        ORGANIZATION = 'ORGANIZATION', _('Organization')
        TEAM = 'TEAM', _('Team')
        PROJECT = 'PROJECT', _('Project')
        PERSONAL = 'PERSONAL', _('Personal')

    name = models.CharField(_('name'), max_length=255, db_index=True)
    description = models.TextField(_('description'), blank=True)
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='workspaces',
        verbose_name=_('organization')
    )
    owner = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='owned_workspaces',
        verbose_name=_('owner')
    )
    collaborators = models.ManyToManyField(
        'core.User',
        through='WorkspaceCollaborator',
        related_name='collaborated_workspaces',
        verbose_name=_('collaborators')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    workspace_type = models.CharField(
        _('workspace type'),
        max_length=20,
        choices=WorkspaceType.choices,
        default=WorkspaceType.TEAM,
        db_index=True
    )
    is_system_workspace = models.BooleanField(
        _('system workspace'),
        default=False,
        help_text=_('Designates whether this workspace is a system workspace.'),
        db_index=True
    )
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    started_at = models.DateTimeField(_('started at'), null=True, blank=True)

    objects = SoftDeletableManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _('workspace')
        verbose_name_plural = _('workspaces')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['is_active', 'status'])
        ]

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        # Set started_at when status becomes ACTIVE for the first time
        if not self.started_at and self.status == self.Status.ACTIVE:
            self.started_at = timezone.now()
        super().save(*args, **kwargs)


class WorkspaceCollaborator(BaseModel):
    """Represents a user's role and permissions within a workspace."""
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        EDITOR = 'EDITOR', _('Editor')
        VIEWER = 'VIEWER', _('Viewer')

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='workspace_collaborators',
        verbose_name=_('workspace')
    )
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='workspace_collaborations',
        verbose_name=_('user')
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
        db_index=True
    )
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)

    class Meta:
        verbose_name = _('workspace collaborator')
        verbose_name_plural = _('workspace collaborators')
        unique_together = ('workspace', 'user')
        indexes = [
            models.Index(fields=['workspace', 'role']),
            models.Index(fields=['user', 'role'])
        ]

    def __str__(self):
        return f'{self.user.email} - {self.workspace.name} ({self.get_role_display()})'

    def is_admin(self) -> bool:
        """Check if the collaborator has admin role."""
        return self.role == self.Role.ADMIN

    def is_editor(self) -> bool:
        """Check if the collaborator has editor or higher role."""
        return self.role in {self.Role.ADMIN, self.Role.EDITOR}

    def has_role(self, role: str) -> bool:
        """Check if the collaborator has the specified role or higher."""
        role_hierarchy = {
            self.Role.VIEWER: 0,
            self.Role.EDITOR: 1,
            self.Role.ADMIN: 2
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(role, 0)