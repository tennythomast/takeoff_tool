# apps/permissions/services.py
from typing import Dict, Any
from .models import Role, Integration, UserIntegrationPermission
from apps.integrations.services import IntegrationService

class PermissionCalculationService:
    """Handles the RBAC + Smart Defaults + User Choice logic"""
    
    def calculate_effective_permissions(self, user, integration: Integration) -> Dict[str, Any]:
        """Main permission calculation method"""
        
        # Step 1: Get role constraints (RBAC layer)
        role_constraints = self._get_role_constraints(user, integration)
        
        # Step 2: Get external permissions (Smart defaults input)
        external_permissions = self._get_external_permissions(user, integration)
        
        # Step 3: Calculate smart defaults
        smart_defaults = self._calculate_smart_defaults(
            external_permissions, 
            role_constraints, 
            integration
        )
        
        # Step 4: Get user choice
        user_permission, created = UserIntegrationPermission.objects.get_or_create(
            user=user,
            integration=integration,
            defaults={
                'role_constraints': role_constraints,
                'external_permissions': external_permissions,
                'calculated_defaults': smart_defaults
            }
        )
        
        # Step 5: Apply user choice
        effective_permissions = self._apply_user_choice(
            user_permission, 
            smart_defaults, 
            role_constraints
        )
        
        # Step 6: Update and return
        user_permission.effective_permissions = effective_permissions
        user_permission.save()
        
        # Step 7: Log the calculation
        self._log_calculation(user_permission, {
            'role_constraints': role_constraints,
            'external_permissions': external_permissions,
            'smart_defaults': smart_defaults,
            'user_choice': user_permission.user_choice,
            'effective_permissions': effective_permissions
        })
        
        return effective_permissions
    
    def _get_role_constraints(self, user, integration: Integration) -> Dict[str, Any]:
        """Get RBAC constraints from user's role"""
        if not hasattr(user, 'role') or not user.role:
            return self._get_default_role_constraints()
        
        role = user.role
        
        # Check if integration is allowed
        if integration.name not in role.allowed_integrations:
            return {'access': 'denied', 'reason': 'integration_not_allowed'}
        
        # Get role-specific constraints
        constraints = {
            'max_data_scope': role.max_data_scope,
            'prohibited_actions': role.prohibited_actions,
            'integration_specific': role.get_integration_constraints(integration.name)
        }
        
        return constraints
    
    def _get_external_permissions(self, user, integration: Integration) -> Dict[str, Any]:
        """Get user's actual permissions in external system"""
        integration_service = IntegrationService(integration.name)
        
        try:
            # Get user's actual Jira/Slack/etc permissions
            external_perms = integration_service.get_user_permissions(user)
            return external_perms
        except Exception as e:
            # Fallback to safe defaults if API call fails
            return {'access': 'limited', 'error': str(e)}
    
    def _calculate_smart_defaults(self, external_permissions: Dict, role_constraints: Dict, integration: Integration) -> Dict[str, Any]:
        """Calculate smart defaults from external permissions + role constraints"""
        
        # If role denies access, return denial
        if role_constraints.get('access') == 'denied':
            return role_constraints
        
        # Get base smart defaults for this integration
        base_defaults = integration.default_permissions.copy()
        
        # Apply role-specific defaults if available
        if hasattr(integration, 'role_defaults') and role_constraints.get('role_name'):
            role_specific = integration.role_defaults.get(role_constraints['role_name'], {})
            base_defaults.update(role_specific)
        
        # Intersect with external permissions (user can't have more than they actually have)
        smart_defaults = self._intersect_permissions(base_defaults, external_permissions)
        
        # Apply role constraints (user can't exceed role boundaries)
        constrained_defaults = self._apply_role_constraints(smart_defaults, role_constraints)
        
        return constrained_defaults
    
    def _apply_user_choice(self, user_permission: UserIntegrationPermission, smart_defaults: Dict, role_constraints: Dict) -> Dict[str, Any]:
        """Apply user's choice to smart defaults"""
        
        choice = user_permission.user_choice
        
        if choice == 'minimal':
            return self._get_minimal_permissions(smart_defaults)
        
        elif choice == 'smart_default':
            return smart_defaults
        
        elif choice == 'enhanced':
            enhanced = self._get_enhanced_permissions(smart_defaults, user_permission.external_permissions)
            # Still constrain by role
            return self._apply_role_constraints(enhanced, role_constraints)
        
        elif choice == 'custom':
            custom = user_permission.custom_permissions
            # Validate custom permissions don't exceed role constraints
            return self._apply_role_constraints(custom, role_constraints)
        
        return smart_defaults
    
    def _intersect_permissions(self, perms1: Dict, perms2: Dict) -> Dict[str, Any]:
        """Intersect two permission sets (return minimum)"""
        # Implementation depends on your permission structure
        # This is where the smart permission logic lives
        pass
    
    def _apply_role_constraints(self, permissions: Dict, constraints: Dict) -> Dict[str, Any]:
        """Ensure permissions don't exceed role boundaries"""
        # Implementation depends on your role constraint structure
        pass
    
    def _log_calculation(self, user_permission: UserIntegrationPermission, calculation_data: Dict):
        """Log permission calculation for audit trail"""
        from .models import PermissionCalculationLog
        
        PermissionCalculationLog.objects.create(
            user_permission=user_permission,
            calculation_input=calculation_data,
            calculation_output=user_permission.effective_permissions,
            calculation_reason=f"Calculated for user {user_permission.user.id} with choice '{user_permission.user_choice}'"
        )