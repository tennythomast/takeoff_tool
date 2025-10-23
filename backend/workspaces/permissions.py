from rest_framework import permissions


class IsWorkspaceAdmin(permissions.BasePermission):
    """
    Custom permission to only allow workspace admins to edit the workspace.
    Workspace admins are either:
    1. The workspace owner
    2. Collaborators with ADMIN role
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any collaborator
        if request.method in permissions.SAFE_METHODS:
            return request.user == obj.owner or obj.collaborators.filter(id=request.user.id).exists()

        # Write permissions are only allowed to workspace admins
        user_collab = obj.workspace_collaborators.filter(user=request.user).first()
        return request.user == obj.owner or (user_collab and user_collab.is_admin())


class IsWorkspaceCollaboratorAdmin(permissions.BasePermission):
    """
    Custom permission to only allow workspace admins to manage collaborators.
    """

    def has_permission(self, request, view):
        workspace_id = view.kwargs.get('workspace_pk')
        if not workspace_id:
            return False

        # Get the workspace
        from .models import Workspace
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return False

        # Check if user is workspace owner or admin
        user_collab = workspace.workspace_collaborators.filter(user=request.user).first()
        return request.user == workspace.owner or (user_collab and user_collab.is_admin())
