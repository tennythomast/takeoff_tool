from django.contrib import admin
from django.utils.html import format_html
from .models import Provider, Model, APIKey, RoutingRule, RoutingRuleModel, ModelMetrics


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'supports_embeddings','supports_vision', 'website_link']
    list_filter = ['status', 'supports_embeddings','supports_vision']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

    def website_link(self, obj):
        if obj.website:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.website, obj.website)
        return '-'
    website_link.short_description = 'Website'


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'model_type', 'version', 'status', 'embedding_dimensions', 'cost_display']
    list_filter = ['provider', 'model_type', 'status']
    search_fields = ['name', 'version']
    readonly_fields = ['created_at', 'updated_at']

    def cost_display(self, obj):
        return f'${obj.cost_input}/{obj.cost_output} per 1K tokens'
    cost_display.short_description = 'Cost (Input/Output)'


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['label', 'provider', 'organization', 'is_default', 'quota_display']
    list_filter = ['provider', 'organization', 'is_default']
    search_fields = ['label', 'organization__name']
    readonly_fields = ['created_at', 'updated_at']

    def quota_display(self, obj):
        daily = f'${obj.daily_quota}/day' if obj.daily_quota else 'No daily limit'
        monthly = f'${obj.monthly_quota}/month' if obj.monthly_quota else 'No monthly limit'
        return f'{daily}, {monthly}'
    quota_display.short_description = 'Quotas'


class RoutingRuleModelInline(admin.TabularInline):
    model = RoutingRuleModel
    extra = 1


@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'model_type', 'priority', 'is_active', 'models_count']
    list_filter = ['model_type', 'organization', 'is_active']
    search_fields = ['name', 'description']
    inlines = [RoutingRuleModelInline]
    readonly_fields = ['created_at', 'updated_at']

    def models_count(self, obj):
        return obj.models.count()
    models_count.short_description = 'Models'


@admin.register(ModelMetrics)
class ModelMetricsAdmin(admin.ModelAdmin):
    list_display = ['model', 'organization', 'timestamp', 'status', 'latency_ms','image_count', 'cost']
    list_filter = ['model', 'organization', 'status', 'timestamp']
    search_fields = ['model__name', 'organization__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'timestamp'
