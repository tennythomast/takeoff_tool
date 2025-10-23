from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import Organization, Membership
from core.serializers import OrganizationSerializer, UserSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Organization objects"""
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Return the user's organization or all organizations for superusers"""
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        
        # Since users can only belong to one organization, just return that one
        user_org = user.organization
        if user_org:
            return self.queryset.filter(id=user_org.id)
        return Organization.objects.none()
    
    @action(detail=True, methods=['get'])
    def budget_info(self, request, pk=None):
        """Get detailed budget information for an organization"""
        organization = self.get_object()
        current_spend = organization.get_current_month_ai_spend()
        
        data = {
            'monthly_budget': float(organization.monthly_ai_budget) if organization.monthly_ai_budget else None,
            'current_spend': float(current_spend),
            'remaining': float(organization.monthly_ai_budget - current_spend) if organization.monthly_ai_budget else None,
            'alerts_enabled': organization.ai_usage_alerts,
            'approaching_limit': organization.is_approaching_budget(0.8),
            'optimization_strategy': organization.default_optimization_strategy,
            'api_key_strategy': organization.api_key_strategy
        }
        
        return Response(data)
    
    @action(detail=True, methods=['get'], url_path='users', url_name='organization-users')
    def users(self, request, pk=None):
        """
        Get all users in an organization with optional filtering.
        
        Optionally filter users by:
        - workspace_id: Exclude users who are already collaborators in the workspace
        - search: Search by name or email
        """
        organization = self.get_object()
        
        # Get all users in the organization
        users = User.objects.filter(
            memberships__organization=organization,
            is_active=True
        )
        
        # Filter out users who are already collaborators in the workspace if specified
        workspace_id = request.query_params.get('workspace_id')
        if workspace_id:
            from workspaces.models import WorkspaceCollaborator
            existing_collaborators = WorkspaceCollaborator.objects.filter(
                workspace_id=workspace_id
            ).values_list('user_id', flat=True)
            
            users = users.exclude(id__in=existing_collaborators)
        
        # Search by name or email if specified
        search_query = request.query_params.get('search')
        if search_query:
            users = users.filter(
                Q(first_name__icontains=search_query) | 
                Q(last_name__icontains=search_query) | 
                Q(email__icontains=search_query)
            )
        
        # Serialize and return the users
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
