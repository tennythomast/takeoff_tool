from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import BaseModel, SoftDeletableMixin, SoftDeletableManager
from core.models import Organization


class Drawing(SoftDeletableMixin):
    """
    Drawing model that stores fixed metadata in a relational structure.
    
    This model represents engineering drawings with standardized metadata
    that is consistent across all drawings in the system.
    """
    # Relationships
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='drawings'
    )
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_drawings'
    )
    
    # Basic information
    client = models.CharField(max_length=255, db_index=True)
    project = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=255)
    drawing_number = models.CharField(max_length=100, db_index=True)
    drawing_title = models.CharField(max_length=500)
    date = models.DateField()
    revision = models.CharField(max_length=50, blank=True)
    scale = models.CharField(max_length=50, blank=True)
    page_count = models.IntegerField(default=1)
    
    # File information
    file_path = models.CharField(max_length=1000, blank=True)
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=50, default='pdf')
    
    # Link to RAG document if available
    rag_document = models.ForeignKey(
        'rag_service.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='drawings'
    )
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    objects = SoftDeletableManager()
    
    class Meta:
        db_table = 'takeoff_drawing'
        verbose_name = 'Drawing'
        verbose_name_plural = 'Drawings'
        ordering = ['-created_at']
        unique_together = ['organization', 'drawing_number']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['client', 'project']),
        ]
    
    def __str__(self):
        return f"{self.drawing_number}: {self.drawing_title}"


class TakeoffElement(SoftDeletableMixin):
    """
    Flexible element data - hybrid
    
    Each element represents a specific item from an engineering drawing
    that has been identified during the takeoff process.
    """
    # Relationships
    drawing = models.ForeignKey(
        Drawing, 
        on_delete=models.CASCADE,
        related_name='elements'
    )
    extraction = models.ForeignKey(
        'TakeoffExtraction',
        on_delete=models.CASCADE,
        related_name='element_items',
        null=True,
        blank=True
    )
    
    # Element identification
    element_id = models.CharField(max_length=100, db_index=True)
    element_type = models.CharField(max_length=100, db_index=True)
    
    # JSON! Flexible, extensible, queryable
    specifications = models.JSONField(default=dict)
    location = models.JSONField(default=dict, blank=True)
    
    # Metadata
    confidence_score = models.FloatField(default=0.0)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_elements'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeletableManager()
    
    class Meta:
        db_table = 'takeoff_element'
        verbose_name = 'Takeoff Element'
        verbose_name_plural = 'Takeoff Elements'
        ordering = ['drawing', 'element_type', 'element_id']
        indexes = [
            models.Index(fields=['drawing', 'element_type']),
            models.Index(fields=['element_id']),
            models.Index(fields=['verified']),
        ]
        unique_together = ['drawing', 'element_id']
    
    def __str__(self):
        return f"{self.element_type} {self.element_id}"
    
    def save(self, *args, **kwargs):
        # Update verified_at timestamp if verified
        if self.verified and not self.verified_at:
            self.verified_at = timezone.now()
            
        super().save(*args, **kwargs)


class TakeoffExtraction(SoftDeletableMixin):
    """
    TakeoffExtraction model that stores metadata for each extraction process.
    
    This model links to the Drawing and contains metadata about the extraction process,
    while the actual extracted elements are stored in a flexible JSON structure.
    """
    # Extraction status options
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('verified', 'Verified'),
    ]
    
    # Extraction method options
    METHOD_CHOICES = [
        ('manual', 'Manual Entry'),
        ('rule_based', 'Rule-based Extraction'),
        ('ai_assisted', 'AI-assisted Extraction'),
        ('imported', 'Imported from External Source'),
    ]
    
    # Relationships
    drawing = models.ForeignKey(
        Drawing, 
        on_delete=models.CASCADE,
        related_name='extractions'
    )
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_extractions'
    )
    verified_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_extractions'
    )
    
    # Extraction information
    extraction_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    extraction_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='rule_based',
        db_index=True
    )
    
    # Processing information
    processing_time_ms = models.IntegerField(default=0)
    processing_error = models.TextField(blank=True)
    extraction_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )
    
    # Quality metrics
    confidence_score = models.FloatField(
        default=0.0,
        help_text="Overall confidence score for the extraction (0-1)"
    )
    verified = models.BooleanField(
        default=False,
        help_text="Whether this extraction has been verified by a user"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Extracted elements - flexible JSON structure
    elements = models.JSONField(
        default=dict,
        help_text="Flexible JSON structure containing all extracted takeoff elements"
    )
    
    # Statistics
    element_count = models.IntegerField(default=0)
    
    objects = SoftDeletableManager()
    
    class Meta:
        db_table = 'takeoff_extraction'
        verbose_name = 'Takeoff Extraction'
        verbose_name_plural = 'Takeoff Extractions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['drawing', 'is_active']),
            models.Index(fields=['status', 'extraction_method']),
            models.Index(fields=['verified']),
        ]
    
    def __str__(self):
        return f"Extraction {self.id} for {self.drawing}"
    
    def save(self, *args, **kwargs):
        # Update element count before saving
        if isinstance(self.elements, dict) and 'items' in self.elements:
            self.element_count = len(self.elements.get('items', []))
        
        # Update verified_at timestamp if verified
        if self.verified and not self.verified_at:
            self.verified_at = timezone.now()
            
        super().save(*args, **kwargs)
        
        # Create TakeoffElement objects from elements JSON if needed
        if isinstance(self.elements, dict) and 'items' in self.elements:
            self.create_element_objects()
    
    def create_element_objects(self):
        """Create TakeoffElement objects from elements JSON"""
        # Import here to avoid circular import
        from .models import TakeoffElement
        
        if not isinstance(self.elements, dict) or 'items' not in self.elements:
            return
            
        items = self.elements.get('items', [])
        for item in items:
            element_id = item.get('element_id')
            element_type = item.get('element_type')
            
            if not element_id or not element_type:
                continue
                
            # Create or update element
            element, created = TakeoffElement.objects.update_or_create(
                drawing=self.drawing,
                element_id=element_id,
                defaults={
                    'extraction': self,
                    'element_type': element_type,
                    'specifications': item.get('specifications', {}),
                    'location': item.get('location', {}),
                    'confidence_score': item.get('metadata', {}).get('confidence', 0.0)
                }
            )
    
    def update_element_count(self):
        """Update element count based on related TakeoffElement objects"""
        self.element_count = self.element_items.filter(is_active=True).count()
        self.save(update_fields=['element_count'])


class TakeoffProject(SoftDeletableMixin):
    """
    TakeoffProject model that groups related drawings and extractions.
    
    This model provides a way to organize drawings and extractions by project,
    and to track project-level metrics and status.
    """
    # Relationships
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='takeoff_projects'
    )
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_takeoff_projects'
    )
    
    # Basic information
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    client = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Dates
    start_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning',
        db_index=True
    )
    
    # Statistics
    drawing_count = models.IntegerField(default=0)
    extraction_count = models.IntegerField(default=0)
    verified_extraction_count = models.IntegerField(default=0)
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    objects = SoftDeletableManager()
    
    class Meta:
        db_table = 'takeoff_project'
        verbose_name = 'Takeoff Project'
        verbose_name_plural = 'Takeoff Projects'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['status']),
            models.Index(fields=['client']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.client})"
    
    def update_statistics(self):
        """Update project statistics"""
        self.drawing_count = self.drawings.filter(is_active=True).count()
        self.extraction_count = TakeoffExtraction.objects.filter(
            drawing__project=self,
            is_active=True
        ).count()
        self.verified_extraction_count = TakeoffExtraction.objects.filter(
            drawing__project=self,
            is_active=True,
            verified=True
        ).count()
        self.save(update_fields=['drawing_count', 'extraction_count', 'verified_extraction_count'])

