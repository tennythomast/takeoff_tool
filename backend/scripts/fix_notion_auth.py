#!/usr/bin/env python
"""
Script to fix the auth_data structure for Notion connections.
Ensures that the auth token is stored with key 'token' instead of 'apiKey'.
"""
import os
import sys
import django

# Add the project path to the Python path
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from mcp.models import MCPServerConnection

def fix_notion_connections():
    """Fix auth_data structure for Notion connections."""
    print("Checking Notion connections...")
    
    # Get all Notion connections
    notion_connections = MCPServerConnection.objects.filter(
        server__qualified_name__contains='notion'
    )
    
    print(f"Found {notion_connections.count()} Notion connections")
    
    for conn in notion_connections:
        print(f"\nProcessing connection: {conn.connection_name} (ID: {conn.id})")
        
        try:
            # Decrypt the current auth data
            auth_data = conn.decrypt_auth_data()
            print(f"  Current auth_data keys: {list(auth_data.keys())}")
            
            # Check if we need to fix the structure
            if 'apiKey' in auth_data and 'token' not in auth_data:
                print(f"  ⚠️ Found 'apiKey' but no 'token' - fixing structure")
                
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
                print(f"  Updated auth_data keys: {list(updated_auth_data.keys())}")
                
                if 'token' in updated_auth_data:
                    print(f"  ✅ Fix successful - auth_data now has 'token' key")
                else:
                    print(f"  ❌ Fix failed - auth_data still missing 'token' key")
                
            elif 'token' in auth_data:
                print(f"  ✅ Auth data already has correct structure with 'token' key")
            else:
                print(f"  ⚠️ Auth data doesn't have 'apiKey' or 'token' keys: {list(auth_data.keys())}")
                
        except Exception as e:
            print(f"  ❌ Error processing connection {conn.id}: {str(e)}")

if __name__ == "__main__":
    print("Starting auth_data structure fix for Notion connections...")
    fix_notion_connections()
    print("\nCompleted auth_data structure check and fix.")
