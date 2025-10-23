import json
import traceback
from django.core.management.base import BaseCommand
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
from mcp.models import MCPServerConnection, MCPServerRegistry

class Command(BaseCommand):
    help = 'Fix auth_data structure for Notion connections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update the connection with a new token',
        )
        parser.add_argument(
            '--token',
            type=str,
            help='New Notion API token to use (only with --force-update)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking Notion connections...'))
        
        force_update = options.get('force_update', False)
        new_token = options.get('token')
        
        # Get all Notion connections
        notion_connections = MCPServerConnection.objects.filter(
            server__qualified_name__contains='notion'
        )
        
        self.stdout.write(f"Found {notion_connections.count()} Notion connections")
        
        for conn in notion_connections:
            self.stdout.write(f"\nProcessing connection: {conn.connection_name} (ID: {conn.id})")
            self.stdout.write(f"  Server: {conn.server.qualified_name}")
            self.stdout.write(f"  Auth data present: {'Yes' if conn.auth_data else 'No'}")
            
            if force_update and new_token:
                self.stdout.write(self.style.WARNING(f"  Forcing update with new token"))
                
                # Create new auth_data with the provided token
                new_auth_data = {'token': new_token}
                
                try:
                    # Encrypt and save the new auth_data
                    conn.encrypt_auth_data(new_auth_data)
                    conn.save()
                    self.stdout.write(self.style.SUCCESS(f"  Connection updated with new token"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Failed to update connection: {str(e)}"))
                    traceback.print_exc()
                continue
            
            # Try to decrypt and fix the existing auth_data
            try:
                # Try to decrypt the current auth data
                if not conn.auth_data:
                    self.stdout.write(self.style.ERROR(f"  No auth_data found for this connection"))
                    continue
                    
                try:
                    # First try normal decryption
                    auth_data = conn.decrypt_auth_data()
                    self.stdout.write(f"  Current auth_data keys: {list(auth_data.keys())}")
                except InvalidToken:
                    self.stdout.write(self.style.ERROR(f"  Invalid token format - cannot decrypt"))
                    continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Decryption error: {str(e)}"))
                    traceback.print_exc()
                    continue
                
                # Check if we need to fix the structure
                if 'apiKey' in auth_data and 'token' not in auth_data:
                    self.stdout.write(self.style.WARNING(f"  Found 'apiKey' but no 'token' - fixing structure"))
                    
                    # Create new auth_data with correct structure
                    new_auth_data = {'token': auth_data['apiKey']}
                    
                    # Copy any other keys
                    for key, value in auth_data.items():
                        if key != 'apiKey':
                            new_auth_data[key] = value
                    
                    # Encrypt and save the fixed auth_data
                    conn.encrypt_auth_data(new_auth_data)
                    conn.save()
                    
                    # Verify the fix
                    updated_auth_data = conn.decrypt_auth_data()
                    self.stdout.write(f"  Updated auth_data keys: {list(updated_auth_data.keys())}")
                    
                    if 'token' in updated_auth_data:
                        self.stdout.write(self.style.SUCCESS(f"  Fix successful - auth_data now has 'token' key"))
                    else:
                        self.stdout.write(self.style.ERROR(f"  Fix failed - auth_data still missing 'token' key"))
                    
                elif 'token' in auth_data:
                    self.stdout.write(self.style.SUCCESS(f"  Auth data already has correct structure with 'token' key"))
                    self.stdout.write(f"  Token starts with: {auth_data['token'][:4]}...")
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  Auth data doesn't have 'apiKey' or 'token' keys: {list(auth_data.keys())}"
                    ))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error processing connection {conn.id}: {str(e)}"))
                traceback.print_exc()
        
        self.stdout.write(self.style.SUCCESS('\nCompleted auth_data structure check and fix.'))
