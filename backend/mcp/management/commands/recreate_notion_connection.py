from django.core.management.base import BaseCommand
from django.conf import settings
from mcp.models import MCPServerConnection, MCPServerRegistry
import json
from cryptography.fernet import Fernet
import traceback


class Command(BaseCommand):
    help = 'Recreates a Notion connection with proper auth data structure'

    def add_arguments(self, parser):
        parser.add_argument('--connection-id', type=int, help='ID of the connection to recreate')
        parser.add_argument('--token', type=str, help='New Notion API token to use')
        parser.add_argument('--list', action='store_true', help='List all Notion connections')

    def handle(self, *args, **options):
        if options['list']:
            self.list_connections()
            return

        connection_id = options['connection_id']
        token = options['token']

        if not connection_id:
            self.stdout.write(self.style.ERROR('Connection ID is required'))
            return

        if not token:
            self.stdout.write(self.style.ERROR('Token is required'))
            return

        try:
            # Get the connection
            connection = MCPServerConnection.objects.get(id=connection_id)
            
            # Check if it's a Notion connection
            if 'notion' not in connection.server.qualified_name.lower():
                self.stdout.write(self.style.ERROR(f'Connection {connection_id} is not a Notion connection'))
                return
            
            # Create proper auth data structure
            auth_data = {'token': token}
            
            # Print current encryption key
            self.stdout.write(f"Using MCP_ENCRYPTION_KEY: {settings.MCP_ENCRYPTION_KEY[:5]}...")
            
            # Test encryption and decryption
            cipher = Fernet(settings.MCP_ENCRYPTION_KEY.encode())
            auth_json = json.dumps(auth_data)
            encrypted_data = cipher.encrypt(auth_json.encode())
            
            # Test decryption
            decrypted_data = cipher.decrypt(encrypted_data)
            decrypted_auth = json.loads(decrypted_data.decode())
            
            if decrypted_auth.get('token') != token:
                self.stdout.write(self.style.ERROR('Encryption/decryption test failed'))
                return
            
            # Update the connection
            connection.auth_data = encrypted_data.decode()
            connection.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully updated connection {connection.connection_name} (ID: {connection.id})'))
            
            # Verify the update
            try:
                auth_data = connection.decrypt_auth_data()
                self.stdout.write(self.style.SUCCESS(f'Verification successful. Token starts with: {auth_data["token"][:4]}...'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Verification failed: {str(e)}'))
                traceback.print_exc()
                
        except MCPServerConnection.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Connection with ID {connection_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            traceback.print_exc()
    
    def list_connections(self):
        """List all Notion connections"""
        notion_connections = MCPServerConnection.objects.filter(
            server__qualified_name__icontains='notion'
        )
        
        self.stdout.write(f'Found {notion_connections.count()} Notion connections:')
        for conn in notion_connections:
            self.stdout.write(f'ID: {conn.id}, Name: {conn.connection_name}, Server: {conn.server.qualified_name}')
