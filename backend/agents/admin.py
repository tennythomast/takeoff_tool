
from django.contrib import admin
from .models import (
    Agent, AgentTool, AgentParameter, AgentExecution,
    AgentConfigurationStep, AgentOptimization
)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'status', 'creator', 'organization', 'created_at']
    list_filter = ['status', 'category', 'organization']
    search_fields = ['name', 'description']


@admin.register(AgentTool)
class AgentToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'agent', 'tool_type', 'is_required', 'created_at']
    list_filter = ['tool_type', 'is_required']
    search_fields = ['name', 'agent__name']


@admin.register(AgentParameter)
class AgentParameterAdmin(admin.ModelAdmin):
    list_display = ['name', 'agent', 'parameter_type', 'is_required', 'created_at']
    list_filter = ['parameter_type', 'is_required']
    search_fields = ['name', 'agent__name']


@admin.register(AgentExecution)
class AgentExecutionAdmin(admin.ModelAdmin):
    list_display = ['agent', 'user', 'status', 'started_at', 'cost', 'created_at']
    list_filter = ['status']
    search_fields = ['agent__name', 'user__email']


@admin.register(AgentConfigurationStep)
class AgentConfigurationStepAdmin(admin.ModelAdmin):
    list_display = ['agent', 'wizard_completed', 'completed_at', 'created_at']
    list_filter = ['wizard_completed']
    search_fields = ['agent__name']


@admin.register(AgentOptimization)
class AgentOptimizationAdmin(admin.ModelAdmin):
    list_display = ['agent', 'suggestion_type', 'applied', 'created_at']
    list_filter = ['suggestion_type', 'applied']
    search_fields = ['agent__name']