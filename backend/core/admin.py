from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import User, Organization, Membership


def soft_delete_selected(modeladmin, request, queryset):
    queryset.update(is_active=False, deactivated_at=timezone.now())
soft_delete_selected.short_description = _('Deactivate selected items')


def restore_selected(modeladmin, request, queryset):
    queryset.update(is_active=True, deactivated_at=None)
restore_selected.short_description = _('Restore selected items')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'org_type', 'api_key_strategy', 'monthly_ai_budget', 'default_optimization_strategy', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'api_key_strategy', 'default_optimization_strategy', 'ai_usage_alerts')
    search_fields = ('name', 'slug')
    ordering = ('name',)
    actions = [soft_delete_selected, restore_selected]
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'org_type', 'is_active')}),
        ('API & Model Settings', {'fields': ('api_key_strategy', 'monthly_ai_budget', 'ai_usage_alerts', 'default_optimization_strategy')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'deactivated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'get_full_name', 'is_staff', 'is_active', 'is_verified', 'last_login_ip', 'deactivated_at')
    list_filter = ('is_staff', 'is_active', 'is_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    actions = [soft_delete_selected, restore_selected]

    def get_queryset(self, request):
        return self.model.all_objects.all()
    
    def get_full_name(self, obj):
        return obj.full_name
    get_full_name.short_description = 'Name'
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'last_login_ip', 'created_at', 'updated_at', 'deactivated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login_ip')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role', 'created_at')
    list_filter = ('role', 'organization')
    search_fields = ('user__email', 'user__name', 'organization__name')
    raw_id_fields = ('user', 'organization')
    ordering = ('-created_at',)
