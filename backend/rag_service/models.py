import uuid
import hashlib
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async

from core.models import BaseModel, SoftDeletableMixin, SoftDeletableManager


class KnowledgeBase(SoftDeletableMixin):
    """
    A knowledge base is a collection of documents that can be used for RAG.
    It belongs to an organization and optionally a workspace.
    """
    
    EMBEDDING_STRATEGIES = [
        ('basic', 'Basic Chunking'),
        ('semantic', 'Semantic Chunking'),
        ('hybrid', 'Hybrid Chunking'),
        ('sliding_window', 'Sliding Window'),
        ('custom', 'Custom Strategy'),
    ]
    
    RETRIEVAL_STRATEGIES = [
        ('similarity', 'Similarity Search'),
        ('mmr', 'Maximum Marginal Relevance'),
        ('hybrid', 'Hybrid Search'),
        ('reranking', 'Retrieval with Reranking'),
        ('custom', 'Custom Strategy'),
    ]
    
    # Multi-tenant structure
    organization = models.ForeignKey(
        'core.Organization',
        on_delete=models.CASCADE,
        related_name='knowledge_bases',
        db_index=True
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='knowledge_bases',
        null=True,
        blank=True,
        db_index=True
    )
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_knowledge_bases'
    )
    
    # Basic information
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    
    # Configuration
    embedding_model = models.ForeignKey(
        'modelhub.Model',
        on_delete=models.SET_NULL,
        null=True,
        related_name='knowledge_bases',
        help_text="Embedding model used for this knowledge base"
    )
    embedding_strategy = models.CharField(
        max_length=30, 
        choices=EMBEDDING_STRATEGIES,
        default='semantic',
        db_index=True
    )
    retrieval_strategy = models.CharField(
        max_length=30, 
        choices=RETRIEVAL_STRATEGIES,
        default='similarity',
        db_index=True
    )
    
    # Advanced configuration
    chunk_size = models.IntegerField(default=1000)
    chunk_overlap = models.IntegerField(default=200)
    similarity_top_k = models.IntegerField(default=5)
    mmr_diversity_bias = models.FloatField(
        default=0.3,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    advanced_config = models.JSONField(default=dict, blank=True)
    
    # Statistics
    document_count = models.IntegerField(default=0)
    chunk_count = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    total_embedding_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        default=0
    )
    last_updated = models.DateTimeField(auto_now=True)
    last_queried = models.DateTimeField(null=True, blank=True)
    
    # Access control
    is_public = models.BooleanField(
        default=False,
        help_text="If True, this knowledge base is available to all organization members"
    )
    
    objects = SoftDeletableManager()
    
    class Meta:
        db_table = 'rag_knowledge_base'
        verbose_name = 'Knowledge Base'
        verbose_name_plural = 'Knowledge Bases'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['embedding_strategy']),
            models.Index(fields=['retrieval_strategy']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.organization.name})"
    
    def clean(self):
        super().clean()
        # Validate workspace belongs to organization
        if self.workspace and self.workspace.organization_id != self.organization_id:
            raise ValidationError({
                'workspace': 'Workspace must belong to the same organization'
            })
    
    def update_statistics(self):
        """Update document and chunk counts"""
        self.document_count = self.documents.filter(is_active=True).count()
        self.chunk_count = Chunk.objects.filter(
            document__knowledge_base=self,
            document__is_active=True
        ).count()
        self.total_tokens = Chunk.objects.filter(
            document__knowledge_base=self,
            document__is_active=True
        ).aggregate(total=models.Sum('token_count'))['total'] or 0
        self.save(update_fields=['document_count', 'chunk_count', 'total_tokens', 'last_updated'])
    
    def record_query(self):
        """Record that this knowledge base was queried"""
        self.last_queried = timezone.now()
        self.save(update_fields=['last_queried'])
    
    def can_access(self, user):
        """Check if user can access this knowledge base"""
        if not user or not user.is_active:
            return False
            
        # Superuser access
        if user.is_superuser:
            return True
            
        # Must be in same organization
        if user.organization != self.organization:
            return False
            
        # Creator can always access
        if self.created_by_id == user.id:
            return True
            
        # Public knowledge bases are accessible to all org members
        if self.is_public:
            return True
            
        # Workspace access check
        if self.workspace:
            # Workspace owner
            if self.workspace.owner_id == user.id:
                return True
                
            # Workspace collaborator
            from workspaces.models import WorkspaceCollaborator
            return WorkspaceCollaborator.objects.filter(
                workspace=self.workspace,
                user=user
            ).exists()
            
        return False
        
    def can_edit(self, user):
        """Check if user can edit this knowledge base"""
        if not self.can_access(user):
            return False
            
        # Creator can edit
        if self.created_by_id == user.id:
            return True
            
        # Workspace admin can edit workspace knowledge bases
        if self.workspace:
            from workspaces.models import WorkspaceCollaborator
            return WorkspaceCollaborator.objects.filter(
                workspace=self.workspace,
                user=user,
                role=WorkspaceCollaborator.Role.ADMIN
            ).exists()
            
        # Organization admin can edit
        return user.has_role(self.organization, 'ADMIN')
    
    @classmethod
    @database_sync_to_async
    def get_knowledge_base_async(cls, knowledge_base_id):
        """Get knowledge base by ID asynchronously"""
        try:
            return cls.objects.select_related('organization', 'workspace', 'embedding_model').get(
                id=knowledge_base_id,
                is_active=True
            )
        except cls.DoesNotExist:
            return None
            
    @classmethod
    def get_workspace_knowledge_bases(cls, workspace, user=None):
        """Get knowledge bases accessible in a workspace"""
        # Base query: knowledge bases in workspace + public org knowledge bases
        queryset = cls.objects.filter(
            organization=workspace.organization,
            is_active=True
        ).filter(
            models.Q(workspace=workspace) |
            models.Q(is_public=True, workspace__isnull=True)
        )
        
        # If user specified, also include their private knowledge bases
        if user:
            private_kbs = models.Q(
                created_by=user,
                workspace__isnull=True,
                is_public=False
            )
            queryset = queryset.filter(
                models.Q(workspace=workspace) |
                models.Q(is_public=True, workspace__isnull=True) |
                private_kbs
            )
            
        return queryset.select_related('created_by', 'embedding_model').order_by('-created_at')
    
    @classmethod
    def get_user_knowledge_bases(cls, user):
        """Get knowledge bases accessible to a user"""
        queryset = cls.objects.filter(
            organization=user.organization,
            is_active=True
        ).filter(
            models.Q(created_by=user) |
            models.Q(is_public=True) |
            models.Q(
                workspace__in=user.collaborated_workspaces.values_list('id', flat=True)
            )
        )
            
        return queryset.select_related('created_by', 'embedding_model').order_by('-created_at')


class Document(SoftDeletableMixin):
    """
    A document in a knowledge base.
    Can be linked to a file in the file_storage app or created directly.
    Supports both chunked and complete document storage approaches.
    """
    
    PROCESSING_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    DOCUMENT_TYPES = [
        ('text', 'Plain Text'),
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('html', 'HTML'),
        ('markdown', 'Markdown'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('code', 'Code'),
        ('other', 'Other'),
    ]
    
    STORAGE_APPROACHES = [
        ('chunked', 'Chunked Storage'),
        ('complete', 'Complete Document Storage'),
        ('hybrid', 'Hybrid Storage'),
    ]
    
    # Relationships
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file_upload = models.ForeignKey(
        'file_storage.FileUpload',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rag_documents'
    )
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_documents'
    )
    
    # Basic information
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        default='text',
        db_index=True
    )
    
    # Storage approach
    storage_approach = models.CharField(
        max_length=20,
        choices=STORAGE_APPROACHES,
        default='complete',  # Default to complete document storage
        db_index=True,
        help_text="Approach used for storing document content"
    )
    
    # Content (for directly created documents or extracted text)
    content = models.TextField(
        blank=True,
        help_text="Document content or extracted text from file"
    )
    
    # Full-text search vector (requires PostgreSQL)
    content_search_vector = models.JSONField(
        null=True,
        blank=True,
        help_text="Search vector for full-text search capabilities"
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS,
        default='pending',
        db_index=True
    )
    processing_error = models.TextField(blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    source_url = models.URLField(blank=True)
    
    # Extraction information
    extraction_method = models.CharField(max_length=30, blank=True)
    extraction_cost_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        default=0
    )
    extraction_quality_score = models.FloatField(default=0.0)
    extraction_metadata = models.JSONField(default=dict, blank=True)
    
    # Statistics
    chunk_count = models.IntegerField(default=0)
    token_count = models.IntegerField(default=0)
    embedding_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )
    
    # Timestamps
    processed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeletableManager()
    
    class Meta:
        db_table = 'rag_document'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['knowledge_base', 'is_active']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['document_type']),
            models.Index(fields=['storage_approach']),
            # Note: For production, consider adding a GIN index for content
            # This requires a PostgreSQL extension and migration
            # models.Index(name='content_gin_idx', fields=['content'], opclasses=['gin_trgm_ops'])
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"
    
    def update_statistics(self):
        """Update document statistics based on storage approach"""
        if self.storage_approach == 'chunked' or self.storage_approach == 'hybrid':
            # For chunked or hybrid approach, count chunks
            self.chunk_count = self.chunks.count()
            self.token_count = self.chunks.aggregate(
                total=models.Sum('token_count')
            )['total'] or 0
        else:
            # For complete document storage, estimate token count from content length
            # Rough estimate: 1 token ≈ 4 characters for English text
            self.chunk_count = 1  # The document itself is one chunk
            self.token_count = len(self.content) // 4 if self.content else 0
            
        self.save(update_fields=['chunk_count', 'token_count'])
    
    def mark_processing_started(self):
        """Mark document as processing"""
        self.status = 'processing'
        self.save(update_fields=['status'])
    
    def mark_processing_completed(self, cost=None):
        """Mark document as completed"""
        self.status = 'completed'
        self.processed_at = timezone.now()
        if cost is not None:
            self.embedding_cost = cost
            
        # For complete document storage, generate search vectors
        if self.storage_approach == 'complete' and self.content:
            # Generate search vector before saving
            self.generate_search_vector()
            
        self.save(update_fields=['status', 'processed_at', 'embedding_cost'])
        
        # Update knowledge base statistics
        self.knowledge_base.update_statistics()
    
    def mark_processing_failed(self, error_message):
        """Mark document as failed"""
        self.status = 'failed'
        self.processing_error = error_message
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processing_error', 'processed_at'])
    
    def record_access(self):
        """Record document access"""
        self.last_accessed = timezone.now()
        self.save(update_fields=['last_accessed'])
        
        # If linked to a file, also record access there
        if self.file_upload:
            self.file_upload.record_access()
            
    def generate_search_vector(self):
        """Generate search vector for full-text search"""
        # This is a simplified implementation
        # For production, consider using PostgreSQL's tsvector
        if not self.content:
            return
            
        # Create a simple search vector from content
        # Extract keywords, remove stopwords, etc.
        import re
        from collections import Counter
        
        # Normalize text: lowercase, remove punctuation, split into words
        text = self.content.lower()
        words = re.findall(r'\w+', text)
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Remove common stopwords
        stopwords = {'the', 'and', 'is', 'of', 'to', 'a', 'in', 'that', 'it', 'with'}
        for word in stopwords:
            if word in word_counts:
                del word_counts[word]
                
        # Store top keywords with their frequencies
        self.content_search_vector = {
            'keywords': dict(word_counts.most_common(100)),
            'updated_at': timezone.now().isoformat()
        }
        
        self.save(update_fields=['content_search_vector'])
    
    @property
    def is_processed(self):
        """Check if document is processed"""
        return self.status == 'completed'
    
    @classmethod
    @database_sync_to_async
    def get_document_async(cls, document_id):
        """Get document by ID asynchronously"""
        try:
            return cls.objects.select_related('knowledge_base', 'file_upload').get(
                id=document_id,
                is_active=True
            )
        except cls.DoesNotExist:
            return None


class Chunk(BaseModel):
    """
    A semantic chunk of a document optimized for RAG retrieval.
    Different chunk types preserve different kinds of information.
    """
    
    # Relationships
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    
    # Content
    content = models.TextField(help_text="Human-readable content representation")
    chunk_index = models.IntegerField(help_text="Order within document")
    
    # Chunk type
    chunk_type = models.CharField(
        max_length=50,
        choices=[
            ('table', 'Table - Atomic'),
            ('metadata', 'Document Metadata - Atomic'),
            ('text', 'Text Content - Variable Size'),
            ('visual_element_group', 'Visual Element Group - Spatial'),
            ('drawing_metadata', 'Drawing Metadata - Atomic'),
        ],
        default='text'
    )
    
    # Embedding information
    embedding_model = models.CharField(max_length=100)
    embedding_vector_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="ID of the vector in the vector store"
    )
    embedding_vector = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding for semantic search"
    )
    token_count = models.IntegerField(default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Structured metadata for filtering and retrieval")
    page_number = models.IntegerField(null=True, blank=True)
    
    # Relationships between chunks
    parent_chunk = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_chunks'
    )
    related_chunks = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='linked_chunks'
    )
    
    # Statistics
    relevance_score_avg = models.FloatField(
        null=True,
        blank=True,
        help_text="Average relevance score in queries"
    )
    retrieval_count = models.IntegerField(
        default=0,
        help_text="Number of times this chunk was retrieved"
    )
    
    class Meta:
        db_table = 'rag_chunk'
        verbose_name = 'Chunk'
        verbose_name_plural = 'Chunks'
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['embedding_vector_id']),
            models.Index(fields=['retrieval_count']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['document', 'chunk_index'],
                name='unique_chunk_per_document'
            )
        ]
    
    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"
    
    def record_retrieval(self, relevance_score=None):
        """Record that this chunk was retrieved in a query"""
        self.retrieval_count += 1
        
        # Update average relevance score
        if relevance_score is not None:
            if self.relevance_score_avg is None:
                self.relevance_score_avg = relevance_score
            else:
                # Weighted average
                prev_total = self.relevance_score_avg * (self.retrieval_count - 1)
                new_avg = (prev_total + relevance_score) / self.retrieval_count
                self.relevance_score_avg = new_avg
                
        self.save(update_fields=['retrieval_count', 'relevance_score_avg'])
        
    @classmethod
    @database_sync_to_async
    def get_chunks_by_vector_ids_async(cls, vector_ids):
        """Get chunks by vector IDs asynchronously"""
        return list(cls.objects.filter(
            embedding_vector_id__in=vector_ids
        ).select_related('document').order_by('id'))


class VectorIndex(BaseModel):
    """
    Represents a vector index for a knowledge base.
    Stores configuration and metadata for vector databases like Qdrant, Pinecone, etc.
    """
    
    INDEX_TYPES = [
        ('qdrant', 'Qdrant'),
        ('pinecone', 'Pinecone'),
        ('weaviate', 'Weaviate'),
        ('milvus', 'Milvus'),
        ('redis', 'Redis'),
        ('pgvector', 'PostgreSQL pgvector'),
        ('custom', 'Custom Vector Store'),
    ]
    
    INDEX_STATUS = [
        ('initializing', 'Initializing'),
        ('active', 'Active'),
        ('updating', 'Updating'),
        ('error', 'Error'),
        ('rebuilding', 'Rebuilding'),
    ]
    
    # Relationships
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='vector_indexes'
    )
    
    # Basic information
    name = models.CharField(max_length=255)
    index_type = models.CharField(
        max_length=20,
        choices=INDEX_TYPES,
        default='qdrant'
    )
    status = models.CharField(
        max_length=20,
        choices=INDEX_STATUS,
        default='initializing',
        db_index=True
    )
    
    # Configuration
    collection_name = models.CharField(
        max_length=255,
        help_text="Name of the collection in the vector database"
    )
    dimensions = models.IntegerField(
        default=1536,
        help_text="Dimensions of the embedding vectors"
    )
    metric = models.CharField(
        max_length=20,
        default='cosine',
        help_text="Distance metric used for similarity search (cosine, euclidean, dot)"
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Vector store specific configuration"
    )
    
    # Connection information (encrypted in production)
    connection_string = models.TextField(
        blank=True,
        help_text="Connection string or endpoint URL"
    )
    api_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="API key for the vector database (encrypted)"
    )
    
    # Statistics
    vector_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    last_optimized = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'rag_vector_index'
        verbose_name = 'Vector Index'
        verbose_name_plural = 'Vector Indexes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['knowledge_base', 'status']),
            models.Index(fields=['index_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['knowledge_base', 'name'],
                name='unique_vector_index_per_kb'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_index_type_display()}) - {self.get_status_display()}"
    
    def update_vector_count(self):
        """Update the vector count from the knowledge base"""
        self.vector_count = self.knowledge_base.chunk_count
        self.save(update_fields=['vector_count', 'last_updated'])
    
    def mark_active(self):
        """Mark the index as active"""
        self.status = 'active'
        self.save(update_fields=['status', 'last_updated'])
    
    def mark_updating(self):
        """Mark the index as updating"""
        self.status = 'updating'
        self.save(update_fields=['status', 'last_updated'])
    
    def mark_error(self, error_message):
        """Mark the index as having an error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'last_updated'])
    
    def mark_rebuilding(self):
        """Mark the index as rebuilding"""
        self.status = 'rebuilding'
        self.save(update_fields=['status', 'last_updated'])
    
    def record_optimization(self):
        """Record that the index was optimized"""
        self.last_optimized = timezone.now()
        self.save(update_fields=['last_optimized'])
    
    @property
    def is_active(self):
        """Check if the index is active"""
        return self.status == 'active'
    
    @classmethod
    @database_sync_to_async
    def get_active_index_for_kb_async(cls, knowledge_base_id):
        """Get the active vector index for a knowledge base asynchronously"""
        try:
            return cls.objects.filter(
                knowledge_base_id=knowledge_base_id,
                status='active'
            ).latest('created_at')
        except cls.DoesNotExist:
            return None


class RAGQuery(BaseModel):
    """
    Represents a query to a knowledge base.
    Tracks query performance, results, and user feedback.
    """
    
    QUERY_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    FEEDBACK_TYPES = [
        ('thumbs_up', 'Thumbs Up'),
        ('thumbs_down', 'Thumbs Down'),
        ('accurate', 'Accurate'),
        ('inaccurate', 'Inaccurate'),
        ('helpful', 'Helpful'),
        ('unhelpful', 'Unhelpful'),
        ('missing_context', 'Missing Context'),
        ('hallucination', 'Hallucination'),
    ]
    
    # Relationships
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='queries'
    )
    user = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='rag_queries'
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rag_queries'
    )
    
    # Query content
    query_text = models.TextField()
    query_embedding_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID of the query embedding in the vector store"
    )
    
    # Configuration used
    retrieval_strategy = models.CharField(max_length=30)
    similarity_top_k = models.IntegerField(default=5)
    mmr_diversity_bias = models.FloatField(null=True, blank=True)
    reranking_enabled = models.BooleanField(default=False)
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=QUERY_STATUS,
        default='pending',
        db_index=True
    )
    error_message = models.TextField(blank=True)
    
    # Performance metrics
    latency_ms = models.IntegerField(null=True, blank=True)
    embedding_latency_ms = models.IntegerField(null=True, blank=True)
    retrieval_latency_ms = models.IntegerField(null=True, blank=True)
    reranking_latency_ms = models.IntegerField(null=True, blank=True)
    
    # Cost tracking
    embedding_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )
    reranking_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0
    )
    
    # User feedback
    has_feedback = models.BooleanField(default=False)
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_TYPES,
        null=True,
        blank=True
    )
    feedback_text = models.TextField(blank=True)
    
    # Context tracking
    session_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Session ID for tracking conversation context"
    )
    context_session = models.ForeignKey(
        'context_manager.ContextSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rag_queries'
    )
    
    # Integration tracking
    source_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source of the query: 'chat', 'agent', 'workflow', etc."
    )
    source_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the source entity"
    )
    
    class Meta:
        db_table = 'rag_query'
        verbose_name = 'RAG Query'
        verbose_name_plural = 'RAG Queries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['knowledge_base', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['workspace', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['session_id']),
            models.Index(fields=['source_type', 'source_id']),
        ]
    
    def __str__(self):
        return f"Query: {self.query_text[:50]}{'...' if len(self.query_text) > 50 else ''}"
    
    def mark_processing(self):
        """Mark query as processing"""
        self.status = 'processing'
        self.save(update_fields=['status'])
    
    def mark_completed(self, latency_ms=None, embedding_latency_ms=None, 
                      retrieval_latency_ms=None, reranking_latency_ms=None,
                      embedding_cost=None, reranking_cost=None):
        """Mark query as completed with performance metrics"""
        self.status = 'completed'
        
        if latency_ms is not None:
            self.latency_ms = latency_ms
        if embedding_latency_ms is not None:
            self.embedding_latency_ms = embedding_latency_ms
        if retrieval_latency_ms is not None:
            self.retrieval_latency_ms = retrieval_latency_ms
        if reranking_latency_ms is not None:
            self.reranking_latency_ms = reranking_latency_ms
        if embedding_cost is not None:
            self.embedding_cost = embedding_cost
        if reranking_cost is not None:
            self.reranking_cost = reranking_cost
            
        # Calculate total cost
        self.total_cost = self.embedding_cost + self.reranking_cost
        
        self.save(update_fields=[
            'status', 'latency_ms', 'embedding_latency_ms',
            'retrieval_latency_ms', 'reranking_latency_ms',
            'embedding_cost', 'reranking_cost', 'total_cost'
        ])
        
        # Update knowledge base last_queried timestamp
        self.knowledge_base.record_query()
    
    def mark_failed(self, error_message):
        """Mark query as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])
    
    def add_feedback(self, feedback_type, feedback_text=''):
        """Add user feedback to the query"""
        self.has_feedback = True
        self.feedback_type = feedback_type
        self.feedback_text = feedback_text
        self.save(update_fields=['has_feedback', 'feedback_type', 'feedback_text'])
    
    @classmethod
    @database_sync_to_async
    def create_query_async(cls, knowledge_base, query_text, user=None, workspace=None,
                         session_id='', source_type='', source_id=None,
                         retrieval_strategy='similarity', similarity_top_k=5,
                         mmr_diversity_bias=None, reranking_enabled=False):
        """Create a new query asynchronously"""
        return cls.objects.create(
            knowledge_base=knowledge_base,
            query_text=query_text,
            user=user,
            workspace=workspace,
            session_id=session_id,
            source_type=source_type,
            source_id=source_id,
            retrieval_strategy=retrieval_strategy,
            similarity_top_k=similarity_top_k,
            mmr_diversity_bias=mmr_diversity_bias,
            reranking_enabled=reranking_enabled
        )


class RAGQueryResult(BaseModel):
    """
    Represents a result from a RAG query.
    Links to the chunks that were retrieved and tracks relevance scores.
    """
    
    # Relationships
    query = models.ForeignKey(
        RAGQuery,
        on_delete=models.CASCADE,
        related_name='results'
    )
    chunk = models.ForeignKey(
        Chunk,
        on_delete=models.CASCADE,
        related_name='query_results'
    )
    
    # Retrieval metrics
    rank = models.IntegerField()
    relevance_score = models.FloatField()
    reranking_score = models.FloatField(null=True, blank=True)
    
    # User feedback
    is_relevant = models.BooleanField(null=True, blank=True)
    feedback_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'rag_query_result'
        verbose_name = 'Query Result'
        verbose_name_plural = 'Query Results'
        ordering = ['query', 'rank']
        indexes = [
            models.Index(fields=['query', 'rank']),
            models.Index(fields=['chunk', 'relevance_score']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['query', 'chunk'],
                name='unique_chunk_per_query'
            )
        ]
    
    def __str__(self):
        return f"Result {self.rank} for {self.query}"
    
    def mark_relevant(self, is_relevant, notes=''):
        """Mark this result as relevant or not"""
        self.is_relevant = is_relevant
        self.feedback_notes = notes
        self.save(update_fields=['is_relevant', 'feedback_notes'])
        
        # Update chunk retrieval statistics
        self.chunk.record_retrieval(self.relevance_score)
    
    @classmethod
    @database_sync_to_async
    def create_result_async(cls, query, chunk, rank, relevance_score, reranking_score=None):
        """Create a new query result asynchronously"""
        return cls.objects.create(
            query=query,
            chunk=chunk,
            rank=rank,
            relevance_score=relevance_score,
            reranking_score=reranking_score
        )