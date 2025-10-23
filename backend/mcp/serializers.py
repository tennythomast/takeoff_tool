from rest_framework import serializers
from .models import (
    MCPServerRegistry, MCPServerConnection, MCPResourceDiscovery,
    MCPWorkspaceAccess, MCPResourceUsage, MCPResourceMapping
)
from django.contrib.auth import get_user_model

User = get_user_model()

class MCPServerRegistrySerializer(serializers.ModelSerializer):
    """Serializer for MCP server registry entries"""
    
    class Meta:
        model = MCPServerRegistry
        fields = [
            'id', 'qualified_name', 'display_name', 'description', 'category',
            'server_type', 'capabilities', 'supported_operations',
            'supports_workspace_scoping', 'version', 'is_verified', 'is_active',
            'documentation_url', 'source_url', 'rating', 'icon'
        ]
        read_only_fields = ['id', 'is_verified', 'rating', 'usage_count']


class MCPServerConnectionSerializer(serializers.ModelSerializer):
    """Serializer for organization's MCP server connections"""
    
    server_name = serializers.CharField(source='server.display_name', read_only=True)
    server_type = serializers.CharField(source='server.server_type', read_only=True)
    
    class Meta:
        model = MCPServerConnection
        fields = [
            'id', 'organization', 'user', 'server', 'server_name', 'server_type',
            'connection_name', 'description', 'config', 'is_active', 'is_connected',
            'health_status', 'last_health_check', 'total_requests', 'failed_requests',
            'avg_response_time', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'is_connected', 'health_status', 'last_health_check',
            'total_requests', 'failed_requests', 'avg_response_time',
            'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Additional validation for connection creation"""
        print(f"[DEBUG] Validating data: {data}")
        
        # Check if auth_data is present in the request - only required for new connections
        request = self.context.get('request')
        if not self.instance and request and not request.data.get('auth_data'):
            print("[DEBUG] auth_data is missing from the request for a new connection")
            raise serializers.ValidationError({"auth_data": "Authentication data is required for new connections"})
        
        # Get the current user from the request context
        user = self.context.get('request').user
        
        # Add user to validated data if not present (for compliance tracking)
        if 'user' not in data and not self.instance:
            # Only add for new instances, not updates
            data['user'] = user
            print(f"[DEBUG] Added user {user.email} to validated data")
        
        # We'll skip strict organization validation here since we're going to
        # override it in perform_create anyway to ensure it matches the user's organization
        # This allows the frontend to send any organization ID or even omit it
        if 'organization' in data:
            org = data['organization']
            user_org = user.organization
            print(f"[DEBUG] Frontend sent organization: {org.id}, user's organization: {user_org.id if user_org else None}")
            
            # Just log a warning if they don't match, but don't raise an error
            if user_org and org.id != user_org.id:
                print(f"[DEBUG] Warning: Organization {org.id} does not match user's organization {user_org.id}")
                print(f"[DEBUG] Will use user's organization {user_org.id} instead")
        
        return data
    
    def create(self, validated_data):
        """Handle auth_data encryption during creation"""
        request = self.context.get('request')
        auth_data = request.data.get('auth_data', {}) if request else {}
        print(f"[DEBUG] Creating connection with validated data: {validated_data}")
        print(f"[DEBUG] Auth data present: {bool(auth_data)}")
        
        try:
            instance = super().create(validated_data)
            
            if auth_data:
                instance.encrypt_auth_data(auth_data)
                instance.save()
            
            return instance
        except Exception as e:
            print(f"[DEBUG] Error in create: {e}")
            raise
    
    def update(self, instance, validated_data):
        """Handle auth_data encryption during update"""
        auth_data = self.context.get('request').data.get('auth_data', {})
        instance = super().update(instance, validated_data)
        
        if auth_data:
            instance.encrypt_auth_data(auth_data)
            instance.save()
        
        return instance


class MCPResourceDiscoverySerializer(serializers.ModelSerializer):
    """Serializer for discovered MCP resources"""
    
    connection_name = serializers.CharField(source='connection.connection_name', read_only=True)
    server_name = serializers.CharField(source='connection.server.display_name', read_only=True)
    parent_name = serializers.CharField(source='parent_resource.resource_name', read_only=True, allow_null=True)
    
    class Meta:
        model = MCPResourceDiscovery
        fields = [
            'id', 'connection', 'connection_name', 'server_name',
            'resource_uri', 'resource_name', 'resource_type', 'description',
            'schema', 'operations', 'external_id', 'parent_resource', 'parent_name',
            'discovered_at', 'last_verified', 'is_available'
        ]
        read_only_fields = ['id', 'discovered_at', 'last_verified']


class MCPWorkspaceAccessSerializer(serializers.ModelSerializer):
    """Serializer for workspace-level MCP resource access"""
    
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    connection_name = serializers.CharField(source='connection.connection_name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    allowed_resource_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MCPWorkspaceAccess
        fields = [
            'id', 'workspace', 'workspace_name', 'connection', 'connection_name',
            'access_name', 'description', 'allowed_resources', 'allowed_resource_count',
            'resource_filters', 'permission_level', 'is_active', 'auto_sync',
            'last_used', 'usage_count', 'created_at', 'updated_at',
            'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'last_used', 'usage_count', 'created_at', 'updated_at']
    
    def get_allowed_resource_count(self, obj):
        """Get count of allowed resources"""
        return obj.allowed_resources.count()


class MCPResourceUsageSerializer(serializers.ModelSerializer):
    """Serializer for MCP resource usage tracking"""
    
    workspace_name = serializers.CharField(source='workspace_access.workspace.name', read_only=True)
    resource_name = serializers.CharField(source='resource.resource_name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = MCPResourceUsage
        fields = [
            'id', 'workspace_access', 'workspace_name', 'resource', 'resource_name',
            'user', 'username', 'operation', 'request_data', 'response_size',
            'response_time', 'success', 'error_message', 'cost',
            'timestamp', 'session_id'
        ]
        read_only_fields = ['id', 'timestamp']


class MCPResourceMappingSerializer(serializers.ModelSerializer):
    """Serializer for mapping MCP resources to internal components"""
    
    workspace_name = serializers.CharField(source='workspace_access.workspace.name', read_only=True)
    resource_name = serializers.CharField(source='resource.resource_name', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)
    
    class Meta:
        model = MCPResourceMapping
        fields = [
            'id', 'workspace_access', 'workspace_name', 'resource', 'resource_name',
            'resource_type', 'workflow_component', 'component_type',
            'mapping_config', 'is_active', 'last_sync', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
