from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Monitor Dataelan API usage and send alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alert-threshold',
            type=float,
            default=0.8,
            help='Alert when usage exceeds this percentage of quota',
        )

    def handle(self, *args, **options):
        """Monitor Dataelan usage and send alerts"""
        from modelhub.models import APIKey, ModelMetrics
        
        threshold = options['alert_threshold']
        
        # Get all Dataelan keys
        dataelan_keys = APIKey.objects.filter(
            organization__isnull=True,
            is_active=True
        )
        
        for key in dataelan_keys:
            # Check daily usage
            today = timezone.now().date()
            daily_usage = ModelMetrics.objects.filter(
                api_key=key,
                timestamp__date=today
            ).aggregate(total=models.Sum('cost'))['total'] or Decimal('0')
            
            # Check monthly usage
            start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_usage = ModelMetrics.objects.filter(
                api_key=key,
                timestamp__gte=start_of_month
            ).aggregate(total=models.Sum('cost'))['total'] or Decimal('0')
            
            # Check thresholds
            if key.daily_quota and daily_usage >= (key.daily_quota * Decimal(str(threshold))):
                self.stdout.write(
                    self.style.WARNING(
                        f'🚨 {key.provider.name} approaching daily limit: '
                        f'${daily_usage}/${key.daily_quota} ({daily_usage/key.daily_quota*100:.1f}%)'
                    )
                )
            
            if key.monthly_quota and monthly_usage >= (key.monthly_quota * Decimal(str(threshold))):
                self.stdout.write(
                    self.style.ERROR(
                        f'🚨 {key.provider.name} approaching monthly limit: '
                        f'${monthly_usage}/${key.monthly_quota} ({monthly_usage/key.monthly_quota*100:.1f}%)'
                    )
                )
            
            # Display current usage
            self.stdout.write(
                f'📊 {key.provider.name}: '
                f'Daily ${daily_usage}/${key.daily_quota or "∞"}, '
                f'Monthly ${monthly_usage}/${key.monthly_quota or "∞"}'
            )