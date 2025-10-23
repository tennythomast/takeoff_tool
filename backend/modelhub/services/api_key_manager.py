import logging
from typing import Optional, Tuple
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)

class APIKeyManager:
    """Manages API key selection based on organization strategy"""
    
    @staticmethod
    @database_sync_to_async
    def get_api_key_for_request(organization, provider_slug: str) -> Tuple[Optional[str], str]:
        """
        Get API key for request based on organization strategy
        
        Returns:
            tuple: (api_key, source) where source is 'org' or 'dataelan' or None
        """
        from modelhub.models import APIKey
        
        if not organization:
            # No organization - use Dataelan keys only
            return APIKeyManager._get_dataelan_key(provider_slug)
        
        strategy = organization.api_key_strategy
        
        if strategy == 'org_only':
            # Organization keys only - no fallback
            return APIKeyManager._get_org_key(organization, provider_slug)
            
        elif strategy == 'org_with_dataelan_fallback':
            # Try organization key first, fallback to Dataelan
            api_key, source = APIKeyManager._get_org_key(organization, provider_slug)
            if api_key:
                return api_key, source
            else:
                logger.info(f"No org key for {provider_slug}, falling back to Dataelan")
                return APIKeyManager._get_dataelan_key(provider_slug)
                
        elif strategy == 'dataelan_only':
            # Dataelan keys only (free tier)
            return APIKeyManager._get_dataelan_key(provider_slug)
        
        else:
            logger.error(f"Unknown API key strategy: {strategy}")
            return None, None
    
    @staticmethod
    def _get_org_key(organization, provider_slug: str) -> Tuple[Optional[str], str]:
        """Get organization-specific API key"""
        from modelhub.models import APIKey
        
        try:
            api_key = APIKey.objects.filter(
                organization=organization,
                provider__slug=provider_slug,
                is_active=True
            ).first()
            
            if api_key:
                # Update last used timestamp
                api_key.last_used_at = timezone.now()
                api_key.save(update_fields=['last_used_at'])
                return api_key.key, 'org'
            else:
                return None, None
                
        except Exception as e:
            logger.error(f"Error getting org API key: {e}")
            return None, None
    
    @staticmethod
    def _get_dataelan_key(provider_slug: str) -> Tuple[Optional[str], str]:
        """Get Dataelan system API key"""
        from modelhub.models import APIKey
        
        try:
            # Get Dataelan system key (organization=None)
            api_key = APIKey.objects.filter(
                organization__isnull=True,
                provider__slug=provider_slug,
                is_active=True
            ).first()
            
            if api_key:
                # Update last used timestamp
                api_key.last_used_at = timezone.now()
                api_key.save(update_fields=['last_used_at'])
                return api_key.key, 'dataelan'
            else:
                logger.warning(f"No Dataelan key available for {provider_slug}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error getting Dataelan API key: {e}")
            return None, None
    
    @staticmethod
    @database_sync_to_async
    def check_budget_limits(organization, estimated_cost: float) -> Tuple[bool, str]:
        """
        Check if request would exceed budget limits
        
        Returns:
            tuple: (allowed, reason)
        """
        if not organization or not organization.monthly_ai_budget:
            return True, "No budget limit set"
        
        current_spend = organization.get_current_month_ai_spend()
        projected_spend = current_spend + Decimal(str(estimated_cost))
        
        if projected_spend > organization.monthly_ai_budget:
            return False, f"Would exceed monthly budget of ${organization.monthly_ai_budget}"
        
        # Check if approaching budget (90% threshold)
        if projected_spend > (organization.monthly_ai_budget * Decimal('0.9')):
            logger.warning(f"Organization {organization.name} approaching budget limit")
        
        return True, "Within budget"
