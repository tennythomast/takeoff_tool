import uuid
from django.db import models
from django.utils import timezone
import json

class BenchmarkRun(models.Model):
    """Master record for each benchmark execution"""
    STATUS_CHOICES = (
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    run_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset_name = models.CharField(max_length=100)
    run_timestamp = models.DateTimeField(default=timezone.now)
    total_samples = models.IntegerField(default=0)
    configuration = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    
    def __str__(self):
        return f"{self.dataset_name} - {self.run_timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration_seconds(self):
        if self.status != 'completed':
            return None
        
        # Get the latest result's timestamp
        latest_result = self.benchmarkresult_set.order_by('-created_at').first()
        if not latest_result:
            return None
            
        return (latest_result.created_at - self.run_timestamp).total_seconds()
    
    @property
    def progress_percentage(self):
        if self.total_samples == 0:
            return 0
        
        completed_samples = self.benchmarkresult_set.count()
        return round((completed_samples / self.total_samples) * 100, 2)

class BenchmarkResult(models.Model):
    """Individual test sample result"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    benchmark_run = models.ForeignKey(BenchmarkRun, on_delete=models.CASCADE)
    sample_id = models.CharField(max_length=100)
    input_text = models.TextField()
    expected_output = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Your platform results
    complexity_score = models.FloatField(null=True, blank=True)
    complexity_level = models.CharField(max_length=50, null=True, blank=True)
    complexity_reasoning = models.JSONField(null=True, blank=True)
    routing_decision = models.JSONField(null=True, blank=True)
    selected_model = models.CharField(max_length=100, null=True, blank=True)
    estimated_cost = models.FloatField(null=True, blank=True)
    actual_response = models.TextField(null=True, blank=True)
    execution_time_ms = models.IntegerField(null=True, blank=True)
    
    # Baseline comparisons
    gpt4_response = models.TextField(null=True, blank=True)
    gpt4_cost = models.FloatField(null=True, blank=True)
    claude_response = models.TextField(null=True, blank=True)
    claude_cost = models.FloatField(null=True, blank=True)
    
    # Quality metrics
    semantic_similarity_vs_gpt4 = models.FloatField(null=True, blank=True)
    semantic_similarity_vs_claude = models.FloatField(null=True, blank=True)
    quality_retained = models.BooleanField(null=True, blank=True)
    quality_confidence = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.sample_id} - {self.selected_model or 'pending'}"
    
    @property
    def cost_savings_vs_gpt4(self):
        if not self.estimated_cost or not self.gpt4_cost:
            return None
        
        if self.gpt4_cost == 0:
            return 0
            
        savings = (self.gpt4_cost - self.estimated_cost) / self.gpt4_cost * 100
        return round(savings, 2)
    
    @property
    def cost_savings_vs_claude(self):
        if not self.estimated_cost or not self.claude_cost:
            return None
        
        if self.claude_cost == 0:
            return 0
            
        savings = (self.claude_cost - self.estimated_cost) / self.claude_cost * 100
        return round(savings, 2)

class BenchmarkSummary(models.Model):
    """Aggregated results per benchmark run"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    benchmark_run = models.OneToOneField(BenchmarkRun, on_delete=models.CASCADE)
    total_cost_your_platform = models.FloatField(default=0)
    total_cost_gpt4_baseline = models.FloatField(default=0)
    total_cost_claude_baseline = models.FloatField(default=0)
    cost_savings_vs_gpt4_percent = models.FloatField(default=0)
    cost_savings_vs_claude_percent = models.FloatField(default=0)
    avg_quality_retention = models.FloatField(default=0)
    model_distribution = models.JSONField(default=dict)
    complexity_distribution = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Summary for {self.benchmark_run}"
    
    def update_from_results(self):
        """Update summary statistics from the associated benchmark results"""
        results = self.benchmark_run.benchmarkresult_set.all()
        
        if not results:
            return
        
        # Calculate costs
        self.total_cost_your_platform = sum(r.estimated_cost or 0 for r in results)
        self.total_cost_gpt4_baseline = sum(r.gpt4_cost or 0 for r in results)
        self.total_cost_claude_baseline = sum(r.claude_cost or 0 for r in results)
        
        # Calculate savings percentages
        if self.total_cost_gpt4_baseline > 0:
            self.cost_savings_vs_gpt4_percent = round(
                (self.total_cost_gpt4_baseline - self.total_cost_your_platform) / 
                self.total_cost_gpt4_baseline * 100, 2
            )
        
        if self.total_cost_claude_baseline > 0:
            self.cost_savings_vs_claude_percent = round(
                (self.total_cost_claude_baseline - self.total_cost_your_platform) / 
                self.total_cost_claude_baseline * 100, 2
            )
        
        # Calculate quality retention
        quality_values = [r.quality_retained for r in results if r.quality_retained is not None]
        if quality_values:
            self.avg_quality_retention = sum(1 for q in quality_values if q) / len(quality_values) * 100
        
        # Calculate model distribution
        model_counts = {}
        for result in results:
            if result.selected_model:
                model_counts[result.selected_model] = model_counts.get(result.selected_model, 0) + 1
        self.model_distribution = model_counts
        
        # Calculate complexity distribution
        complexity_counts = {}
        for result in results:
            if result.complexity_level:
                complexity_counts[result.complexity_level] = complexity_counts.get(result.complexity_level, 0) + 1
        self.complexity_distribution = complexity_counts
        
        self.save()
