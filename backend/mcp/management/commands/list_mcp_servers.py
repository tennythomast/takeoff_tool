from django.core.management.base import BaseCommand
from mcp.models import MCPServerRegistry
from django.utils import timezone
import json

class Command(BaseCommand):
    help = 'List all MCP servers in the registry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['text', 'json'],
            default='text',
            help='Output format (text or json)'
        )
        parser.add_argument(
            '--verified-only',
            action='store_true',
            help='Show only verified servers'
        )

    def handle(self, *args, **options):
        output_format = options['format']
        verified_only = options['verified_only']
        
        # Build query
        query = MCPServerRegistry.objects.all()
        if verified_only:
            query = query.filter(is_verified=True)
        
        # Order by name
        servers = query.order_by('qualified_name')
        
        if output_format == 'json':
            server_data = []
            for server in servers:
                server_data.append({
                    'qualified_name': server.qualified_name,
                    'display_name': server.display_name,
                    'description': server.description,
                    'category': server.category,
                    'server_type': server.server_type,
                    'is_verified': server.is_verified,
                    'version': server.version,
                    'capabilities': server.capabilities,
                    'supported_operations': server.supported_operations,
                })
            self.stdout.write(json.dumps(server_data, indent=2))
        else:
            # Text format
            self.stdout.write(self.style.SUCCESS(f"Found {servers.count()} MCP servers:"))
            self.stdout.write("=" * 50)
            
            for server in servers:
                self.stdout.write(self.style.SUCCESS(f"Name: {server.qualified_name}"))
                self.stdout.write(f"Display Name: {server.display_name}")
                self.stdout.write(f"Description: {server.description}")
                self.stdout.write(f"Category: {server.category}")
                self.stdout.write(f"Type: {server.server_type}")
                self.stdout.write(f"Verified: {'Yes' if server.is_verified else 'No'}")
                self.stdout.write(f"Version: {server.version}")
                self.stdout.write(f"Capabilities: {', '.join(server.capabilities) if server.capabilities else 'None'}")
                self.stdout.write(f"Operations: {', '.join(server.supported_operations) if server.supported_operations else 'None'}")
                self.stdout.write("-" * 50)
