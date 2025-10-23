from django.contrib import admin
from .models import (
    MCPServerRegistry, MCPServerConnection, MCPResourceDiscovery, 
    MCPWorkspaceAccess, MCPResourceUsage, MCPResourceMapping,
    UserIntegrationPermission, MCPPermissionScope
)

@admin.register(MCPServerRegistry)
class MCPServerRegistryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'qualified_name', 'category', 'server_type', 'version', 'is_verified', 'is_active')
    list_filter = ('category', 'server_type', 'is_verified', 'is_active')
    search_fields = ('display_name', 'qualified_name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'usage_count')
    fieldsets = (
        ('Server Information', {
            'fields': ('qualified_name', 'display_name', 'description', 'category')
        }),
        ('Configuration', {
            'fields': ('server_type', 'install_command', 'config_schema', 'auth_schema')
        }),
        ('Capabilities', {
            'fields': ('capabilities', 'supported_operations', 'data_schema', 'supports_workspace_scoping', 'scoping_config_schema')
        }),
        ('Metadata', {
            'fields': ('source_url', 'documentation_url', 'version', 'is_verified', 'is_active', 'usage_count', 'rating')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(MCPServerConnection)
class MCPServerConnectionAdmin(admin.ModelAdmin):
    list_display = ('connection_name', 'server', 'organization', 'is_active', 'is_connected', 'health_status')
    list_filter = ('is_active', 'is_connected', 'health_status', 'organization')
    search_fields = ('connection_name', 'description', 'server__display_name')
    readonly_fields = ('created_at', 'updated_at', 'total_requests', 'failed_requests', 'avg_response_time', 'total_cost', 'monthly_cost')
    fieldsets = (
        ('Connection Information', {
            'fields': ('organization', 'user', 'server', 'connection_name', 'description')
        }),
        ('Configuration', {
            'fields': ('config', 'auth_data')
        }),
        ('Status', {
            'fields': ('is_active', 'is_connected', 'health_status', 'last_health_check')
        }),
        ('Metrics', {
            'fields': ('total_requests', 'failed_requests', 'avg_response_time', 'total_cost', 'monthly_cost')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(MCPResourceDiscovery)
class MCPResourceDiscoveryAdmin(admin.ModelAdmin):
    list_display = ('resource_name', 'resource_type', 'connection', 'is_available', 'last_verified')
    list_filter = ('resource_type', 'is_available', 'connection')
    search_fields = ('resource_name', 'resource_uri', 'description', 'external_id')
    readonly_fields = ('discovered_at', 'last_verified')
    fieldsets = (
        ('Resource Information', {
            'fields': ('connection', 'resource_uri', 'resource_name', 'resource_type', 'description')
        }),
        ('Schema & Operations', {
            'fields': ('schema', 'operations')
        }),
        ('Scoping', {
            'fields': ('external_id', 'parent_resource')
        }),
        ('Status', {
            'fields': ('is_available', 'discovered_at', 'last_verified')
        }),
    )

@admin.register(MCPWorkspaceAccess)
class MCPWorkspaceAccessAdmin(admin.ModelAdmin):
    list_display = ('access_name', 'workspace', 'connection', 'permission_level', 'is_active')
    list_filter = ('permission_level', 'is_active', 'auto_sync', 'workspace')
    search_fields = ('access_name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_used', 'usage_count')
    filter_horizontal = ('allowed_resources',)
    fieldsets = (
        ('Access Information', {
            'fields': ('workspace', 'connection', 'access_name', 'description', 'created_by')
        }),
        ('Access Control', {
            'fields': ('allowed_resources', 'resource_filters', 'permission_level')
        }),
        ('Settings', {
            'fields': ('is_active', 'auto_sync')
        }),
        ('Usage', {
            'fields': ('last_used', 'usage_count', 'created_at', 'updated_at')
        }),
    )

@admin.register(MCPResourceUsage)
class MCPResourceUsageAdmin(admin.ModelAdmin):
    list_display = ('workspace_access', 'resource', 'user', 'operation', 'success', 'timestamp')
    list_filter = ('success', 'operation')
    search_fields = ('user__username', 'error_message', 'session_id')
    readonly_fields = ('timestamp',)
    fieldsets = (
        ('Usage Information', {
            'fields': ('workspace_access', 'resource', 'user', 'operation')
        }),
        ('Request Details', {
            'fields': ('request_data', 'response_size', 'response_time', 'session_id')
        }),
        ('Status', {
            'fields': ('success', 'error_message', 'cost', 'timestamp')
        }),
    )

@admin.register(MCPResourceMapping)
class MCPResourceMappingAdmin(admin.ModelAdmin):
    list_display = ('workflow_component', 'component_type', 'resource', 'workspace_access', 'is_active')
    list_filter = ('component_type', 'is_active')
    search_fields = ('workflow_component', 'resource__resource_name')
    readonly_fields = ('created_at', 'updated_at', 'last_sync')
    fieldsets = (
        ('Mapping Information', {
            'fields': ('workspace_access', 'resource', 'workflow_component', 'component_type')
        }),
        ('Configuration', {
            'fields': ('mapping_config', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('last_sync', 'created_at', 'updated_at')
        }),
    )

@admin.register(UserIntegrationPermission)
class UserIntegrationPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'integration_type', 'permission_level')
    list_filter = ('integration_type', 'permission_level', 'organization')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Permission Information', {
            'fields': ('id', 'user', 'organization', 'integration_type', 'permission_level')
        }),
        ('Details', {
            'fields': ('permission_details',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(MCPPermissionScope)
class MCPPermissionScopeAdmin(admin.ModelAdmin):
    list_display = ('integration_permission', 'resource_pattern', 'inherited_from_role')
    list_filter = ('inherited_from_role',)
    search_fields = ('resource_pattern',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Scope Information', {
            'fields': ('id', 'integration_permission', 'resource_pattern')
        }),
        ('Operations', {
            'fields': ('allowed_operations', 'inherited_from_role')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
