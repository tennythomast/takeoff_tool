# apps/permissions/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

class Role(models.Model):
    """RBAC roles with clear permission boundaries"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    
    # Role-based constraints (max boundaries, not specific permissions)
    max_data_scope = models.CharField(max_length=50, choices=[
        ('personal', 'Personal data only'),
        ('team', 'Team data'),
        ('department', 'Department data'),
        ('organization', 'Full organization')
    ])
    
    # Integration access boundaries
    allowed_integrations = models.JSONField(default=list)  # ['jira', 'slack']
    prohibited_actions = models.JSONField(default=list)    # ['delete', 'admin']
    
    class Meta:
        db_table = 'permissions_roles'

class Integration(models.Model):
    """External system integrations"""
    name = models.CharField(max_length=100)  # 'jira', 'slack', 'asana'
    display_name = models.CharField(max_length=100)
    
    # Default permission scopes for this integration
    default_permissions = models.JSONField(default=dict)
    
    # Role-specific defaults
    role_defaults = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'permissions_integrations'

class UserIntegrationPermission(models.Model):
    """The main permission model combining RBAC + Smart Defaults + User Choice"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE)
    
    # === RBAC Layer ===
    role_constraints = models.JSONField(default=dict)  # From user's role
    
    # === Smart Defaults Layer ===
    external_permissions = models.JSONField(default=dict)  # From Jira/Slack API
    calculated_defaults = models.JSONField(default=dict)   # Smart default result
    
    # === User Choice Layer ===
    user_choice = models.CharField(max_length=20, choices=[
        ('minimal', 'Minimal Access'),
        ('smart_default', 'Smart Default'),
        ('enhanced', 'Enhanced Access'),
        ('custom', 'Custom Configuration')
    ], default='smart_default')
    
    custom_permissions = models.JSONField(default=dict)  # When user_choice='custom'
    
    # === Final Effective Permissions ===
    effective_permissions = models.JSONField(default=dict)  # Calculated result
    
    # Metadata
    last_calculated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'permissions_user_integrations'
        unique_together = ['user', 'integration']

class PermissionCalculationLog(models.Model):
    """Audit trail for permission calculations"""
    user_permission = models.ForeignKey(UserIntegrationPermission, on_delete=models.CASCADE)
    
    calculation_input = models.JSONField()  # What went into the calculation
    calculation_output = models.JSONField() # What came out
    calculation_reason = models.TextField() # Why these permissions were chosen
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'permissions_calculation_logs'


class Integration(models.Model):
    """Updated to work with MCP servers"""
    name = models.CharField(max_length=100, unique=True)  # 'mcp:github', 'mcp:slack'
    display_name = models.CharField(max_length=100)
    integration_type = models.CharField(max_length=20, choices=[
        ('mcp', 'MCP Server'),
        ('api', 'Direct API'),
        ('webhook', 'Webhook'),
    ], default='mcp')
    
    # MCP-specific fields
    mcp_server = models.ForeignKey(
        'mcp.MCPServerRegistry', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE,
        help_text="Associated MCP server if integration_type is 'mcp'"
    )
    
    # Permission configuration
    default_permissions = models.JSONField(default=dict)
    role_defaults = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'permissions_integrations'

class MCPPermissionScope(models.Model):
    """MCP-specific permission scopes that extend the base permission system"""
    
    user_permission = models.OneToOneField(
        'permissions.UserIntegrationPermission',
        on_delete=models.CASCADE,
        related_name='mcp_scope'
    )
    
    # MCP server connection reference
    mcp_connection = models.ForeignKey(
        'mcp.MCPServerConnection',
        on_delete=models.CASCADE,
        help_text="Which MCP server connection these permissions apply to"
    )
    
    # Resource-level permissions
    accessible_resources = models.JSONField(default=list, help_text="List of resource URIs user can access")
    resource_permissions = models.JSONField(default=dict, help_text="Permissions per resource type")
    
    # Operation-level permissions
    allowed_operations = models.JSONField(default=list, help_text="Operations user can perform")
    denied_operations = models.JSONField(default=list, help_text="Explicitly denied operations")
    
    # Data scope limitations
    data_filters = models.JSONField(default=dict, help_text="Filters to apply to data access")
    rate_limits = models.JSONField(default=dict, help_text="Rate limiting configuration")
    
    class Meta:
        db_table = 'permissions_mcp_scopes'