import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from agents.models import AgentResponseCache

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up expired agent response cache entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Delete entries older than specified days (even if not expired)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Always delete expired entries
        expired_query = AgentResponseCache.objects.filter(
            expires_at__lt=timezone.now()
        )
        expired_count = expired_query.count()
        
        self.stdout.write(f"Found {expired_count} expired cache entries")
        
        if not dry_run and expired_count > 0:
            expired_query.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {expired_count} expired cache entries"))
        
        # Delete old entries if days parameter is provided
        if days > 0:
            cutoff_date = timezone.now() - timezone.timedelta(days=days)
            old_query = AgentResponseCache.objects.filter(
                created_at__lt=cutoff_date
            )
            old_count = old_query.count()
            
            self.stdout.write(f"Found {old_count} cache entries older than {days} days")
            
            if not dry_run and old_count > 0:
                old_query.delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {old_count} old cache entries"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No entries were deleted"))
        
        # Report statistics on remaining cache
        remaining = AgentResponseCache.objects.count()
        self.stdout.write(f"Remaining cache entries: {remaining}")
        
        # Report cache hit statistics
        if remaining > 0:
            total_hits = AgentResponseCache.objects.extra(
                select={'total_hits': 'SUM(hit_count)'}
            ).values('total_hits').first()['total_hits']
            
            avg_hits = AgentResponseCache.objects.extra(
                select={'avg_hits': 'AVG(hit_count)'}
            ).values('avg_hits').first()['avg_hits']
            
            total_saved = AgentResponseCache.objects.extra(
                select={'total_saved': 'SUM(cost_saved * hit_count)'}
            ).values('total_saved').first()['total_saved']
            
            self.stdout.write(self.style.SUCCESS(
                f"Cache statistics:\n"
                f"- Total hits: {total_hits}\n"
                f"- Average hits per entry: {avg_hits:.2f}\n"
                f"- Estimated total cost saved: ${total_saved:.2f}"
            ))
