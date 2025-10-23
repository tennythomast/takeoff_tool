import os
from django.core.management.base import BaseCommand
from mcp.models import MCPServerConnection
from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = 'Debug MCP encryption key and connection auth data'

    def handle(self, *args, **options):
        # Check if MCP_ENCRYPTION_KEY is set in environment
        encryption_key = os.environ.get('MCP_ENCRYPTION_KEY')
        self.stdout.write(f"MCP_ENCRYPTION_KEY present: {encryption_key is not None}")
        
        if encryption_key:
            self.stdout.write(f"Key length: {len(encryption_key)}")
            # Check if key is valid for Fernet
            try:
                fernet = Fernet(encryption_key.encode())
                self.stdout.write("✅ Key is valid for Fernet")
            except Exception as e:
                self.stdout.write(f"❌ Key is not valid for Fernet: {str(e)}")
        
        # List all connections
        connections = MCPServerConnection.objects.all()
        self.stdout.write(f"Found {connections.count()} connections")
        
        for conn in connections:
            self.stdout.write(f"\nConnection ID: {conn.id}")
            self.stdout.write(f"Name: {conn.connection_name}")
            self.stdout.write(f"Server: {conn.server.display_name if conn.server else 'None'}")
            self.stdout.write(f"Auth data present: {conn.auth_data is not None}")
            
            if conn.auth_data:
                self.stdout.write(f"Auth data length: {len(conn.auth_data)}")
                
                # Try to decrypt
                try:
                    decrypted = conn.decrypt_auth_data()
                    self.stdout.write(f"✅ Successfully decrypted auth data: {decrypted}")
                except Exception as e:
                    self.stdout.write(f"❌ Failed to decrypt auth data: {str(e)}")
                    
                    # Try manual decryption if encryption key is available
                    if encryption_key:
                        try:
                            fernet = Fernet(encryption_key.encode())
                            decrypted_data = fernet.decrypt(conn.auth_data.encode()).decode()
                            self.stdout.write(f"Manual decryption result: {decrypted_data}")
                        except Exception as e:
                            self.stdout.write(f"Manual decryption also failed: {str(e)}")
