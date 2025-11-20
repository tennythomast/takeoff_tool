from django.contrib import admin
from .models import Project, ProjectCollaborator


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client_name', 'status', 'project_type', 'owner', 'created_at')
    list_filter = ('status', 'project_type', 'created_at')
    search_fields = ('title', 'client_name', 'client_company', 'description')
    readonly_fields = ('created_at', 'updated_at', 'started_at')
    fieldsets = (
        ('Project Information', {
            'fields': ('title', 'description', 'project_type', 'status', 'tags')
        }),
        ('Client Information', {
            'fields': ('client_name', 'client_email', 'client_phone', 'client_company')
        }),
        ('Financial', {
            'fields': ('budget',)
        }),
        ('Organization', {
            'fields': ('organization', 'owner', 'location')
        }),
        ('Timeline', {
            'fields': ('started_at', 'deadline', 'created_at', 'updated_at')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectCollaborator)
class ProjectCollaboratorAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('project__title', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
