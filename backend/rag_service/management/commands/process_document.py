"""
Management command to process a document through the RAG pipeline.

This command processes a document through either:
1. The full RAG pipeline (extraction, chunking, embedding)
2. The rule-based direct pipeline (extraction only, no chunking/embedding)

Usage:
    # Full RAG pipeline:
    python manage.py process_document --kb_id=<knowledge_base_id> --file=<path_to_file>
    
    # Rule-based direct pipeline (no chunking/embedding):
    python manage.py process_document --kb_id=<knowledge_base_id> --file=<path_to_file> --rule-based
"""

import os
import logging
import asyncio
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from rag_service.models import KnowledgeBase, Document, Chunk
from rag_service.services.storage_retrieval import StorageService
from rag_service.services.extraction.text import TextExtractor
from rag_service.services.extraction.table_extractor import TableExtractor
from rag_service.services.extraction.layout_analyzer import LayoutAnalyzer
from rag_service.services.extraction.unified_extractor import UnifiedExtractor, ExtractionRequest, ExtractionTask
from rag_service.services.chunking.chunking_service import ChunkingService
from rag_service.services.document_pipeline import DocumentPipeline

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process a document through the RAG pipeline and save results to the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--kb_id",
            type=str,
            required=True,
            help="Knowledge base ID (UUID) to associate the document with",
        )
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the file to process",
        )
        parser.add_argument(
            "--title",
            type=str,
            default=None,
            help="Title for the document (defaults to filename)",
        )
        parser.add_argument(
            "--rule-based",
            action="store_true",
            help="Use rule-based extraction without chunking or embedding",
        )
        parser.add_argument(
            "--user_id",
            type=int,
            default=None,
            help="User ID to associate as the creator (defaults to first admin user)",
        )

    def handle(self, *args, **options):
        # Get command line arguments
        kb_id = options["kb_id"]
        file_path = options["file"]
        title = options["title"] or os.path.basename(file_path)
        user_id = options["user_id"]
        rule_based = options["rule_based"]

        # Validate inputs
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        try:
            knowledge_base = KnowledgeBase.objects.get(id=kb_id)
        except KnowledgeBase.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Knowledge base with ID {kb_id} not found"))
            return

        # Get user
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User with ID {user_id} not found"))
                return
        else:
            # Default to first admin user
            user = User.objects.filter(is_staff=True).first()
            if not user:
                self.stderr.write(self.style.ERROR("No admin user found"))
                return

        # Determine document type from file extension
        _, ext = os.path.splitext(file_path)
        doc_type = ext.lower().lstrip('.')
        if doc_type == 'pdf':
            doc_type = 'pdf'
        elif doc_type in ('docx', 'doc'):
            doc_type = 'docx'
        elif doc_type in ('txt', 'md', 'csv'):
            doc_type = ext.lower().lstrip('.')
        else:
            doc_type = 'other'

        # Run the async processing
        if rule_based:
            self.stdout.write(self.style.SUCCESS(f"Using rule-based pipeline without chunking or embedding"))
            asyncio.run(self.process_document_rule_based(kb_id, file_path, title, user_id))
        else:
            self.stdout.write(self.style.SUCCESS(f"Using full RAG pipeline with chunking and embedding"))
            asyncio.run(self.process_document(kb_id, file_path, title, user_id))

    async def process_document_rule_based(self, kb_id, file_path, title, user_id):
        """Process document using rule-based pipeline without chunking or embedding"""
        try:
            # Get user
            if user_id:
                get_user = sync_to_async(lambda: User.objects.get(id=user_id))
                user = await get_user()
            else:
                get_user = sync_to_async(lambda: User.objects.filter(is_staff=True).first())
                user = await get_user()

            # Initialize pipeline
            pipeline = DocumentPipeline()
            
            # Process document
            self.stdout.write(f"Processing {file_path} with rule-based pipeline...")
            result = await pipeline.process_document(
                file_path=file_path,
                knowledge_base_id=kb_id,
                title=title,
                created_by_id=user.id if user else None
            )
            
            # Output results
            if result.get('status') == 'completed':
                self.stdout.write(self.style.SUCCESS(
                    f"Document processed successfully: {result.get('document_id')}\n"
                    f"- Text length: {result.get('text_length', 0)} characters\n"
                    f"- Tables: {result.get('tables_count', 0)}\n"
                    f"- Layout blocks: {result.get('layout_blocks_count', 0)}\n"
                    f"- Processing time: {result.get('processing_time_ms', 0):.2f}ms"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"Document processing failed: {result.get('error', 'Unknown error')}"
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    async def process_document(self, kb_id, file_path, title, user_id):
        """Process document using full RAG pipeline with chunking and embedding"""
        self.stdout.write(self.style.SUCCESS(f"Processing document: {title}"))

        # Initialize services
        storage_service = StorageService()
        text_extractor = TextExtractor()
        table_extractor = TableExtractor()
        layout_analyzer = LayoutAnalyzer()
        unified_extractor = UnifiedExtractor()
        chunking_service = ChunkingService()

        # 1. Create document in database
        document = await sync_to_async(Document.objects.create)(
            knowledge_base=knowledge_base,
            title=title,
            document_type=doc_type,
            file_upload=None,  # In a real scenario, you'd link to a FileUpload
            status='pending',
            created_by=user
        )

        try:
            # 2. Process the document
            # Mark document as processing
            document.status = 'processing'
            await sync_to_async(document.save)()
            
            # Step 1: Extract text
            self.stdout.write("1. Extracting text...")
            text_result = text_extractor.extract(file_path)
            self.stdout.write(f"   Text extraction: {len(text_result['text'])} characters")
            
            # Step 2: Extract tables
            self.stdout.write("2. Extracting tables...")
            tables = []
            try:
                tables = await table_extractor.extract_tables(file_path)
                self.stdout.write(f"   Found {len(tables)} tables")
                for i, table in enumerate(tables):
                    if hasattr(table, 'shape'):
                        self.stdout.write(f"   Table {i+1}: {table.shape[0]} rows x {table.shape[1]} columns")
                    else:
                        self.stdout.write(f"   Table {i+1}: format unknown")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   Table extraction error: {e}"))
            
            # Step 3: Analyze layout
            self.stdout.write("3. Analyzing document layout...")
            layout_blocks = []
            try:
                layout_blocks = await layout_analyzer.analyze_layout(file_path)
                self.stdout.write(f"   Found {len(layout_blocks)} layout blocks")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   Layout analysis error: {e}"))
            
            # Step 4: Try unified extraction
            self.stdout.write("4. Trying unified extraction...")
            unified_result = None
            try:
                # Create extraction request
                request = ExtractionRequest(
                    file_path=file_path,
                    tasks=[ExtractionTask.TEXT, ExtractionTask.TABLES, ExtractionTask.LAYOUT],
                    organization=None,  # No organization for now
                    quality_priority='balanced',
                    max_pages=10
                )
                
                # Perform extraction
                unified_result = await unified_extractor.extract(request)
                
                if unified_result and unified_result.success:
                    self.stdout.write(f"   Unified extraction successful!")
                    self.stdout.write(f"   Text: {len(unified_result.text)} characters")
                    self.stdout.write(f"   Tables: {len(unified_result.tables)}")
                    self.stdout.write(f"   Layout blocks: {len(unified_result.layout_blocks)}")
                else:
                    self.stdout.write(self.style.WARNING(f"   Unified extraction failed: {unified_result.error if unified_result else 'Unknown error'}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   Unified extraction error: {e}"))
            
            # Step 5: Create extraction response for chunking
            self.stdout.write("5. Chunking document content...")
            extraction_response = {
                'text': text_result['text'],
                'tables': [{
                    'headers': table.columns.tolist() if hasattr(table, 'columns') else [],
                    'rows': table.values.tolist() if hasattr(table, 'values') else []
                } for table in tables if hasattr(table, 'columns')],
                'layout_blocks': [{
                    'type': getattr(block, 'block_type', 'text'),
                    'text': getattr(block, 'text', ''),
                    'position': getattr(block, 'position', {})
                } for block in layout_blocks],
                'metadata': {}
            }
            
            # Step 5: Use the chunking service to create chunks
            chunks = chunking_service.chunk_document(extraction_response, document)
            
            # Verify chunks were created
            if chunks:
                self.stdout.write(f"   Created {len(chunks)} chunks")
                
                # Save chunks to the database
                for i, chunk in enumerate(chunks):
                    # Ensure chunk is associated with document
                    chunk.document = document
                    # Save chunk to database
                    await sync_to_async(chunk.save)()
                    
                    # Log first 3 chunks
                    if i < 3:
                        self.stdout.write(f"   Chunk {i+1}: {chunk.chunk_type} ({len(chunk.content)} chars)")
            else:
                self.stdout.write(self.style.WARNING("   No chunks were created"))
            
            # Mark document as completed
            document.status = 'completed'
            await sync_to_async(document.save)()
            
            self.stdout.write(self.style.SUCCESS(f"Document processed successfully: {document.id}"))
            
        except Exception as e:
            document.status = 'failed'
            document.error_message = str(e)
            await sync_to_async(document.save)()
            self.stdout.write(self.style.ERROR(f"Error processing document: {e}"))
