from django.contrib import admin
from django.utils.html import format_html
from .models import BenchmarkRun, BenchmarkResult, BenchmarkSummary

class BenchmarkResultInline(admin.TabularInline):
    model = BenchmarkResult
    fields = ('sample_id', 'complexity_level', 'selected_model', 'estimated_cost', 'quality_retained')
    readonly_fields = fields
    extra = 0
    max_num = 10
    can_delete = False
    show_change_link = True
    verbose_name = "Sample Result"
    verbose_name_plural = "Sample Results (10 most recent)"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Don't slice the queryset, just order it
        # Django admin will handle limiting the display to max_num items
        return qs.order_by('-created_at')

@admin.register(BenchmarkRun)
class BenchmarkRunAdmin(admin.ModelAdmin):
    list_display = ('dataset_name', 'run_timestamp', 'total_samples', 'status', 'progress_display')
    list_filter = ('dataset_name', 'status', 'run_timestamp')
    readonly_fields = ('run_id', 'run_timestamp', 'progress_display', 'duration_display')
    search_fields = ('dataset_name',)
    inlines = [BenchmarkResultInline]
    
    fieldsets = (
        (None, {
            'fields': ('run_id', 'dataset_name', 'run_timestamp', 'total_samples', 'status')
        }),
        ('Progress', {
            'fields': ('progress_display', 'duration_display')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        if obj.status == 'running':
            percentage = obj.progress_percentage
            return format_html(
                '<div style="width:100%; background-color:#f8f9fa; height:20px; border-radius:5px;">' 
                '<div style="width:{}%; background-color:#007bff; height:20px; border-radius:5px; text-align:center; color:white;">' 
                '{}%</div></div>', 
                percentage, f"{percentage:.1f}"
            )
        elif obj.status == 'completed':
            return format_html('<span style="color:green;">Completed (100%)</span>')
        else:
            return format_html('<span style="color:red;">Failed</span>')
    progress_display.short_description = 'Progress'
    
    def duration_display(self, obj):
        seconds = obj.duration_seconds
        if seconds is None:
            return "N/A"
        
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"
    duration_display.short_description = 'Duration'

@admin.register(BenchmarkResult)
class BenchmarkResultAdmin(admin.ModelAdmin):
    list_display = ('sample_id', 'benchmark_run', 'complexity_level', 'selected_model', 
                   'estimated_cost', 'gpt4_cost', 'claude_cost', 'quality_retained')
    list_filter = ('benchmark_run__dataset_name', 'complexity_level', 'selected_model', 'quality_retained')
    search_fields = ('sample_id', 'input_text', 'actual_response')
    readonly_fields = ('id', 'benchmark_run', 'created_at', 'cost_savings_vs_gpt4', 'cost_savings_vs_claude')
    
    fieldsets = (
        (None, {
            'fields': ('id', 'benchmark_run', 'sample_id', 'created_at')
        }),
        ('Input & Expected Output', {
            'fields': ('input_text', 'expected_output')
        }),
        ('Platform Results', {
            'fields': ('complexity_score', 'complexity_level', 'complexity_reasoning', 
                      'routing_decision', 'selected_model', 'estimated_cost', 
                      'actual_response', 'execution_time_ms')
        }),
        ('Baseline Comparisons', {
            'fields': ('gpt4_response', 'gpt4_cost', 'claude_response', 'claude_cost',
                      'cost_savings_vs_gpt4', 'cost_savings_vs_claude')
        }),
        ('Quality Metrics', {
            'fields': ('semantic_similarity_vs_gpt4', 'semantic_similarity_vs_claude',
                      'quality_retained', 'quality_confidence')
        }),
    )

@admin.register(BenchmarkSummary)
class BenchmarkSummaryAdmin(admin.ModelAdmin):
    list_display = ('benchmark_run', 'total_cost_your_platform', 'total_cost_gpt4_baseline',
                   'cost_savings_vs_gpt4_percent', 'avg_quality_retention')
    readonly_fields = ('id', 'benchmark_run', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('id', 'benchmark_run', 'created_at', 'updated_at')
        }),
        ('Cost Metrics', {
            'fields': ('total_cost_your_platform', 'total_cost_gpt4_baseline', 'total_cost_claude_baseline',
                      'cost_savings_vs_gpt4_percent', 'cost_savings_vs_claude_percent')
        }),
        ('Quality Metrics', {
            'fields': ('avg_quality_retention',)
        }),
        ('Distributions', {
            'fields': ('model_distribution', 'complexity_distribution')
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Summaries should only be created by the system
