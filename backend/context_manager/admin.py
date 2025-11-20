# context_manager/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum, Avg, Q
from decimal import Decimal
from datetime import datetime, timedelta

from .models import (
    ContextSession, ContextEntry, ContextSummaryCache,
    ContextTransition, MemoryCleanupPolicy, MemoryUsageStats
)
from .utils import format_context_for_display


@admin.register(ContextSession)
class ContextSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for Universal Context Sessions
    
    Provides overview of all conversation sessions across domains (Chat, Agents, Workflows)
    """
    list_display = [
        'id', 'organization_id', 'session_type', 'entity_type', 'tier', 
        'entry_count', 'cost_breakdown', 'cache_hit_rate', 'last_activity_at', 'created_at'
    ]
    list_filter = [
        'session_type', 'entity_type', 'tier', 'is_archived', 'created_at'
    ]
    search_fields = ['id', 'organization_id', 'entity_id']
    readonly_fields = [
        'id', 'created_at', 'last_activity_at', 'cache_hit_rate', 
        'avg_preparation_time_ms', 'total_context_requests'
    ]
    ordering = ['-last_activity_at']
    
    fieldsets = (
        ('Universal Entity Reference', {
            'fields': ('id', 'organization_id', 'session_type', 'entity_id', 'entity_type', 'tier')
        }),
        ('Context Management', {
            'fields': (
                'last_summarized_at', 'summary_version', 'context_window_preferences',
                'total_context_requests', 'cache_hit_rate', 'avg_preparation_time_ms'
            )
        }),
        ('Cost Tracking', {
            'fields': (
                'total_context_preparation_cost', 'total_summarization_cost', 
                'total_embedding_cost'
            )
        }),
        ('Lifecycle', {
            'fields': ('created_at', 'last_activity_at', 'expires_at', 'is_archived')
        }),
    )
    
    def entry_count(self, obj):
        """Count of messages in this session with domain indicator"""
        count = obj.entries.count()
        if count > 0:
            url = reverse('admin:context_manager_contextentry_changelist')
            # Add domain indicator
            domain_icon = {
                'chat': '💬',
                'agent': '🤖', 
                'custom': '🔧'
            }.get(obj.session_type, '📝')
            
            return format_html(
                '{} <a href="{}?session__id__exact={}">{}</a>', 
                domain_icon, url, obj.id, count
            )
        return f"{obj.session_type} (0)"
    entry_count.short_description = 'Messages'
    entry_count.admin_order_field = 'entries__count'
    
    def cost_breakdown(self, obj):
        """Visual cost breakdown by category"""
        total_cost = (
            obj.total_context_preparation_cost + 
            obj.total_summarization_cost + 
            obj.total_embedding_cost
        )
        
        if total_cost > 0:
            context_pct = (obj.total_context_preparation_cost / total_cost) * 100
            summary_pct = (obj.total_summarization_cost / total_cost) * 100
            embed_pct = (obj.total_embedding_cost / total_cost) * 100
            
            return format_html(
                '<div style="font-size: 11px; line-height: 1.2;">'
                '<strong>${:.4f}</strong><br>'
                '🔄 Context: {:.0f}%<br>'
                '📄 Summary: {:.0f}%<br>'
                '🔍 Embed: {:.0f}%'
                '</div>',
                total_cost, context_pct, summary_pct, embed_pct
            )
        return format_html('<span style="color: gray;">$0.0000</span>')
    cost_breakdown.short_description = 'Cost Breakdown'
    
    def get_queryset(self, request):
        """Optimize queryset with annotations"""
        qs = super().get_queryset(request)
        return qs.annotate(
            entry_count=Count('entries'),
            total_entry_cost=Sum('entries__total_cost')
        ).select_related()


@admin.register(ContextEntry)
class ContextEntryAdmin(admin.ModelAdmin):
    """
    Admin interface for Universal Context Entries
    
    Shows conversation history across all domains with rich metadata
    """
    list_display = [
        'id', 'session_link', 'role', 'content_type', 'content_preview', 
        'model_used', 'context_strategy', 'importance_score', 'cost_display', 'created_at'
    ]
    list_filter = [
        'role', 'content_type', 'model_used', 'context_strategy', 
        'is_starred', 'created_at'
    ]
    search_fields = ['content', 'session__id', 'organization_id', 'source_entity_id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'vector_id', 'parent_entry_id'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Universal Message Information', {
            'fields': (
                'id', 'session', 'role', 'content', 'content_type',
                'source_entity_id', 'source_entity_type', 'parent_entry_id'
            )
        }),
        ('Rich Content Support', {
            'fields': ('structured_data', 'execution_metadata'),
            'classes': ('collapse',)
        }),
        ('Context & AI Metadata', {
            'fields': (
                'model_used', 'context_strategy', 'context_tokens_used', 
                'vector_id', 'embedding_model'
            )
        }),
        ('Cost & Quality Tracking', {
            'fields': (
                'total_cost', 'context_preparation_cost', 'embedding_cost',
                'importance_score', 'confidence_score', 'is_starred'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def session_link(self, obj):
        """Link to the parent session with domain indicator"""
        url = reverse('admin:context_manager_contextsession_change', args=[obj.session.pk])
        domain_icon = {
            'chat': '💬',
            'agent': '🤖', 
            'custom': '🔧'
        }.get(obj.session.session_type, '📝')
        
        return format_html(
            '{} <a href="{}">{}</a>', 
            domain_icon, url, str(obj.session.id)[:8]
        )
    session_link.short_description = 'Session'
    
    def content_preview(self, obj):
        """Enhanced content preview with type indicators"""
        preview = format_context_for_display(obj.content, max_length=80)
        
        # Add content type indicator
        type_icons = {
            'text': '📝',
            'json': '📋',
            'code': '💻',
            'image_url': '🖼️',
            'tool_result': '🔧',
            'function_result': '⚙️'
        }
        icon = type_icons.get(obj.content_type, '📄')
        
        # Add special indicators
        indicators = []
        if obj.is_starred:
            indicators.append('⭐')
        if obj.structured_data:
            indicators.append('🔗')
        if obj.execution_metadata:
            indicators.append('⚡')
        
        indicator_str = ' '.join(indicators)
        if indicator_str:
            return format_html('{} {} {}', icon, indicator_str, preview)
        return format_html('{} {}', icon, preview)
    content_preview.short_description = 'Content'
    
    def cost_display(self, obj):
        """Enhanced cost display with breakdown"""
        if obj.total_cost > 0:
            # Show breakdown if context preparation cost exists
            if obj.context_preparation_cost > 0:
                model_cost = obj.total_cost - obj.context_preparation_cost
                total_cost_str = f"${float(obj.total_cost):.4f}"
                model_cost_str = f"${float(model_cost):.4f}"
                context_cost_str = f"${float(obj.context_preparation_cost):.4f}"
                
                return format_html(
                    '<div style="font-size: 11px;">' 
                    '<strong>{}</strong><br>' 
                    'Model: {}<br>' 
                    'Context: {}' 
                    '</div>',
                    total_cost_str, model_cost_str, context_cost_str
                )
            else:
                total_cost_str = f"${float(obj.total_cost):.4f}"
                return format_html('<strong>{}</strong>', total_cost_str)
        return format_html('<span style="color: gray;">$0.0000</span>')
    cost_display.short_description = 'Cost'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('session')


@admin.register(ContextSummaryCache)
class ContextSummaryCacheAdmin(admin.ModelAdmin):
    """
    Admin interface for Enhanced Summary Cache
    
    Monitor caching performance with model family awareness
    """
    list_display = [
        'id', 'session_link', 'summary_type', 'model_family', 'target_tokens',
        'access_count', 'generation_cost', 'cost_savings', 'compression_ratio', 
        'last_used_at', 'created_at'
    ]
    list_filter = [
        'summary_type', 'model_family', 'model_used_for_summary', 
        'created_at', 'last_used_at'
    ]
    search_fields = ['session__id', 'conversation_signature', 'model_family']
    readonly_fields = [
        'id', 'created_at', 'conversation_signature', 'compression_ratio',
        'information_preservation_score'
    ]
    ordering = ['-access_count', '-last_used_at']
    
    fieldsets = (
        ('Enhanced Cache Information', {
            'fields': (
                'id', 'session', 'conversation_signature', 'summary_type',
                'target_tokens', 'target_context_window', 'model_family'
            )
        }),
        ('Content & Quality', {
            'fields': (
                'summary_content', 'conversation_length', 'compression_ratio',
                'information_preservation_score'
            )
        }),
        ('Performance & Cost', {
            'fields': (
                'generation_cost', 'model_used_for_summary', 'generation_time_ms',
                'access_count', 'last_used_at'
            )
        }),
        ('Lifecycle', {
            'fields': ('created_at', 'expires_at')
        }),
    )
    
    def session_link(self, obj):
        """Link to the parent session with domain indicator"""
        url = reverse('admin:context_manager_contextsession_change', args=[obj.session.pk])
        domain_icon = {
            'chat': '💬',
            'agent': '🤖', 
            'custom': '🔧'
        }.get(obj.session.session_type, '📝')
        
        return format_html(
            '{} <a href="{}">{}</a>', 
            domain_icon, url, str(obj.session.id)[:8]
        )
    session_link.short_description = 'Session'
    
    def cost_savings(self, obj):
        """Enhanced cost savings calculation"""
        if obj.access_count > 1:
            savings = (obj.access_count - 1) * obj.generation_cost
            efficiency = (savings / obj.generation_cost) * 100 if obj.generation_cost > 0 else 0
            
            return format_html(
                '<div style="color: green; font-size: 11px;">'
                '<strong>${:.4f}</strong><br>'
                '{:.0f}% efficiency'
                '</div>',
                savings, efficiency
            )
        return format_html('<span style="color: gray;">$0.0000</span>')
    cost_savings.short_description = 'Savings'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('session')


@admin.register(ContextTransition)
class ContextTransitionAdmin(admin.ModelAdmin):
    """
    Admin interface for Context Transitions
    
    Track model switches and context strategy effectiveness across domains
    """
    list_display = [
        'id', 'session_link', 'transition_type', 'model_transition', 
        'strategy_transition', 'cost_impact', 'quality_impact', 'created_at'
    ]
    list_filter = [
        'transition_type', 'to_context_strategy', 'to_model', 'created_at'
    ]
    search_fields = ['session__id', 'to_model', 'from_model']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transition Information', {
            'fields': (
                'id', 'session', 'transition_type', 
                'from_model', 'to_model', 'from_context_strategy', 'to_context_strategy'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'context_tokens_used', 'context_utilization_percentage',
                'preparation_time_ms', 'latency_impact_ms'
            )
        }),
        ('Cost & Quality Impact', {
            'fields': (
                'preparation_cost', 'cost_savings',
                'information_preservation_score', 'user_satisfaction_score'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'metadata'),
            'classes': ('collapse',)
        }),
    )
    
    def session_link(self, obj):
        """Link to the parent session with domain indicator"""
        url = reverse('admin:context_manager_contextsession_change', args=[obj.session.pk])
        domain_icon = {
            'chat': '💬',
            'agent': '🤖', 
            'custom': '🔧'
        }.get(obj.session.session_type, '📝')
        
        return format_html(
            '{} <a href="{}">{}</a>', 
            domain_icon, url, str(obj.session.id)[:8]
        )
    session_link.short_description = 'Session'
    
    def model_transition(self, obj):
        """Visual model transition display"""
        if obj.from_model and obj.to_model:
            return format_html(
                '<span style="font-size: 11px;">{} → {}</span>',
                obj.from_model, obj.to_model
            )
        return obj.to_model or 'N/A'
    model_transition.short_description = 'Model Change'
    
    def strategy_transition(self, obj):
        """Visual strategy transition display"""
        if obj.from_context_strategy and obj.to_context_strategy:
            return format_html(
                '<span style="font-size: 11px;">{} → {}</span>',
                obj.from_context_strategy, obj.to_context_strategy
            )
        return obj.to_context_strategy or 'N/A'
    strategy_transition.short_description = 'Strategy Change'
    
    def cost_impact(self, obj):
        """Cost impact visualization"""
        if obj.cost_savings > 0:
            return format_html(
                '<span style="color: green;">-${:.4f}</span>', 
                obj.cost_savings
            )
        elif obj.preparation_cost > 0:
            return format_html(
                '<span style="color: orange;">${:.4f}</span>', 
                obj.preparation_cost
            )
        return format_html('<span style="color: gray;">$0.0000</span>')
    cost_impact.short_description = 'Cost Impact'
    
    def quality_impact(self, obj):
        """Quality impact visualization"""
        score = obj.information_preservation_score
        if score:
            if score >= 0.9:
                color = 'green'
                icon = '🟢'
            elif score >= 0.7:
                color = 'orange'
                icon = '🟡'
            else:
                color = 'red'
                icon = '🔴'
                
            return format_html(
                '<span style="color: {};">{} {:.1%}</span>',
                color, icon, score
            )
        return 'N/A'
    quality_impact.short_description = 'Quality'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('session')


@admin.register(MemoryCleanupPolicy)
class MemoryCleanupPolicyAdmin(admin.ModelAdmin):
    """
    Admin interface for Enhanced Memory Cleanup Policies
    
    Configure retention and cleanup rules with domain-specific settings
    """
    list_display = [
        'organization_id', 'tier', 'domain_retention_summary', 
        'cost_controls_summary', 'preserve_starred_content', 'updated_at'
    ]
    list_filter = ['tier', 'preserve_starred_content']
    search_fields = ['organization_id']
    readonly_fields = ['organization_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Organization', {
            'fields': ('organization_id', 'tier')
        }),
        ('Domain-Specific Retention Policies', {
            'fields': (
                'chat_session_retention_days', 
                'summary_cache_retention_days'
            )
        }),
        ('Cost Controls', {
            'fields': (
                'max_context_cost_per_day', 'max_summarization_cost_per_day', 
                'max_embedding_cost_per_day'
            )
        }),
        ('Quality & Preservation Controls', {
            'fields': (
                'importance_threshold', 'preserve_starred_content', 
                'preserve_high_confidence_responses'
            )
        }),
        ('Domain-Specific Rules', {
            'fields': (
                'preserve_tool_results',
            )
        }),
        ('Custom Rules (Enterprise)', {
            'fields': ('custom_retention_rules',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def domain_retention_summary(self, obj):
        """Summary of retention policies by domain"""
        return format_html(
            '<div style="font-size: 11px; line-height: 1.3;">'
            '💬 Chat: {} days<br>'
            '📄 Cache: {} days'
            '</div>',
            obj.chat_session_retention_days,
            obj.summary_cache_retention_days
        )
    domain_retention_summary.short_description = 'Retention by Domain'
    
    def cost_controls_summary(self, obj):
        """Summary of cost control limits"""
        total_daily_limit = (
            obj.max_context_cost_per_day + 
            obj.max_summarization_cost_per_day + 
            obj.max_embedding_cost_per_day
        )
        
        return format_html(
            '<div style="font-size: 11px; line-height: 1.3;">'
            '<strong>Daily: ${:.2f}</strong><br>'
            'Context: ${:.2f}<br>'
            'Summary: ${:.2f}<br>'
            'Embed: ${:.2f}'
            '</div>',
            total_daily_limit,
            obj.max_context_cost_per_day,
            obj.max_summarization_cost_per_day,
            obj.max_embedding_cost_per_day
        )
    cost_controls_summary.short_description = 'Cost Limits'


@admin.register(MemoryUsageStats)
class MemoryUsageStatsAdmin(admin.ModelAdmin):
    """
    Admin interface for Enhanced Memory Usage Statistics
    
    Monitor usage patterns across all domains with detailed breakdowns
    """
    list_display = [
        'id', 'organization_id', 'session_link', 'date',
        'domain_distribution', 'total_entries', 'cost_breakdown',
        'performance_summary', 'updated_at'
    ]
    list_filter = ['date', 'session__tier']
    search_fields = ['organization_id', 'session__id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-date', '-updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'organization_id', 'session', 'date')
        }),
        ('Domain Volume Metrics', {
            'fields': (
                'chat_entries_count',
                'total_entries'
            )
        }),
        ('Operation Counts', {
            'fields': (
                'summarization_events_count', 'embedding_events_count',
                'context_preparation_count'
            )
        }),
        ('Cost Metrics by Category', {
            'fields': (
                'total_context_cost', 'total_summarization_cost', 
                'total_embedding_cost'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'cache_hit_rate', 'average_context_preparation_time_ms',
                'average_summarization_time_ms'
            )
        }),
        ('Model Usage Distribution', {
            'fields': (
                'large_model_usage_count', 'medium_model_usage_count', 
                'small_model_usage_count'
            )
        }),
        ('Strategy Distribution', {
            'fields': (
                'full_context_usage_count', 'smart_summary_usage_count',
                'cached_context_usage_count', 'adaptive_summary_usage_count'
            )
        }),
        ('Quality Metrics', {
            'fields': (
                'average_information_preservation', 'average_user_satisfaction'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def session_link(self, obj):
        """Link to the parent session with domain indicator"""
        if obj.session:
            url = reverse('admin:context_manager_contextsession_change', args=[obj.session.pk])
            domain_icon = {
                'chat': '💬',
                'agent': '🤖', 
                    'custom': '🔧'
            }.get(obj.session.session_type, '📝')
            
            return format_html(
                '{} <a href="{}">{}</a>', 
                domain_icon, url, str(obj.session.id)[:8]
            )
        return '-'
    session_link.short_description = 'Session'
    
    def domain_distribution(self, obj):
        """Show domain distribution visually"""
        total = obj.total_entries
        if total == 0:
            return "No entries"
        
        chat_pct = (obj.chat_entries_count / total) * 100
        
        return format_html(
            '<div style="font-size: 11px; line-height: 1.3;">'
            '💬 {:.0f}% ({})'
            '</div>',
            chat_pct, obj.chat_entries_count
        )
    domain_distribution.short_description = 'Domain Split'
    
    def cost_breakdown(self, obj):
        """Enhanced cost breakdown display"""
        total_cost = (
            obj.total_context_cost + 
            obj.total_summarization_cost + 
            obj.total_embedding_cost
        )
        
        if total_cost > 0:
            return format_html(
                '<div style="font-size: 11px; line-height: 1.3;">'
                '<strong>${:.4f}</strong><br>'
                '🔄 ${:.4f}<br>'
                '📄 ${:.4f}<br>'
                '🔍 ${:.4f}'
                '</div>',
                total_cost,
                obj.total_context_cost,
                obj.total_summarization_cost,
                obj.total_embedding_cost
            )
        return format_html('<span style="color: gray;">$0.0000</span>')
    cost_breakdown.short_description = 'Cost Breakdown'
    
    def performance_summary(self, obj):
        """Performance metrics summary"""
        return format_html(
            '<div style="font-size: 11px; line-height: 1.3;">'
            'Cache: {:.0f}%<br>'
            'Prep: {:.0f}ms<br>'
            'Quality: {:.1f}'
            '</div>',
            obj.cache_hit_rate * 100,
            obj.average_context_preparation_time_ms,
            obj.average_information_preservation or 0.0
        )
    performance_summary.short_description = 'Performance'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('session')


# Enhanced Admin Actions
@admin.action(description='Clean up low importance entries (domain-aware)')
def cleanup_low_importance_entries(modeladmin, request, queryset):
    """Enhanced admin action to clean up low importance entries across domains"""
    from .services.universal_context_service import UniversalContextService
    
    context_service = UniversalContextService()
    total_cleaned = 0
    
    for session in queryset:
        cleaned_result = context_service.cleanup_low_importance_entries(
            organization_id=session.organization_id,
            entity_id=str(session.entity_id),
            entity_type=session.entity_type,
            importance_threshold=0.3,
            older_than_days=30
        )
        total_cleaned += cleaned_result.get('entries_removed', 0)
    
    modeladmin.message_user(
        request, 
        f"Cleaned up {total_cleaned} low importance entries across {queryset.count()} sessions."
    )


@admin.action(description='Refresh cache statistics and model families')
def refresh_cache_statistics(modeladmin, request, queryset):
    """Enhanced admin action to refresh cache statistics with model family updates"""
    from .services.cache_service import SummaryCacheService
    
    cache_service = SummaryCacheService()
    updated_count = 0
    
    for cache_entry in queryset:
        # Update model family if missing
        if not cache_entry.model_family and cache_entry.model_used_for_summary:
            cache_entry.model_family = cache_service._get_model_family(
                cache_entry.model_used_for_summary
            )
            cache_entry.save(update_fields=['model_family'])
            updated_count += 1
    
    modeladmin.message_user(
        request, 
        f"Refreshed statistics for {queryset.count()} cache entries. "
        f"Updated model families for {updated_count} entries."
    )


# Add actions to admin classes
ContextSessionAdmin.actions = [cleanup_low_importance_entries]
ContextSummaryCacheAdmin.actions = [refresh_cache_statistics]


# Enhanced Admin Site Configuration
admin.site.site_header = "AI Cost Optimizer - Universal Context Management"
admin.site.site_title = "Context Manager Admin"
admin.site.index_title = "Universal Context Management System"


class ContextManagerAdminConfig:
    """
    Enhanced configuration for the Context Manager admin interface
    
    Provides comprehensive dashboard with domain-aware metrics
    """
    
    def get_admin_dashboard_context(self, request):
        """Get enhanced context data for admin dashboard"""
        from django.db.models import Count, Sum, Avg, Q
        from datetime import datetime, timedelta
        
        # Get metrics for the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        # Universal session metrics by domain
        session_metrics = {
            'total': ContextSession.objects.count(),
            'active_30d': ContextSession.objects.filter(
                last_activity_at__gte=thirty_days_ago
            ).count(),
            'by_domain': {}
        }
        
        for domain in ['chat', 'agent', 'custom']:
            session_metrics['by_domain'][domain] = ContextSession.objects.filter(
                session_type=domain,
                last_activity_at__gte=thirty_days_ago
            ).count()
        
        # Entry metrics by domain
        entry_metrics = {
            'total': ContextEntry.objects.count(),
            'recent_30d': ContextEntry.objects.filter(
                created_at__gte=thirty_days_ago
            ).count(),
            'by_role': {}
        }
        
        for role in ['user', 'assistant', 'agent', 'system']:
            entry_metrics['by_role'][role] = ContextEntry.objects.filter(
                role=role,
                created_at__gte=thirty_days_ago
            ).count()
        
        # Enhanced cost metrics with breakdown
        cost_metrics = {}
        
        # Total costs across all categories
        total_costs = ContextSession.objects.aggregate(
            context_cost=Sum('total_context_preparation_cost'),
            summary_cost=Sum('total_summarization_cost'),
            embed_cost=Sum('total_embedding_cost')
        )
        
        cost_metrics['total_context'] = total_costs['context_cost'] or Decimal('0.00')
        cost_metrics['total_summary'] = total_costs['summary_cost'] or Decimal('0.00')
        cost_metrics['total_embed'] = total_costs['embed_cost'] or Decimal('0.00')
        cost_metrics['total_all'] = (
            cost_metrics['total_context'] + 
            cost_metrics['total_summary'] + 
            cost_metrics['total_embed']
        )
        
        # Recent costs (last 30 days)
        recent_cost = ContextEntry.objects.filter(
            created_at__gte=thirty_days_ago
        ).aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0.00')
        
        cost_metrics['recent_30d'] = recent_cost
        
        # Enhanced cache metrics with model family breakdown
        cache_metrics = {
            'total_entries': ContextSummaryCache.objects.count(),
            'total_hits': ContextSummaryCache.objects.aggregate(
                hits=Sum('access_count')
            )['hits'] or 0,
            'by_family': {},
            'by_type': {}
        }
        
        # Cache metrics by model family
        families = ContextSummaryCache.objects.values('model_family').distinct()
        for family_data in families:
            family = family_data['model_family'] or 'unknown'
            cache_metrics['by_family'][family] = ContextSummaryCache.objects.filter(
                model_family=family
            ).aggregate(
                count=Count('id'),
                hits=Sum('access_count'),
                cost=Sum('generation_cost')
            )
        
        # Cache metrics by summary type
        types = ContextSummaryCache.objects.values('summary_type').distinct()
        for type_data in types:
            summary_type = type_data['summary_type'] or 'conversation'
            cache_metrics['by_type'][summary_type] = ContextSummaryCache.objects.filter(
                summary_type=summary_type
            ).count()
        
        # Calculate cache savings
        cache_savings = Decimal('0.00')
        for cache_entry in ContextSummaryCache.objects.all():
            if cache_entry.access_count > 1:
                cache_savings += (cache_entry.access_count - 1) * cache_entry.generation_cost
        
        cache_metrics['total_savings'] = cache_savings
        
        # Performance metrics
        performance_metrics = {
            'avg_cache_hit_rate': ContextSession.objects.aggregate(
                avg_hit_rate=Avg('cache_hit_rate')
            )['avg_hit_rate'] or 0.0,
            'avg_prep_time': ContextSession.objects.aggregate(
                avg_time=Avg('avg_preparation_time_ms')
            )['avg_time'] or 0.0,
            'total_requests': ContextSession.objects.aggregate(
                total=Sum('total_context_requests')
            )['total'] or 0
        }
        
        # Model usage breakdown
        model_usage = {}
        model_entries = ContextEntry.objects.filter(
            created_at__gte=thirty_days_ago,
            model_used__isnull=False
        ).values('model_used').annotate(
            count=Count('id'),
            cost=Sum('total_cost')
        ).order_by('-count')[:10]
        
        for entry in model_entries:
            model_usage[entry['model_used']] = {
                'count': entry['count'],
                'cost': entry['cost'] or Decimal('0.00')
            }
        
        # Context strategy effectiveness
        strategy_metrics = {}
        strategies = ContextEntry.objects.filter(
            created_at__gte=thirty_days_ago,
            context_strategy__isnull=False
        ).values('context_strategy').annotate(
            count=Count('id'),
            avg_cost=Avg('context_preparation_cost'),
            avg_tokens=Avg('context_tokens_used')
        )
        
        for strategy in strategies:
            strategy_metrics[strategy['context_strategy']] = {
                'count': strategy['count'],
                'avg_cost': strategy['avg_cost'] or Decimal('0.00'),
                'avg_tokens': strategy['avg_tokens'] or 0
            }
        
        # Recent transitions for optimization insights
        recent_transitions = ContextTransition.objects.filter(
            created_at__gte=seven_days_ago
        ).values('transition_type').annotate(
            count=Count('id'),
            avg_cost_savings=Avg('cost_savings'),
            avg_quality=Avg('information_preservation_score')
        )
        
        transition_metrics = {}
        for transition in recent_transitions:
            transition_metrics[transition['transition_type']] = {
                'count': transition['count'],
                'avg_savings': transition['avg_cost_savings'] or Decimal('0.00'),
                'avg_quality': transition['avg_quality'] or 0.0
            }
        
        return {
            'session_metrics': session_metrics,
            'entry_metrics': entry_metrics,
            'cost_metrics': cost_metrics,
            'cache_metrics': cache_metrics,
            'performance_metrics': performance_metrics,
            'model_usage': model_usage,
            'strategy_metrics': strategy_metrics,
            'transition_metrics': transition_metrics,
            'dashboard_generated_at': datetime.now()
        }