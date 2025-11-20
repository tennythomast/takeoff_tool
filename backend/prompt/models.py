from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel, SoftDeletableMixin, SoftDeletableManager


class PromptSession(SoftDeletableMixin, BaseModel):
    """
    Clean AI interaction session with unified context management.
    
    This model represents chat sessions and integrates seamlessly with the
    universal context management system for cross-domain consistency.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')

    class ModelType(models.TextChoices):
        TEXT = 'TEXT', _('Text')
        CODE = 'CODE', _('Code')
        IMAGE = 'IMAGE', _('Image')
        VOICE = 'VOICE', _('Voice')
        VIDEO = 'VIDEO', _('Video')

    # Core session fields
    title = models.CharField(_('title'), max_length=255, db_index=True)
    description = models.TextField(_('description'), blank=True)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='prompt_sessions',
        verbose_name=_('project')
    )
    creator = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='created_sessions',
        verbose_name=_('creator')
    )
    model_type = models.CharField(
        max_length=20,
        choices=ModelType.choices,
        default=ModelType.TEXT,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    
    # Context integration (required)
    context_session_id = models.UUIDField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text=_('Reference to universal context session')
    )
    
    # Session lifecycle
    started_at = models.DateTimeField(_('started at'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)

    objects = SoftDeletableManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _('prompt session')
        verbose_name_plural = _('prompt sessions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['creator', 'status']),
            models.Index(fields=['model_type', 'status']),
            models.Index(fields=['is_active', 'status']),
            models.Index(fields=['context_session_id']),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'

    def get_context_session(self):
        """Get or create associated context session."""
        if self.context_session_id:
            try:
                from context_manager.models import ContextSession
                return ContextSession.objects.get(id=self.context_session_id)
            except ContextSession.DoesNotExist:
                # Context session was deleted, create new one
                pass
        
        # Try to find existing context session by entity_id/entity_type first
        from context_manager.models import ContextSession
        try:
            context_session = ContextSession.objects.get(
                entity_id=self.id,
                entity_type='prompt_session'
            )
            # Update our reference to this existing session
            self.context_session_id = context_session.id
            self.save(update_fields=['context_session_id'])
            return context_session
        except ContextSession.DoesNotExist:
            return self._create_context_session()
    
    def _create_context_session(self):
        """Create a new context session for this prompt session."""
        from context_manager.models import ContextSession
        
        organization_id = self.project.organization.id
        tier = getattr(self.project.organization, 'tier', 'starter')
        
        context_session, created = ContextSession.objects.get_or_create(
            entity_id=self.id,
            entity_type='prompt_session',
            defaults={
                'organization_id': organization_id,
                'session_type': 'chat',
                'tier': tier
            }
        )
        
        self.context_session_id = context_session.id
        self.save(update_fields=['context_session_id'])
        return context_session

    async def aget_context_session(self):
        """Async version of get_context_session."""
        if self.context_session_id:
            try:
                from context_manager.models import ContextSession
                return await ContextSession.objects.aget(id=self.context_session_id)
            except ContextSession.DoesNotExist:
                pass
        
        return await self._acreate_context_session()
    
    async def _acreate_context_session(self):
        """Async version of _create_context_session."""
        from context_manager.models import ContextSession
        from channels.db import database_sync_to_async
        
        organization_id = self.project.organization.id
        tier = getattr(self.project.organization, 'tier', 'starter')
        
        context_session = await ContextSession.objects.acreate(
            organization_id=organization_id,
            session_type='chat',
            entity_id=self.id,
            entity_type='prompt_session',
            tier=tier
        )
        
        self.context_session_id = context_session.id
        await database_sync_to_async(self.save)(update_fields=['context_session_id'])
        
        return context_session

    # Clean cost computation properties
    @property
    def total_cost(self):
        """Total cost from all sources."""
        return self.model_execution_cost + self.context_preparation_cost
    
    @property
    def model_execution_cost(self):
        """Model execution costs from ModelMetrics."""
        from modelhub.models import ModelMetrics
        result = ModelMetrics.objects.filter(
            session_id=self.id,
        ).aggregate(total=models.Sum('cost'))['total']
        return result or Decimal('0.00')
    
    @property
    def context_preparation_cost(self):
        """Context preparation costs from ContextSession."""
        context_session = self.get_context_session()
        return context_session.total_context_preparation_cost or Decimal('0.00')
    
    @property
    def cost_breakdown(self):
        """Detailed cost breakdown with percentages."""
        model_cost = float(self.model_execution_cost)
        context_cost = float(self.context_preparation_cost)
        total = model_cost + context_cost
        
        return {
            'model_execution': model_cost,
            'context_preparation': context_cost,
            'total': total,
            'model_percentage': (model_cost / total * 100) if total > 0 else 0,
            'context_percentage': (context_cost / total * 100) if total > 0 else 0
        }

    def get_execution_count(self):
        """Get number of model executions."""
        from modelhub.models import ModelMetrics
        return ModelMetrics.objects.filter(
            session_id=self.id,
        ).count()
    
    def get_conversation_length(self):
        """Get total conversation entries."""
        context_session = self.get_context_session()
        return context_session.entries.count()
    
    def get_context_metrics(self):
        """Get context performance metrics."""
        context_session = self.get_context_session()
        return {
            'cache_hit_rate': context_session.cache_hit_rate,
            'avg_preparation_time_ms': context_session.avg_preparation_time_ms,
            'total_context_cost': float(context_session.total_context_preparation_cost),
            'total_entries': context_session.entries.count()
        }


class Prompt(SoftDeletableMixin, BaseModel):
    """
    Clean prompt model focused on execution and metadata.
    
    Conversation storage is handled by ContextEntry for consistency.
    This model handles prompt execution and prompt-specific metadata only.
    """
    
    session = models.ForeignKey(
        PromptSession,
        on_delete=models.CASCADE,
        related_name='prompts',
        verbose_name=_('session')
    )
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='submitted_prompts',
        verbose_name=_('user')
    )
    input_text = models.TextField(_('input text'))
    
    # Execution metadata only
    execution_metadata = models.JSONField(
        _('execution metadata'), 
        default=dict, 
        blank=True,
        help_text=_('Model execution details, optimization strategy, etc.')
    )
    
    # Quality scoring for this specific prompt
    importance_score = models.FloatField(
        default=1.0,
        help_text=_('Importance score for prioritization and cleanup')
    )
    is_starred = models.BooleanField(
        default=False,
        help_text=_('User-starred prompt (Enterprise feature)')
    )

    class Meta:
        verbose_name = _('prompt')
        verbose_name_plural = _('prompts')
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['importance_score']),
            models.Index(fields=['is_starred', '-created_at']),
        ]
        ordering = ['-created_at']

    objects = SoftDeletableManager()
    all_objects = models.Manager()

    def __str__(self):
        return f'Prompt by {self.user.email} in session {self.session.title}'

    async def execute_with_optimization(self, optimization_strategy='balanced'):
        """
        Execute prompt with unified context management and cost optimization.
        
        Clean implementation that integrates seamlessly with the universal
        context system without any legacy compatibility layers.
        
        Args:
            optimization_strategy (str): Cost optimization strategy
            
        Returns:
            tuple: (LLMResponse, metadata)
        """
        from modelhub.services.llm_router import execute_with_cost_optimization, OptimizationStrategy, RequestContext
        from modelhub.models import ModelMetrics
        from context_manager.services.universal_context_service import UniversalContextService, ContextRequest
        from types import SimpleNamespace
        from channels.db import database_sync_to_async
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"🚀 Executing prompt {self.id} with strategy: {optimization_strategy}")
        
        try:
            strategy_map = {
                'cost_first': OptimizationStrategy.COST_FIRST,
                'balanced': OptimizationStrategy.BALANCED,
                'quality_first': OptimizationStrategy.QUALITY_FIRST,
                'performance_first': OptimizationStrategy.PERFORMANCE_FIRST,
            }
            
            # Get organization
            organization = self.session.project.organization
            
            # 1. Prepare context using universal service
            context_service = UniversalContextService()
            
            # Create a ContextRequest object instead of passing keyword arguments
            context_request = ContextRequest(
                entity_id=str(self.session.id),
                entity_type='prompt_session',
                organization_id=str(organization.id),
                target_model='gpt-3.5-turbo',  # Will be optimized by router
                user_message=self.input_text
            )
            context_response = await context_service.prepare_context(context_request)
            
            logger.info(f"📝 Context prepared: {context_response.strategy_used}, "
                       f"{context_response.tokens_used} tokens, "
                       f"${context_response.preparation_cost:.6f}")
            
            # 2. Execute with cost optimization
            request_context = RequestContext(
                complexity='medium',
                max_tokens=512,
                session_id=str(self.session.id),
                prompt_id=str(self.id),
                user_preferences={
                    'context_content': context_response.context_content,
                    'context_tokens': context_response.tokens_used
                },
                entity_type='prompt_session'  # Explicitly set entity_type for prompt calls
            )
            
            response, execution_metadata = await execute_with_cost_optimization(
                organization=organization,
                model_type=self.session.model_type,
                request_context=request_context,
                strategy=strategy_map.get(optimization_strategy, OptimizationStrategy.BALANCED),
                prompt=self.input_text,
                max_tokens=512,
                temperature=0.7
            )
            
            # 3. Store execution metadata
            self.execution_metadata = {
                'optimization_strategy': optimization_strategy,
                'execution_timestamp': timezone.now().isoformat(),
                'model_metadata': execution_metadata,
                'context_metadata': {
                    'strategy_used': context_response.strategy_used,
                    'tokens_used': context_response.tokens_used,
                    'preparation_cost': float(context_response.preparation_cost),
                    'preparation_time_ms': context_response.preparation_time_ms,
                    'cache_hit': context_response.cache_hit,
                    'quality_score': context_response.information_preservation_score
                },
                'total_tokens': response.tokens_input + response.tokens_output,
                'cost_breakdown': {
                    'model_execution': float(response.cost),
                    'context_preparation': float(context_response.preparation_cost),
                    'total': float(response.cost) + float(context_response.preparation_cost)
                }
            }
            
            await database_sync_to_async(self.save)()
            
            # 4. Store conversation in unified context system
            # Store user input
            await context_service.store_interaction(
                entity_id=str(self.session.id),
                entity_type='prompt_session',
                organization_id=str(organization.id),
                role='user',
                content=self.input_text,
                source_entity_id=str(self.id),
                source_entity_type='prompt',
                importance_score=self.importance_score,
                context_preparation_cost=context_response.preparation_cost
            )
            
            # Store assistant response
            await context_service.store_interaction(
                entity_id=str(self.session.id),
                entity_type='prompt_session',
                organization_id=str(organization.id),
                role='assistant',
                content=response.content,
                source_entity_id=str(self.id),
                source_entity_type='prompt',
                model_used=execution_metadata.get('selected_model'),
                context_strategy=context_response.strategy_used,
                context_tokens_used=context_response.tokens_used,
                total_cost=response.cost,
                context_preparation_cost=context_response.preparation_cost
            )
            
            # 5. Update ModelMetrics with session references
            try:
                latest_metrics = await database_sync_to_async(
                    lambda: ModelMetrics.objects.filter(organization=organization).latest('created_at')
                )()
                
                latest_metrics.session_id = self.session.id
                latest_metrics.session_type = 'prompt_session'
                latest_metrics.context_session_id = self.session.context_session_id
                latest_metrics.prompt_text = self.input_text[:1000]
                
                await database_sync_to_async(latest_metrics.save)()
                logger.info(f"✅ Updated metrics with session references")
                
            except ModelMetrics.DoesNotExist:
                logger.warning("No metrics found to update")
            
            # 6. Update session status
            if self.session.status == PromptSession.Status.DRAFT:
                self.session.status = PromptSession.Status.ACTIVE
                self.session.started_at = timezone.now()
                await database_sync_to_async(self.session.save)()
            
            # 7. Return clean response
            formatted_response = SimpleNamespace()
            formatted_response.content = response.content
            formatted_response.tokens_input = response.tokens_input
            formatted_response.tokens_output = response.tokens_output
            formatted_response.cost = response.cost
            
            # Enhanced metadata with full context information
            enhanced_metadata = {
                **execution_metadata,
                'context': {
                    'strategy_used': context_response.strategy_used,
                    'tokens_used': context_response.tokens_used,
                    'preparation_cost': float(context_response.preparation_cost),
                    'cache_hit': context_response.cache_hit,
                    'quality_score': context_response.information_preservation_score
                },
                'cost_breakdown': {
                    'model_execution': float(response.cost),
                    'context_preparation': float(context_response.preparation_cost),
                    'total': float(response.cost) + float(context_response.preparation_cost)
                }
            }
            
            logger.info(f"✅ Prompt executed successfully: "
                       f"{response.tokens_input + response.tokens_output} tokens, "
                       f"total cost: ${float(response.cost) + float(context_response.preparation_cost):.6f}")
            
            return formatted_response, enhanced_metadata
            
        except Exception as e:
            logger.error(f"❌ Prompt execution failed: {str(e)}")
            
            # Update session status on failure
            if self.session.status in [PromptSession.Status.DRAFT, PromptSession.Status.ACTIVE]:
                self.session.status = PromptSession.Status.FAILED
                await database_sync_to_async(self.session.save)()
            
            # Store error in execution metadata
            self.execution_metadata = {
                'optimization_strategy': optimization_strategy,
                'execution_timestamp': timezone.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            }
            await database_sync_to_async(self.save)()
            
            # Return error response
            error_response = SimpleNamespace()
            error_response.content = f"Execution failed: {str(e)}"
            error_response.tokens_input = 0
            error_response.tokens_output = 0
            error_response.cost = Decimal('0.00')
            
            error_metadata = {
                'error': str(e),
                'optimization_strategy': optimization_strategy,
                'status': 'failed'
            }
            
            return error_response, error_metadata

    def get_conversation_context(self):
        """Get this prompt's context entries from the unified system."""
        from context_manager.models import ContextEntry
        
        if not self.session.context_session_id:
            return []
        
        return ContextEntry.objects.filter(
            session_id=self.session.context_session_id,
            source_entity_id=self.id,
            source_entity_type='prompt'
        ).order_by('created_at')
    
    async def aget_conversation_context(self):
        """Async version of get_conversation_context."""
        from context_manager.models import ContextEntry
        
        if not self.session.context_session_id:
            return []
        
        entries = []
        async for entry in ContextEntry.objects.filter(
            session_id=self.session.context_session_id,
            source_entity_id=self.id,
            source_entity_type='prompt'
        ).order_by('created_at'):
            entries.append(entry)
        return entries
    
    @property
    def execution_cost(self):
        """Get execution cost from metadata."""
        return self.execution_metadata.get('cost_breakdown', {}).get('total', 0.0)
    
    @property
    def model_used(self):
        """Get the model used for this execution."""
        return self.execution_metadata.get('model_metadata', {}).get('selected_model')
    
    @property
    def context_strategy_used(self):
        """Get the context strategy used."""
        return self.execution_metadata.get('context_metadata', {}).get('strategy_used')