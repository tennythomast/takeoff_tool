from django.db.models import Q, QuerySet
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
from .models import Project, ProjectCollaborator
from .serializers import (
    ProjectSerializer, ProjectDetailSerializer, ProjectCollaboratorSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary='List projects',
        description='Get a list of all projects the user has access to.',
        tags=['projects']
    ),
    retrieve=extend_schema(
        summary='Get project details',
        description='Get detailed information about a specific project.',
        tags=['projects']
    ),
    create=extend_schema(
        summary='Create project',
        description='Create a new project.',
        tags=['projects']
    ),
    update=extend_schema(
        summary='Update project',
        description='Update all fields of a specific project.',
        tags=['projects']
    ),
    partial_update=extend_schema(
        summary='Partial update project',
        description='Update one or more fields of a specific project.',
        tags=['projects']
    ),
    destroy=extend_schema(
        summary='Delete project',
        description='Delete a specific project. This is a soft delete.',
        tags=['projects']
    )
)
class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for managing projects.
    
    Provides CRUD operations for projects and additional actions for project lifecycle management.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'project_type', 'client_name']
    search_fields = ['title', 'description', 'client_name', 'client_company']
    ordering_fields = ['title', 'created_at', 'updated_at', 'status', 'deadline']
    ordering = ['-created_at']

    def get_queryset(self) -> QuerySet[Project]:
        """Filter projects based on user's organization membership.
        
        Returns projects where the user is either the owner or a collaborator.
        """
        user = self.request.user
        return Project.objects.filter(
            (Q(owner=user) | Q(collaborators=user)) &
            Q(organization=user.default_org)
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectSerializer

    def perform_create(self, serializer):
        # Set owner to current user
        serializer.save(owner=self.request.user)

    @extend_schema(
        summary='Archive project',
        description='Archive a project, making it read-only.',
        responses={200: ProjectSerializer},
        tags=['projects']
    )
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a project."""
        project = self.get_object()
        project.status = Project.Status.ARCHIVED
        project.save()
        return Response(self.get_serializer(project).data)

    @extend_schema(
        summary='Complete project',
        description='Mark a project as completed.',
        responses={200: ProjectSerializer},
        tags=['projects']
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a project as completed."""
        project = self.get_object()
        project.status = Project.Status.COMPLETED
        project.save()
        return Response(self.get_serializer(project).data)

    @extend_schema(
        summary='Reactivate project',
        description='Reactivate an archived or completed project.',
        responses={200: ProjectSerializer},
        tags=['projects']
    )
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Reactivate an archived or completed project."""
        project = self.get_object()
        project.status = Project.Status.ACTIVE
        project.save()
        return Response(self.get_serializer(project).data)


@extend_schema_view(
    list=extend_schema(
        summary='List collaborators',
        description='Get a list of all collaborators for a project.',
        tags=['projects']
    ),
    retrieve=extend_schema(
        summary='Get collaborator details',
        description='Get detailed information about a specific collaborator.',
        tags=['projects']
    ),
    create=extend_schema(
        summary='Add collaborator',
        description='Add a new collaborator to the project.',
        tags=['projects']
    ),
    update=extend_schema(
        summary='Update collaborator',
        description='Update collaborator role or permissions.',
        tags=['projects']
    ),
    partial_update=extend_schema(
        summary='Partial update collaborator',
        description='Update specific fields of a collaborator.',
        tags=['projects']
    ),
    destroy=extend_schema(
        summary='Remove collaborator',
        description='Remove a collaborator from the project.',
        tags=['projects']
    )
)
class ProjectCollaboratorViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project collaborators."""
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectCollaboratorSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'role']
    ordering = ['-created_at']

    def get_queryset(self) -> QuerySet[ProjectCollaborator]:
        """Filter collaborators for a specific project."""
        project_id = self.kwargs.get('project_pk')
        return ProjectCollaborator.objects.filter(project_id=project_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        project_id = self.kwargs.get('project_pk')
        if project_id:
            context['project'] = get_object_or_404(Project, id=project_id)
        return context

    def perform_create(self, serializer):
        project = self.get_serializer_context()['project']
        
        # Get the user's role in the project
        user_collab = project.project_collaborators.filter(user=self.request.user).first()
        is_owner = project.owner == self.request.user
        
        # Only owners and admins can add collaborators
        if not (is_owner or (user_collab and user_collab.is_admin())):
            raise serializers.ValidationError(
                {"detail": _('You do not have permission to add collaborators.')}
            )
        
        try:
            serializer.save()
        except IntegrityError:
            raise serializers.ValidationError(
                {"detail": _('This user is already a collaborator on this project.')}
            )
