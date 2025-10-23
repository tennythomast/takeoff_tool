import logging
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, QuerySet, Count, Sum, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes
from .models import PromptSession, Prompt
from .serializers import (
    PromptSessionSerializer, PromptSerializer, ModelMetricsSerializer, 
    ExecutePromptRequestSerializer, SessionSummarySerializer,
    ContextMetricsSerializer
)
from modelhub.models import ModelMetrics
from workspaces.models import Workspace

# Configure logger
logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary='List prompt sessions',
        description='Get a list of all prompt sessions the user has access to with cost metrics.',
        parameters=[
            OpenApiParameter('workspace_id', OpenApiTypes.UUID, description='Filter by workspace ID'),
            OpenApiParameter('model_type', OpenApiTypes.STR, description='Filter by model type (TEXT, CODE, IMAGE, etc.)'),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status (DRAFT, ACTIVE, etc.)'),
            OpenApiParameter('search', OpenApiTypes.STR, description='Search in title and description'),
            OpenApiParameter('ordering', OpenApiTypes.STR, description='Order by field (created_at, total_cost, etc.)')
        ]
    ),
    create=extend_schema(
        summary='Create prompt session',
        description='Create a new prompt session for AI interaction with unified context management.',
        request=PromptSessionSerializer,
        responses={201: PromptSessionSerializer}
    ),
    retrieve=extend_schema(
        summary='Get session details',
        description='Get detailed information about a specific prompt session including cost breakdown.',
        parameters=[OpenApiParameter('id', OpenApiTypes.UUID, description='Session ID')],
        responses={200: PromptSessionSerializer}
    ),
    update=extend_schema(
        summary='Update session',
        description='Update all fields of a specific prompt session.',
        parameters=[OpenApiParameter('id', OpenApiTypes.UUID, description='Session ID')],
        request=PromptSessionSerializer,
        responses={200: PromptSessionSerializer}
    ),
    partial_update=extend_schema(
        summary='Partial update session',
        description='Update one or more fields of a specific prompt session.',
        parameters=[OpenApiParameter('id', OpenApiTypes.UUID, description='Session ID')],
        request=PromptSessionSerializer,
        responses={200: PromptSessionSerializer}
    ),
    destroy=extend_schema(
        summary='Delete session',
        description='Delete a specific prompt session. This is a soft delete.',
        parameters=[OpenApiParameter('id', OpenApiTypes.UUID, description='Session ID')],
        responses={204: None}
    )
)
class PromptSessionViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r'[0-9a-f-]+'
    """ViewSet for managing prompt sessions with unified context integration."""
    permission_classes = [IsAuthenticated]
    serializer_class = PromptSessionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'total_cost', 'status']
    ordering = ['-created_at']

    def get_queryset(self) -> QuerySet[PromptSession]:
        """Filter prompt sessions based on user access."""
        workspace_pk = self.kwargs.get('workspace_pk')

        # Get all workspaces the user has access to
        base_qs = PromptSession.objects.select_related('workspace').filter(
            workspace__organization=self.request.user.default_org,
            workspace__is_active=True,
            is_active=True
        ).filter(
            Q(workspace__owner=self.request.user) |
            Q(workspace__collaborators=self.request.user)
        )
        
        # If we have a workspace_pk, filter by it
        if workspace_pk:
            base_qs = base_qs.filter(workspace_id=workspace_pk)

        # Get distinct session IDs first to handle many-to-many properly
        distinct_ids = base_qs.values('id').distinct()
        qs = PromptSession.objects.filter(id__in=distinct_ids.values('id')).select_related(
            'workspace',
            'workspace__owner',
            'workspace__organization'
        ).prefetch_related(
            'prompts',
            'workspace__collaborators'
        )
        
        return qs

    def perform_create(self, serializer: PromptSessionSerializer) -> None:
        """Set the workspace and creator when creating a new session."""
        workspace_pk = self.kwargs.get('workspace_pk')
        workspace = get_object_or_404(
            Workspace,
            (Q(owner=self.request.user) |
             Q(collaborators=self.request.user)) &
            Q(organization=self.request.user.default_org),
            id=workspace_pk,
            is_active=True
        )
        
        serializer.save(
            workspace=workspace,
            creator=self.request.user
        )

    @extend_schema(
        summary='Get session context metrics',
        description='Get detailed context management metrics for a session.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Session ID')
        ],
        responses={200: ContextMetricsSerializer}
    )
    @action(detail=True, methods=['get'])
    def context_metrics(self, request: Request, workspace_pk: str = None, pk: str = None) -> Response:
        """Get context management metrics for a session."""
        try:
            session = self.get_object()
            context_metrics = session.get_context_metrics()
            
            # Add strategy usage breakdown
            if session.context_session_id:
                from context_manager.models import ContextEntry
                entries = ContextEntry.objects.filter(session_id=session.context_session_id)
                
                strategy_usage = {}
                for entry in entries:
                    strategy = entry.context_strategy or 'unknown'
                    strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
                
                context_metrics['strategy_usage'] = strategy_usage
            else:
                context_metrics['strategy_usage'] = {}
            
            return Response(context_metrics)
            
        except Exception as e:
            logger.error(f"Error getting context metrics for session {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to get context metrics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary='Get all messages for a specific session',
        description='Get the complete conversation history for a prompt session.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Session ID')
        ],
        responses={200: inline_serializer(
            name='SessionMessagesResponseSerializer',
            fields={
                'session_id': serializers.UUIDField(),
                'context_session_id': serializers.UUIDField(),
                'messages': serializers.ListField(child=serializers.DictField())
            }
        )}
    )
    @action(detail=True, methods=['get'])
    def messages(self, request, workspace_pk=None, pk=None):
        """
        Get all messages for a specific prompt session.
        
        Retrieves the complete conversation history for a prompt session
        by accessing the associated context entries.
        """
        session = self.get_object()
        
        try:
            # Check if the session has a context_session_id
            if not session.context_session_id:
                return Response(
                    {"detail": "No messages found for this session."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get conversation context from the unified system
            from context_manager.models import ContextEntry
            entries = ContextEntry.objects.filter(
                session_id=session.context_session_id
            ).order_by('created_at')
            
            # Format messages for the response
            messages = []
            for entry in entries:
                message = {
                    'id': str(entry.id),
                    'role': entry.role,
                    'content': entry.content,
                    'content_type': entry.content_type,
                    'timestamp': entry.created_at.isoformat(),
                    'model_used': entry.model_used,
                    'execution_metadata': entry.execution_metadata
                }
                messages.append(message)
            
            return Response({
                'session_id': str(session.id),
                'context_session_id': str(session.context_session_id),
                'messages': messages
            })
            
        except Exception as e:
            logger.error(f"Error retrieving messages for session {pk}: {e}")
            return Response(
                {"detail": f"Error retrieving messages: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @extend_schema(
        summary='Get session messages',
        description='Get all messages for a specific prompt session.',
        parameters=[OpenApiParameter('id', OpenApiTypes.UUID, description='Session ID')],
        responses={
            200: inline_serializer(
                name='SessionMessagesResponse',
                fields={
                    'session_id': serializers.UUIDField(),
                    'context_session_id': serializers.UUIDField(),
                    'messages': serializers.ListField(
                        child=inline_serializer(
                            name='ChatMessage',
                            fields={
                                'id': serializers.UUIDField(),
                                'role': serializers.CharField(),
                                'content': serializers.CharField(),
                                'content_type': serializers.CharField(required=False),
                                'timestamp': serializers.DateTimeField(),
                                'model_used': serializers.CharField(required=False),
                                'execution_metadata': serializers.JSONField(required=False),
                            }
                        )
                    )
                }
            )
        }
    )
    @action(detail=True, methods=['get'])
    def messages(self, request, workspace_pk=None, pk=None):
        """Get all messages for a specific prompt session."""
        session = self.get_object()
        
        # Check if context_session_id exists
        if not session.context_session_id:
            return Response(
                {"error": "No context session found for this prompt session."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Import here to avoid circular imports
        from context_manager.models import ContextEntry
        
        # Get all context entries for this session
        entries = ContextEntry.objects.filter(
            session_id=session.context_session_id
        ).order_by('created_at')
        
        # Format messages for the response
        messages = []
        for entry in entries:
            # Skip system messages if needed
            if entry.role == 'system' and not request.query_params.get('include_system', False):
                continue
                
            message = {
                'id': entry.id,
                'role': entry.role,
                'content': entry.content,
                'content_type': entry.content_type,
                'timestamp': entry.created_at,
            }
            
            # Add model information if available
            if hasattr(entry, 'model_used') and entry.model_used:
                message['model_used'] = entry.model_used
            
            # Add execution metadata if available
            if hasattr(entry, 'execution_metadata') and entry.execution_metadata:
                message['execution_metadata'] = entry.execution_metadata
            
            messages.append(message)
        
        return Response({
            'session_id': session.id,
            'context_session_id': session.context_session_id,
            'messages': messages
        })


@extend_schema_view(
    create=extend_schema(
        summary='Create prompt',
        description='Create a new prompt in a session.',
        parameters=[OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID')],
        request=PromptSerializer,
        responses={201: PromptSerializer}
    ),
    retrieve=extend_schema(
        summary='Get prompt details',
        description='Get detailed information about a specific prompt including execution metadata.',
        parameters=[
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Prompt ID')
        ],
        responses={200: PromptSerializer}
    ),
    update=extend_schema(
        summary='Update prompt',
        description='Update all fields of a specific prompt.',
        parameters=[
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Prompt ID')
        ],
        request=PromptSerializer,
        responses={200: PromptSerializer}
    ),
    partial_update=extend_schema(
        summary='Partial update prompt',
        description='Update one or more fields of a specific prompt.',
        parameters=[
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Prompt ID')
        ],
        request=PromptSerializer,
        responses={200: PromptSerializer}
    ),
    destroy=extend_schema(
        summary='Delete prompt',
        description='Delete a specific prompt.',
        parameters=[
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Prompt ID')
        ],
        responses={204: None}
    )
)
class PromptViewSet(viewsets.ModelViewSet):
    lookup_value_regex = r'[0-9a-f-]+'
    """ViewSet for managing prompts within a session with unified context integration."""
    serializer_class = PromptSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['input_text']
    ordering_fields = ['created_at', 'importance_score']
    ordering = ['-created_at']

    def get_queryset(self) -> QuerySet[Prompt]:
        """Filter prompts based on user access."""
        workspace_pk = self.kwargs.get('workspace_pk')
        session_pk = self.kwargs.get('session_pk')

        # Get all prompts the user has access to
        base_qs = Prompt.objects.select_related('session__workspace').filter(
            session__workspace__organization=self.request.user.default_org,
            session__workspace__is_active=True,
            session__is_active=True,
            is_active=True
        ).filter(
            Q(session__workspace__owner=self.request.user) |
            Q(session__workspace__collaborators=self.request.user)
        )
        
        # If we have a workspace_pk or session_pk, filter by them
        if workspace_pk:
            base_qs = base_qs.filter(session__workspace_id=workspace_pk)
        if session_pk:
            base_qs = base_qs.filter(session_id=session_pk)

        # Get distinct prompt IDs first to handle many-to-many properly
        distinct_ids = base_qs.values('id').distinct()
        qs = Prompt.objects.filter(id__in=distinct_ids.values('id')).select_related(
            'session',
            'session__workspace',
            'session__workspace__owner',
            'session__workspace__organization'
        ).prefetch_related(
            'session__workspace__collaborators'
        )
        
        return qs

    def perform_create(self, serializer: PromptSerializer) -> None:
        """Set the session and user when creating a new prompt."""
        workspace_pk = self.kwargs.get('workspace_pk')
        session_pk = self.kwargs.get('session_pk')
        session = get_object_or_404(
            PromptSession.objects.select_related('workspace'),
            (Q(workspace__owner=self.request.user) |
             Q(workspace__collaborators=self.request.user)) &
            Q(workspace__organization=self.request.user.default_org),
            workspace_id=workspace_pk,
            id=session_pk,
            workspace__is_active=True,
            is_active=True
        )
        serializer.save(session=session, user=self.request.user)

    @extend_schema(
        summary='Execute prompt with optimization',
        description='Execute a prompt using unified context management and cost optimization.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Prompt ID')
        ],
        request=ExecutePromptRequestSerializer,
        responses={
            200: inline_serializer(
                name='ExecutePromptResponseSerializer',
                fields={
                    'success': serializers.BooleanField(),
                    'response': serializers.DictField(),
                    'metrics': ModelMetricsSerializer(),
                    'metadata': serializers.DictField(),
                    'context_info': serializers.DictField()
                }
            ),
            400: {'description': 'Invalid request parameters'},
            404: {'description': 'Prompt not found'},
            500: {'description': 'Model execution failed'}
        }
    )
    @action(detail=True, methods=['post'])
    async def execute(self, request: Request, workspace_pk: str = None, session_pk: str = None, pk: str = None) -> Response:
        """Execute a prompt using unified context management and cost optimization."""
        try:
            prompt = self.get_object()
            serializer = ExecutePromptRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Get parameters
            optimization_strategy = serializer.validated_data.get('optimization_strategy', 'balanced')
            max_tokens = serializer.validated_data.get('max_tokens', 512)
            temperature = serializer.validated_data.get('temperature', 0.7)
            
            logger.info(f" Executing prompt {pk} with strategy: {optimization_strategy}")
            
            # Execute prompt with optimization
            try:
                response, metadata = await prompt.execute_with_optimization(optimization_strategy)
                
                # Get the latest metrics linked to this session
                latest_metrics = ModelMetrics.objects.filter(
                    session_id=prompt.session.id,
                    session_type='prompt_session'
                ).order_by('-created_at').first()
                
                # Prepare response data
                response_data = {
                    'success': True,
                    'response': {
                        'content': response.content if hasattr(response, 'content') else str(response),
                        'cost': float(response.cost) if hasattr(response, 'cost') else 0.0,
                        'tokens_input': response.tokens_input if hasattr(response, 'tokens_input') else 0,
                        'tokens_output': response.tokens_output if hasattr(response, 'tokens_output') else 0,
                        'latency_ms': getattr(response, 'latency_ms', 0)
                    },
                    'metadata': metadata,
                    'context_info': metadata.get('context', {}),
                    'metrics': ModelMetricsSerializer(latest_metrics).data if latest_metrics else None
                }
                
                logger.info(f" Prompt {pk} executed successfully")
                return Response(response_data, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f" Error executing prompt {pk}: {str(e)}")
                
                # Update session status on failure
                if prompt.session.status in [PromptSession.Status.DRAFT, PromptSession.Status.ACTIVE]:
                    prompt.session.status = PromptSession.Status.FAILED
                    await prompt.session.asave()
                    
                return Response(
                    {
                        'success': False,
                        'error': 'Model execution failed',
                        'details': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error in execute view for prompt {pk}: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Request processing failed',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary='Get prompt conversation context',
        description='Get the conversation context entries for this prompt.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Prompt ID')
        ],
        responses={200: serializers.ListField(child=serializers.DictField())}
    )
    @action(detail=True, methods=['get'])
    def conversation_context(self, request: Request, workspace_pk: str = None, session_pk: str = None, pk: str = None) -> Response:
        """Get conversation context entries for this prompt."""
        try:
            prompt = self.get_object()
            context_entries = prompt.get_conversation_context()
            
            context_data = [
                {
                    'id': str(entry.id),
                    'role': entry.role,
                    'content': entry.content,
                    'created_at': entry.created_at.isoformat(),
                    'importance_score': entry.importance_score,
                    'context_preparation_cost': float(entry.context_preparation_cost or 0),
                    'context_strategy': entry.context_strategy,
                    'context_tokens_used': entry.context_tokens_used,
                    'model_used': entry.model_used,
                    'total_cost': float(entry.total_cost or 0)
                }
                for entry in context_entries
            ]
            
            return Response({
                'prompt_id': str(prompt.id),
                'session_id': str(prompt.session.id),
                'context_entries': context_data,
                'total_entries': len(context_data)
            })
            
        except Exception as e:
            logger.error(f"Error getting conversation context for prompt {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to get conversation context'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    list=extend_schema(
        summary='List model metrics',
        description='Get a list of model metrics for a specific session with cost breakdown.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID')
        ],
        responses={200: ModelMetricsSerializer}
    ),
    retrieve=extend_schema(
        summary='Get model metrics details',
        description='Get detailed information about specific model metrics.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID'),
            OpenApiParameter('id', OpenApiTypes.UUID, description='Metrics ID')
        ],
        responses={200: ModelMetricsSerializer}
    )
)
class ModelMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_value_regex = r'[0-9a-f-]+'
    """ViewSet for viewing model metrics associated with prompt sessions."""
    serializer_class = ModelMetricsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['model__name', 'model__provider__name', 'prompt_text']
    ordering_fields = ['created_at', 'model_execution_cost', 'latency_ms']
    ordering = ['-created_at']

    def get_queryset(self) -> QuerySet[ModelMetrics]:
        """Filter metrics based on user access."""
        try:
            workspace_pk = self.kwargs.get('workspace_pk')
            session_pk = self.kwargs.get('session_pk')
            
            if not self.request.user.default_org:
                return ModelMetrics.objects.none()
            
            # Get all metrics the user has access to via session relationships
            base_qs = ModelMetrics.objects.select_related(
                'model', 'model__provider', 'organization'
            ).filter(
                organization=self.request.user.default_org,
                session_type='prompt_session'
            )
            
            # Filter by session if we have session_pk
            if session_pk:
                # Verify user has access to this session
                session = get_object_or_404(
                    PromptSession.objects.select_related('workspace'),
                    (Q(workspace__owner=self.request.user) |
                     Q(workspace__collaborators=self.request.user)) &
                    Q(workspace__organization=self.request.user.default_org),
                    workspace_id=workspace_pk,
                    id=session_pk,
                    workspace__is_active=True,
                    is_active=True
                )
                base_qs = base_qs.filter(session_id=session_pk)
            
            # Filter by workspace if we have workspace_pk but no session_pk
            elif workspace_pk:
                # Get all sessions in this workspace user has access to
                accessible_sessions = PromptSession.objects.filter(
                    (Q(workspace__owner=self.request.user) |
                     Q(workspace__collaborators=self.request.user)) &
                    Q(workspace__organization=self.request.user.default_org),
                    workspace_id=workspace_pk,
                    workspace__is_active=True,
                    is_active=True
                ).values_list('id', flat=True)
                
                base_qs = base_qs.filter(session_id__in=accessible_sessions)
            
            return base_qs.distinct()
            
        except Exception as e:
            logger.error(f"Error in ModelMetricsViewSet.get_queryset: {str(e)}")
            return ModelMetrics.objects.none()
    
    @extend_schema(
        summary='Get metrics summary',
        description='Get a comprehensive summary of metrics for a specific session.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID')
        ],
        responses={200: SessionSummarySerializer}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request, workspace_pk=None, session_pk=None):
        """Get a comprehensive summary of metrics for a session."""
        try:
            if not session_pk:
                return Response(
                    {'error': 'Session ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get the session
            session = get_object_or_404(
                PromptSession.objects.select_related('workspace'),
                (Q(workspace__owner=self.request.user) |
                Q(workspace__collaborators=self.request.user)) &
                Q(workspace__organization=self.request.user.default_org),
                workspace_id=workspace_pk,
                id=session_pk
            )
            
            # Get metrics for this session
            metrics = ModelMetrics.objects.filter(
                session_id=session.id,
                session_type='prompt_session'
            )
            
            # Calculate summary statistics
            model_execution_cost = metrics.aggregate(Sum('model_execution_cost'))['model_execution_cost__sum'] or 0
            total_tokens_input = metrics.aggregate(Sum('tokens_input'))['tokens_input__sum'] or 0
            total_tokens_output = metrics.aggregate(Sum('tokens_output'))['tokens_output__sum'] or 0
            avg_latency = metrics.aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
            execution_count = metrics.count()
            
            # Calculate success rate
            success_count = metrics.filter(status='SUCCESS').count()
            success_rate = (success_count / execution_count * 100) if execution_count > 0 else 0
            
            # Get model breakdown
            model_breakdown = metrics.values(
                'model__name', 'model__provider__name'
            ).annotate(
                count=Count('id'),
                total_cost=Sum('model_execution_cost'),
                avg_latency=Avg('latency_ms'),
                success_count=Count('id', filter=Q(status='SUCCESS'))
            ).order_by('-count')
            
            # Add success rate to each model
            for model in model_breakdown:
                model['success_rate'] = (model['success_count'] / model['count'] * 100) if model['count'] > 0 else 0
            
            # Get context metrics
            context_metrics = session.get_context_metrics()
            
            return Response({
                'session_id': str(session.id),
                'session_title': session.title,
                'total_cost': float(session.total_cost),
                'model_execution_cost': float(model_execution_cost),
                'context_preparation_cost': float(session.context_preparation_cost),
                'total_tokens_input': total_tokens_input,
                'total_tokens_output': total_tokens_output,
                'avg_latency_ms': round(avg_latency, 2),
                'execution_count': execution_count,
                'conversation_length': session.get_conversation_length(),
                'success_rate': round(success_rate, 2),
                'model_breakdown': list(model_breakdown),
                'context_metrics': context_metrics
            })
            
        except Exception as e:
            logger.error(f"Error in metrics summary: {str(e)}")
            return Response(
                {'error': 'Failed to generate metrics summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary='Get optimization metrics',
        description='Get detailed optimization metrics for a specific session.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID')
        ],
        responses={200: inline_serializer(
            name='OptimizationMetricsResponseSerializer',
            fields={
                'session_id': serializers.UUIDField(),
                'cost_savings': serializers.FloatField(),
                'performance_impact': serializers.FloatField(),
                'optimization_strategies': serializers.DictField(),
                'recommended_strategy': serializers.CharField(),
                'total_optimized_requests': serializers.IntegerField(),
                'context_efficiency': serializers.DictField(),
                'cost_breakdown': serializers.DictField()
            }
        )}
    )
    @action(detail=False, methods=['get'])
    def optimization(self, request, workspace_pk=None, session_pk=None):
        """Get optimization metrics for a session."""
        try:
            if not session_pk:
                return Response(
                    {'error': 'Session ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get the session
            session = get_object_or_404(
                PromptSession.objects.select_related('workspace'),
                (Q(workspace__owner=self.request.user) |
                Q(workspace__collaborators=self.request.user)) &
                Q(workspace__organization=self.request.user.default_org),
                workspace_id=workspace_pk,
                id=session_pk
            )
            
            # Get metrics with optimization metadata
            metrics = ModelMetrics.objects.filter(
                session_id=session.id,
                session_type='prompt_session'
            )
            metrics_with_optimization = metrics.exclude(optimization_metadata__isnull=True)
            
            if not metrics_with_optimization.exists():
                return Response({
                    'session_id': str(session.id),
                    'cost_savings': 0.0,
                    'performance_impact': 0.0,
                    'optimization_strategies': {},
                    'recommended_strategy': 'balanced',
                    'total_optimized_requests': 0,
                    'context_efficiency': session.get_context_metrics(),
                    'cost_breakdown': session.cost_breakdown
                })
            
            # Get strategies used from optimization metadata
            strategies_used = []
            for metric in metrics_with_optimization:
                if (metric.optimization_metadata and 
                    'optimization_strategy' in metric.optimization_metadata):
                    strategies_used.append(metric.optimization_metadata['optimization_strategy'])
            
            strategies_used = list(set(filter(None, strategies_used)))
            
            strategy_metrics = {}
            for strategy in strategies_used:
                if not strategy:
                    continue
                    
                strategy_data = metrics_with_optimization.filter(
                    optimization_metadata__optimization_strategy=strategy
                )
                
                if strategy_data.exists():
                    strategy_metrics[strategy] = {
                        'count': strategy_data.count(),
                        'avg_cost': float(strategy_data.aggregate(
                            Avg('model_execution_cost'))['model_execution_cost__avg'] or 0),
                        'total_cost': float(strategy_data.aggregate(
                            Sum('model_execution_cost'))['model_execution_cost__sum'] or 0),
                        'avg_latency': float(strategy_data.aggregate(
                            Avg('latency_ms'))['latency_ms__avg'] or 0)
                    }
            
            # Determine recommended strategy based on cost efficiency
            recommended_strategy = 'balanced'  # Default
            if strategy_metrics:
                # Find strategy with lowest average cost
                recommended_strategy = min(
                    strategy_metrics.items(),
                    key=lambda x: x[1]['avg_cost']
                )[0]
            
            # Estimate cost savings
            baseline_cost = metrics.aggregate(Avg('model_execution_cost'))['model_execution_cost__avg'] or 0
            optimized_cost = metrics_with_optimization.aggregate(
                Avg('model_execution_cost'))['model_execution_cost__avg'] or 0
            cost_savings = max(0, (baseline_cost - optimized_cost) / baseline_cost * 100) if baseline_cost > 0 else 0
            
            # Estimate performance impact
            baseline_latency = metrics.aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0
            optimized_latency = metrics_with_optimization.aggregate(
                Avg('latency_ms'))['latency_ms__avg'] or 0
            performance_impact = ((optimized_latency - baseline_latency) / baseline_latency * 100) if baseline_latency > 0 else 0
            
            return Response({
                'session_id': str(session.id),
                'cost_savings': round(cost_savings, 2),
                'performance_impact': round(performance_impact, 2),
                'optimization_strategies': strategy_metrics,
                'recommended_strategy': recommended_strategy,
                'total_optimized_requests': metrics_with_optimization.count(),
                'context_efficiency': session.get_context_metrics(),
                'cost_breakdown': session.cost_breakdown
            })
            
        except Exception as e:
            logger.error(f"Error in optimization metrics: {str(e)}")
            return Response(
                {'error': 'Failed to generate optimization metrics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary='Get cost analysis',
        description='Get detailed cost analysis comparing model execution vs context preparation costs.',
        parameters=[
            OpenApiParameter('workspace_pk', OpenApiTypes.UUID, description='Workspace ID'),
            OpenApiParameter('session_pk', OpenApiTypes.UUID, description='Session ID')
        ],
        responses={200: inline_serializer(
            name='CostAnalysisResponseSerializer',
            fields={
                'session_id': serializers.UUIDField(),
                'total_cost': serializers.FloatField(),
                'model_execution_cost': serializers.FloatField(),
                'context_preparation_cost': serializers.FloatField(),
                'cost_breakdown_percentage': serializers.DictField(),
                'cost_trends': serializers.ListField(),
                'cost_optimization_opportunities': serializers.ListField()
            }
        )}
    )
    @action(detail=False, methods=['get'])
    def cost_analysis(self, request, workspace_pk=None, session_pk=None):
        """Get detailed cost analysis for a session."""
        try:
            if not session_pk:
                return Response(
                    {'error': 'Session ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get the session
            session = get_object_or_404(
                PromptSession.objects.select_related('workspace'),
                (Q(workspace__owner=self.request.user) |
                Q(workspace__collaborators=self.request.user)) &
                Q(workspace__organization=self.request.user.default_org),
                workspace_id=workspace_pk,
                id=session_pk
            )
            
            # Get cost breakdown
            cost_breakdown = session.cost_breakdown
            
            # Get cost trends over time
            metrics = ModelMetrics.objects.filter(
                session_id=session.id,
                session_type='prompt_session'
            ).order_by('created_at')
            
            cost_trends = []
            running_total = 0
            for metric in metrics:
                running_total += float(metric.model_execution_cost)
                cost_trends.append({
                    'timestamp': metric.created_at.isoformat(),
                    'cumulative_cost': running_total,
                    'execution_cost': float(metric.model_execution_cost),
                    'model_used': metric.model.name if metric.model else 'unknown'
                })
            
            # Identify cost optimization opportunities
            opportunities = []
            
            # Check if context costs are high
            if cost_breakdown['context_percentage'] > 30:
                opportunities.append({
                    'type': 'context_optimization',
                    'description': 'Context preparation costs are high. Consider using more aggressive context compression.',
                    'potential_savings': f"{cost_breakdown['context_percentage']:.1f}% of total cost"
                })
            
            # Check for expensive model usage
            expensive_models = metrics.filter(
                model_execution_cost__gt=0.01  # Adjust threshold as needed
            ).values('model__name').annotate(
                total_cost=Sum('model_execution_cost'),
                count=Count('id')
            ).order_by('-total_cost')
            
            if expensive_models.exists():
                top_expensive = expensive_models.first()
                opportunities.append({
                    'type': 'model_optimization',
                    'description': f"Model '{top_expensive['model__name']}' accounts for significant costs. Consider using cost_first optimization strategy.",
                    'potential_savings': f"${top_expensive['total_cost']:.4f} from {top_expensive['count']} executions"
                })
            
            return Response({
                'session_id': str(session.id),
                'total_cost': cost_breakdown['total'],
                'model_execution_cost': cost_breakdown['model_execution'],
                'context_preparation_cost': cost_breakdown['context_preparation'],
                'cost_breakdown_percentage': {
                    'model_percentage': cost_breakdown['model_percentage'],
                    'context_percentage': cost_breakdown['context_percentage']
                },
                'cost_trends': cost_trends,
                'cost_optimization_opportunities': opportunities
            })
            
        except Exception as e:
            logger.error(f"Error in cost analysis: {str(e)}")
            return Response(
                {'error': 'Failed to generate cost analysis'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )