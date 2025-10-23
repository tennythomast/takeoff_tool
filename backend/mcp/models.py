from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import URLValidator
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import json
import uuid

User = get_user_model()

class MCPServerRegistry(models.Model):
    """Global registry of available MCP servers"""
    
    # Server identification
    qualified_name = models.CharField(max_length=200, unique=True)  # e.g., "github/mcp-server"
    display_name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)  # 'productivity', 'development', 'data'
    icon = models.CharField(max_length=255, blank=True, null=True, help_text="Icon identifier or URL for the integration")
    
    # Server configuration
    server_type = models.CharField(max_length=50, choices=[
        ('stdio', 'Standard I/O'),
        ('http', 'HTTP Server'),
        ('websocket', 'WebSocket'),
    ])
    
    # Installation and deployment info
    install_command = models.TextField(help_text="Command to install/run the server")
    config_schema = models.JSONField(default=dict, help_text="JSON schema for server configuration")
    auth_schema = models.JSONField(default=dict, help_text="JSON schema for authentication")
    
    # Capabilities and metadata
    capabilities = models.JSONField(default=list)  # ['tools', 'resources', 'prompts']
    supported_operations = models.JSONField(default=list)  # List of operations this server supports
    data_schema = models.JSONField(default=dict, help_text="Output data structure")
    
    # Resource scoping capabilities
    supports_workspace_scoping = models.BooleanField(default=False, help_text="Can limit access to specific workspaces/projects")
    scoping_config_schema = models.JSONField(default=dict, help_text="Schema for workspace scoping configuration")
    
    # Registry metadata
    source_url = models.URLField(null=True, blank=True, help_text="Source repository URL")
    documentation_url = models.URLField(null=True, blank=True)
    version = models.CharField(max_length=50, default="latest")
    is_verified = models.BooleanField(default=False, help_text="Verified by Dataelan team")
    is_active = models.BooleanField(default=True)
    
    # Usage and popularity
    usage_count = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mcp_server_registry'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f"{self.display_name} ({self.qualified_name})"

class MCPServerConnection(models.Model):
    """Organization-level MCP server configurations"""
    
    # Ownership and identification
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User who configured this connection")
    server = models.ForeignKey(MCPServerRegistry, on_delete=models.CASCADE)
    
    # User-defined configuration
    connection_name = models.CharField(max_length=200, help_text="User-friendly name for this connection")
    description = models.TextField(blank=True)
    
    # Server configuration and authentication
    config = models.JSONField(default=dict, help_text="Server-specific configuration")
    auth_data = models.TextField(help_text="Encrypted authentication credentials")
    
    # Connection status and health
    is_active = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)
    last_health_check = models.DateTimeField(null=True, blank=True)
    health_status = models.CharField(max_length=50, choices=[
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('unknown', 'Unknown'),
    ], default='unknown')
    
    # Performance and usage metrics
    total_requests = models.PositiveIntegerField(default=0)
    failed_requests = models.PositiveIntegerField(default=0)
    avg_response_time = models.DecimalField(max_digits=8, decimal_places=3, default=0.000)
    
    # Cost tracking
    total_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    monthly_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mcp_server_connections'
        unique_together = [['organization', 'connection_name']]
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def encrypt_auth_data(self, auth_dict):
        """Encrypt authentication data before storing"""
        cipher = Fernet(settings.MCP_ENCRYPTION_KEY.encode())
        auth_json = json.dumps(auth_dict)
        encrypted_data = cipher.encrypt(auth_json.encode())
        self.auth_data = encrypted_data.decode()
    
    def decrypt_auth_data(self):
        """Decrypt authentication data for use"""
        cipher = Fernet(settings.MCP_ENCRYPTION_KEY.encode())
        decrypted_data = cipher.decrypt(self.auth_data.encode())
        return json.loads(decrypted_data.decode())
    
    def __str__(self):
        return f"{self.connection_name} ({self.server.display_name})"



class MCPResourceDiscovery(models.Model):
    """Discovered resources from MCP servers"""
    
    # Connection reference
    connection = models.ForeignKey(MCPServerConnection, on_delete=models.CASCADE, related_name='resources')
    
    # Resource identification
    resource_uri = models.CharField(max_length=500)  # e.g., "jira://PROJ-123/issues"
    resource_name = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=100)  # 'issues', 'projects', 'users'
    description = models.TextField(blank=True)
    
    # Resource schema and capabilities
    schema = models.JSONField(default=dict, help_text="Resource data schema")
    operations = models.JSONField(default=list, help_text="Supported operations on this resource")
    
    # Scoping metadata
    external_id = models.CharField(max_length=200, help_text="External system ID (e.g., Asana project ID)")
    parent_resource = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                                       help_text="Parent resource for hierarchical access")
    
    # Discovery metadata
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'mcp_resource_discovery'
        unique_together = [['connection', 'resource_uri']]
        indexes = [
            models.Index(fields=['connection', 'resource_type']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        return f"{self.resource_name} ({self.resource_type})"
        
    def save(self, *args, **kwargs):
        """Override save to broadcast updates"""
        # Check if this is an update (has ID) or new resource
        is_update = self.pk is not None
        
        # Save the resource
        super().save(*args, **kwargs)
        
        # Import here to avoid circular imports
        from .events import broadcast_resource_update
        
        # Broadcast update if resource was modified
        if is_update:
            broadcast_resource_update(self)

class MCPWorkspaceAccess(models.Model):
    """Workspace-level access control for MCP resources"""
    
    # Workspace and connection
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE, related_name='mcp_access')
    connection = models.ForeignKey(MCPServerConnection, on_delete=models.CASCADE, related_name='workspace_access')
    
    # Access configuration
    access_name = models.CharField(max_length=200, help_text="Friendly name for this access configuration")
    description = models.TextField(blank=True)
    
    # Resource scoping
    allowed_resources = models.ManyToManyField(MCPResourceDiscovery, blank=True,
                                             help_text="Specific resources accessible to this workspace")
    
    # Fine-grained access control
    resource_filters = models.JSONField(default=dict, help_text="JSON filters for resource access")
    # Example: {"project_ids": ["PROJ-123", "PROJ-456"], "issue_types": ["bug", "feature"]}
    
    permission_level = models.CharField(max_length=50, choices=[
        ('read', 'Read Only'),
        ('write', 'Read/Write'),
        ('admin', 'Full Access'),
    ], default='read')
    
    # Operational settings
    is_active = models.BooleanField(default=True)
    auto_sync = models.BooleanField(default=True, help_text="Automatically sync new resources")
    
    # Usage tracking
    last_used = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'mcp_workspace_access'
        unique_together = [['workspace', 'connection', 'access_name']]
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['connection', 'is_active']),
        ]
    
    def get_accessible_resources_mvp(self, resource_type=None):
        """Simplified resource access for MVP"""
        # Start with just explicit resource lists
        resources = self.allowed_resources.filter(is_available=True)
        
        if resource_type:
            resources = resources.filter(resource_type=resource_type)
        
        # Skip complex filtering for MVP - just use explicit allow lists
        return resources
    
    def get_accessible_resources(self, resource_type=None):
        """Get resources accessible to this workspace"""
        # For MVP, use the simplified version
        return self.get_accessible_resources_mvp(resource_type)
        
        # The following is the full implementation that will be enabled after MVP
        """
        # Start with explicitly allowed resources
        base_resources = self.allowed_resources.filter(is_available=True)
        
        # Add resources that are children of allowed resources (hierarchical access)
        child_resources = MCPResourceDiscovery.objects.filter(
            connection=self.connection,
            is_available=True,
            parent_resource__in=base_resources
        )
        
        # Combine explicitly allowed and child resources
        # We use a union to avoid duplicates
        resources = base_resources.union(child_resources)
        
        # Filter by resource type if specified
        if resource_type:
            resources = resources.filter(resource_type=resource_type)
        
        # Apply resource filters based on server type
        if self.resource_filters:
            # Get all resources from the connection
            all_connection_resources = MCPResourceDiscovery.objects.filter(
                connection=self.connection,
                is_available=True
            )
            
            if resource_type:
                all_connection_resources = all_connection_resources.filter(resource_type=resource_type)
            
            # Create a set of IDs from our current resources
            current_ids = set(resources.values_list('id', flat=True))
            filtered_ids = set()
            
            # Apply filters to each resource
            for resource in all_connection_resources:
                if self._check_resource_filters(resource):
                    filtered_ids.add(resource.id)
            
            # Combine with our current resources
            final_ids = current_ids.union(filtered_ids)
            
            # Get the final queryset
            resources = MCPResourceDiscovery.objects.filter(id__in=final_ids)
        
        return resources
        """
    
    def can_access_resource_mvp(self, resource):
        """Simplified resource access check for MVP"""
        # First check if workspace access is active
        if not self.is_active:
            return False
            
        # Quick check - is this resource from the same connection?
        if resource.connection_id != self.connection_id:
            return False
            
        # For MVP, only check if resource is explicitly allowed
        return self.allowed_resources.filter(id=resource.id).exists()
    
    def can_access_resource(self, resource):
        """Check if workspace can access a specific resource"""
        # For MVP, use the simplified version
        return self.can_access_resource_mvp(resource)
        
        # The following is the full implementation that will be enabled after MVP
        """
        # Quick check - is this resource from the same connection?
        if resource.connection_id != self.connection_id:
            return False
            
        # Check if resource is explicitly allowed
        if self.allowed_resources.filter(id=resource.id).exists():
            return True
            
        # Check if any parent resource is allowed (hierarchical access)
        parent = resource.parent_resource
        while parent:
            if self.allowed_resources.filter(id=parent.id).exists():
                return True
            parent = parent.parent_resource
            
        # Apply resource filters if no explicit or hierarchical access
        if self.resource_filters:
            return self._check_resource_filters(resource)
            
        return False
        """
    
    def _check_resource_filters(self, resource):
        """Apply resource filters to determine access"""
        # Get server type to apply appropriate filter logic
        server_type = resource.connection.server.qualified_name.split('/')[0]
        resource_type = resource.resource_type
        
        # Common filters that apply to all resource types
        if 'resource_types' in self.resource_filters and resource_type not in self.resource_filters['resource_types']:
            return False
            
        # Server-specific filtering logic
        if server_type == 'asana':
            return self._check_asana_filters(resource)
        elif server_type == 'jira':
            return self._check_jira_filters(resource)
        elif server_type == 'github':
            return self._check_github_filters(resource)
        elif server_type == 'slack':
            return self._check_slack_filters(resource)
        elif server_type == 'openai' or server_type == 'anthropic':
            return self._check_llm_filters(resource)
        
        # For any other server type, apply generic filtering
        return self._check_generic_filters(resource)
        
    def _check_asana_filters(self, resource):
        """Asana-specific resource filtering"""
        filters = self.resource_filters
        
        # Project-based filtering
        if 'project_ids' in filters and resource.external_id:
            if resource.resource_type == 'project' and resource.external_id in filters['project_ids']:
                return True
            if resource.resource_type == 'task' and resource.parent_resource and \
               resource.parent_resource.external_id in filters['project_ids']:
                return True
                
        # Workspace-based filtering (Asana workspaces, not our workspaces)
        if 'workspace_ids' in filters and 'workspace_id' in resource.schema:
            return resource.schema['workspace_id'] in filters['workspace_ids']
            
        return False
        
    def _check_jira_filters(self, resource):
        """JIRA-specific resource filtering"""
        filters = self.resource_filters
        
        # Project-based filtering
        if 'project_keys' in filters:
            if resource.resource_type == 'project' and resource.external_id in filters['project_keys']:
                return True
            # Check if issue belongs to allowed project
            if resource.resource_type == 'issue' and resource.resource_uri:
                # Extract project key from issue key (e.g., 'PROJ-123' -> 'PROJ')
                parts = resource.resource_uri.split('/')
                if len(parts) > 0:
                    issue_key = parts[-1]
                    project_key = issue_key.split('-')[0] if '-' in issue_key else None
                    if project_key and project_key in filters['project_keys']:
                        return True
        
        # Issue type filtering
        if 'issue_types' in filters and resource.resource_type == 'issue' and 'issue_type' in resource.schema:
            return resource.schema['issue_type'] in filters['issue_types']
            
        return False
        
    def _check_github_filters(self, resource):
        """GitHub-specific resource filtering"""
        filters = self.resource_filters
        
        # Repository-based filtering
        if 'repositories' in filters:
            if resource.resource_type == 'repository' and resource.resource_name in filters['repositories']:
                return True
            if resource.parent_resource and resource.parent_resource.resource_type == 'repository' and \
               resource.parent_resource.resource_name in filters['repositories']:
                return True
                
        # Organization-based filtering
        if 'organizations' in filters and 'organization' in resource.schema:
            return resource.schema['organization'] in filters['organizations']
            
        return False
        
    def _check_slack_filters(self, resource):
        """Slack-specific resource filtering"""
        filters = self.resource_filters
        
        # Channel-based filtering
        if 'channels' in filters and resource.resource_type == 'channel':
            return resource.resource_name in filters['channels'] or resource.external_id in filters['channels']
            
        # User-based filtering
        if 'users' in filters and resource.resource_type == 'user':
            return resource.resource_name in filters['users'] or resource.external_id in filters['users']
            
        return False
        
    def _check_llm_filters(self, resource):
        """LLM provider-specific resource filtering"""
        filters = self.resource_filters
        
        # Model-based filtering
        if 'models' in filters and resource.resource_type == 'model':
            return resource.resource_name in filters['models']
            
        # Feature-based filtering
        if 'features' in filters and 'features' in resource.schema:
            # Check if all required features are supported
            required_features = set(filters['features'])
            supported_features = set(resource.schema.get('features', []))
            return required_features.issubset(supported_features)
            
        return False
        
    def _check_generic_filters(self, resource):
        """Generic resource filtering for any MCP server type"""
        filters = self.resource_filters
        
        # Type-based filtering
        if 'resource_types' in filters:
            if resource.resource_type not in filters['resource_types']:
                return False
                
        # Name-based filtering
        if 'resource_names' in filters:
            if resource.resource_name in filters['resource_names']:
                return True
                
        # URI pattern matching
        if 'uri_patterns' in filters:
            for pattern in filters['uri_patterns']:
                if pattern in resource.resource_uri or resource.resource_uri.startswith(pattern):
                    return True
                    
        # Schema property matching
        if 'properties' in filters and resource.schema:
            for prop_name, prop_value in filters['properties'].items():
                if prop_name not in resource.schema or resource.schema[prop_name] != prop_value:
                    return False
            return True
            
        return False
    
    def __str__(self):
        return f"{self.workspace.name} -> {self.connection.connection_name} ({self.access_name})"

class MCPResourceUsage(models.Model):
    """Track resource usage for analytics and billing"""
    
    workspace_access = models.ForeignKey(MCPWorkspaceAccess, on_delete=models.CASCADE, related_name='usage')
    resource = models.ForeignKey(MCPResourceDiscovery, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Usage details
    operation = models.CharField(max_length=100)  # 'read', 'write', 'list', 'search'
    request_data = models.JSONField(default=dict, help_text="Request parameters")
    response_size = models.PositiveIntegerField(default=0, help_text="Response size in bytes")
    
    # Performance metrics
    response_time = models.DecimalField(max_digits=8, decimal_places=3, help_text="Response time in seconds")
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Cost tracking
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.000000)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'mcp_resource_usage'
        indexes = [
            models.Index(fields=['workspace_access', 'timestamp']),
            models.Index(fields=['resource', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} -> {self.resource.resource_name} ({self.operation})"

class MCPResourceMapping(models.Model):
    """Maps external resource identifiers to internal workflow components"""
    
    workspace_access = models.ForeignKey(MCPWorkspaceAccess, on_delete=models.CASCADE, related_name='mappings')
    resource = models.ForeignKey(MCPResourceDiscovery, on_delete=models.CASCADE)
    
    # Internal mapping
    workflow_component = models.CharField(max_length=200, help_text="Internal component ID")
    component_type = models.CharField(max_length=50, choices=[
        ('agent', 'AI Agent'),
        ('workflow', 'Workflow'),
        ('template', 'Template'),
        ('tool', 'Tool'),
    ])
    
    # Mapping configuration
    mapping_config = models.JSONField(default=dict, help_text="Configuration for how resource is used")
    
    # Status
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mcp_resource_mapping'
        unique_together = [['workspace_access', 'resource', 'workflow_component']]
        indexes = [
            models.Index(fields=['workspace_access', 'component_type']),
        ]
    
    def __str__(self):
        return f"{self.workspace_access} - {self.resource} - {self.workflow_component}"


class UserIntegrationPermission(models.Model):
    """Base permission model for user integration access"""
    
    class PermissionLevel(models.TextChoices):
        READ = 'READ', _('Read Only')
        WRITE = 'WRITE', _('Read & Write')
        ADMIN = 'ADMIN', _('Admin')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='integration_permissions'
    )
    
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='integration_permissions'
    )
    
    integration_type = models.CharField(
        max_length=50,
        choices=[
            ('MCP', 'Model Control Plane'),
            ('JIRA', 'Jira'),
            ('GITHUB', 'GitHub'),
            ('SLACK', 'Slack'),
            ('ASANA', 'Asana'),
            ('CUSTOM', 'Custom Integration')
        ],
        default='MCP'
    )
    
    permission_level = models.CharField(
        max_length=20,
        choices=PermissionLevel.choices,
        default=PermissionLevel.READ
    )
    
    # JSON field to store integration-specific permission details
    permission_details = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Integration-specific permission details')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'organization', 'integration_type')
        verbose_name = _('User Integration Permission')
        verbose_name_plural = _('User Integration Permissions')
    
    def __str__(self):
        return f"{self.user.email} - {self.integration_type} - {self.permission_level}"


class MCPPermissionScope(models.Model):
    """Permission scope specific to MCP resources"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration_permission = models.ForeignKey(
        UserIntegrationPermission,
        on_delete=models.CASCADE,
        related_name='mcp_scopes',
        limit_choices_to={'integration_type': 'MCP'}
    )
    
    # Resource scope patterns (e.g., "jira:project/*", "github:repo/user/*")
    resource_pattern = models.CharField(
        max_length=255,
        help_text=_('Resource pattern for permission scope (supports wildcards)')
    )
    
    # Specific operations allowed on matching resources
    allowed_operations = models.JSONField(
        default=list,
        help_text=_('List of allowed operations on matching resources')
    )
    
    # Whether this scope is inherited from organization role
    inherited_from_role = models.BooleanField(
        default=False,
        help_text=_('Whether this scope is inherited from organization role')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('MCP Permission Scope')
        verbose_name_plural = _('MCP Permission Scopes')
    
    def __str__(self):
        return f"{self.integration_permission.user.email} - {self.resource_pattern}"