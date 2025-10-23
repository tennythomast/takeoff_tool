# File: backend/modelhub/services/cost_protection.py
# Fixed version with proper Django imports

import logging
from decimal import Decimal
from typing import Tuple, Optional
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db import models  # ADD THIS IMPORT
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CostProtectionManager:
    """Manages cost protection for Dataelan against unexpected API charges"""
    
    # Dataelan protection limits
    DATAELAN_DAILY_LIMIT = Decimal('10.00')      # $10 per day max
    DATAELAN_MONTHLY_LIMIT = Decimal('100.00')   # $100 per month max
    DATAELAN_PER_REQUEST_LIMIT = Decimal('1.00') # $1 per request max
    
    @staticmethod
    @database_sync_to_async
    def check_dataelan_usage_limits(provider_slug: str, estimated_cost: Decimal) -> Tuple[bool, str, dict]:
        """
        Check if request would exceed Dataelan usage limits
        
        Returns:
            tuple: (allowed, reason, usage_stats)
        """
        from modelhub.models import APIKey, ModelMetrics
        
        # Get Dataelan key for this provider
        try:
            dataelan_key = APIKey.objects.filter(
                organization__isnull=True,
                provider__slug=provider_slug,
                is_active=True
            ).first()
            
            if not dataelan_key:
                return False, f"No Dataelan key available for {provider_slug}", {}
            
            # Check per-request limit
            if estimated_cost > CostProtectionManager.DATAELAN_PER_REQUEST_LIMIT:
                return False, f"Request cost ${estimated_cost} exceeds per-request limit ${CostProtectionManager.DATAELAN_PER_REQUEST_LIMIT}", {}
            
            # Check daily usage
            today = timezone.now().date()
            daily_usage = ModelMetrics.objects.filter(
                api_key=dataelan_key,
                timestamp__date=today
            ).aggregate(total=models.Sum('cost'))['total'] or Decimal('0')
            
            if daily_usage + estimated_cost > CostProtectionManager.DATAELAN_DAILY_LIMIT:
                return False, f"Would exceed daily Dataelan limit: ${daily_usage + estimated_cost} > ${CostProtectionManager.DATAELAN_DAILY_LIMIT}", {
                    'daily_used': float(daily_usage),
                    'daily_limit': float(CostProtectionManager.DATAELAN_DAILY_LIMIT)
                }
            
            # Check monthly usage
            start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_usage = ModelMetrics.objects.filter(
                api_key=dataelan_key,
                timestamp__gte=start_of_month
            ).aggregate(total=models.Sum('cost'))['total'] or Decimal('0')
            
            if monthly_usage + estimated_cost > CostProtectionManager.DATAELAN_MONTHLY_LIMIT:
                return False, f"Would exceed monthly Dataelan limit: ${monthly_usage + estimated_cost} > ${CostProtectionManager.DATAELAN_MONTHLY_LIMIT}", {
                    'monthly_used': float(monthly_usage),
                    'monthly_limit': float(CostProtectionManager.DATAELAN_MONTHLY_LIMIT)
                }
            
            # Check API key specific quotas
            if dataelan_key.daily_quota:
                key_daily_usage = ModelMetrics.objects.filter(
                    api_key=dataelan_key,
                    timestamp__date=today
                ).aggregate(total=models.Sum('cost'))['total'] or Decimal('0')
                
                if key_daily_usage + estimated_cost > dataelan_key.daily_quota:
                    return False, f"Would exceed API key daily quota: ${key_daily_usage + estimated_cost} > ${dataelan_key.daily_quota}", {}
            
            if dataelan_key.monthly_quota:
                key_monthly_usage = ModelMetrics.objects.filter(
                    api_key=dataelan_key,
                    timestamp__gte=start_of_month
                ).aggregate(total=models.Sum('cost'))['total'] or Decimal('0')
                
                if key_monthly_usage + estimated_cost > dataelan_key.monthly_quota:
                    return False, f"Would exceed API key monthly quota: ${key_monthly_usage + estimated_cost} > ${dataelan_key.monthly_quota}", {}
            
            # All checks passed
            usage_stats = {
                'daily_used': float(daily_usage),
                'daily_limit': float(dataelan_key.daily_quota or CostProtectionManager.DATAELAN_DAILY_LIMIT),
                'monthly_used': float(monthly_usage),
                'monthly_limit': float(dataelan_key.monthly_quota or CostProtectionManager.DATAELAN_MONTHLY_LIMIT),
                'estimated_cost': float(estimated_cost)
            }
            
            return True, "Within Dataelan limits", usage_stats
            
        except Exception as e:
            logger.error(f"Error checking Dataelan limits: {e}")
            return False, f"Error checking limits: {str(e)}", {}
    
    @staticmethod
    @database_sync_to_async
    def enforce_organization_api_key_requirement(organization) -> Tuple[bool, str]:
        """
        Enforce that paid organizations must use their own API keys
        
        Returns:
            tuple: (can_use_dataelan, reason)
        """
        if not organization:
            # Anonymous users can use Dataelan keys (free tier)
            return True, "Anonymous user - free tier access"
        
        # Check organization's plan/tier
        if hasattr(organization, 'subscription') and organization.subscription:
            if organization.subscription.plan_type in ['paid', 'professional', 'enterprise']:
                # Paid organizations must use their own keys
                from modelhub.models import APIKey
                
                org_keys = APIKey.objects.filter(
                    organization=organization,
                    is_active=True
                ).exists()
                
                if not org_keys:
                    return False, "Paid organizations must configure their own API keys"
                
                return False, "Paid organizations should use their own API keys"
        
        # Free tier can use Dataelan keys with limits
        return True, "Free tier - limited Dataelan access allowed"