from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import FileStorageBackend, FileUpload, FileProcessingJob, FileFolder, create_file_processing_jobs
from .serializers import (
    FileStorageBackendSerializer, FileUploadSerializer, FileUploadCreateSerializer,
    FileProcessingJobSerializer, FileUploadDetailSerializer, FileFolderSerializer
)


@extend_schema_view(
    list=extend_schema(description="List all storage backends available to the organization"),
    retrieve=extend_schema(description="Get details of a specific storage backend"),
    create=extend_schema(description="Create a new storage backend"),
    update=extend_schema(description="Update a storage backend"),
    partial_update=extend_schema(description="Partially update a storage backend"),
    destroy=extend_schema(description="Delete a storage backend")
)
class FileStorageBackendViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file storage backends.
    
    Provides CRUD operations for storage backends with appropriate permissions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FileStorageBackendSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['backend_type', 'is_active', 'is_default']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter backends based on user's organization membership."""
        user = self.request.user
        # Only organization admins should see storage backends
        if user.is_superuser or user.has_role(user.organization, 'ADMIN'):
            return FileStorageBackend.objects.all()
        return FileStorageBackend.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        """Create a new storage backend."""
        # If this is marked as default, unmark other defaults
        if serializer.validated_data.get('is_default', False):
            FileStorageBackend.objects.filter(is_default=True).update(is_default=False)
        serializer.save()
    
    def perform_update(self, serializer):
        """Update a storage backend."""
        # If this is marked as default, unmark other defaults
        if serializer.validated_data.get('is_default', False):
            FileStorageBackend.objects.filter(is_default=True).exclude(
                id=serializer.instance.id
            ).update(is_default=False)
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        description="List all files accessible to the user",
        parameters=[
            OpenApiParameter(
                name="purpose",
                description="Filter by file purpose",
                required=False,
                type=OpenApiTypes.STR,
                enum=[p[0] for p in FileUpload.FILE_PURPOSES]
            ),
            OpenApiParameter(
                name="workspace",
                description="Filter by workspace ID",
                required=False,
                type=OpenApiTypes.INT
            ),
        ]
    ),
    retrieve=extend_schema(description="Get details of a specific file"),
    create=extend_schema(description="Create a new file upload record"),
    update=extend_schema(description="Update a file upload record"),
    partial_update=extend_schema(description="Partially update a file upload record"),
    destroy=extend_schema(description="Delete a file upload record")
)
class FileUploadViewSet(viewsets.ModelViewSet):
    """ViewSet for managing file uploads.
    
    Provides CRUD operations for file uploads with appropriate permissions.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['purpose', 'access_level', 'status', 'workspace', 'uploaded_by']
    ordering_fields = ['original_filename', 'created_at', 'file_size_bytes']
    ordering = ['-created_at']
    search_fields = ['original_filename', 'description']
    throttle_classes = []  # Disable throttling for files endpoint
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return FileUploadCreateSerializer
        elif self.action == 'retrieve':
            return FileUploadDetailSerializer
        return FileUploadSerializer
    
    def get_queryset(self):
        """Filter files based on user's access permissions."""
        user = self.request.user
        
        # Get query parameters
        purpose = self.request.query_params.get('purpose')
        workspace_id = self.request.query_params.get('workspace')
        
        if workspace_id:
            # Get files for a specific workspace
            from workspaces.models import Workspace
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                return FileUpload.get_workspace_files(workspace, user)
            except Workspace.DoesNotExist:
                return FileUpload.objects.none()
        else:
            # Get all files accessible to the user
            return FileUpload.get_user_files(user, purpose)
    
    def perform_create(self, serializer):
        """Create a new file upload record."""
        file_upload = serializer.save()
        
        # Create processing jobs based on file type and purpose
        create_file_processing_jobs(file_upload)
    
    def check_object_permissions(self, request, obj):
        """Check if user has permission to access this file."""
        super().check_object_permissions(request, obj)
        
        # Check if user can access this file
        if not obj.can_access(request.user):
            self.permission_denied(request, message="You do not have permission to access this file.")
        
        # For write operations, check if user can edit this file
        if request.method not in ['GET', 'HEAD', 'OPTIONS'] and not obj.can_edit(request.user):
            self.permission_denied(request, message="You do not have permission to edit this file.")
    
    @action(detail=True, methods=['post'])
    def record_access(self, request, pk=None):
        """Record that the file was accessed."""
        file_upload = self.get_object()
        file_upload.record_access()
        return Response({"status": "access recorded"})
    
    @action(detail=False, methods=['get'])
    def storage_usage(self, request):
        """Get storage usage statistics for the organization."""
        from .models import get_organization_storage_usage
        
        stats = get_organization_storage_usage(request.user.organization)
        return Response(stats)

    @action(detail=True, methods=['POST'], url_path='upload')
    def upload_content(self, request, pk=None):
        """Upload file content for an existing file upload record."""
        file_upload = self.get_object()
        
        # Check if file is already uploaded
        if file_upload.status == 'completed':
            return Response({"error": "File already uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get file from request
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set status to uploading while we process
        file_upload.status = 'uploading'
        file_upload.save(update_fields=['status'])
        
        try:
            # Save file to a temporary local storage folder
            import os
            import shutil
            from django.conf import settings
            
            # Create a temporary storage directory if it doesn't exist
            os.makedirs(settings.TEMP_STORAGE_ROOT, exist_ok=True)
            
            # Create subdirectory based on organization and workspace
            org_id = str(file_upload.organization.id)
            workspace_id = str(file_upload.workspace.id) if file_upload.workspace else 'no-workspace'
            file_dir = os.path.join(settings.TEMP_STORAGE_ROOT, org_id, workspace_id)
            os.makedirs(file_dir, exist_ok=True)
            
            # Generate a unique filename to avoid overwriting existing files
            import uuid
            filename_parts = os.path.splitext(file_upload.original_filename)
            unique_filename = f"{filename_parts[0]}_{uuid.uuid4().hex[:8]}{filename_parts[1]}"
            
            # Save the file
            file_path = os.path.join(file_dir, unique_filename)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            # Generate the URL for accessing the file
            relative_path = os.path.join(org_id, workspace_id, unique_filename)
            file_url = settings.TEMP_STORAGE_URL + relative_path
            
            # Update file upload record with success info
            file_upload.status = 'completed'
            file_upload.storage_path = relative_path
            file_upload.file_url = file_url
            file_upload.save()
            
            # Create processing jobs if needed
            from .models import create_file_processing_jobs
            create_file_processing_jobs(file_upload)
            
        except Exception as e:
            # Handle any errors during file upload
            file_upload.status = 'failed'
            file_upload.processing_error = str(e)
            file_upload.save(update_fields=['status', 'processing_error'])
            
            return Response({
                "error": f"Failed to upload file: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Return the updated file upload record
        serializer = self.get_serializer(file_upload)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        description="List all folders accessible to the user",
        parameters=[
            OpenApiParameter(
                name="workspace",
                description="Filter by workspace ID",
                required=False,
                type=OpenApiTypes.UUID
            ),
            OpenApiParameter(
                name="parent_folder",
                description="Filter by parent folder ID",
                required=False,
                type=OpenApiTypes.UUID
            ),
        ]
    ),
    retrieve=extend_schema(description="Get details of a specific folder"),
    create=extend_schema(description="Create a new folder"),
    update=extend_schema(description="Update a folder"),
    partial_update=extend_schema(description="Partially update a folder"),
    destroy=extend_schema(description="Delete a folder")
)
class FileFolderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing folders.
    
    Provides CRUD operations for folders with appropriate permissions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FileFolderSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['workspace', 'parent_folder', 'access_level']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    search_fields = ['name', 'description']
    throttle_classes = []  # Disable throttling for folders endpoint
    
    def get_queryset(self):
        """Filter folders based on user's access permissions."""
        user = self.request.user
        
        # Get query parameters
        workspace_id = self.request.query_params.get('workspace')
        parent_folder = self.request.query_params.get('parent_folder')
        
        # Base query: folders in user's organization
        queryset = FileFolder.objects.filter(
            organization=user.organization,
            is_active=True
        )
        
        # Filter by workspace if specified
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
            
        # Filter by parent folder if specified
        if parent_folder:
            queryset = queryset.filter(parent_folder=parent_folder)
        else:
            # Root folders (no parent)
            queryset = queryset.filter(parent_folder__isnull=True)
        
        # Filter by access level
        return queryset.filter(
            Q(created_by=user) |  # User's folders
            Q(access_level='organization') |  # Org folders
            Q(  # Workspace folders where user has access
                access_level='workspace',
                workspace__in=user.collaborated_workspaces.values_list('id', flat=True)
            )
        )
    
    def perform_create(self, serializer):
        """Create a new folder."""
        serializer.save()
    
    def check_object_permissions(self, request, obj):
        """Check if user has permission to access this folder."""
        super().check_object_permissions(request, obj)
        
        # Check if user can access this folder
        if not obj.can_access(request.user):
            self.permission_denied(request, message="You do not have permission to access this folder.")


@extend_schema_view(
    list=extend_schema(
        description="List processing jobs",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by job status",
                required=False,
                type=OpenApiTypes.STR,
                enum=[s[0] for s in FileProcessingJob.JOB_STATUS]
            ),
            OpenApiParameter(
                name="job_type",
                description="Filter by job type",
                required=False,
                type=OpenApiTypes.STR,
                enum=[t[0] for t in FileProcessingJob.JOB_TYPES]
            ),
        ]
    ),
    retrieve=extend_schema(description="Get details of a specific processing job")
)
class FileProcessingJobViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing file processing jobs.
    
    Read-only access to processing jobs for monitoring.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FileProcessingJobSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['file_upload', 'job_type', 'status']
    ordering_fields = ['created_at', 'started_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter jobs based on user's organization membership."""
        user = self.request.user
        return FileProcessingJob.objects.filter(
            file_upload__organization=user.organization
        ).select_related('file_upload')
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed processing job."""
        job = self.get_object()
        
        # Only retry failed jobs
        if job.status != 'failed':
            return Response(
                {"error": "Only failed jobs can be retried"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset job status
        job.status = 'queued'
        job.error_message = ''
        job.save(update_fields=['status', 'error_message'])
        
        # In a real implementation, you would trigger an async task to process the job
        # For now, we'll just return the updated job
        serializer = self.get_serializer(job)
        return Response(serializer.data)
