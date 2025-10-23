from django.db.models import Count, Sum, Q, QuerySet, Subquery, OuterRef
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError
from rest_framework import viewsets, status, filters, serializers
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Workspace, WorkspaceCollaborator
from modelhub.models import ModelMetrics
from .serializers import (
    WorkspaceSerializer, WorkspaceDetailSerializer, WorkspaceCollaboratorSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary='List workspaces',
        description='Get a list of all workspaces the user has access to.',
        parameters=[
            OpenApiParameter('id', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('name', OpenApiTypes.STR, description='Workspace name'),
            OpenApiParameter('owner', OpenApiTypes.UUID, description='Owner ID'),
            OpenApiParameter('created_at', OpenApiTypes.DATETIME, description='Creation date')
        ]
    ),
    retrieve=extend_schema(
        summary='Get workspace details',
        description='Get detailed information about a specific workspace.',
        parameters=[
            OpenApiParameter('id', OpenApiTypes.UUID, description='Workspace ID')
        ]
    ),
    create=extend_schema(
        summary='Create workspace',
        description='Create a new workspace.',
        request=WorkspaceSerializer
    ),
    update=extend_schema(
        summary='Update workspace',
        description='Update all fields of a specific workspace.',
        parameters=[
            OpenApiParameter('id', OpenApiTypes.UUID, description='Workspace ID')
        ],
        request=WorkspaceSerializer
    ),
    partial_update=extend_schema(
        summary='Partial update workspace',
        description='Update one or more fields of a specific workspace.',
        parameters=[
            OpenApiParameter('id', OpenApiTypes.UUID, description='Workspace ID')
        ],
        request=WorkspaceSerializer
    ),
    destroy=extend_schema(
        summary='Delete workspace',
        description='Delete a specific workspace. This is a soft delete.',
        parameters=[
            OpenApiParameter('id', OpenApiTypes.UUID, description='Workspace ID')
        ]
    )
)
class WorkspaceViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r'[0-9a-f-]+'
    """ViewSet for managing workspaces.
    
    Provides CRUD operations for workspaces and additional actions for workspace lifecycle management.
    Workspaces are the main organizational unit in Dataelan, containing prompt sessions and tasks.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'workspace_type', 'is_system_workspace']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at', 'status', 'workspace_type']
    ordering = ['-created_at']

    @extend_schema(
        parameters=[
            OpenApiParameter(name='name', description='Workspace name', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='description', description='Workspace description', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='created_at', description='Workspace creation date', required=False, type=OpenApiTypes.DATETIME),
            OpenApiParameter(name='updated_at', description='Workspace update date', required=False, type=OpenApiTypes.DATETIME),
            OpenApiParameter(name='status', description='Workspace status', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='workspace_type', description='Workspace type (ORGANIZATION, TEAM, PROJECT, PERSONAL)', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='is_system_workspace', description='Is system workspace', required=False, type=OpenApiTypes.BOOL),
        ]
    )
    def get_queryset(self) -> QuerySet[Workspace]:
        """Filter workspaces based on user's organization membership.
        
        Returns workspaces where the user is either the owner or a collaborator.
        For retrieve action, includes additional analytics data.
        
        Returns:
            QuerySet[Workspace]: Filtered workspaces with analytics data for retrieve action
        """
        user = self.request.user
        base_qs = Workspace.objects.filter(
            (Q(owner=user) | Q(collaborators=user)) &
            Q(organization=user.default_org)
        ).distinct()

        if self.action == 'retrieve':
            # Add analytics for workspace detail view
            return base_qs.annotate(
                prompt_sessions_count=Count('prompt_sessions'),
                active_sessions_count=Count(
                    'prompt_sessions',
                    filter=Q(prompt_sessions__status='ACTIVE')
                ),
                total_cost=Subquery(
                    ModelMetrics.objects.filter(
                        session__workspace=OuterRef('pk')
                    ).values('session__workspace').annotate(
                        total=Sum('cost')
                    ).values('total')
                )
            )
        return base_qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkspaceDetailSerializer
        return WorkspaceSerializer

    def perform_create(self, serializer):
        # Set owner to current user
        serializer.save(owner=self.request.user)

    @extend_schema(
        summary='Archive workspace',
        description='Archive a workspace, making it read-only.',
        responses={200: WorkspaceSerializer}
    )
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a workspace.
        
        Sets the workspace status to ARCHIVED. Archived workspaces are read-only
        and won't accept new prompt sessions or tasks.
        
        Returns:
            Response: Updated workspace data
        
        Raises:
            PermissionDenied: If user doesn't have permission to archive the workspace
        """
        workspace = self.get_object()
        workspace.status = workspace.Status.ARCHIVED
        workspace.save()
        return Response(self.get_serializer(workspace).data)

    @extend_schema(
        summary='Complete workspace',
        description='Mark a workspace as completed.',
        responses={200: WorkspaceSerializer}
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a workspace as completed.
        
        Sets the workspace status to COMPLETED. Completed workspaces are read-only
        and represent finished work.
        
        Returns:
            Response: Updated workspace data
        
        Raises:
            PermissionDenied: If user doesn't have permission to complete the workspace
        """
        workspace = self.get_object()
        workspace.status = workspace.Status.COMPLETED
        workspace.save()
        return Response(self.get_serializer(workspace).data)

    @extend_schema(
        summary='Reactivate workspace',
        description='Reactivate an archived or completed workspace.',
        responses={200: WorkspaceSerializer}
    )
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Reactivate an archived or completed workspace.
        
        Sets the workspace status back to ACTIVE, allowing new prompt sessions
        and tasks to be created.
        
        Returns:
            Response: Updated workspace data
        
        Raises:
            PermissionDenied: If user doesn't have permission to reactivate the workspace
        """
        workspace = self.get_object()
        workspace.status = workspace.Status.ACTIVE
        workspace.save()
        return Response(self.get_serializer(workspace).data)


@extend_schema_view(
    list=extend_schema(
        summary='List collaborators',
        description='Get a list of all collaborators for a workspace.',
        parameters=[
            OpenApiParameter('id', OpenApiTypes.UUID, description='Collaborator ID'),
            OpenApiParameter('workspace_id', OpenApiTypes.UUID, description='workspace ID'),
            OpenApiParameter('user_id', OpenApiTypes.UUID, description='User ID'),
            OpenApiParameter('role', OpenApiTypes.STR, description='Role'),
            OpenApiParameter('created_at', OpenApiTypes.DATETIME, description='Creation date')
        ]
    ),
    retrieve=extend_schema(
        summary='Get collaborator details',
        description='Get detailed information about a specific collaborator.',
        parameters=[
            OpenApiParameter('workspace_id', OpenApiTypes.UUID, description='workspace ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Collaborator ID')
        ]
    ),
    create=extend_schema(
        summary='Add collaborator',
        description='Add a new collaborator to the workspace.',
        parameters=[
            OpenApiParameter('workspace_id', OpenApiTypes.UUID, description='workspace ID')
        ]
    ),
    update=extend_schema(
        summary='Update collaborator',
        description='Update collaborator role or permissions.',
        parameters=[
            OpenApiParameter('workspace_id', OpenApiTypes.UUID, description='workspace ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Collaborator ID')
        ]
    ),
    partial_update=extend_schema(
        summary='Partial update collaborator',
        description='Update specific fields of a collaborator.',
        parameters=[
            OpenApiParameter('workspace_id', OpenApiTypes.UUID, description='workspace ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Collaborator ID')
        ]
    ),
    destroy=extend_schema(
        summary='Remove collaborator',
        description='Remove a collaborator from the workspace.',
        parameters=[
            OpenApiParameter('workspace_id', OpenApiTypes.UUID, description='workspace ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Collaborator ID')
        ]
    )
)
class WorkspaceCollaboratorViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r'[0-9a-f-]+'
    """ViewSet for managing workspace collaborators.
    
    Provides CRUD operations for workspace collaborators. Collaborators are users
    who have access to a workspace with specific roles (VIEWER, EDITOR, ADMIN).
    Only workspace owners and admins can manage collaborators.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceCollaboratorSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'role']
    ordering = ['-created_at']

    def get_queryset(self) -> QuerySet[WorkspaceCollaborator]:
        """Filter collaborators for a specific workspace.
        
        Returns:
            QuerySet[WorkspaceCollaborator]: Filtered collaborators for the workspace
        """
        workspace_id = self.kwargs.get('workspace_pk')
        return WorkspaceCollaborator.objects.filter(workspace_id=workspace_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        workspace_id = self.kwargs.get('workspace_pk')
        if workspace_id:
            context['workspace'] = get_object_or_404(Workspace, id=workspace_id)
        return context

    def perform_create(self, serializer):
        workspace = self.get_serializer_context()['workspace']
        
        # Get the user's role in the workspace
        user_collab = workspace.workspace_collaborators.filter(user=self.request.user).first()
        is_owner = workspace.owner == self.request.user
        
        # Only owners and admins can add collaborators
        if not (is_owner or (user_collab and user_collab.is_admin())):
            raise serializers.ValidationError(
                {"detail": _('You do not have permission to add collaborators.')}
            )
        
        # Get the role being assigned
        new_role = serializer.validated_data.get('role')
        
        # Owners can assign any role
        if not is_owner:
            # Get the role hierarchy
            role_hierarchy = {
                WorkspaceCollaborator.Role.VIEWER: 0,
                WorkspaceCollaborator.Role.EDITOR: 1,
                WorkspaceCollaborator.Role.ADMIN: 2
            }
            
            # Check if trying to assign a higher role
            if role_hierarchy.get(new_role, 0) > role_hierarchy.get(user_collab.role, 0):
                raise serializers.ValidationError(
                    {"detail": _('You cannot assign a role higher than your own.')}
                )
        
        try:
            serializer.save()
        except IntegrityError:
            raise serializers.ValidationError(
                {"detail": _('This user is already a collaborator on this workspace.')}
            )
