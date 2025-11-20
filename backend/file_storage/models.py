from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import hashlib
import uuid
import os
from typing import Optional

from core.models import BaseModel, SoftDeletableMixin, SoftDeletableManager

User = get_user_model()


class FileStorageBackend(BaseModel):
    """Configuration for storage backends - simplified for MVP"""
    
    BACKEND_TYPES = [
        ('gcp_storage', 'Google Cloud Storage'),
        ('local', 'Local Storage'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    backend_type = models.CharField(max_length=20, choices=BACKEND_TYPES)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Essential configuration only
    config = models.JSONField(
        default=dict,
        help_text="Backend configuration (bucket name, credentials path, etc.)"
    )
    
    # Basic security limits
    max_file_size_mb = models.PositiveIntegerField(default=50)
    allowed_extensions = models.JSONField(
        default=list,
        help_text="Allowed file extensions: ['.pdf', '.docx', '.txt', '.md', '.csv']"
    )

    class Meta:
        db_table = 'file_storage_backend'
        verbose_name = 'File Storage Backend'
        verbose_name_plural = 'File Storage Backends'

    def __str__(self):
        return f"{self.name} ({self.get_backend_type_display()})"


class FileUpload(SoftDeletableMixin):
    """
    Core file model with essential multi-tenant access control.
    MVP focus: workspace/organization access + agent/workflow integration.
    """
    
    FILE_PURPOSES = [
        ('user_document', 'User Document'),
        ('workspace_document', 'Workspace Document'),
        ('rag_document', 'RAG Document'),
        ('agent_asset', 'Agent Asset'),
        ('workflow_asset', 'Workflow Asset'),
    ]
    
    PROCESSING_STATUS = [
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    ACCESS_LEVELS = [
        ('private', 'Private (Owner Only)'),
        ('workspace', 'Workspace Members'),
        ('organization', 'Organization Members'),
    ]

    # Multi-tenant structure
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='file_uploads',
        db_index=True
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='file_uploads',
        null=True,
        blank=True,
        db_index=True
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_files'
    )

    # File metadata
    original_filename = models.CharField(max_length=255, db_index=True)
    content_type = models.CharField(max_length=100)
    file_size_bytes = models.PositiveBigIntegerField()
    file_extension = models.CharField(max_length=10)
    parent_folder = models.ForeignKey(
        'FileFolder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='files'
    )
    
    # File purpose and access
    purpose = models.CharField(
        max_length=30, 
        choices=FILE_PURPOSES, 
        default='user_document',
        db_index=True
    )
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVELS,
        default='private',
        db_index=True
    )
    description = models.TextField(blank=True)

    # Storage backend
    storage_backend = models.ForeignKey(
        FileStorageBackend,
        on_delete=models.PROTECT,
        related_name='files'
    )
    storage_path = models.TextField()
    
    # File integrity
    file_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash for deduplication"
    )

    # Processing status
    status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUS, 
        default='pending',
        db_index=True
    )
    processing_error = models.TextField(blank=True)
    
    # Simple extracted content (for RAG)
    extracted_text = models.TextField(
        blank=True,
        help_text="Extracted text content for RAG processing"
    )
    
    # Basic usage tracking
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeletableManager()

    class Meta:
        db_table = 'file_upload'
        verbose_name = 'File Upload'
        verbose_name_plural = 'File Uploads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'purpose', 'is_active']),
            models.Index(fields=['project', 'is_active']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['access_level']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'file_hash'],
                name='unique_file_per_org'
            )
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.organization.name})"

    def clean(self):
        super().clean()
        # Validate project belongs to organization
        if self.project and self.project.organization_id != self.organization_id:
            raise ValidationError({
                'project': 'Project must belong to the same organization'
            })

    def save(self, *args, **kwargs):
        # Auto-generate storage path if not provided
        if not self.storage_path:
            self.storage_path = self._generate_storage_path()
        
        # Auto-set access level based on purpose
        if not hasattr(self, '_access_level_set'):
            self._auto_set_access_level()
        
        super().save(*args, **kwargs)

    def _generate_storage_path(self):
        """Generate storage path: org/project/purpose/hash/filename"""
        hash_prefix = self.file_hash[:8] if self.file_hash else 'temp'
        
        path_parts = [
            str(self.organization.id),
            str(self.project.id) if self.project else 'no-project',
            self.purpose,
            hash_prefix,
            self.original_filename
        ]
        
        return '/'.join(path_parts)

    def _auto_set_access_level(self):
        """Auto-set access level based on purpose"""
        purpose_mapping = {
            'user_document': 'private',
            'workspace_document': 'project',
            'rag_document': 'project',
            'agent_asset': 'project',
            'workflow_asset': 'project',
        }
        
        if not self.access_level or self.access_level == 'private':
            self.access_level = purpose_mapping.get(self.purpose, 'private')

    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size_bytes / (1024 * 1024), 2)

    @property
    def is_processed(self):
        """Check if file is ready for use"""
        return self.status == 'completed'
        
    @property
    def get_file_url(self):
        """Get the URL for accessing the file"""
        from django.conf import settings
        
        if not self.storage_path:
            return None
            
        # For temporary storage files
        if self.storage_path.startswith('temp_storage'):
            return settings.TEMP_STORAGE_URL + self.storage_path.replace('temp_storage/', '')
            
        # For other storage backends, implement as needed
        return None

    def can_access(self, user: User) -> bool:
        """
        Essential access control for MVP.
        Checks: owner, organization membership, workspace access.
        """
        if not user or not user.is_active:
            return False

        # Superuser access
        if user.is_superuser:
            return True

        # File owner can always access
        if self.uploaded_by_id == user.id:
            return True

        # Must be in same organization
        if user.organization != self.organization:
            return False

        # Check access level
        if self.access_level == 'private':
            return False
        elif self.access_level == 'organization':
            return True
        elif self.access_level == 'project':
            return self._has_project_access(user)
        
        return False
        
    def _has_project_access(self, user: User) -> bool:
        """Check if user has project access"""
        if not self.project:
            return False
        
        # Project owner
        if self.project.owner_id == user.id:
            return True
        
        # Project collaborator
        from projects.models import ProjectCollaborator
        return ProjectCollaborator.objects.filter(
            project=self.project,
            user=user
        ).exists()

    def can_edit(self, user: User) -> bool:
        """Check if user can edit/delete file"""
        if not self.can_access(user):
            return False
        
        # Owner can edit
        if self.uploaded_by_id == user.id:
            return True
        
        # Project admin can edit project files
        if self.project:
            from projects.models import ProjectCollaborator
            return ProjectCollaborator.objects.filter(
                project=self.project,
                user=user,
                role=ProjectCollaborator.Role.ADMIN
            ).exists()
        
        # Organization admin can edit
        return user.has_role(self.organization, 'ADMIN')

    def can_use_in_agents_workflows(self, project) -> bool:
        """
        Check if agents/workflows in a project can use this file.
        Core MVP feature for RAG integration.
        """
        if not self.is_processed:
            return False
        
        # Must be project or organization level access
        if self.access_level == 'private':
            return False
        
        # If project file, must be same project
        if self.access_level == 'project':
            return self.project_id == project.id
        
        # Organization files accessible to all projects in org
        return self.access_level == 'organization'

    def record_access(self):
        """Simple access tracking for MVP"""
        self.last_accessed_at = timezone.now()
        self.save(update_fields=['last_accessed_at'])

    @classmethod
    def get_project_files(cls, project, user=None):
        """
        Get files accessible in a project.
        Core method for agent/workflow file access.
        """
        # Base query: files in project + organization files
        queryset = cls.objects.filter(
            organization=project.organization,
            is_active=True,
            status='completed'
        ).filter(
            models.Q(project=project, access_level='project') |
            models.Q(access_level='organization')
        )
        
        # If user specified, also include their private files
        if user:
            private_files = models.Q(
                uploaded_by=user,
                access_level='private'
            )
            queryset = queryset.filter(
                models.Q(project=project, access_level='project') |
                models.Q(access_level='organization') |
                private_files
            )
        
        return queryset.select_related('uploaded_by', 'storage_backend').order_by('-created_at')

    @classmethod
    def get_user_files(cls, user, purpose=None):
        """Get files accessible to a user"""
        queryset = cls.objects.filter(
            organization=user.organization,
            is_active=True
        ).filter(
            models.Q(uploaded_by=user) |  # User's files
            models.Q(access_level='organization') |  # Org files
            models.Q(  # Project files where user has access
                access_level='project',
                project__in=user.collaborated_projects.values_list('id', flat=True)
            )
        )
        
        if purpose:
            queryset = queryset.filter(purpose=purpose)
            
        return queryset.order_by('-created_at')


class FileProcessingJob(BaseModel):
    """Simplified file processing for MVP"""
    
    JOB_TYPES = [
        ('text_extraction', 'Text Extraction'),
        ('rag_embedding', 'RAG Embedding'),
    ]
    
    JOB_STATUS = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    file_upload = models.ForeignKey(
        FileUpload,
        on_delete=models.CASCADE,
        related_name='processing_jobs'
    )
    
    job_type = models.CharField(max_length=30, choices=JOB_TYPES)
    status = models.CharField(max_length=20, choices=JOB_STATUS, default='queued')
    
    # Execution tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'file_processing_job'
        verbose_name = 'File Processing Job'
        verbose_name_plural = 'File Processing Jobs'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['file_upload', 'job_type']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_job_type_display()} for {self.file_upload.original_filename}"

    def start(self):
        """Mark job as started"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def complete(self, result_data: dict = None):
        """Mark job as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result_data:
            self.result_data = result_data
        self.save(update_fields=['status', 'completed_at', 'result_data'])

    def fail(self, error_message: str):
        """Mark job as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'completed_at', 'error_message', 'retry_count'])


# Utility functions for MVP

def create_file_processing_jobs(file_upload: FileUpload):
    """Create necessary processing jobs for a file"""
    jobs_to_create = []
    
    # Text extraction for document types
    if file_upload.file_extension.lower() in ['.pdf', '.docx', '.txt', '.md']:
        jobs_to_create.append('text_extraction')
    
    # RAG embedding for RAG documents
    if file_upload.purpose == 'rag_document':
        jobs_to_create.append('rag_embedding')
    
    # Create the jobs
    created_jobs = []
    for job_type in jobs_to_create:
        job = FileProcessingJob.objects.create(
            file_upload=file_upload,
            job_type=job_type
        )
        created_jobs.append(job)
    
    return created_jobs


def get_organization_storage_usage(organization):
    """Get basic storage stats for organization"""
    from django.db.models import Sum, Count
    
    stats = FileUpload.objects.filter(
        organization=organization,
        is_active=True
    ).aggregate(
        total_files=Count('id'),
        total_size_bytes=Sum('file_size_bytes')
    )
    
    return {
        'total_files': stats['total_files'] or 0,
        'total_size_bytes': stats['total_size_bytes'] or 0,
        'total_size_mb': round((stats['total_size_bytes'] or 0) / (1024 * 1024), 2)
    }


def check_file_upload_permissions(user: User, project=None, purpose='user_document'):
    """Check if user can upload files to project/organization"""
    if not user or not user.is_active:
        return False
    
    # Check organization membership
    if not user.organization:
        return False
    
    # If project specified, check project access
    if project:
        if project.owner_id == user.id:
            return True
        
        from projects.models import ProjectCollaborator
        return ProjectCollaborator.objects.filter(
            project=project,
            user=user
        ).exists()
    
    # Organization level upload
    return True


# Integration helpers for RAG and Agents

def get_rag_documents_for_knowledge_base(knowledge_base):
    """Get all RAG documents accessible to a knowledge base"""
    if not knowledge_base.project:
        return FileUpload.objects.none()
    
    return FileUpload.objects.filter(
        organization=knowledge_base.organization,
        purpose='rag_document',
        status='completed',
        is_active=True
    ).filter(
        models.Q(project=knowledge_base.project) |
        models.Q(access_level='organization')
    ).exclude(
        extracted_text__isnull=True
    ).exclude(
        extracted_text=''
    )


def get_agent_accessible_files(agent):
    """Get files accessible to an agent in its project"""
    if not agent.project:
        return FileUpload.objects.none()
    
    return FileUpload.get_project_files(agent.project)


def get_workflow_accessible_files(workflow_execution):
    """Get files accessible to a workflow execution"""
    if not workflow_execution.workflow.project:
        return FileUpload.objects.none()
    
    return FileUpload.get_project_files(workflow_execution.workflow.project)


class FileFolder(SoftDeletableMixin, BaseModel):
    """Folder model for organizing files"""
    
    # Multi-tenant structure
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='file_folders',
        db_index=True
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='file_folders',
        null=True,
        blank=True,
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_folders'
    )
    
    # Folder properties
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent_folder = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_folders'
    )
    
    # Access control
    access_level = models.CharField(
        max_length=20,
        choices=FileUpload.ACCESS_LEVELS,
        default='private',
        db_index=True
    )
    
    objects = SoftDeletableManager()
    
    class Meta:
        db_table = 'file_folder'
        verbose_name = 'File Folder'
        verbose_name_plural = 'File Folders'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization', 'project', 'parent_folder']),
            models.Index(fields=['created_by']),
            models.Index(fields=['access_level']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'parent_folder', 'project', 'organization'],
                name='unique_folder_per_location'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.organization.name})"
    
    @property
    def file_count(self):
        """Count files in this folder"""
        return FileUpload.objects.filter(
            parent_folder=self.id,
            is_active=True
        ).count()
    
    def can_access(self, user: User) -> bool:
        """Check if user has access to this folder"""
        if not user or not user.is_active:
            return False

        # Superuser access
        if user.is_superuser:
            return True

        # Folder owner can always access
        if self.created_by_id == user.id:
            return True

        # Must be in same organization
        if user.organization != self.organization:
            return False

        # Check access level
        if self.access_level == 'private':
            return False
        elif self.access_level == 'organization':
            return True
        elif self.access_level == 'project':
            return self._has_project_access(user)
        
        return False
    
    def _has_project_access(self, user: User) -> bool:
        """Check if user has project access"""
        if not self.project:
            return False
        
        # Project owner
        if self.project.owner_id == user.id:
            return True
        
        # Project collaborator
        from projects.models import ProjectCollaborator
        return ProjectCollaborator.objects.filter(
            project=self.project,
            user=user
        ).exists()