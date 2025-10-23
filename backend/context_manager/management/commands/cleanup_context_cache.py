# context_manager/management/commands/cleanup_context_cache.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import asyncio

from ...services.cache_service import SummaryCacheService
from ...services.storage_service import FullContextStorageService


class Command(BaseCommand):
    help = 'Clean up expired context cache entries and low-importance content'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--organization-id',
            type=str,
            help='Specific organization ID to clean up (optional)',
        )
        parser.add_argument(
            '--days-old',
            type=int,
            default=30,
            help='Clean up entries older than this many days',
        )
        parser.add_argument(
            '--importance-threshold',
            type=float,
            default=0.3,
            help='Clean up entries below this importance score',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
    
    def handle(self, *args, **options):
        organization_id = options.get('organization_id')
        days_old = options['days_old']
        importance_threshold = options['importance_threshold']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f"Starting context cache cleanup...")
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No actual cleanup will be performed")
            )
        
        # Run async cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            cache_cleaned, storage_cleaned = loop.run_until_complete(
                self._run_cleanup(organization_id, days_old, importance_threshold, dry_run)
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleanup completed:\n"
                    f"  - Cache entries cleaned: {cache_cleaned}\n"
                    f"  - Storage entries cleaned: {storage_cleaned}"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Cleanup failed: {str(e)}")
            )
        finally:
            loop.close()
    
    async def _run_cleanup(self, organization_id, days_old, importance_threshold, dry_run):
        cache_service = SummaryCacheService()
        storage_service = FullContextStorageService()
        
        cache_cleaned = 0
        storage_cleaned = 0
        
        if not dry_run:
            # Clean up expired cache entries
            cache_cleaned = await cache_service.cleanup_expired_cache(organization_id)
            
            # Clean up low-importance storage entries
            if organization_id:
                storage_cleaned = await storage_service.cleanup_low_importance_entries(
                    organization_id, importance_threshold, days_old
                )
            else:
                self.stdout.write("Storage cleanup requires --organization-id")
        else:
            # Dry run - just count what would be cleaned
            from ...models import ContextSummaryCache, ContextEntry
            
            cache_query = ContextSummaryCache.objects.filter(
                expires_at__lt=timezone.now()
            )
            if organization_id:
                cache_query = cache_query.filter(organization_id=organization_id)
            
            cache_cleaned = await cache_query.acount()
            
            if organization_id:
                cutoff_date = timezone.now() - timedelta(days=days_old)
                storage_query = ContextEntry.objects.filter(
                    organization_id=organization_id,
                    importance_score__lt=importance_threshold,
                    created_at__lt=cutoff_date,
                    is_starred=False
                )
                storage_cleaned = await storage_query.acount()
        
        return cache_cleaned, storage_cleaned


# context_manager/management/commands/analyze_context_performance.py

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
import asyncio

from ...services.cache_service import SummaryCacheService
from ...services.storage_service import FullContextStorageService
from ...models import ContextSession, ContextEntry, ContextSummaryCache, ContextTransition


class Command(BaseCommand):
    help = 'Analyze context management performance and generate report'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--organization-id',
            type=str,
            help='Specific organization ID to analyze (optional)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Analyze data from the last N days',
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file for the report (optional)',
        )
    
    def handle(self, *args, **options):
        organization_id = options.get('organization_id')
        days = options['days']
        output_file = options.get('output_file')
        
        self.stdout.write(
            self.style.SUCCESS(f"Analyzing context performance for last {days} days...")
        )
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            report = loop.run_until_complete(
                self._generate_report(organization_id, days)
            )
            
            # Display report
            self._display_report(report)
            
            # Save to file if requested
            if output_file:
                self._save_report(report, output_file)
                self.stdout.write(
                    self.style.SUCCESS(f"Report saved to {output_file}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Analysis failed: {str(e)}")
            )
        finally:
            loop.close()
    
    async def _generate_report(self, organization_id, days):
        since_date = timezone.now() - timedelta(days=days)
        
        # Basic metrics
        sessions_query = ContextSession.objects.filter(created_at__gte=since_date)
        entries_query = ContextEntry.objects.filter(created_at__gte=since_date)
        cache_query = ContextSummaryCache.objects.filter(created_at__gte=since_date)
        transitions_query = ContextTransition.objects.filter(created_at__gte=since_date)
        
        if organization_id:
            sessions_query = sessions_query.filter(organization_id=organization_id)
            entries_query = entries_query.filter(organization_id=organization_id)
            cache_query = cache_query.filter(organization_id=organization_id)
            transitions_query = transitions_query.filter(organization_id=organization_id)
        
        # Session metrics
        total_sessions = await sessions_query.acount()
        active_sessions = await sessions_query.filter(
            last_activity_at__gte=since_date
        ).acount()
        
        # Entry metrics
        total_entries = await entries_query.acount()
        avg_importance = 0
        total_cost = 0
        
        if total_entries > 0:
            entry_stats = await entries_query.aaggregate(
                avg_importance=Avg('importance_score'),
                total_cost=Sum('total_cost')
            )
            avg_importance = entry_stats['avg_importance'] or 0
            total_cost = entry_stats['total_cost'] or 0
        
        # Cache metrics
        cache_service = SummaryCacheService()
        if organization_id:
            cache_metrics = await cache_service.get_cache_metrics(organization_id, days)
        else:
            # Global metrics would need aggregation across all orgs
            cache_metrics = None
        
        # Strategy distribution
        strategy_counts = {}
        async for transition in transitions_query:
            strategy = transition.context_strategy
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            'period_days': days,
            'organization_id': organization_id,
            'sessions': {
                'total': total_sessions,
                'active': active_sessions,
                'activity_rate': (active_sessions / total_sessions * 100) if total_sessions > 0 else 0
            },
            'entries': {
                'total': total_entries,
                'average_importance': avg_importance,
                'total_cost': total_cost,
                'average_cost': (total_cost / total_entries) if total_entries > 0 else 0
            },
            'cache': {
                'hit_rate': cache_metrics.hit_rate if cache_metrics else 0,
                'total_summaries': cache_metrics.total_cached_summaries if cache_metrics else 0,
                'cost_savings': cache_metrics.cost_savings if cache_metrics else 0
            },
            'strategies': strategy_counts,
            'generated_at': timezone.now().isoformat()
        }
    
    def _display_report(self, report):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("CONTEXT MANAGEMENT PERFORMANCE REPORT"))
        self.stdout.write("="*60)
        
        if report['organization_id']:
            self.stdout.write(f"Organization: {report['organization_id']}")
        else:
            self.stdout.write("Scope: All Organizations")
        
        self.stdout.write(f"Period: Last {report['period_days']} days")
        self.stdout.write(f"Generated: {report['generated_at']}")
        
        self.stdout.write("\n" + "-"*40)
        self.stdout.write(self.style.SUCCESS("SESSION METRICS"))
        self.stdout.write("-"*40)
        self.stdout.write(f"Total Sessions: {report['sessions']['total']:,}")
        self.stdout.write(f"Active Sessions: {report['sessions']['active']:,}")
        self.stdout.write(f"Activity Rate: {report['sessions']['activity_rate']:.1f}%")
        
        self.stdout.write("\n" + "-"*40)
        self.stdout.write(self.style.SUCCESS("CONTENT METRICS"))
        self.stdout.write("-"*40)
        self.stdout.write(f"Total Messages: {report['entries']['total']:,}")
        self.stdout.write(f"Average Importance: {report['entries']['average_importance']:.2f}")
        self.stdout.write(f"Total Cost: ${report['entries']['total_cost']:.4f}")
        self.stdout.write(f"Average Cost per Message: ${report['entries']['average_cost']:.4f}")
        
        self.stdout.write("\n" + "-"*40)
        self.stdout.write(self.style.SUCCESS("CACHE PERFORMANCE"))
        self.stdout.write("-"*40)
        self.stdout.write(f"Cache Hit Rate: {report['cache']['hit_rate']:.1%}")
        self.stdout.write(f"Total Cached Summaries: {report['cache']['total_summaries']:,}")
        self.stdout.write(f"Cost Savings: ${report['cache']['cost_savings']:.4f}")
        
        if report['strategies']:
            self.stdout.write("\n" + "-"*40)
            self.stdout.write(self.style.SUCCESS("STRATEGY DISTRIBUTION"))
            self.stdout.write("-"*40)
            for strategy, count in report['strategies'].items():
                self.stdout.write(f"{strategy}: {count:,}")
        
        self.stdout.write("\n" + "="*60)
    
    def _save_report(self, report, filename):
        import json
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)


# context_manager/management/commands/test_context_system.py

from django.core.management.base import BaseCommand
import asyncio
import uuid
from decimal import Decimal

from ...services.context_service import ContextService, ContextRequest


class Command(BaseCommand):
    help = 'Test the context management system with sample data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--session-id',
            type=str,
            default=None,
            help='Session ID to test with (generates random if not provided)',
        )
        parser.add_argument(
            '--organization-id',
            type=str,
            default='test-org-123',
            help='Organization ID to test with',
        )
        parser.add_argument(
            '--model',
            type=str,
            default='gpt-4',
            help='Target model to test with',
        )
        parser.add_argument(
            '--messages',
            type=int,
            default=5,
            help='Number of test messages to create',
        )
    
    def handle(self, *args, **options):
        session_id = options.get('session_id') or f"test-session-{uuid.uuid4().hex[:8]}"
        organization_id = options['organization_id']
        model = options['model']
        message_count = options['messages']
        
        self.stdout.write(
            self.style.SUCCESS(f"Testing context system with session {session_id}")
        )
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                self._run_test(session_id, organization_id, model, message_count)
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Test failed: {str(e)}")
            )
        finally:
            loop.close()
    
    async def _run_test(self, session_id, organization_id, model, message_count):
        context_service = ContextService()
        
        # Test messages
        test_messages = [
            ("user", "Hello, I'm looking for information about your pricing plans."),
            ("assistant", "I'd be happy to help you with our pricing information. We offer three main plans: Starter ($99/month), Professional ($299/month), and Enterprise ($999+/month). What specific aspects would you like to know about?"),
            ("user", "What's included in the Professional plan?"),
            ("assistant", "The Professional plan includes up to $2,500 in optimized AI spend, advanced analytics, priority support, and team collaboration features. It's designed for growing teams that need more capacity and insights."),
            ("user", "How does the cost optimization work?"),
            ("assistant", "Our cost optimization works by intelligently routing requests to the most cost-effective model that can handle the task. For example, simple tasks use Mixtral (85% cheaper), while complex tasks use GPT-4. We typically achieve 40-60% cost savings."),
            ("user", "Can you give me more details about the technical implementation?"),
            ("assistant", "Certainly! Our system uses a smart routing algorithm that analyzes request complexity, maintains conversation context, and selects the optimal model. We also implement intelligent caching and context management to minimize costs while preserving quality."),
            ("user", "What were we discussing about pricing?"),  # This will test context retrieval
        ]
        
        # Take only the requested number of messages
        test_messages = test_messages[:message_count * 2]  # Each pair is user + assistant
        
        self.stdout.write(f"Creating {len(test_messages)} test messages...")
        
        # Store initial messages
        for i, (role, content) in enumerate(test_messages[:-1]):  # All except last
            await context_service.store_interaction(
                session_id=session_id,
                organization_id=organization_id,
                role=role,
                content=content,
                model_used=model if role == 'assistant' else None
            )
            
            self.stdout.write(f"  Stored {role} message {i+1}")
        
        # Test context preparation with the last message
        last_role, last_content = test_messages[-1]
        
        self.stdout.write(f"\nTesting context preparation for: '{last_content[:50]}...'")
        
        request = ContextRequest(
            session_id=session_id,
            organization_id=organization_id,
            target_model=model,
            user_message=last_content
        )
        
        response = await context_service.prepare_context(request)
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("CONTEXT PREPARATION RESULT"))
        self.stdout.write("="*60)
        self.stdout.write(f"Strategy Used: {response.strategy_used}")
        self.stdout.write(f"Tokens Used: {response.tokens_used:,}")
        self.stdout.write(f"Preparation Cost: ${response.preparation_cost}")
        self.stdout.write(f"Preparation Time: {response.preparation_time_ms}ms")
        self.stdout.write(f"Cache Hit: {response.cache_hit}")
        self.stdout.write(f"Quality Score: {response.information_preservation_score:.2f}")
        
        self.stdout.write(f"\nContext Content Preview:")
        self.stdout.write("-" * 40)
        preview = response.context_content[:500] + "..." if len(response.context_content) > 500 else response.context_content
        self.stdout.write(preview)
        
        # Store the last message and test again to see caching
        await context_service.store_interaction(
            session_id=session_id,
            organization_id=organization_id,
            role=last_role,
            content=last_content
        )
        
        self.stdout.write(f"\n\nTesting context preparation again (should use cache)...")
        
        request2 = ContextRequest(
            session_id=session_id,
            organization_id=organization_id,
            target_model=model,
            user_message="Follow up question to test caching"
        )
        
        response2 = await context_service.prepare_context(request2)
        
        self.stdout.write(f"Second preparation - Strategy: {response2.strategy_used}, Cache Hit: {response2.cache_hit}")
        
        # Get analytics
        analytics = await context_service.get_session_analytics(session_id, organization_id)
        
        if analytics:
            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.SUCCESS("SESSION ANALYTICS"))
            self.stdout.write("="*60)
            self.stdout.write(f"Session Tier: {analytics['session_info']['tier']}")
            self.stdout.write(f"Total Cost: ${analytics['session_info']['total_summarization_cost']}")
            self.stdout.write(f"Cache Hit Rate: {analytics['cache_performance']['hit_rate']:.1%}")
            self.stdout.write(f"Cost Savings: ${analytics['cache_performance']['cost_savings']}")
            self.stdout.write(f"Total Entries: {analytics['storage_metrics']['total_entries']}")
        
        self.stdout.write("\n" + self.style.SUCCESS("Test completed successfully!"))
        self.stdout.write(f"Session ID: {session_id}")
        self.stdout.write(f"Organization ID: {organization_id}")


# __init__.py file for management commands
# context_manager/management/__init__.py
# (empty file)

# context_manager/management/commands/__init__.py  
# (empty file)