from rest_framework import serializers
from .models import (
    Agent, AgentTool, AgentParameter, AgentExecution,
    AgentConfigurationStep, AgentOptimization, AgentToolExecution,
    AgentCacheAnalytics
)


class AgentToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTool
        fields = [
            'id', 'name', 'description', 'tool_type', 
            'config', 'is_required', 'created_at',
            # Webhook fields
            'webhook_url', 'webhook_method', 'webhook_headers',
            'webhook_auth_type', 'webhook_auth_config',
            # Schema validation fields
            'input_schema', 'output_schema',
            # Smart recommendation fields
            'match_percentage', 'performance_impact', 'recommendation_reason'
        ]
        read_only_fields = ['id', 'created_at', 'match_percentage', 'performance_impact', 'recommendation_reason']


class AgentParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentParameter
        fields = [
            'id', 'name', 'description', 'parameter_type',
            'default_value', 'is_required', 'options', 'validation',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AgentListSerializer(serializers.ModelSerializer):
    execution_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'category', 'status',
            'icon', 'is_public', 'is_template', 'created_at',
            'execution_count', 'metadata', 'primary_role',
            'capability_level', 'memory_type',
            'predicted_accuracy', 'predicted_response_time'
        ]
        read_only_fields = ['id', 'created_at', 'execution_count',
                          'capability_level', 'memory_type',
                          'predicted_accuracy', 'predicted_response_time']
    
    def get_execution_count(self, obj):
        return obj.get_execution_count()


class AgentDetailSerializer(serializers.ModelSerializer):
    tools = AgentToolSerializer(many=True, read_only=True)
    parameters = AgentParameterSerializer(many=True, read_only=True)
    execution_count = serializers.SerializerMethodField()
    average_execution_time = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    workspace_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'instructions', 'category',
            'status', 'icon', 'routing_rule', 'prompt_session',
            'creator', 'creator_name', 'organization', 'organization_name',
            'workspace', 'workspace_name', 'is_public', 'is_template',
            'parent_agent', 'config', 'metadata', 'tools', 'parameters',
            'created_at', 'updated_at', 'execution_count', 'average_execution_time',
            # Smart configuration fields
            'primary_role', 'target_users', 'problem_statement',
            'communication_style', 'output_format', 'quality_preference',
            # Capability settings
            'capabilities', 'capability_level',
            # Memory settings
            'memory_type', 'memory_window', 'memory_config',
            # Performance prediction fields
            'predicted_accuracy', 'predicted_response_time', 'predicted_cost_per_1k'
        ]
        read_only_fields = [
            'id', 'creator', 'organization', 'created_at', 'updated_at',
            'execution_count', 'average_execution_time', 'creator_name',
            'organization_name', 'workspace_name', 'predicted_accuracy',
            'predicted_response_time', 'predicted_cost_per_1k'
        ]
    
    def get_execution_count(self, obj):
        return obj.get_execution_count()
    
    def get_average_execution_time(self, obj):
        return obj.get_average_execution_time()
    
    def get_creator_name(self, obj):
        return obj.creator.full_name if obj.creator else None
    
    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None
    
    def get_workspace_name(self, obj):
        return obj.workspace.name if obj.workspace else None


class AgentCreateSerializer(serializers.ModelSerializer):
    tools = AgentToolSerializer(many=True, required=False)
    parameters = AgentParameterSerializer(many=True, required=False)
    
    class Meta:
        model = Agent
        fields = [
            'name', 'description', 'instructions', 'category',
            'status', 'icon', 'routing_rule', 'workspace',
            'is_public', 'is_template', 'config', 'tools', 'parameters',
            # Smart configuration fields
            'primary_role', 'target_users', 'problem_statement',
            'communication_style', 'output_format', 'quality_preference',
            # Capability settings
            'capabilities', 'capability_level',
            # Memory settings
            'memory_type', 'memory_window', 'memory_config'
        ]
    
    def create(self, validated_data):
        tools_data = validated_data.pop('tools', [])
        parameters_data = validated_data.pop('parameters', [])
        
        # Get the current user and organization
        request = self.context.get('request')
        user = request.user
        
        # Get organization using the property we added to the User model
        organization = user.organization
        if not organization:
            raise serializers.ValidationError({
                'organization': 'User does not belong to any organization. Please join or create an organization first.'
            })
            
        # Check if user has permission to create agents in this organization
        # Assuming MEMBER role is sufficient for agent creation, adjust as needed
        if not user.has_org_permission(organization, min_role='MEMBER'):
            raise serializers.ValidationError({
                'permission': f'You do not have sufficient permissions in {organization.name} to create agents.'
            })
        
        # Create the agent
        agent = Agent.objects.create(
            creator=user,
            organization=organization,
            **validated_data
        )
        
        # Create tools
        for tool_data in tools_data:
            AgentTool.objects.create(agent=agent, **tool_data)
        
        # Create parameters
        for param_data in parameters_data:
            AgentParameter.objects.create(agent=agent, **param_data)
        
        return agent


class AgentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = [
            'name', 'description', 'instructions', 'category',
            'status', 'icon', 'routing_rule', 'workspace',
            'is_public', 'is_template', 'config',
            # Smart configuration fields
            'primary_role', 'target_users', 'problem_statement',
            'communication_style', 'output_format', 'quality_preference',
            # Capability settings
            'capabilities', 'capability_level',
            # Memory settings
            'memory_type', 'memory_window', 'memory_config'
        ]


class AgentToolCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTool
        fields = [
            'name', 'description', 'tool_type', 'config', 'is_required',
            # Webhook fields
            'webhook_url', 'webhook_method', 'webhook_headers',
            'webhook_auth_type', 'webhook_auth_config',
            # Schema validation fields
            'input_schema', 'output_schema'
        ]


class AgentParameterCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentParameter
        fields = [
            'name', 'description', 'parameter_type',
            'default_value', 'is_required', 'options', 'validation'
        ]


class AgentExecutionSerializer(serializers.ModelSerializer):
    agent_name = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    model_name = serializers.SerializerMethodField()
    tool_executions = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentExecution
        fields = [
            'id', 'agent', 'agent_name', 'user', 'user_name',
            'status', 'input_data', 'output_data', 'model', 'model_name',
            'tokens_used', 'cost', 'execution_time', 'tool_executions',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']
    
    def get_agent_name(self, obj):
        return obj.agent.name if obj.agent else None
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None
    
    def get_model_name(self, obj):
        return obj.model.name if obj.model else None
        
    def get_tool_executions(self, obj):
        # Return a summary of tool executions
        tool_executions = obj.tool_executions.all()
        if not tool_executions:
            return []
            
        return [{
            'id': te.id,
            'tool_name': te.tool.name if te.tool else None,
            'tool_type': te.tool.get_tool_type_display() if te.tool else None,
            'status': te.status,
            'status_display': te.get_status_display(),
            'execution_time': te.execution_time,
            'created_at': te.created_at
        } for te in tool_executions]


class AgentConfigurationStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentConfigurationStep
        fields = [
            'id', 'agent', 'step_1_completed', 'step_2_completed',
            'step_3_completed', 'step_4_completed', 'wizard_completed',
            'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentOptimizationSerializer(serializers.ModelSerializer):
    suggestion_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentOptimization
        fields = [
            'id', 'agent', 'suggestion_type', 'suggestion_type_display',
            'suggestion_text', 'estimated_impact', 'applied',
            'applied_at', 'actual_impact', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'suggestion_type_display']
    
    def get_suggestion_type_display(self, obj):
        return obj.get_suggestion_type_display()


class AgentToolExecutionSerializer(serializers.ModelSerializer):
    tool_name = serializers.SerializerMethodField()
    tool_type = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentToolExecution
        fields = [
            'id', 'agent_execution', 'tool', 'tool_name', 'tool_type',
            'status', 'status_display', 'input_data', 'output_data',
            'error_message', 'execution_time', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_tool_name(self, obj):
        return obj.tool.name if obj.tool else None
    
    def get_tool_type(self, obj):
        return obj.tool.get_tool_type_display() if obj.tool else None
    
    def get_status_display(self, obj):
        return obj.get_status_display()


class AgentExecuteSerializer(serializers.Serializer):
    input_data = serializers.JSONField(required=False)
    async_execution = serializers.BooleanField(default=False)
    enable_tools = serializers.BooleanField(default=True)
    use_cache = serializers.BooleanField(default=True, help_text="Whether to use response caching")


class AgentCacheAnalyticsSerializer(serializers.ModelSerializer):
    hit_rate = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentCacheAnalytics
        fields = [
            'id', 'agent', 'agent_name', 'total_requests', 'cache_hits', 
            'cache_misses', 'total_cost_saved', 'hit_rate', 'last_updated'
        ]
        read_only_fields = fields
    
    def get_hit_rate(self, obj):
        return f"{obj.hit_rate():.2f}%"
    
    def get_agent_name(self, obj):
        return obj.agent.name if obj.agent else None
