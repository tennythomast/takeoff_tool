import json
from decimal import Decimal
from datetime import datetime, date
from django.core.serializers.json import DjangoJSONEncoder

class DecimalEncoder(DjangoJSONEncoder):
    """Custom JSON encoder that handles Decimal objects"""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def safe_json_serialize(data):
    """Safely serialize data to JSON, handling Decimal objects"""
    return json.loads(json.dumps(data, cls=DecimalEncoder))