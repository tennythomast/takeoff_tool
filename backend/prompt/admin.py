from django.contrib import admin
from django.utils.html import format_html
from .models import PromptSession, Prompt


@admin.register(PromptSession)
class PromptSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'workspace', 'creator', 'model_type',
        'status', 'context_session_id', 'started_at', 'completed_at', 'created_at'
    ]
    list_filter = ['status', 'model_type', 'workspace', 'is_active']
    search_fields = ['title', 'description', 'creator__username', 'workspace__name']
    readonly_fields = ['created_at', 'updated_at', 'context_session_id']
    date_hierarchy = 'created_at'
    fieldsets = [
        ('Basic Information', {
            'fields': ('title', 'description', 'workspace', 'creator', 'model_type', 'status')
        }),
        ('Context Integration', {
            'fields': ('context_session_id',)
        }),
        ('Session Lifecycle', {
            'fields': ('started_at', 'completed_at', 'created_at', 'updated_at', 'is_active')
        }),
    ]


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'session_link', 'user', 'truncated_input', 
        'is_starred', 'created_at'
    ]
    list_filter = ['session__status', 'is_starred', 'is_active']
    search_fields = ['input_text', 'user__username', 'session__title']
    readonly_fields = ['created_at', 'updated_at', 'execution_metadata']
    date_hierarchy = 'created_at'
    fieldsets = [
        ('Basic Information', {
            'fields': ('session', 'user', 'input_text', 'is_starred')
        }),
        ('Execution Details', {
            'fields': ('execution_metadata', 'importance_score')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_active')
        }),
    ]
    
    def truncated_input(self, obj):
        """Display truncated input text."""
        if len(obj.input_text) > 50:
            return f"{obj.input_text[:50]}..."
        return obj.input_text
    truncated_input.short_description = 'Input Text'
    
    def session_link(self, obj):
        """Display a link to the related session."""
        url = f"/admin/prompt/promptsession/{obj.session.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.session.title)
    session_link.short_description = 'Session'