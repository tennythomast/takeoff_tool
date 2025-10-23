#!/usr/bin/env python
"""
Script to check if a connection's auth_data is properly structured and can be decrypted.
"""
import os
import sys
import django
import json
import traceback

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

try:
    django.setup()
except Exception as e:
    print(f"Failed to set up Django: {e}")
    sys.exit(1)

try:
    from mcp.models import MCPServerConnection
except ImportError as e:
    print(f"Failed to import models: {e}")
    sys.exit(1)

def check_connection(connection_id):
    """Check if a connection's auth_data is properly structured."""
    try:
        conn = MCPServerConnection.objects.get(id=connection_id)
        print(f"Connection found: {conn.connection_name} (ID: {conn.id})")
        print(f"Server: {conn.server.qualified_name}")
        print(f"Auth data present: {'Yes' if conn.auth_data else 'No'}")
        
        if conn.auth_data:
            try:
                auth_data = conn.decrypt_auth_data()
                print(f"Successfully decrypted auth_data")
                print(f"Auth data keys: {list(auth_data.keys())}")
                
                if 'token' in auth_data:
                    print(f"✅ Token found with value starting with: {auth_data['token'][:4]}...")
                    return True
                else:
                    print(f"❌ No 'token' key found in auth_data")
                    return False
            except Exception as e:
                print(f"❌ Failed to decrypt auth_data: {str(e)}")
                traceback.print_exc()
                return False
        else:
            print("❌ No auth_data stored for this connection")
            return False
    except MCPServerConnection.DoesNotExist:
        print(f"❌ Connection with ID {connection_id} not found")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_connection.py <connection_id>")
        sys.exit(1)
    
    try:
        connection_id = int(sys.argv[1])
    except ValueError:
        print("Connection ID must be an integer")
        sys.exit(1)
    
    success = check_connection(connection_id)
    if success:
        print("\n✅ Connection auth_data is properly structured")
    else:
        print("\n❌ Connection auth_data has issues")
