import logging
from decimal import Decimal
from django.utils import timezone
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)

class BillingManager:
    """Manages billing and cost attribution"""
    
    @staticmethod
    @database_sync_to_async
    def record_usage_for_billing(
        organization,
        provider_slug: str,
        model_name: str,
        cost: Decimal,
        api_key_source: str,
        metadata: dict = None
    ):
        """Record usage for billing purposes"""
        from modelhub.models import ModelMetrics
        
        try:
            # Create detailed billing record
            billing_metadata = {
                'api_key_source': api_key_source,  # 'org' or 'dataelan'
                'billing_category': BillingManager._get_billing_category(organization, api_key_source),
                'provider': provider_slug,
                'model': model_name,
                'timestamp': timezone.now().isoformat(),
                **(metadata or {})
            }
            
            # If using Dataelan keys, flag for internal billing
            if api_key_source == 'dataelan':
                billing_metadata['dataelan_usage'] = True
                billing_metadata['charge_to_dataelan'] = True
                
                # Log for monitoring
                logger.info(f"Dataelan usage: {organization.name if organization else 'Anonymous'} - ${cost} - {provider_slug}:{model_name}")
            
            return billing_metadata
            
        except Exception as e:
            logger.error(f"Error recording billing usage: {e}")
            return {}
    
    @staticmethod
    def _get_billing_category(organization, api_key_source: str) -> str:
        """Determine billing category"""
        if not organization:
            return 'anonymous_free_tier'
        
        if api_key_source == 'org':
            return 'organization_api_key'
        elif api_key_source == 'dataelan':
            # Check organization type
            if hasattr(organization, 'subscription'):
                if organization.subscription and organization.subscription.plan_type != 'free':
                    return 'paid_org_using_dataelan'  # Should be rare/emergency
                else:
                    return 'free_tier_dataelan'
            else:
                return 'free_tier_dataelan'
        
        return 'unknown'

