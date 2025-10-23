from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum

from .models import Drawing, TakeoffElement, TakeoffExtraction, TakeoffProject


class TakeoffElementInline(admin.TabularInline):
    model = TakeoffElement
    fields = ('element_id', 'element_type', 'confidence_score', 'verified')
    readonly_fields = ('confidence_score',)
    extra = 0
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return True


class TakeoffExtractionInline(admin.TabularInline):
    model = TakeoffExtraction
    fields = ('status', 'extraction_method', 'element_count', 'confidence_score', 'verified')
    readonly_fields = ('element_count', 'confidence_score')
    extra = 0
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Drawing)
class DrawingAdmin(admin.ModelAdmin):
    list_display = (
        'drawing_number', 'drawing_title', 'client', 'project',
        'date', 'page_count', 'organization_name', 'is_active'
    )
    list_filter = ('is_active', 'file_type', 'date')
    search_fields = ('drawing_number', 'drawing_title', 'client', 'project')
    readonly_fields = ('file_size',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('drawing_number', 'drawing_title', 'organization', 'created_by')
        }),
        ('Project Information', {
            'fields': ('client', 'project', 'location', 'date', 'revision', 'scale')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_type', 'file_size', 'page_count', 'rag_document')
        }),
        ('Additional Information', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    inlines = [TakeoffExtractionInline]
    
    def organization_name(self, obj):
        return obj.organization.name
    organization_name.short_description = 'Organization'


@admin.register(TakeoffElement)
class TakeoffElementAdmin(admin.ModelAdmin):
    list_display = (
        'element_id', 'element_type', 'drawing_info',
        'confidence_score', 'verified'
    )
    list_filter = ('element_type', 'verified')
    search_fields = ('element_id', 'element_type', 'drawing__drawing_number')
    readonly_fields = ('specifications_preview', 'location_preview')
    fieldsets = (
        ('Basic Information', {
            'fields': ('drawing', 'extraction', 'element_id', 'element_type')
        }),
        ('Specifications', {
            'fields': ('specifications_preview',)
        }),
        ('Location', {
            'fields': ('location_preview',)
        }),
        ('Verification', {
            'fields': ('confidence_score', 'verified', 'verified_by', 'verified_at')
        }),
    )
    
    def drawing_info(self, obj):
        return f"{obj.drawing.drawing_number}: {obj.drawing.drawing_title}"
    drawing_info.short_description = 'Drawing'
    
    def specifications_preview(self, obj):
        """Format the specifications JSON for display in admin"""
        if not obj.specifications:
            return "No specifications available"
            
        html = '<div style="max-height: 400px; overflow-y: auto;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align: left; padding: 8px;">Property</th>'
        html += '<th style="text-align: left; padding: 8px;">Value</th></tr>'
        
        for key, value in obj.specifications.items():
            html += f'<tr><td style="padding: 4px;">{key}</td>'
            
            # Handle nested objects
            if isinstance(value, dict):
                nested_values = ', '.join([f'{k}: {v}' for k, v in value.items()])
                html += f'<td style="padding: 4px;">{nested_values}</td></tr>'
            else:
                html += f'<td style="padding: 4px;">{value}</td></tr>'
            
        html += '</table>'
        html += '</div>'
        return format_html(html)
    specifications_preview.short_description = 'Specifications'
    
    def location_preview(self, obj):
        """Format the location JSON for display in admin"""
        if not obj.location:
            return "No location data available"
            
        html = '<div style="max-height: 400px; overflow-y: auto;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align: left; padding: 8px;">Property</th>'
        html += '<th style="text-align: left; padding: 8px;">Value</th></tr>'
        
        for key, value in obj.location.items():
            html += f'<tr><td style="padding: 4px;">{key}</td>'
            
            # Handle coordinates array
            if key == 'coordinates' and isinstance(value, list):
                coords_str = '<br>'.join([f'({c.get("x", 0)}, {c.get("y", 0)})' for c in value])
                html += f'<td style="padding: 4px;">{coords_str}</td></tr>'
            else:
                html += f'<td style="padding: 4px;">{value}</td></tr>'
            
        html += '</table>'
        html += '</div>'
        return format_html(html)
    location_preview.short_description = 'Location'


@admin.register(TakeoffExtraction)
class TakeoffExtractionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'drawing_info', 'status', 'extraction_method',
        'element_count', 'confidence_score', 'verified'
    )
    list_filter = ('status', 'extraction_method', 'verified')
    search_fields = ('drawing__drawing_number', 'drawing__drawing_title')
    readonly_fields = ('element_count', 'processing_time_ms', 'extraction_cost_usd', 'verified_at', 'elements_preview')
    fieldsets = (
        ('Basic Information', {
            'fields': ('drawing', 'status', 'extraction_method')
        }),
        ('User Information', {
            'fields': ('created_by', 'verified', 'verified_by', 'verified_at')
        }),
        ('Processing Information', {
            'fields': ('extraction_date', 'processing_time_ms', 'processing_error', 'extraction_cost_usd')
        }),
        ('Quality Information', {
            'fields': ('confidence_score', 'element_count')
        }),
        ('Elements', {
            'fields': ('elements_preview',),
            'classes': ('collapse',)
        }),
    )
    inlines = [TakeoffElementInline]
    
    def drawing_info(self, obj):
        return f"{obj.drawing.drawing_number}: {obj.drawing.drawing_title}"
    drawing_info.short_description = 'Drawing'
    
    def elements_preview(self, obj):
        """Format the elements JSON for display in admin"""
        if not obj.elements:
            return "No elements available"
            
        items = obj.elements.get('items', [])
        if not items:
            return "No elements found"
            
        # Format the elements with their types and counts
        html = '<div style="max-height: 400px; overflow-y: auto;">'
        
        # Group elements by type
        element_types = {}
        for item in items:
            element_type = item.get('element_type', 'unknown')
            if element_type not in element_types:
                element_types[element_type] = []
            element_types[element_type].append(item)
        
        # Display summary
        html += f'<h4>Total Elements: {len(items)}</h4>'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align: left; padding: 8px;">Element Type</th>'
        html += '<th style="text-align: right; padding: 8px;">Count</th></tr>'
        
        for element_type, elements in element_types.items():
            html += f'<tr><td style="padding: 4px;">{element_type}</td>'
            html += f'<td style="text-align: right; padding: 4px;">{len(elements)}</td></tr>'
            
        html += '</table>'
        
        # Display sample elements (first 5)
        if items:
            html += '<h4>Sample Elements</h4>'
            html += '<table style="width: 100%; border-collapse: collapse;">'
            html += '<tr><th>ID</th><th>Type</th><th>Specifications</th></tr>'
            
            for item in items[:5]:
                item_id = item.get('element_id', 'N/A')
                item_type = item.get('element_type', 'N/A')
                specs = item.get('specifications', {})
                specs_str = ', '.join([f'{k}: {v}' for k, v in specs.items()][:3])
                if len(specs) > 3:
                    specs_str += '...'
                    
                html += f'<tr><td>{item_id}</td><td>{item_type}</td><td>{specs_str}</td></tr>'
                
            html += '</table>'
        
        html += '</div>'
        return format_html(html)
    elements_preview.short_description = 'Elements Preview'


@admin.register(TakeoffProject)
class TakeoffProjectAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'client', 'status', 'drawing_count',
        'extraction_count', 'verified_extraction_count', 'organization_name'
    )
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'client', 'description')
    readonly_fields = ('drawing_count', 'extraction_count', 'verified_extraction_count')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'organization', 'created_by')
        }),
        ('Client Information', {
            'fields': ('client', 'location')
        }),
        ('Dates', {
            'fields': ('start_date', 'due_date', 'completed_date')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Statistics', {
            'fields': ('drawing_count', 'extraction_count', 'verified_extraction_count')
        }),
        ('Additional Information', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def organization_name(self, obj):
        return obj.organization.name
    organization_name.short_description = 'Organization'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.update_statistics()
