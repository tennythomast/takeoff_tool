from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Workspace, WorkspaceCollaborator


class WorkspaceCollaboratorInline(admin.TabularInline):
    model = WorkspaceCollaborator
    extra = 1
    raw_id_fields = ('user',)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'owner', 'workspace_type', 'is_system_workspace', 'status', 'is_active', 'created_at')
    list_filter = ('status', 'is_active', 'organization', 'workspace_type', 'is_system_workspace')
    search_fields = ('name', 'description', 'owner__email')
    raw_id_fields = ('owner', 'organization')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WorkspaceCollaboratorInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'organization', 'owner', 'status')
        }),
        (_('Workspace Settings'), {
            'fields': ('workspace_type', 'is_system_workspace', 'metadata')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'started_at')
        }),
    )

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(WorkspaceCollaborator)
class WorkspaceCollaboratorAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('workspace__name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('workspace', 'user')
    def soft_delete(self, request, queryset):
        for obj in queryset:
            obj.soft_delete()
    soft_delete.short_description = _('Soft delete selected %(verbose_name_plural)s')

    def restore(self, request, queryset):
        for obj in queryset:
            obj.restore()
    restore.short_description = _('Restore selected %(verbose_name_plural)s')