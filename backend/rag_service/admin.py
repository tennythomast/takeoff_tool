from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum

from .models import (
    KnowledgeBase, Document, DocumentPage, Chunk, VectorIndex,
    RAGQuery, RAGQueryResult
)


class DocumentInline(admin.TabularInline):
    model = Document
    fields = ('title', 'document_type', 'status', 'chunk_count', 'token_count')
    readonly_fields = ('chunk_count', 'token_count')
    extra = 0
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False


class VectorIndexInline(admin.TabularInline):
    model = VectorIndex
    fields = ('name', 'index_type', 'status', 'vector_count')
    readonly_fields = ('vector_count',)
    extra = 0
    show_change_link = True


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'organization_name', 'project_name', 'document_count',
        'chunk_count', 'embedding_model_name', 'is_public', 'is_active'
    )
    list_filter = ('is_active', 'is_public', 'embedding_strategy', 'retrieval_strategy')
    search_fields = ('name', 'description', 'organization__name', 'project__title')
    readonly_fields = ('document_count', 'chunk_count', 'total_tokens', 'total_embedding_cost', 'last_updated', 'last_queried')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'organization', 'project', 'created_by')
        }),
        ('Configuration', {
            'fields': ('embedding_model', 'embedding_strategy', 'retrieval_strategy', 'is_public')
        }),
        ('Advanced Configuration', {
            'fields': ('chunk_size', 'chunk_overlap', 'similarity_top_k', 'mmr_diversity_bias', 'advanced_config'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('document_count', 'chunk_count', 'total_tokens', 'total_embedding_cost', 'last_updated', 'last_queried')
        }),
    )
    inlines = [DocumentInline, VectorIndexInline]
    
    def organization_name(self, obj):
        return obj.organization.name
    organization_name.short_description = 'Organization'
    
    def project_name(self, obj):
        if obj.project:
            return obj.project.title
        return '-'
    project_name.short_description = 'Project'
    
    def embedding_model_name(self, obj):
        if obj.embedding_model:
            return f"{obj.embedding_model.provider.name} - {obj.embedding_model.name}"
        return '-'
    embedding_model_name.short_description = 'Embedding Model'


class DocumentPageInline(admin.TabularInline):
    model = DocumentPage
    fields = ('page_number', 'page_text_preview', 'word_count', 'token_count')
    readonly_fields = ('page_number', 'page_text_preview', 'word_count', 'token_count')
    extra = 0
    show_change_link = True
    max_num = 10
    
    def page_text_preview(self, obj):
        if obj.page_text and len(obj.page_text) > 100:
            return obj.page_text[:100] + '...'
        return obj.page_text or ''
    page_text_preview.short_description = 'Text Preview'
    
    def has_add_permission(self, request, obj=None):
        return False


class ChunkInline(admin.TabularInline):
    model = Chunk
    fields = ('chunk_index', 'token_count', 'page_number', 'retrieval_count', 'relevance_score_avg')
    readonly_fields = ('chunk_index', 'token_count', 'retrieval_count', 'relevance_score_avg')
    extra = 0
    show_change_link = True
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'knowledge_base_name', 'document_type', 'storage_approach', 'status',
        'page_count', 'chunk_count', 'token_count', 'is_active'
    )
    list_filter = ('is_active', 'status', 'document_type', 'storage_approach')
    search_fields = ('title', 'description', 'knowledge_base__name')
    readonly_fields = ('page_count', 'chunk_count', 'token_count', 'embedding_cost', 'processed_at', 'last_accessed', 'search_vector_preview')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'knowledge_base', 'document_type', 'storage_approach')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('collapse',)
        }),
        ('Search Vector', {
            'fields': ('search_vector_preview',),
            'classes': ('collapse',)
        }),
        ('File Information', {
            'fields': ('file_upload', 'source_url')
        }),
        ('Processing', {
            'fields': ('status', 'processing_error', 'processed_at')
        }),
        ('Extraction', {
            'fields': ('extraction_method', 'extraction_cost_usd', 'extraction_quality_score', 'extraction_metadata'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('page_count', 'chunk_count', 'token_count', 'embedding_cost', 'last_accessed')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    inlines = [DocumentPageInline, ChunkInline]
    
    def knowledge_base_name(self, obj):
        return obj.knowledge_base.name
    knowledge_base_name.short_description = 'Knowledge Base'
    
    def page_count(self, obj):
        return obj.pages.count()
    page_count.short_description = 'Pages'
    
    def search_vector_preview(self, obj):
        """Format the search vector for display in admin"""
        if not obj.content_search_vector:
            return "No search vector available"
            
        keywords = obj.content_search_vector.get('keywords', {})
        if not keywords:
            return "Empty search vector"
            
        # Format the top keywords with their frequencies
        html = '<div style="max-height: 400px; overflow-y: auto;">'  
        html += '<h4>Top Keywords</h4>'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align: left; padding: 8px;">Keyword</th>'
        html += '<th style="text-align: right; padding: 8px;">Frequency</th></tr>'
        
        # Sort keywords by frequency (descending)
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        
        # Display top 50 keywords
        for keyword, frequency in sorted_keywords[:50]:
            html += f'<tr><td style="padding: 4px;">{keyword}</td>'
            html += f'<td style="text-align: right; padding: 4px;">{frequency}</td></tr>'
            
        html += '</table>'
        
        # Add metadata
        if 'updated_at' in obj.content_search_vector:
            html += f'<p><small>Last updated: {obj.content_search_vector["updated_at"]}</small></p>'
            
        html += '</div>'
        return format_html(html)
    search_vector_preview.short_description = 'Search Vector'


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'document_title', 'page_number', 'word_count',
        'token_count', 'page_text_preview'
    )
    list_filter = ('document__document_type', 'document__status')
    search_fields = ('page_text', 'document__title')
    readonly_fields = ('document', 'page_number', 'word_count', 'token_count')
    fieldsets = (
        ('Basic Information', {
            'fields': ('document', 'page_number', 'word_count', 'token_count')
        }),
        ('Content', {
            'fields': ('page_text',)
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
    )
    
    def document_title(self, obj):
        return obj.document.title
    document_title.short_description = 'Document'
    
    def page_text_preview(self, obj):
        if obj.page_text and len(obj.page_text) > 100:
            return obj.page_text[:100] + '...'
        return obj.page_text or ''
    page_text_preview.short_description = 'Text Preview'


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'document_title', 'chunk_index', 'token_count',
        'retrieval_count', 'relevance_score_avg'
    )
    list_filter = ('document__document_type', 'document__status')
    search_fields = ('content', 'document__title')
    readonly_fields = ('document', 'chunk_index', 'token_count', 'embedding_model',
                      'embedding_vector_id', 'retrieval_count', 'relevance_score_avg')
    fieldsets = (
        ('Basic Information', {
            'fields': ('document', 'chunk_index', 'token_count')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Embedding Information', {
            'fields': ('embedding_model', 'embedding_vector_id')
        }),
        ('Metadata', {
            'fields': ('metadata', 'page_number')
        }),
        ('Statistics', {
            'fields': ('retrieval_count', 'relevance_score_avg')
        }),
    )
    
    def document_title(self, obj):
        return obj.document.title
    document_title.short_description = 'Document'


@admin.register(VectorIndex)
class VectorIndexAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'knowledge_base_name', 'index_type', 'status',
        'vector_count', 'dimensions'
    )
    list_filter = ('status', 'index_type')
    search_fields = ('name', 'knowledge_base__name')
    readonly_fields = ('vector_count', 'last_updated', 'last_optimized')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'knowledge_base', 'index_type')
        }),
        ('Configuration', {
            'fields': ('collection_name', 'dimensions', 'metric', 'config')
        }),
        ('Connection Information', {
            'fields': ('connection_string', 'api_key')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Statistics', {
            'fields': ('vector_count', 'last_updated', 'last_optimized')
        }),
    )
    
    def knowledge_base_name(self, obj):
        return obj.knowledge_base.name
    knowledge_base_name.short_description = 'Knowledge Base'


class RAGQueryResultInline(admin.TabularInline):
    model = RAGQueryResult
    fields = ('rank', 'chunk_content', 'relevance_score', 'reranking_score', 'is_relevant')
    readonly_fields = ('rank', 'chunk_content', 'relevance_score', 'reranking_score')
    extra = 0
    max_num = 10
    
    def chunk_content(self, obj):
        content = obj.chunk.content
        if len(content) > 100:
            return content[:100] + '...'
        return content
    chunk_content.short_description = 'Content'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RAGQuery)
class RAGQueryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'query_text_short', 'knowledge_base_name', 'status',
        'latency_ms', 'result_count', 'has_feedback'
    )
    list_filter = ('status', 'has_feedback', 'retrieval_strategy', 'reranking_enabled')
    search_fields = ('query_text', 'knowledge_base__name', 'user__email')
    readonly_fields = ('latency_ms', 'embedding_latency_ms', 'retrieval_latency_ms',
                      'reranking_latency_ms', 'embedding_cost', 'reranking_cost', 'total_cost')
    fieldsets = (
        ('Basic Information', {
            'fields': ('query_text', 'knowledge_base', 'user', 'project')
        }),
        ('Configuration', {
            'fields': ('retrieval_strategy', 'similarity_top_k', 'mmr_diversity_bias', 'reranking_enabled')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Performance', {
            'fields': ('latency_ms', 'embedding_latency_ms', 'retrieval_latency_ms', 'reranking_latency_ms')
        }),
        ('Cost', {
            'fields': ('embedding_cost', 'reranking_cost', 'total_cost')
        }),
        ('Feedback', {
            'fields': ('has_feedback', 'feedback_type', 'feedback_text')
        }),
        ('Context', {
            'fields': ('session_id', 'context_session', 'source_type', 'source_id')
        }),
    )
    inlines = [RAGQueryResultInline]
    
    def query_text_short(self, obj):
        if len(obj.query_text) > 50:
            return obj.query_text[:50] + '...'
        return obj.query_text
    query_text_short.short_description = 'Query'
    
    def knowledge_base_name(self, obj):
        return obj.knowledge_base.name
    knowledge_base_name.short_description = 'Knowledge Base'
    
    def result_count(self, obj):
        return obj.results.count()
    result_count.short_description = 'Results'


@admin.register(RAGQueryResult)
class RAGQueryResultAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'query_text', 'rank', 'relevance_score',
        'reranking_score', 'is_relevant'
    )
    list_filter = ('is_relevant',)
    search_fields = ('query__query_text', 'chunk__content')
    readonly_fields = ('query', 'chunk', 'rank', 'relevance_score', 'reranking_score')
    fieldsets = (
        ('Basic Information', {
            'fields': ('query', 'chunk', 'rank')
        }),
        ('Scores', {
            'fields': ('relevance_score', 'reranking_score')
        }),
        ('Feedback', {
            'fields': ('is_relevant', 'feedback_notes')
        }),
    )
    
    def query_text(self, obj):
        text = obj.query.query_text
        if len(text) > 50:
            return text[:50] + '...'
        return text
    query_text.short_description = 'Query'
