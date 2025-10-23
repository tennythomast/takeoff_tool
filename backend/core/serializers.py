from django.contrib.auth import get_user_model
from rest_framework import serializers
from decimal import Decimal
from .models import Organization, Membership

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the users object"""
    name = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()
    current_role = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'password', 'first_name', 'last_name', 'name',
            'organization', 'organizations', 'current_role', 'is_verified'
        )
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 5},
            'id': {'read_only': True},
            'first_name': {'required': True},
            'last_name': {'required': False}
        }
    
    def get_name(self, obj):
        """Return the full name of the user using the model's full_name property"""
        return obj.full_name
    
    def get_organization(self, obj):
        """Return the user's current organization"""
        org = obj.organization
        if org:
            return {
                'id': org.id,
                'name': org.name,
                'slug': org.slug,
                'org_type': org.org_type
            }
        return None
    
    def get_organizations(self, obj):
        """Return the user's organization with role (as a list for backward compatibility)"""
        membership = obj.memberships.select_related('organization').filter(
            organization__is_active=True
        ).first()
        
        if membership:
            return [
                {
                    'id': membership.organization.id,
                    'name': membership.organization.name,
                    'slug': membership.organization.slug,
                    'org_type': membership.organization.org_type,
                    'role': membership.role,
                    'is_default': True  # Always true since users can only have one organization
                }
            ]
        return []
    
    def get_current_role(self, obj):
        """Return user's role in their current organization"""
        org = obj.organization
        if org:
            membership = obj.get_membership(org)
            return membership.role if membership else None
        return None
    
    def create(self, validated_data):
        """Create a new user with encrypted password and return it"""
        return User.objects.create_user(**validated_data)


class MembershipSerializer(serializers.ModelSerializer):
    """Serializer for Membership model"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = Membership
        fields = [
            'id', 'user', 'organization', 'role', 'created_at',
            'user_name', 'user_email', 'organization_name'
        ]
        read_only_fields = ['id', 'created_at']


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""
    current_month_spend = serializers.SerializerMethodField()
    budget_status = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'org_type', 'is_active', 
            'api_key_strategy', 'monthly_ai_budget', 'ai_usage_alerts',
            'default_optimization_strategy', 'current_month_spend',
            'budget_status', 'member_count', 'user_role'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'current_month_spend', 
            'budget_status', 'member_count', 'user_role'
        ]
    
    def get_current_month_spend(self, obj):
        """Get current month AI spending"""
        try:
            return float(obj.get_current_month_ai_spend())
        except Exception:
            return 0.0
    
    def get_budget_status(self, obj):
        """Get budget status information"""
        if not obj.monthly_ai_budget:
            return {
                'has_budget': False,
                'message': 'No budget set'
            }
        
        current_spend = obj.get_current_month_ai_spend()
        percentage = (current_spend / obj.monthly_ai_budget) * 100 if obj.monthly_ai_budget else 0
        
        status = 'normal'
        if percentage >= 90:
            status = 'critical'
        elif percentage >= 75:
            status = 'warning'
        
        return {
            'has_budget': True,
            'budget': float(obj.monthly_ai_budget),
            'current_spend': float(current_spend),
            'remaining': float(obj.monthly_ai_budget - current_spend),
            'percentage': float(percentage),
            'status': status
        }
    
    def get_member_count(self, obj):
        """Get number of active members in the organization"""
        return obj.memberships.filter(user__is_active=True).count()
    
    def get_user_role(self, obj):
        """Get the current user's role in this organization"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = request.user.get_membership(obj)
            return membership.role if membership else None
        return None


class SwitchOrganizationSerializer(serializers.Serializer):
    """
    This serializer is maintained for backward compatibility.
    Since users can only belong to one organization, this serializer
    simply validates that the user belongs to the specified organization.
    """
    organization_id = serializers.UUIDField()
    
    def validate_organization_id(self, value):
        """Validate that the user belongs to this organization"""
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        try:
            organization = Organization.objects.get(id=value, is_active=True)
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Organization not found or inactive")
        
        # Get the user's organization
        user_org = user.organization
        
        # Check if the requested organization matches the user's organization
        if not user_org or user_org.id != organization.id:
            raise serializers.ValidationError("You can only belong to one organization")
        
        return value
    
    def save(self):
        """This method is maintained for backward compatibility"""
        request = self.context.get('request')
        user = request.user
        
        # Since users can only belong to one organization, there's nothing to switch
        # Just return the user for backward compatibility
        return user