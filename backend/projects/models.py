from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, SoftDeletableMixin, SoftDeletableManager


class Project(SoftDeletableMixin, BaseModel):
    """Projects for Takeoff - client project management."""
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        ARCHIVED = 'ARCHIVED', _('Archived')
        COMPLETED = 'COMPLETED', _('Completed')
        ON_HOLD = 'ON_HOLD', _('On Hold')
    
    class ProjectType(models.TextChoices):
        FIXED_PRICE = 'FIXED_PRICE', _('Fixed Price')
        TIME_AND_MATERIALS = 'TIME_AND_MATERIALS', _('Time & Materials')
        RETAINER = 'RETAINER', _('Retainer')
        OTHER = 'OTHER', _('Other')

    # Core fields
    title = models.CharField(_('title'), max_length=255, db_index=True)
    description = models.TextField(_('description'), blank=True)
    
    # Client information (PRIORITY)
    client_name = models.CharField(_('client name'), max_length=255, db_index=True)
    client_email = models.EmailField(_('client email'), blank=True)
    client_phone = models.CharField(_('client phone'), max_length=50, blank=True)
    client_company = models.CharField(_('client company'), max_length=255, blank=True)
    
    # Project details
    project_type = models.CharField(
        _('project type'),
        max_length=30,
        choices=ProjectType.choices,
        default=ProjectType.TIME_AND_MATERIALS,
        db_index=True
    )
    budget = models.DecimalField(
        _('budget'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Total project budget')
    )
    location = models.CharField(_('location'), max_length=255, blank=True)
    tags = models.JSONField(_('tags'), default=list, blank=True)
    
    # Organization and ownership
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name=_('organization')
    )
    owner = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='owned_projects',
        verbose_name=_('owner')
    )
    collaborators = models.ManyToManyField(
        'core.User',
        through='ProjectCollaborator',
        related_name='collaborated_projects',
        verbose_name=_('collaborators')
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    started_at = models.DateTimeField(_('started at'), null=True, blank=True)
    deadline = models.DateTimeField(_('deadline'), null=True, blank=True)

    objects = SoftDeletableManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _('project')
        verbose_name_plural = _('projects')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['client_name']),
            models.Index(fields=['is_active', 'status'])
        ]

    def __str__(self):
        return f'{self.title} - {self.client_name} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        # Set started_at when status becomes ACTIVE for the first time
        if not self.started_at and self.status == self.Status.ACTIVE:
            self.started_at = timezone.now()
        super().save(*args, **kwargs)


class ProjectCollaborator(BaseModel):
    """Represents a user's role and permissions within a project."""
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        EDITOR = 'EDITOR', _('Editor')
        VIEWER = 'VIEWER', _('Viewer')

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_collaborators',
        verbose_name=_('project')
    )
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='project_collaborations',
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
        verbose_name = _('project collaborator')
        verbose_name_plural = _('project collaborators')
        unique_together = ('project', 'user')
        indexes = [
            models.Index(fields=['project', 'role']),
            models.Index(fields=['user', 'role'])
        ]

    def __str__(self):
        return f'{self.user.email} - {self.project.title} ({self.get_role_display()})'

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
