import os
import json
import base64
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from mcp.models import MCPServerConnection
from cryptography.fernet import Fernet, InvalidToken


class Command(BaseCommand):
    help = 'Fix MCP encryption key and connection auth data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--connection-id',
            type=int,
            help='ID of the connection to fix'
        )
        parser.add_argument(
            '--token',
            type=str,
            help='Notion API token to use'
        )
        parser.add_argument(
            '--generate-key',
            action='store_true',
            help='Generate a new encryption key'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all connections'
        )

    def handle(self, *args, **options):
        # Check if MCP_ENCRYPTION_KEY is set in environment
        encryption_key = os.environ.get('MCP_ENCRYPTION_KEY')
        
        if options['generate_key']:
            # Generate a new Fernet key
            key = Fernet.generate_key().decode()
            self.stdout.write(f"Generated new encryption key: {key}")
            self.stdout.write("\nAdd this to your .env file as:")
            self.stdout.write(f"MCP_ENCRYPTION_KEY={key}")
            return
            
        if options['list']:
            # List all connections
            connections = MCPServerConnection.objects.all()
            self.stdout.write(f"Found {connections.count()} connections:")
            
            for conn in connections:
                self.stdout.write(f"\nConnection ID: {conn.id}")
                self.stdout.write(f"Name: {conn.connection_name}")
                self.stdout.write(f"Server: {conn.server.display_name if conn.server else 'None'}")
                self.stdout.write(f"Auth data present: {conn.auth_data is not None}")
                
                if conn.auth_data and encryption_key:
                    try:
                        decrypted = conn.decrypt_auth_data()
                        self.stdout.write(f"✅ Auth data can be decrypted: {decrypted}")
                    except Exception as e:
                        self.stdout.write(f"❌ Failed to decrypt auth data: {str(e)}")
            return
            
        # Fix a specific connection
        if not options['connection_id']:
            raise CommandError("Please provide a connection ID with --connection-id")
            
        if not options['token']:
            raise CommandError("Please provide a Notion API token with --token")
            
        if not encryption_key:
            self.stdout.write(self.style.ERROR("MCP_ENCRYPTION_KEY environment variable is not set"))
            self.stdout.write("Please set it in your .env file or use --generate-key to create a new one")
            return
            
        try:
            # Test if the encryption key is valid
            fernet = Fernet(encryption_key.encode())
            test_data = fernet.encrypt(b"test")
            fernet.decrypt(test_data)
            self.stdout.write("✅ Encryption key is valid")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Invalid encryption key: {str(e)}"))
            return
            
        # Get the connection
        try:
            connection = MCPServerConnection.objects.get(id=options['connection_id'])
        except MCPServerConnection.DoesNotExist:
            raise CommandError(f"Connection with ID {options['connection_id']} does not exist")
            
        # Create auth data with the token
        auth_data = {"token": options['token']}
        
        # Encrypt and save
        try:
            connection.encrypt_auth_data(auth_data)
            connection.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Successfully updated auth data for connection {connection.connection_name}"))
            
            # Verify decryption
            try:
                decrypted = connection.decrypt_auth_data()
                self.stdout.write(f"✅ Verified decryption: {decrypted}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to verify decryption: {str(e)}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to update auth data: {str(e)}"))
