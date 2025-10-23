from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FileStorageBackend, FileUpload, FileProcessingJob, FileFolder

User = get_user_model()


class FileStorageBackendSerializer(serializers.ModelSerializer):
    """Serializer for FileStorageBackend model"""
    
    class Meta:
        model = FileStorageBackend
        fields = [
            'id', 'name', 'backend_type', 'is_active', 'is_default',
            'max_file_size_mb', 'allowed_extensions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Remove sensitive config details from representation"""
        ret = super().to_representation(instance)
        if 'config' in ret:
            # Only include non-sensitive config keys
            safe_config = {}
            if instance.config:
                safe_keys = ['bucket_name', 'region', 'base_url']
                for key in safe_keys:
                    if key in instance.config:
                        safe_config[key] = instance.config[key]
            ret['config'] = safe_config
        return ret


class FileFolderSerializer(serializers.ModelSerializer):
    """Serializer for FileFolder model"""
    
    created_by_name = serializers.SerializerMethodField()
    file_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = FileFolder
        fields = [
            'id', 'organization', 'workspace', 'created_by', 'created_by_name',
            'name', 'description', 'parent_folder', 'access_level',
            'file_count', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'file_count', 'created_at', 'updated_at'
        ]
    
    def get_created_by_name(self, obj):
        """Get the name of the user who created the folder"""
        if obj.created_by:
            # Use username as fallback since get_full_name might not be available
            return getattr(obj.created_by, 'username', 'Unknown User')
        return None
        
    def create(self, validated_data):
        """Create a new folder"""
        # Set organization from the current user
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['created_by'] = user
        
        return super().create(validated_data)


class FileUploadSerializer(serializers.ModelSerializer):
    """Serializer for FileUpload model"""
    
    uploaded_by_name = serializers.SerializerMethodField()
    file_size_mb = serializers.FloatField(read_only=True)
    storage_backend_name = serializers.CharField(source='storage_backend.name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'organization', 'workspace', 'uploaded_by', 'uploaded_by_name',
            'original_filename', 'content_type', 'file_size_bytes', 'file_size_mb',
            'file_extension', 'purpose', 'access_level', 'description',
            'storage_backend', 'storage_backend_name', 'status', 'file_url',
            'last_accessed_at', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = [
            'id', 'file_hash', 'storage_path', 'uploaded_by_name',
            'file_size_mb', 'storage_backend_name', 'status',
            'last_accessed_at', 'created_at', 'updated_at'
        ]
    
    def get_uploaded_by_name(self, obj):
        """Get the name of the user who uploaded the file"""
        if obj.uploaded_by:
            # Use username as fallback since get_full_name might not be available
            return getattr(obj.uploaded_by, 'username', 'Unknown User')
        return None
        
    def get_file_url(self, obj):
        """Get the URL for accessing the file"""
        if hasattr(obj, 'file_url') and obj.file_url:
            return obj.file_url
        return obj.get_file_url


class FileUploadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new FileUpload"""
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'original_filename', 'content_type', 'file_size_bytes', 
            'file_extension', 'purpose', 'access_level', 'description',
            'workspace', 'file_hash', 'status'
        ]
        read_only_fields = ['id', 'status']
    
    def create(self, validated_data):
        """Create a new file upload record"""
        # Set organization from the current user
        user = self.context['request'].user
        validated_data['organization'] = user.organization
        validated_data['uploaded_by'] = user
        
        # Get default storage backend if not specified
        if 'storage_backend' not in validated_data:
            default_backend = FileStorageBackend.objects.filter(
                is_default=True, is_active=True
            ).first()
            if not default_backend:
                raise serializers.ValidationError(
                    {"storage_backend": "No default storage backend is available"}
                )
            validated_data['storage_backend'] = default_backend
        
        # Create the file upload record
        return super().create(validated_data)


class FileProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for FileProcessingJob model"""
    
    file_filename = serializers.CharField(source='file_upload.original_filename', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = FileProcessingJob
        fields = [
            'id', 'file_upload', 'file_filename', 'job_type', 'status',
            'started_at', 'completed_at', 'duration_seconds',
            'result_data', 'error_message', 'retry_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_filename', 'started_at', 'completed_at',
            'duration_seconds', 'result_data', 'error_message',
            'retry_count', 'created_at', 'updated_at'
        ]
    
    def get_duration_seconds(self, obj):
        """Calculate job duration in seconds"""
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class FileUploadDetailSerializer(FileUploadSerializer):
    """Detailed serializer for FileUpload with processing jobs"""
    
    processing_jobs = FileProcessingJobSerializer(many=True, read_only=True)
    
    class Meta(FileUploadSerializer.Meta):
        fields = FileUploadSerializer.Meta.fields + ['processing_jobs', 'extracted_text']
