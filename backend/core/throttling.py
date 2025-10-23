from rest_framework.throttling import UserRateThrottle
from core.models import Organization


class UserTierRateThrottle(UserRateThrottle):
    """Rate throttle based on user's organization tier."""
    
    TIER_RATES = {
        Organization.OrgType.SOLO: '100/minute',    # Free tier
        Organization.OrgType.TEAM: '1000/minute',   # Pro tier
        Organization.OrgType.ENTERPRISE: '5000/minute',  # Enterprise tier
    }
    
    def get_rate(self):
        """Get the rate based on user's organization tier."""
        return '100/minute'  # Default rate
    
    def allow_request(self, request, view):
        """Check if request should be allowed."""
        self.request = request
        
        if not request.user.is_authenticated:
            self.rate = '50/minute'  # Default rate for unauthenticated users
        else:
            org_type = request.user.default_org.org_type
            self.rate = self.TIER_RATES.get(org_type, '100/minute')  # Default to free tier rate
        
        return super().allow_request(request, view)
