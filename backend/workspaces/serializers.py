from rest_framework import serializers
from .models import Workspace, WorkspaceCollaborator


class WorkspaceCollaboratorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = WorkspaceCollaborator
        fields = ('id', 'user', 'user_email', 'user_name', 'role', 'created_at', 'metadata')
        read_only_fields = ('id', 'created_at')

    def validate(self, data):
        if not self.instance:  # Only validate on create
            workspace = self.context.get('workspace')
            if workspace and 'user' in data:
                # Check if this user is already a collaborator
                if WorkspaceCollaborator.objects.filter(
                    workspace=workspace,
                    user=data['user']
                ).exists():
                    raise serializers.ValidationError(
                        'This user is already a collaborator on this workspace.'
                    )
        return data

    def create(self, validated_data):
        workspace = self.context.get('workspace')
        if not workspace:
            raise serializers.ValidationError('Workspace context is required')
        validated_data['workspace'] = workspace
        return super().create(validated_data)


class WorkspaceSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    owner_name = serializers.CharField(source='owner.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    collaborators = WorkspaceCollaboratorSerializer(source='workspace_collaborators', many=True, read_only=True)
    workspace_type_display = serializers.CharField(source='get_workspace_type_display', read_only=True)

    class Meta:
        model = Workspace
        fields = (
            'id', 'name', 'description', 'organization', 'organization_name',
            'owner', 'owner_email', 'owner_name', 'status', 'collaborators',
            'workspace_type', 'workspace_type_display', 'is_system_workspace',
            'created_at', 'updated_at', 'started_at', 'metadata'
        )
        read_only_fields = ('id', 'owner', 'created_at', 'updated_at', 'started_at')

    def validate_organization(self, value):
        """Ensure user has access to the organization."""
        user = self.context.get('request').user if self.context.get('request') else None
        if user and not user.is_member(value):
            raise serializers.ValidationError("You don't have access to this organization.")
        return value

    def validate(self, data):
        """Ensure owner is not set directly."""
        if 'owner' in data:
            raise serializers.ValidationError("Owner cannot be set directly.")
        return data

    def create(self, validated_data):
        """Set owner to current user when creating."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        return super().create(validated_data)



class WorkspaceDetailSerializer(WorkspaceSerializer):
    class Meta(WorkspaceSerializer.Meta):
        fields = WorkspaceSerializer.Meta.fields
