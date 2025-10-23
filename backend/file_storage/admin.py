from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import FileStorageBackend, FileUpload, FileProcessingJob


@admin.register(FileStorageBackend)
class FileStorageBackendAdmin(admin.ModelAdmin):
    list_display = ('name', 'backend_type', 'is_active', 'is_default', 'max_file_size_mb', 'created_at')
    list_filter = ('backend_type', 'is_active', 'is_default')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'backend_type', 'is_active', 'is_default')
        }),
        ('Configuration', {
            'fields': ('config',)
        }),
        ('Security Limits', {
            'fields': ('max_file_size_mb', 'allowed_extensions')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = (
        'original_filename', 'organization', 'workspace_link', 'purpose',
        'access_level', 'file_size_display', 'status', 'uploaded_by',
        'created_at'
    )
    list_filter = ('purpose', 'access_level', 'status', 'file_extension', 'storage_backend')
    search_fields = ('original_filename', 'description', 'file_hash')
    readonly_fields = (
        'file_hash', 'storage_path', 'file_size_mb', 'last_accessed_at',
        'created_at', 'updated_at', 'processing_jobs_link'
    )
    raw_id_fields = ('organization', 'workspace', 'uploaded_by', 'storage_backend')
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'original_filename', 'content_type', 'file_extension',
                'file_size_bytes', 'file_size_mb', 'description'
            )
        }),
        ('Organization & Access', {
            'fields': (
                'organization', 'workspace', 'uploaded_by',
                'purpose', 'access_level'
            )
        }),
        ('Storage', {
            'fields': ('storage_backend', 'storage_path', 'file_hash')
        }),
        ('Processing', {
            'fields': ('status', 'processing_error', 'processing_jobs_link')
        }),
        ('Content', {
            'fields': ('extracted_text',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('last_accessed_at', 'created_at', 'updated_at', 'is_active')
        }),
    )
    
    def file_size_display(self, obj):
        """Format file size for display"""
        return f"{obj.file_size_mb} MB"
    file_size_display.short_description = "Size"
    
    def workspace_link(self, obj):
        """Display workspace with link"""
        if obj.workspace:
            url = reverse('admin:workspaces_workspace_change', args=[obj.workspace.id])
            return format_html('<a href="{}">{}</a>', url, obj.workspace.name)
        return "-"
    workspace_link.short_description = "Workspace"
    
    def processing_jobs_link(self, obj):
        """Display link to processing jobs"""
        count = obj.processing_jobs.count()
        if count:
            url = reverse('admin:file_storage_fileprocessingjob_changelist') + f"?file_upload__id__exact={obj.id}"
            return format_html('<a href="{}">{} Processing Jobs</a>', url, count)
        return "No processing jobs"
    processing_jobs_link.short_description = "Processing Jobs"


@admin.register(FileProcessingJob)
class FileProcessingJobAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'file_link', 'job_type', 'status',
        'duration_display', 'retry_count', 'created_at'
    )
    list_filter = ('job_type', 'status')
    search_fields = ('file_upload__original_filename', 'error_message')
    readonly_fields = (
        'started_at', 'completed_at', 'duration_display',
        'created_at', 'updated_at'
    )
    raw_id_fields = ('file_upload',)
    fieldsets = (
        ('Job Information', {
            'fields': ('file_upload', 'job_type', 'status', 'retry_count')
        }),
        ('Execution', {
            'fields': ('started_at', 'completed_at', 'duration_display')
        }),
        ('Results', {
            'fields': ('result_data', 'error_message')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def file_link(self, obj):
        """Display file with link"""
        if obj.file_upload:
            url = reverse('admin:file_storage_fileupload_change', args=[obj.file_upload.id])
            return format_html('<a href="{}">{}</a>', url, obj.file_upload.original_filename)
        return "-"
    file_link.short_description = "File"
    
    def duration_display(self, obj):
        """Format duration for display"""
        if obj.started_at and obj.completed_at:
            seconds = (obj.completed_at - obj.started_at).total_seconds()
            if seconds < 60:
                return f"{seconds:.2f} seconds"
            else:
                minutes = seconds / 60
                return f"{minutes:.2f} minutes"
        return "-"
    duration_display.short_description = "Duration"
