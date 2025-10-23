# rag_service/services/chunking/chunking_service.py

from typing import Dict, List, Any, Optional


class ChunkingService:
    """
    Content-aware chunking service that preserves structure and coordinates.
    Works with the unified_extractor ExtractionResponse format.
    """
    
    def chunk_document(self, extraction_response: Dict[str, Any], document) -> List:
        """
        Main entry point: route to appropriate chunking strategy.
        
        Args:
            extraction_response: The response from document_processor.process_file()
                                Contains: text, tables, layout_blocks, entities, metadata
            document: The Document model instance to associate chunks with
            
        Returns:
            List[Chunk]: List of created document chunks
        """
        chunks = []
        chunk_index = 0
        
        # Extract data from the unified extractor response format
        tables = extraction_response.get('tables', [])
        layout_blocks = extraction_response.get('layout_blocks', [])
        text_content = extraction_response.get('text', '')
        metadata = extraction_response.get('metadata', {})
        
        # 1. Chunk document metadata (atomic)
        if self._has_drawing_metadata(metadata):
            metadata_chunk = self._chunk_drawing_metadata(
                metadata,
                chunk_index,
                document
            )
            chunks.append(metadata_chunk)
            chunk_index += 1
        
        # 2. Chunk tables (atomic)
        if tables:
            for table in tables:
                table_chunk = self._chunk_table(table, chunk_index, document)
                chunks.append(table_chunk)
                chunk_index += 1
        
        # 3. Chunk visual elements from layout_blocks (spatial grouping)
        visual_elements = self._extract_visual_elements_from_layout(layout_blocks)
        if visual_elements:
            visual_chunks = self._chunk_visual_elements(
                visual_elements,
                chunk_index,
                document
            )
            chunks.extend(visual_chunks)
            chunk_index += len(visual_chunks)
        
        # 4. Chunk text content if available
        if text_content:
            text_chunks = self._chunk_text_content(
                text_content,
                chunk_index,
                document
            )
            chunks.extend(text_chunks)
            chunk_index += len(text_chunks)
        
        # 5. Link chunks (cross-reference schedules to visual elements)
        self._link_chunks(chunks, extraction_response)
        
        return chunks
    
    
    def _has_drawing_metadata(self, metadata: Dict) -> bool:
        """Check if metadata contains drawing-specific information."""
        drawing_fields = ['drawing_number', 'drawing_title', 'drawing_type', 'revision']
        return any(metadata.get(field) for field in drawing_fields)
    
    
    def _extract_visual_elements_from_layout(self, layout_blocks: List[Dict]) -> Dict:
        """
        Extract visual elements from layout_blocks.
        
        Args:
            layout_blocks: Layout blocks from unified extractor
            
        Returns:
            Dict with element_groups structure
        """
        element_groups = []
        
        for block in layout_blocks:
            # Check if this is a visual element block
            if block.get('type') in ['visual_element', 'figure', 'image', 'diagram']:
                element_groups.append({
                    'group_id': block.get('id', ''),
                    'element_type': block.get('element_type', block.get('type', 'unknown')),
                    'count': block.get('count', 1),
                    'zone': block.get('zone', ''),
                    'cluster_center': block.get('center', {}),
                    'elements': block.get('elements', [block]),  # Wrap single element in list
                    'spatial_description': block.get('description', block.get('text', ''))
                })
        
        return {'element_groups': element_groups} if element_groups else {}
    
    
    def _chunk_table(self, table_data: Dict, chunk_index: int, document) -> object:
        """
        Strategy A: Keep tables as atomic units.
        
        Args:
            table_data: Table data from extraction result
            chunk_index: Index for this chunk
            document: Document model instance
            
        Returns:
            Chunk: A table chunk
        """
        # Build human-readable content
        content = self._format_table_as_text(table_data)
        
        # Build rich metadata
        metadata = {
            "chunk_type": "table",
            "table_type": table_data.get("table_type", "general"),
            "table_caption": table_data.get("caption", ""),
            "contains_counts": self._table_has_quantities(table_data),
            "contains_specs": True,
            "column_headers": table_data.get("headers", []),
            "row_count": len(table_data.get("rows", [])),
            "page_number": table_data.get("page_number"),
            "bounding_box": table_data.get("bounding_box"),
            "element_types": table_data.get("element_types_to_count", []),
            "searchable_terms": self._extract_searchable_terms(table_data),
        }
        
        # Create chunk using the extended Chunk model
        from rag_service.models import Chunk
        
        chunk = Chunk(
            document=document,
            chunk_index=chunk_index,
            chunk_type='table',
            content=content,
            metadata=metadata,
            token_count=self._estimate_tokens(content)
        )
        
        return chunk
    
    
    def _chunk_drawing_metadata(self, metadata_data: Dict, chunk_index: int, document) -> object:
        """
        Strategy A: Keep metadata as atomic unit.
        
        Args:
            metadata_data: Drawing metadata from extraction result
            chunk_index: Index for this chunk
            document: Document model instance
            
        Returns:
            Chunk: A metadata chunk
        """
        # Build human-readable content
        content = self._format_metadata_as_text(metadata_data)
        
        # Build rich metadata
        metadata = {
            "chunk_type": "metadata",
            "metadata_type": "drawing_metadata",
            "drawing_number": metadata_data.get("drawing_number"),
            "revision": metadata_data.get("revision"),
            "drawing_title": metadata_data.get("drawing_title"),
            "scale": metadata_data.get("scale"),
            "units": metadata_data.get("units"),
            "date": metadata_data.get("date"),
            "drawn_by": metadata_data.get("drawn_by"),
            "project_name": metadata_data.get("project_name"),
            "drawing_type": metadata_data.get("drawing_type"),
            "searchable_terms": self._extract_metadata_searchable_terms(metadata_data),
        }
        
        # Create chunk using the extended Chunk model
        from rag_service.models import Chunk
        
        chunk = Chunk(
            document=document,
            chunk_index=chunk_index,
            chunk_type='drawing_metadata',
            content=content,
            metadata=metadata,
            token_count=self._estimate_tokens(content)
        )
        
        return chunk
    
    
    def _chunk_visual_elements(
        self, 
        visual_data: Dict, 
        start_index: int, 
        document
    ) -> List:
        """
        Strategy C: Spatial-aware chunking that preserves ALL element coordinates.
        
        CRITICAL: Each chunk contains complete coordinate data for overlay visualization.
        
        Args:
            visual_data: Visual elements data from extraction result
            start_index: Starting index for chunks
            document: Document model instance
            
        Returns:
            List[Chunk]: List of visual element chunks
        """
        chunks = []
        element_groups = visual_data.get("element_groups", [])
        
        # Import the Chunk model
        from rag_service.models import Chunk
        
        for i, group in enumerate(element_groups):
            # Build human-readable content
            content = self._format_visual_group_as_text(group)
            
            # Build rich metadata with COMPLETE coordinate preservation
            metadata = {
                "chunk_type": "visual_element_group",
                "group_id": group.get("group_id"),
                "element_type": group.get("element_type"),
                "element_count": group.get("count"),
                "zone": group.get("zone"),
                "quadrant": self._determine_quadrant(group.get("cluster_center")),
                
                # Spatial information
                "cluster_center": group.get("cluster_center"),
                "bounding_box": self._calculate_group_bounding_box(group.get("elements", [])),
                "spatial_description": group.get("spatial_description"),
                
                # CRITICAL: Store ALL element coordinates
                "elements": group.get("elements", []),  # Complete array with all coordinates
                
                # Schedule linkage
                "linked_to_schedule": False,  # Will be set in _link_chunks
                "schedule_chunk_id": None,
                "schedule_required_quantity": None,
                "validation_status": None,
                
                # Searchable
                "contains_counts": True,
                "searchable_terms": self._extract_visual_searchable_terms(group),
            }
            
            chunk = Chunk(
                document=document,
                chunk_index=start_index + i,
                chunk_type='visual_element_group',
                content=content,
                metadata=metadata,
                token_count=self._estimate_tokens(content)
            )
            
            chunks.append(chunk)
        
        return chunks
    
    
    def _chunk_text_content(self, text_content: str, start_index: int, document) -> List:
        """
        Chunk text content using a sliding window approach.
        
        Args:
            text_content: Raw text content to chunk
            start_index: Starting index for chunks
            document: Document model instance
            
        Returns:
            List[Chunk]: List of text chunks
        """
        from rag_service.models import Chunk
        
        # Simple chunking parameters
        chunk_size = 1000  # characters
        chunk_overlap = 200  # characters
        
        chunks = []
        text_length = len(text_content)
        
        # Skip if text is too short
        if text_length < 100:
            return []
        
        # Create chunks with overlap
        i = 0
        chunk_count = 0
        while i < text_length:
            # Calculate chunk boundaries
            end = min(i + chunk_size, text_length)
            
            # Extract chunk text
            chunk_text = text_content[i:end]
            
            # Create chunk
            chunk = Chunk(
                document=document,
                chunk_index=start_index + chunk_count,
                chunk_type='text',
                content=chunk_text,
                metadata={
                    "chunk_type": "text",
                    "position": chunk_count,
                    "start_char": i,
                    "end_char": end,
                },
                token_count=self._estimate_tokens(chunk_text)
            )
            
            chunks.append(chunk)
            chunk_count += 1
            
            # Move to next chunk with overlap
            i += (chunk_size - chunk_overlap)
            
            # Ensure we don't create tiny chunks at the end
            if i < text_length and (text_length - i) < chunk_overlap:
                break
        
        return chunks
    
    
    def _link_chunks(self, chunks: List, extraction_response: Dict[str, Any]):
        """
        Cross-reference chunks to establish relationships.
        
        Critical linkages:
        - Schedule tables → Visual element groups (validate counts)
        - Metadata → All chunks (document context)
        
        Args:
            chunks: List of created chunks
            extraction_response: Original extraction response from document processor
        """
        # Find schedule tables
        schedule_chunks = [c for c in chunks if c.metadata.get("table_type") == "schedule"]
        
        # Find visual element chunks
        visual_chunks = [c for c in chunks if c.chunk_type == "visual_element_group"]
        
        # Link schedule quantities to visual element groups
        for schedule_chunk in schedule_chunks:
            element_types = schedule_chunk.metadata.get("element_types", [])
            
            for element_type in element_types:
                # Find matching visual chunks
                matching_visual = [
                    vc for vc in visual_chunks 
                    if vc.metadata.get("element_type") == element_type
                ]
                
                if matching_visual:
                    visual_chunk = matching_visual[0]
                    
                    # Get required quantity from schedule
                    required_qty = self._extract_quantity_from_schedule(
                        schedule_chunk, 
                        element_type
                    )
                    
                    # Update visual chunk metadata
                    visual_chunk.metadata["linked_to_schedule"] = True
                    visual_chunk.metadata["schedule_chunk_id"] = str(schedule_chunk.id)
                    visual_chunk.metadata["schedule_required_quantity"] = required_qty
                    
                    # Validate count
                    actual_count = visual_chunk.metadata.get("element_count")
                    visual_chunk.metadata["validation_status"] = (
                        "match" if actual_count == required_qty else "mismatch"
                    )
                    
                    # Create bidirectional relationship after saving
                    if hasattr(visual_chunk, 'id') and visual_chunk.id and hasattr(schedule_chunk, 'id') and schedule_chunk.id:
                        visual_chunk.related_chunks.add(schedule_chunk)
                        schedule_chunk.related_chunks.add(visual_chunk)
    
    
    # Helper methods
    
    def _format_table_as_text(self, table_data: Dict) -> str:
        """Convert table to human-readable text for embedding."""
        caption = table_data.get("caption", "Table")
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        text = f"{caption}\n\n"
        text += " | ".join(headers) + "\n"
        text += "-" * (len(" | ".join(headers))) + "\n"
        
        for row in rows:
            text += " | ".join(str(cell) for cell in row) + "\n"
        
        return text
    
    
    def _format_metadata_as_text(self, metadata_data: Dict) -> str:
        """Convert drawing metadata to human-readable text for embedding."""
        text = "Drawing Information:\n"
        
        # Add key metadata fields
        if metadata_data.get("drawing_number"):
            text += f"Number: {metadata_data.get('drawing_number')}\n"
        
        if metadata_data.get("drawing_title"):
            text += f"Title: {metadata_data.get('drawing_title')}\n"
        
        if metadata_data.get("revision"):
            text += f"Revision: {metadata_data.get('revision')}\n"
        
        if metadata_data.get("scale"):
            text += f"Scale: {metadata_data.get('scale')}"
            if metadata_data.get("units"):
                text += f" ({metadata_data.get('units')})\n"
            else:
                text += "\n"
        
        if metadata_data.get("date"):
            text += f"Date: {metadata_data.get('date')}\n"
        
        if metadata_data.get("drawn_by"):
            text += f"Author: {metadata_data.get('drawn_by')}\n"
        
        if metadata_data.get("project_name"):
            text += f"Project: {metadata_data.get('project_name')}\n"
        
        if metadata_data.get("drawing_type"):
            text += f"Type: {metadata_data.get('drawing_type')}\n"
        
        return text
    
    
    def _format_visual_group_as_text(self, group: Dict) -> str:
        """Convert visual element group to human-readable text for embedding."""
        element_type = group.get("element_type", "element")
        count = group.get("count", 0)
        spatial_desc = group.get("spatial_description", "")
        
        text = f"{element_type}: {count} instances\n"
        text += f"Location: {spatial_desc}\n"
        
        # Add first few element details as example
        elements = group.get("elements", [])[:3]
        if elements:
            text += "\nElement details:\n"
            for elem in elements:
                center = elem.get("center_point", {})
                text += f"- {elem.get('element_id')}: position ({center.get('x')}, {center.get('y')})\n"
        
        if len(group.get("elements", [])) > 3:
            text += f"... and {len(group.get('elements', [])) - 3} more\n"
        
        return text
    
    
    def _determine_quadrant(self, center_point: Dict) -> str:
        """Determine quadrant based on image center (assuming standard image dimensions)."""
        # This would need actual image dimensions - simplified for now
        x = center_point.get("x", 0) if center_point else 0
        y = center_point.get("y", 0) if center_point else 0
        
        # Assuming typical A4 scan at 300 DPI: ~2480 x 3508 pixels
        mid_x, mid_y = 1240, 1754
        
        if x < mid_x and y < mid_y:
            return "Q1_top_left"
        elif x >= mid_x and y < mid_y:
            return "Q2_top_right"
        elif x < mid_x and y >= mid_y:
            return "Q3_bottom_left"
        else:
            return "Q4_bottom_right"
    
    
    def _calculate_group_bounding_box(self, elements: List[Dict]) -> Dict:
        """Calculate bounding box that encompasses all elements in group."""
        if not elements:
            return {}
        
        min_x = min((e.get("bounding_box", {}).get("x", 0) for e in elements), default=0)
        min_y = min((e.get("bounding_box", {}).get("y", 0) for e in elements), default=0)
        
        max_x = max((e.get("bounding_box", {}).get("x", 0) + 
                   e.get("bounding_box", {}).get("width", 0) for e in elements), default=0)
        max_y = max((e.get("bounding_box", {}).get("y", 0) + 
                   e.get("bounding_box", {}).get("height", 0) for e in elements), default=0)
        
        return {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y
        }
    
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return int(len(text.split()) * 1.3)  # Rough estimate
    
    
    def _table_has_quantities(self, table_data: Dict) -> bool:
        """Check if a table contains quantity information."""
        # Simple heuristic: check for numeric values in the table
        rows = table_data.get("rows", [])
        for row in rows:
            for cell in row:
                # Check if cell is numeric or contains numeric values
                if isinstance(cell, (int, float)) or (
                    isinstance(cell, str) and any(c.isdigit() for c in cell)):
                    return True
        return False
    
    
    def _extract_quantity_from_schedule(self, schedule_chunk, element_type: str) -> int:
        """Extract the required quantity for an element type from a schedule table."""
        # Default to 0 if we can't find a quantity
        default_qty = 0
        
        # Get table data from metadata
        table_data = schedule_chunk.metadata
        rows = table_data.get("rows", [])
        headers = table_data.get("headers", [])
        
        # Try to find element type column and quantity column
        type_col_idx = -1
        qty_col_idx = -1
        
        # Look for likely column headers
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if "type" in header_lower or "element" in header_lower or "item" in header_lower:
                type_col_idx = i
            elif "qty" in header_lower or "count" in header_lower or "number" in header_lower or "quantity" in header_lower:
                qty_col_idx = i
        
        # If we found both columns, look for the element type
        if type_col_idx >= 0 and qty_col_idx >= 0:
            for row in rows:
                if len(row) > max(type_col_idx, qty_col_idx):
                    row_type = str(row[type_col_idx]).lower()
                    if element_type.lower() in row_type:
                        try:
                            return int(row[qty_col_idx])
                        except (ValueError, TypeError):
                            # Not a valid integer
                            pass
        
        return default_qty
    
    
    def _extract_searchable_terms(self, table_data: Dict) -> List[str]:
        """Extract searchable terms from table data."""
        terms = []
        
        # Add caption
        caption = table_data.get("caption")
        if caption:
            terms.append(caption)
        
        # Add headers
        headers = table_data.get("headers", [])
        terms.extend(headers)
        
        # Add important cell values
        rows = table_data.get("rows", [])
        for row in rows:
            for cell in row:
                cell_str = str(cell)
                # Only add significant text (not just numbers)
                if len(cell_str) > 3 and not cell_str.isdigit():
                    terms.append(cell_str)
        
        return terms
    
    
    def _extract_metadata_searchable_terms(self, metadata_data: Dict) -> List[str]:
        """Extract searchable terms from drawing metadata."""
        terms = []
        
        # Add key metadata fields
        if metadata_data.get("drawing_number"):
            terms.append(metadata_data.get("drawing_number"))
        
        if metadata_data.get("drawing_title"):
            terms.append(metadata_data.get("drawing_title"))
        
        if metadata_data.get("project_name"):
            terms.append(metadata_data.get("project_name"))
        
        if metadata_data.get("drawing_type"):
            terms.append(metadata_data.get("drawing_type"))
        
        return terms
    
    
    def _extract_visual_searchable_terms(self, group: Dict) -> List[str]:
        """Extract searchable terms from visual element group."""
        terms = []
        
        # Add element type
        if group.get("element_type"):
            terms.append(group.get("element_type"))
        
        # Add spatial description
        if group.get("spatial_description"):
            terms.append(group.get("spatial_description"))
        
        # Add zone information
        if group.get("zone"):
            terms.append(f"Zone {group.get('zone')}")
        
        return terms