import uuid
from django.db import models
from django.utils import timezone
from decimal import Decimal


class ContextSession(models.Model):
    """
    Universal session model for all AI interactions across domains.
    
    Supports Chat, Agents, and Workflows with consistent context management.
    This is the central hub for cross-domain context intelligence.
    """
    
    SESSION_TYPES = [
        ('chat', 'Chat Session'),
        ('agent', 'Agent Session'),
        ('custom', 'Custom Session'),
    ]
    
    TIER_CHOICES = [
        ('starter', 'Starter'),
        ('pro', 'Pro'),
        ('team', 'Team'),
        ('enterprise', 'Enterprise'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)  # Tenant scoping
    
    # Universal entity reference - works for any domain
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    entity_id = models.UUIDField(db_index=True)  # Points to PromptSession, WorkflowExecution
    entity_type = models.CharField(
        max_length=50, 
        db_index=True,
        help_text="Entity type: 'prompt_session', 'workflow_execution', etc."
    )
    
    # Subscription and capability management
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='starter')
    
    # Context management metadata
    last_summarized_at = models.DateTimeField(null=True, blank=True)
    summary_version = models.IntegerField(default=0)
    context_window_preferences = models.JSONField(default=dict, blank=True)
    
    # Cost tracking (context-specific costs only)
    total_context_preparation_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    total_summarization_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    total_embedding_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Performance metrics
    cache_hit_rate = models.FloatField(default=0.0)
    avg_preparation_time_ms = models.FloatField(default=0.0)
    total_context_requests = models.IntegerField(default=0)
    
    # Session lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'context_sessions'
        indexes = [
            models.Index(fields=['organization_id', 'session_type', 'last_activity_at']),
            models.Index(fields=['entity_id', 'entity_type']),  # Fast entity lookup
            models.Index(fields=['organization_id', 'tier', 'expires_at']),
            models.Index(fields=['last_summarized_at', 'summary_version']),
            models.Index(fields=['organization_id', 'total_context_preparation_cost']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['entity_id', 'entity_type'],
                name='unique_entity_context_session'
            )
        ]
    
    def __str__(self):
        return f"Context Session {self.session_type} - {self.entity_type} ({self.tier})"
    
    def get_entity(self):
        """Get the actual domain entity (PromptSession, etc.)"""
        if self.entity_type == 'prompt_session':
            from prompt.models import PromptSession
            try:
                return PromptSession.objects.get(id=self.entity_id)
            except PromptSession.DoesNotExist:
                return None
        return None
    
    async def update_cost_metrics(self, context_cost=None, summary_cost=None, embedding_cost=None):
        """Update aggregated cost metrics"""
        from asgiref.sync import sync_to_async
        
        if context_cost is not None:
            self.total_context_preparation_cost += Decimal(str(context_cost))
        if summary_cost is not None:
            self.total_summarization_cost += Decimal(str(summary_cost))
        if embedding_cost is not None:
            self.total_embedding_cost += Decimal(str(embedding_cost))
        
        # Use sync_to_async to perform database operation in async context
        save_func = sync_to_async(self.save)
        await save_func(update_fields=[
            'total_context_preparation_cost', 
            'total_summarization_cost', 
            'total_embedding_cost'
        ])
    
    async def update_performance_metrics(self, cache_hit=None, preparation_time_ms=None):
        """Update performance metrics with rolling averages"""
        from asgiref.sync import sync_to_async
        
        self.total_context_requests += 1
        
        if cache_hit is not None:
            # Update cache hit rate with weighted average
            current_hits = self.cache_hit_rate * (self.total_context_requests - 1)
            new_hits = current_hits + (1 if cache_hit else 0)
            self.cache_hit_rate = new_hits / self.total_context_requests
        
        if preparation_time_ms is not None:
            # Update average preparation time with weighted average
            current_total_time = self.avg_preparation_time_ms * (self.total_context_requests - 1)
            new_total_time = current_total_time + preparation_time_ms
            self.avg_preparation_time_ms = new_total_time / self.total_context_requests
        
        # Use sync_to_async to perform database operation in async context
        save_func = sync_to_async(self.save)
        await save_func(update_fields=[
            'cache_hit_rate', 
            'avg_preparation_time_ms', 
            'total_context_requests'
        ])


class ContextEntry(models.Model):
    """
    Universal conversation storage for all AI interactions.
    
    Stores messages from Chat, Agent actions, Workflow steps, and any
    future AI interaction types with full fidelity and rich metadata.
    """
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool'),                # For tool execution results
        ('function', 'Function'),        # For function call results
    ]
    
    CONTEXT_STRATEGIES = [
        ('full_context', 'Full Context'),
        ('adaptive_summary', 'Adaptive Summary'),
        ('smart_summary', 'Smart Summary'),
        ('cached_context', 'Cached Context'),
        ('incremental_summary', 'Incremental Summary'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)  # Tenant scoping
    session = models.ForeignKey(ContextSession, on_delete=models.CASCADE, related_name='entries')
    
    # Message content and metadata
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # Rich content support for agents and workflows
    content_type = models.CharField(
        max_length=50, 
        default='text',
        help_text="Content type: 'text', 'json', 'code', 'image_url', 'tool_result', etc."
    )
    structured_data = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Structured data for agents/workflows (tool calls, function results, etc.)"
    )
    
    # Source entity reference (links back to domain-specific data)
    source_entity_id = models.UUIDField(null=True, blank=True, db_index=True)
    source_entity_type = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Source type: 'prompt', 'workflow_step', 'tool_execution', etc."
    )
    
    # Vector embedding support
    vector_id = models.CharField(max_length=255, null=True, blank=True)  # Qdrant/Pinecone Point ID
    embedding_model = models.CharField(max_length=100, null=True, blank=True)
    
    # Model and context tracking
    model_used = models.CharField(max_length=100, null=True, blank=True)
    context_strategy = models.CharField(max_length=30, choices=CONTEXT_STRATEGIES, null=True)
    context_tokens_used = models.IntegerField(null=True, blank=True)
    
    # Cost tracking (context-specific costs)
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    context_preparation_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    embedding_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Quality and importance
    importance_score = models.FloatField(default=1.0)  # For cleanup prioritization
    confidence_score = models.FloatField(null=True, blank=True)  # AI confidence in response
    is_starred = models.BooleanField(default=False)  # Enterprise feature
    
    # Agent/Workflow specific fields
    execution_metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Execution details for agents/workflows (tools used, reasoning steps, etc.)"
    )
    parent_entry_id = models.UUIDField(
        null=True, 
        blank=True,
        help_text="For threaded conversations or workflow step dependencies"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'context_entries'
        indexes = [
            models.Index(fields=['organization_id', 'session', 'created_at']),
            models.Index(fields=['session', 'role', 'created_at']),
            models.Index(fields=['source_entity_id', 'source_entity_type']),
            models.Index(fields=['organization_id', 'importance_score']),
            models.Index(fields=['organization_id', 'total_cost', 'created_at']),
            models.Index(fields=['content_type', 'role']),
            models.Index(fields=['parent_entry_id']),  # For threaded conversations
            models.Index(fields=['vector_id']),  # For vector lookups
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"Entry {self.role} - {self.content_type} ({self.created_at})"
    
    def get_source_entity(self):
        """Get the source entity that created this entry"""
        if not self.source_entity_id or not self.source_entity_type:
            return None
            
        if self.source_entity_type == 'prompt':
            from prompt.models import Prompt
            try:
                return Prompt.objects.get(id=self.source_entity_id)
            except Prompt.DoesNotExist:
                return None
        return None
    
    def get_thread_entries(self):
        """Get all entries in the same thread (for agent conversations)"""
        if not self.parent_entry_id:
            return ContextEntry.objects.filter(parent_entry_id=self.id)
        else:
            return ContextEntry.objects.filter(
                models.Q(parent_entry_id=self.parent_entry_id) | 
                models.Q(id=self.parent_entry_id)
            ).order_by('created_at')


class ContextSummaryCache(models.Model):
    """
    Intelligent caching for conversation summaries across all domains.
    
    Optimizes context preparation through domain-aware caching with
    support for different conversation types and models.
    """
    
    SUMMARY_TYPES = [
        ('conversation', 'Conversation Summary'),
        ('tool_usage', 'Tool Usage Summary'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)  # Tenant scoping
    session = models.ForeignKey(ContextSession, on_delete=models.CASCADE, related_name='summary_cache')
    
    # Cache key components
    conversation_signature = models.CharField(max_length=64)  # Content hash
    summary_type = models.CharField(max_length=30, choices=SUMMARY_TYPES, default='conversation')
    target_tokens = models.IntegerField()  # Summary length target
    target_context_window = models.IntegerField()  # Model context window
    model_family = models.CharField(max_length=50, blank=True)  # 'gpt', 'claude', 'mixtral'
    
    # Cached content
    summary_content = models.TextField()
    conversation_length = models.IntegerField()  # Messages when generated
    
    # Cost and performance tracking
    generation_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    model_used_for_summary = models.CharField(max_length=100)
    generation_time_ms = models.IntegerField(null=True, blank=True)
    
    # Quality metrics
    compression_ratio = models.FloatField(null=True, blank=True)  # Original:Summary token ratio
    information_preservation_score = models.FloatField(null=True, blank=True)
    
    # Usage tracking
    access_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(auto_now=True)
    
    # Lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'context_summary_cache'
        indexes = [
            models.Index(fields=['session', 'conversation_signature', 'target_tokens']),
            models.Index(fields=['organization_id', 'summary_type', 'created_at']),
            models.Index(fields=['last_used_at', 'access_count']),  # Cache optimization
            models.Index(fields=['model_family', 'target_context_window']),
            models.Index(fields=['expires_at']),  # Cleanup optimization
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'conversation_signature', 'target_tokens', 'summary_type'],
                name='unique_summary_cache_entry'
            )
        ]
    
    def __str__(self):
        return f"Summary Cache {self.summary_type} - {self.target_tokens} tokens"
    
    def increment_access(self):
        """Increment access count and update last used timestamp"""
        self.access_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['access_count', 'last_used_at'])


class ContextTransition(models.Model):
    """
    Tracks context strategy transitions and model switches across domains.
    
    Monitors effectiveness of context management for optimization and
    provides insights for improving context strategies.
    """
    
    TRANSITION_TYPES = [
        ('cost_optimization', 'Cost Optimization'),
        ('quality_upgrade', 'Quality Upgrade'),
        ('context_window_constraint', 'Context Window Constraint'),
        ('model_switch', 'Model Switch'),
        ('user_preference', 'User Preference'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)  # Tenant scoping
    session = models.ForeignKey(ContextSession, on_delete=models.CASCADE, related_name='transitions')
    
    # Transition details
    from_model = models.CharField(max_length=100, null=True, blank=True)
    to_model = models.CharField(max_length=100)
    from_context_strategy = models.CharField(max_length=30, null=True, blank=True)
    to_context_strategy = models.CharField(max_length=30)
    transition_type = models.CharField(max_length=30, choices=TRANSITION_TYPES)
    
    # Context strategy performance
    context_tokens_used = models.IntegerField()
    context_utilization_percentage = models.FloatField()  # Window utilization
    
    # Cost impact
    preparation_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    cost_savings = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Performance impact
    preparation_time_ms = models.IntegerField()
    latency_impact_ms = models.IntegerField(default=0)  # Positive = slower, Negative = faster
    
    # Quality metrics
    information_preservation_score = models.FloatField(null=True, blank=True)
    user_satisfaction_score = models.FloatField(null=True, blank=True)  # If available
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'context_transitions'
        indexes = [
            models.Index(fields=['organization_id', 'session', 'created_at']),
            models.Index(fields=['organization_id', 'transition_type', 'created_at']),
            models.Index(fields=['organization_id', 'preparation_cost', 'created_at']),
            models.Index(fields=['to_model', 'to_context_strategy']),
            models.Index(fields=['cost_savings', 'preparation_time_ms']),
        ]
    
    def __str__(self):
        return f"Transition {self.transition_type} - {self.from_model} → {self.to_model}"


class MemoryCleanupPolicy(models.Model):
    """
    Organization-specific cleanup and retention policies.
    
    Manages data lifecycle across all domains with tier-based rules
    and custom enterprise policies.
    """
    
    organization_id = models.UUIDField(primary_key=True)  # One policy per org
    tier = models.CharField(max_length=20, choices=ContextSession.TIER_CHOICES)
    
    # Retention policies by domain
    chat_session_retention_days = models.IntegerField(default=7)
    
    # Cache retention
    summary_cache_retention_days = models.IntegerField(default=7)
    
    # Cost controls
    max_context_cost_per_day = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('1.00')
    )
    max_summarization_cost_per_day = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.50')
    )
    max_embedding_cost_per_day = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.25')
    )
    
    # Quality controls
    importance_threshold = models.FloatField(default=0.5)  # Cleanup criteria
    preserve_starred_content = models.BooleanField(default=False)  # Enterprise
    preserve_high_confidence_responses = models.BooleanField(default=True)
    
    # Domain-specific rules
    preserve_tool_results = models.BooleanField(default=False)    # Tool results can be regenerated
    
    # Custom rules (Enterprise)
    custom_retention_rules = models.JSONField(default=dict, blank=True)
    
    # Lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'memory_cleanup_policies'
    
    def __str__(self):
        return f"Cleanup Policy - {self.tier} (Org: {self.organization_id})"
    
    def get_retention_days_for_session_type(self, session_type):
        """Get retention days for specific session type"""
        return {
            'chat': self.chat_session_retention_days,
        }.get(session_type, self.chat_session_retention_days)


class MemoryUsageStats(models.Model):
    """
    Comprehensive usage and performance tracking across all domains.
    
    Provides insights for optimization and billing across Chat, Agents,
    and Workflows with detailed breakdown by domain and strategy.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)  # Tenant scoping
    session = models.ForeignKey(ContextSession, on_delete=models.CASCADE, related_name='usage_stats')
    
    # Volume metrics by domain
    chat_entries_count = models.IntegerField(default=0)
    total_entries = models.IntegerField(default=0)
    
    # Context operation counts
    summarization_events_count = models.IntegerField(default=0)
    embedding_events_count = models.IntegerField(default=0)
    context_preparation_count = models.IntegerField(default=0)
    
    # Cost metrics by category
    total_context_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    total_summarization_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    total_embedding_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Performance metrics
    cache_hit_rate = models.FloatField(default=0.0)
    average_context_preparation_time_ms = models.FloatField(default=0.0)
    average_summarization_time_ms = models.FloatField(default=0.0)
    
    # Model usage distribution
    large_model_usage_count = models.IntegerField(default=0)     # GPT-4, Claude-3-Opus
    medium_model_usage_count = models.IntegerField(default=0)    # GPT-3.5, Claude-3-Sonnet
    small_model_usage_count = models.IntegerField(default=0)     # Mixtral, Claude-3-Haiku
    
    # Strategy distribution
    full_context_usage_count = models.IntegerField(default=0)
    smart_summary_usage_count = models.IntegerField(default=0)
    cached_context_usage_count = models.IntegerField(default=0)
    adaptive_summary_usage_count = models.IntegerField(default=0)
    
    # Quality metrics
    average_information_preservation = models.FloatField(default=0.0)
    average_user_satisfaction = models.FloatField(null=True, blank=True)
    
    # Timestamps
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'memory_usage_stats'
        indexes = [
            models.Index(fields=['organization_id', 'date']),
            models.Index(fields=['session', 'date']),
            models.Index(fields=['organization_id', 'total_context_cost', 'date']),
            models.Index(fields=['date', 'cache_hit_rate']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'session', 'date'],
                name='unique_daily_usage_stats'
            )
        ]
    
    def __str__(self):
        return f"Usage Stats {self.date} - Session {self.session_id}"
    
    def update_domain_counts(self):
        """Update domain-specific entry counts"""
        entries = self.session.entries.values('role').annotate(count=models.Count('id'))
        
        for entry in entries:
            role = entry['role']
            count = entry['count']
            
            if role in ['user', 'assistant']:
                self.chat_entries_count += count
        
        self.total_entries = self.chat_entries_count
        self.save(update_fields=[
            'chat_entries_count', 
            'total_entries'
        ])