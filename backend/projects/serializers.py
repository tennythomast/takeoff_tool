from rest_framework import serializers
from .models import Project, ProjectCollaborator


class ProjectCollaboratorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = ProjectCollaborator
        fields = ('id', 'user', 'user_email', 'user_name', 'role', 'created_at', 'metadata')
        read_only_fields = ('id', 'created_at')

    def validate(self, data):
        if not self.instance:  # Only validate on create
            project = self.context.get('project')
            if project and 'user' in data:
                # Check if this user is already a collaborator
                if ProjectCollaborator.objects.filter(
                    project=project,
                    user=data['user']
                ).exists():
                    raise serializers.ValidationError(
                        'This user is already a collaborator on this project.'
                    )
        return data

    def create(self, validated_data):
        project = self.context.get('project')
        if not project:
            raise serializers.ValidationError('Project context is required')
        validated_data['project'] = project
        return super().create(validated_data)


class ProjectSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    owner_name = serializers.CharField(source='owner.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    collaborators = ProjectCollaboratorSerializer(source='project_collaborators', many=True, read_only=True)
    project_type_display = serializers.CharField(source='get_project_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Project
        fields = (
            'id', 'title', 'description', 'client_name', 'client_email', 
            'client_phone', 'client_company', 'project_type', 'project_type_display',
            'budget', 'location', 'tags', 'organization', 'organization_name',
            'owner', 'owner_email', 'owner_name', 'status', 'status_display',
            'collaborators', 'created_at', 'updated_at', 'started_at', 
            'deadline', 'metadata'
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


class ProjectDetailSerializer(ProjectSerializer):
    """Detailed project serializer with additional computed fields."""
    
    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields
