from rest_framework import permissions


class IsInOrganization(permissions.BasePermission):
    """
    Permission class that checks if the user is a member of the organization.
    Uses the User.has_org_permission method for checking.
    
    By default, requires at least MEMBER role, but can be configured to require
    higher roles like ADMIN or OWNER.
    """
    min_role = 'MEMBER'
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # For objects with direct organization attribute
        if hasattr(obj, 'organization'):
            return request.user.has_org_permission(obj.organization, self.min_role)
        
        # For objects with organization through another relation
        if hasattr(obj, 'get_organization'):
            return request.user.has_org_permission(obj.get_organization(), self.min_role)
            
        return False


class IsOrganizationAdmin(IsInOrganization):
    """Permission class that requires at least ADMIN role in the organization."""
    min_role = 'ADMIN'


class IsOrganizationOwner(IsInOrganization):
    """Permission class that requires OWNER role in the organization."""
    min_role = 'OWNER'
