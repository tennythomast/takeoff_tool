from typing import Dict, List, Any, Optional
from rest_framework import permissions
from django.contrib.auth import get_user_model
from .models import (
    UserIntegrationPermission, 
    MCPPermissionScope,
    MCPServerConnection, 
    MCPWorkspaceAccess, 
    MCPResourceDiscovery
)

User = get_user_model()

class IsOrganizationMember(permissions.BasePermission):
    """Permission to check if user is a member of the organization"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # For MCPServerConnection objects
        if hasattr(obj, 'organization'):
            return request.user.organizations.filter(id=obj.organization.id).exists()
        
        # For MCPResourceDiscovery objects
        if hasattr(obj, 'connection') and hasattr(obj.connection, 'organization'):
            return request.user.organizations.filter(id=obj.connection.organization.id).exists()
        
        return False


class IsWorkspaceMember(permissions.BasePermission):
    """Permission to check if user is a member of the workspace"""
    
    def has_permission(self, request, view):
        # Basic authentication check
        if not request.user.is_authenticated:
            print(f"User not authenticated: {request.user}")
            return False
            
        # If we're accessing a list endpoint and a workspace query param is provided
        # Check if the user is a member of that workspace
        workspace_id = request.query_params.get('workspace')
        if workspace_id and hasattr(request.user, 'workspaces'):
            print(f"Checking workspace membership for user {request.user.username} in workspace {workspace_id}")
            # Import here to avoid circular imports
            from workspaces.models import Workspace
            try:
                # Check if user is the owner of the workspace
                is_owner = Workspace.objects.filter(id=workspace_id, owner=request.user).exists()
                if is_owner:
                    print(f"User {request.user.username} is the owner of workspace {workspace_id}")
                    return True
                    
                # Check if user is a collaborator in the workspace
                is_collaborator = request.user.collaborated_workspaces.filter(id=workspace_id).exists()
                if is_collaborator:
                    print(f"User {request.user.username} is a collaborator in workspace {workspace_id}")
                    return True
                    
                print(f"User {request.user.username} is NOT a member of workspace {workspace_id}")
                return False
            except Exception as e:
                # Log the error but don't fail the request yet
                print(f"Error checking workspace membership: {e}")
                
        return True  # Default to allowing and let object permission handle it
    
    def has_object_permission(self, request, view, obj):
        # For MCPWorkspaceAccess objects
        if hasattr(obj, 'workspace'):
            return obj.workspace.members.filter(id=request.user.id).exists()
        
        # For MCPResourceMapping objects
        if hasattr(obj, 'workspace_access') and hasattr(obj.workspace_access, 'workspace'):
            return obj.workspace_access.workspace.members.filter(id=request.user.id).exists()
        
        # For MCPResourceUsage objects
        if hasattr(obj, 'workspace_access') and hasattr(obj.workspace_access, 'workspace'):
            return obj.workspace_access.workspace.members.filter(id=request.user.id).exists()
        
        return False


class IsConnectionOwner(permissions.BasePermission):
    """Permission to check if user is the owner of the connection"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # For MCPServerConnection objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class CanManageWorkspaceAccess(permissions.BasePermission):
    """Permission to check if user can manage workspace access configurations"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # For MCPWorkspaceAccess objects
        if hasattr(obj, 'workspace'):
            # Check if user is the workspace owner
            is_workspace_owner = obj.workspace.owner == request.user
            
            # Check if user has admin role in workspace collaborators
            is_workspace_admin = False
            try:
                # Get the collaborator object for this user
                collaborator = obj.workspace.workspace_collaborators.filter(user=request.user).first()
                if collaborator and collaborator.role == 'ADMIN':
                    is_workspace_admin = True
            except Exception as e:
                print(f"Error checking workspace admin status: {e}")
                
            # Check if user is the creator of this access configuration
            is_creator = hasattr(obj, 'created_by') and obj.created_by == request.user
            
            return is_workspace_owner or is_workspace_admin or is_creator
        
        return False


class CanAccessResource(permissions.BasePermission):
    """Permission to check if user can access a specific MCP resource"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # For MCPResourceMapping objects
        if hasattr(obj, 'workspace_access') and hasattr(obj, 'resource'):
            # Check if the workspace access is active
            if not obj.workspace_access.is_active:
                return False
            
            # Check if user is a member of the workspace
            if not obj.workspace_access.workspace.members.filter(id=request.user.id).exists():
                return False
            
            # Check if the resource is allowed in this workspace access
            return obj.workspace_access.can_access_resource(obj.resource)
        
        return False


class MCPPermissionManager:
    """Manage MCP-specific permissions building on the base permission system"""
    
    def __init__(self, user: User, mcp_connection: MCPServerConnection):
        self.user = user
        self.mcp_connection = mcp_connection
        self.base_permission = self._get_or_create_base_permission()
    
    def _get_or_create_base_permission(self) -> UserIntegrationPermission:
        """Get or create base integration permission"""
        integration_name = f"mcp:{self.mcp_connection.server.qualified_name}"
        
        # This leverages your existing permission calculation logic
        permission, created = UserIntegrationPermission.objects.get_or_create(
            user=self.user,
            integration__name=integration_name,
            defaults={
                'user_choice': 'smart_default',
                'effective_permissions': self._calculate_default_permissions()
            }
        )
        
        return permission
    
    def _calculate_default_permissions(self) -> Dict[str, Any]:
        """Calculate default MCP permissions based on server capabilities"""
        # This integrates with your existing permission calculation logic
        server_capabilities = self.mcp_connection.server.capabilities
        
        default_perms = {
            "can_list_resources": True,
            "can_read_resources": True,
            "can_call_tools": "tools" in server_capabilities,
            "can_access_prompts": "prompts" in server_capabilities,
            "max_requests_per_hour": 1000,
            "allowed_resource_types": [],  # Empty means all
        }
        
        return default_perms
    
    def get_mcp_scope(self) -> MCPPermissionScope:
        """Get or create MCP-specific permission scope"""
        mcp_scope, created = MCPPermissionScope.objects.get_or_create(
            user_permission=self.base_permission,
            mcp_connection=self.mcp_connection,
            defaults={
                "accessible_resources": [],
                "allowed_operations": ["list", "read"],
                "data_filters": {},
                "rate_limits": {"requests_per_hour": 1000}
            }
        )
        
        if created:
            self._sync_permissions_from_external()
        
        return mcp_scope
    
    async def _sync_permissions_from_external(self):
        """Sync permissions from external system (e.g., Jira user permissions)"""
        # This could call the MCP server to get user's actual permissions
        # and update the MCPPermissionScope accordingly
        pass
    
    def can_access_resource(self, resource_uri: str) -> bool:
        """Check if user can access specific resource"""
        mcp_scope = self.get_mcp_scope()
        
        # Check base permission first
        if not self.base_permission.effective_permissions.get("can_read_resources", False):
            return False
        
        # Check MCP-specific scope
        if mcp_scope.accessible_resources:
            return resource_uri in mcp_scope.accessible_resources
        
        # If no specific restrictions, allow based on base permissions
        return True
    
    def can_perform_operation(self, operation: str) -> bool:
        """Check if user can perform specific operation"""
        mcp_scope = self.get_mcp_scope()
        
        # Check if operation is explicitly denied
        if operation in mcp_scope.denied_operations:
            return False
        
        # Check if operation is explicitly allowed
        if operation in mcp_scope.allowed_operations:
            return True
        
        # Fall back to base permissions
        return self.base_permission.effective_permissions.get(f"can_{operation}", False)