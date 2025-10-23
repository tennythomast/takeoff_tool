from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone

from .models import (
    MCPServerRegistry, MCPServerConnection, MCPResourceDiscovery,
    MCPWorkspaceAccess, MCPResourceUsage, MCPResourceMapping
)
from .serializers import (
    MCPServerRegistrySerializer, MCPServerConnectionSerializer, MCPResourceDiscoverySerializer,
    MCPWorkspaceAccessSerializer, MCPResourceUsageSerializer, MCPResourceMappingSerializer
)
from .permissions import (
    IsOrganizationMember, IsWorkspaceMember, IsConnectionOwner,
    CanManageWorkspaceAccess, CanAccessResource
)

class MCPServerRegistryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing available MCP servers from the registry
    """
    queryset = MCPServerRegistry.objects.filter(is_active=True)
    serializer_class = MCPServerRegistrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter servers by category, capabilities, etc."""
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by capabilities
        capability = self.request.query_params.get('capability')
        if capability:
            queryset = queryset.filter(capabilities__contains=[capability])
        
        # Filter by server type
        server_type = self.request.query_params.get('server_type')
        if server_type:
            queryset = queryset.filter(server_type=server_type)
            
        # Filter by workspace scoping support
        supports_workspace_scoping = self.request.query_params.get('supports_workspace_scoping')
        if supports_workspace_scoping:
            queryset = queryset.filter(supports_workspace_scoping=supports_workspace_scoping.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def config_schema(self, request, pk=None):
        """Get configuration schema for a server"""
        server = self.get_object()
        return Response({
            'config_schema': server.config_schema,
            'auth_schema': server.auth_schema,
            'scoping_config_schema': server.scoping_config_schema
        })


class MCPServerConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet for organization's MCP server connections"""
    serializer_class = MCPServerConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter connections by user's organizations"""
        user = self.request.user
        try:
            # Get all connections for organizations the user belongs to
            return MCPServerConnection.objects.filter(
                organization__in=user.get_organizations(),
                is_active=True
            ).select_related('server', 'user')
        except Exception as e:
            print(f"Error in MCPServerConnectionViewSet.get_queryset: {e}")
            return MCPServerConnection.objects.none()
    
    def perform_create(self, serializer):
        """Set the user and organization when creating a connection"""
        user = self.request.user
        
        # Get the user's organization (since users can only belong to one organization)
        user_org = user.organization
        
        if not user_org:
            print(f"[DEBUG] User {user.email} does not belong to any organization")
            raise serializers.ValidationError({"organization": "User must belong to an organization"})
        
        # Log the organization being used
        print(f"[DEBUG] Using user's organization: {user_org.name} (ID: {user_org.id})") 
        
        # Always use the user's organization regardless of what was sent in the request
        # This ensures consistency with the single organization model
        serializer.save(user=user, organization=user_org)
    
    def create(self, request, *args, **kwargs):
        """Override create to add detailed logging for debugging"""
        print(f"\n\n[DEBUG] MCPServerConnection create request data: {request.data}\n\n")
        
        # Log the request user and their organization
        user = request.user
        print(f"[DEBUG] Request user: {user.email} (ID: {user.id})")
        
        # Log user's organization
        user_org = user.organization
        if user_org:
            print(f"[DEBUG] User's organization: {user_org.name} (ID: {user_org.id})")
        else:
            print(f"[DEBUG] User does not belong to any organization")
        
        # Continue with normal create process
        try:
            return super().create(request, *args, **kwargs)
        except serializers.ValidationError as e:
            print(f"[DEBUG] Validation error: {e.detail if hasattr(e, 'detail') else str(e)}")
            raise
        except Exception as e:
            print(f"[DEBUG] Error in create: {str(e)}")
            if hasattr(e, 'detail'):
                print(f"[DEBUG] Error details: {e.detail}")
            raise
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test the connection to the MCP server"""
        connection = self.get_object()
        
        # Here we would implement the actual connection test logic
        # For Notion, we would verify the API token is valid
        try:
            # In a real implementation, we would make an API call to Notion here
            # For now, we'll simulate a successful connection
            connection.last_health_check = timezone.now()
            connection.health_status = 'healthy'
            connection.is_connected = True
            
            # Log the connection test
            print(f"[INFO] Connection test successful for {connection.connection_name} (ID: {connection.id})")
            
            # Save all updated fields
            connection.save(update_fields=['last_health_check', 'health_status', 'is_connected'])
            
            # Broadcast a status update
            print(f"[INFO] Broadcast connection status update for connection {connection.id}: connected")
        except Exception as e:
            # If there's an error, mark the connection as unhealthy
            connection.health_status = 'error'
            connection.is_connected = False
            connection.save(update_fields=['last_health_check', 'health_status', 'is_connected'])
            print(f"[ERROR] Connection test failed for {connection.connection_name}: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Connection test failed: {str(e)}',
                'health_status': connection.health_status,
                'last_health_check': connection.last_health_check
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': 'Connection test successful',
            'health_status': connection.health_status,
            'last_health_check': connection.last_health_check
        })


    @action(detail=True, methods=['get'])
    def debug_auth(self, request, pk=None):
        """Debug endpoint to inspect auth data structure"""
        connection = self.get_object()
        
        try:
            # Check what methods exist on the connection object
            auth_methods = [method for method in dir(connection) if 'auth' in method.lower()]
            print(f"[DEBUG] Available auth methods on connection: {auth_methods}")
            
            # Try different methods to get auth data
            auth_data = None
            decryption_method = None
            
            # Try the methods from your documentation
            if hasattr(connection, 'get_auth_data'):
                try:
                    auth_data = connection.get_auth_data()
                    decryption_method = 'get_auth_data'
                    print(f"[DEBUG] Successfully used get_auth_data() method")
                except Exception as e:
                    print(f"[DEBUG] get_auth_data() failed: {e}")
            
            if not auth_data and hasattr(connection, 'decrypt_auth_data'):
                try:
                    auth_data = connection.decrypt_auth_data()
                    decryption_method = 'decrypt_auth_data'
                    print(f"[DEBUG] Successfully used decrypt_auth_data() method")
                except Exception as e:
                    print(f"[DEBUG] decrypt_auth_data() failed: {e}")
            
            if auth_data:
                return Response({
                    'status': 'success',
                    'has_auth_data': bool(connection.auth_data),
                    'decryption_method': decryption_method,
                    'auth_data_keys': list(auth_data.keys()) if auth_data else [],
                    'decryption_successful': True,
                    'auth_data_sample': {k: f"<{type(v).__name__}>" for k, v in auth_data.items()} if auth_data else None,
                    'has_token_field': 'token' in auth_data if auth_data else False,
                    'available_fields': list(auth_data.keys()) if auth_data else []
                })
            else:
                return Response({
                    'status': 'error',
                    'error': 'Could not decrypt auth data with any method',
                    'has_auth_data': bool(connection.auth_data),
                    'decryption_successful': False,
                    'available_methods': auth_methods
                })
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e),
                'has_auth_data': bool(connection.auth_data),
                'decryption_successful': False
            })

    @action(detail=True, methods=['post'])
    def discover_resources(self, request, pk=None):
        print(f"[DEBUG] discover_resources called for connection ID: {pk}")
        connection = self.get_object()
        print(f"[DEBUG] Connection object retrieved: {connection.connection_name} (ID: {connection.id})")
        
        try:
            # Get the authentication data from the connection
            try:
                # Check what methods are available
                auth_methods = [method for method in dir(connection) if 'auth' in method.lower()]
                print(f"[DEBUG] Available auth methods: {auth_methods}")
                
                # Try the correct method from your documentation
                auth_data = None
                if hasattr(connection, 'get_auth_data'):
                    auth_data = connection.get_auth_data()
                    print(f"[DEBUG] Successfully used get_auth_data() method")
                elif hasattr(connection, 'decrypt_auth_data'):
                    auth_data = connection.decrypt_auth_data()
                    print(f"[DEBUG] Successfully used decrypt_auth_data() method")
                else:
                    print(f"[ERROR] No auth data decryption method found")
                    return Response({
                        'status': 'error',
                        'message': 'No auth data decryption method available'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                print(f"[DEBUG] Successfully decrypted auth data")
                print(f"[DEBUG] Auth data keys: {list(auth_data.keys()) if auth_data else 'None'}")
                print(f"[DEBUG] Auth data structure: {auth_data}")
                
                # Check for token with multiple possible field names
                token = None
                token_fields = ['token', 'access_token', 'personal_access_token', 'github_token', 'api_token', 'auth_token', 'apiKey']
                
                for field in token_fields:
                    if auth_data and auth_data.get(field):
                        token = auth_data.get(field)
                        print(f"[DEBUG] Found token in field '{field}' (first 4 chars): {token[:4]}...")
                        break
                
                if not token:
                    print(f"[ERROR] No token found in any expected field")
                    print(f"[DEBUG] Available fields: {list(auth_data.keys()) if auth_data else 'None'}")
                    return Response({
                        'status': 'error',
                        'message': f'No authentication token found. Available fields: {list(auth_data.keys()) if auth_data else "None"}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                print(f"[ERROR] Failed to decrypt auth data: {str(e)}")
                import traceback
                traceback.print_exc()
                return Response({
                    'status': 'error',
                    'message': f'Failed to retrieve authentication data: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Determine the integration type based on the server's qualified_name
            import requests
            server_type = connection.server.qualified_name.lower()
            print(f"[DEBUG] Server type detected: {server_type}")
            
            print(f"[DEBUG] Making API calls to discover resources")
            
            # First, delete any existing resources
            existing_count = MCPResourceDiscovery.objects.filter(connection=connection).count()
            if existing_count > 0:
                print(f"[DEBUG] Deleting {existing_count} existing resources before creating new ones")
                MCPResourceDiscovery.objects.filter(connection=connection).delete()
            
            # Handle different integration types
            if 'github' in server_type:
                return self._discover_github_resources(connection, token)
            elif 'notion' in server_type:
                return self._discover_notion_resources(connection, token)
            else:
                print(f"[ERROR] Unsupported server type: {server_type}")
                return Response({
                    'status': 'error',
                    'message': f'Unsupported server type: {server_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"[ERROR] Resource discovery failed for {connection.connection_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'status': 'error',
                'message': f'Resource discovery failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _discover_github_resources(self, connection, token):
        """Discover GitHub repositories using GitHub API"""
        import requests
        
        # GitHub API headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Dataelan-MCP-Integration"
        }
        
        # Test the token first by getting user info
        print(f"[DEBUG] Testing GitHub token by fetching user info")
        user_response = requests.get("https://api.github.com/user", headers=headers)
        
        if user_response.status_code != 200:
            print(f"[ERROR] GitHub API error when testing token: {user_response.status_code} {user_response.text}")
            return Response({
                'status': 'error',
                'message': f'GitHub API authentication failed: {user_response.status_code} {user_response.text[:200]}'
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        user_data = user_response.json()
        username = user_data.get('login', 'unknown')
        print(f"[DEBUG] Token is valid for GitHub user: {username}")
        
        # Get repositories
        print(f"[DEBUG] Fetching repositories")
        repos_response = requests.get("https://api.github.com/user/repos", headers=headers, params={
            'per_page': 50,
            'sort': 'updated'
        })
        
        if repos_response.status_code != 200:
            print(f"[ERROR] GitHub API error when fetching repos: {repos_response.status_code}")
            return Response({
                'status': 'error',
                'message': f'GitHub API error: {repos_response.status_code} {repos_response.text[:200]}'
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        repos_data = repos_response.json()
        print(f"[DEBUG] Found {len(repos_data)} repositories")
        
        # Create resource objects for each repository
        resource_count = 0
        
        # Create repository resources
        for repo in repos_data:
            try:
                repo_id = str(repo.get('id'))
                repo_name = repo.get('full_name', 'Unknown Repository')
                repo_description = repo.get('description', '') or f"GitHub repository: {repo_name}"
                
                print(f"[DEBUG] Creating resource for repository: {repo_name} (ID: {repo_id})")
                
                MCPResourceDiscovery.objects.create(
                    connection=connection,
                    resource_uri=f"github://repo/{repo_id}",
                    resource_name=repo_name,
                    resource_type='repository',
                    description=repo_description,
                    schema={
                        'owner': repo.get('owner', {}).get('login', ''),
                        'private': repo.get('private', False),
                        'language': repo.get('language', ''),
                        'stars': repo.get('stargazers_count', 0),
                        'forks': repo.get('forks_count', 0),
                        'updated_at': repo.get('updated_at', ''),
                        'html_url': repo.get('html_url', '')
                    },
                    operations=["read", "clone", "issues"],
                    external_id=repo_id,
                    is_available=True
                )
                resource_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to create resource for repo {repo.get('full_name')}: {str(e)}")
                # Continue with other resources
        
        # Update connection last_health_check
        connection.last_health_check = timezone.now()
        connection.save(update_fields=['last_health_check'])
        
        if resource_count > 0:
            print(f"[DEBUG] Successfully discovered {resource_count} resources")
            return Response({
                'status': 'success',
                'message': f'Successfully discovered {resource_count} GitHub repositories',
                'resource_count': resource_count
            })
        else:
            print(f"[DEBUG] No repositories found for user {username}")
            return Response({
                'status': 'warning',
                'message': f'No repositories found for GitHub user {username}',
                'resource_count': 0
            }, status=status.HTTP_200_OK)
    
    def _discover_notion_resources(self, connection, token):
        """Discover Notion pages and databases using Notion API"""
        import requests
        
        # Notion API headers
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        # Test the token first by getting user info
        print(f"[DEBUG] Testing Notion token by fetching user info")
        user_response = requests.get("https://api.notion.com/v1/users/me", headers=headers)
        
        if user_response.status_code != 200:
            print(f"[ERROR] Notion API error when testing token: {user_response.status_code} {user_response.text}")
            return Response({
                'status': 'error',
                'message': f'Notion API authentication failed: {user_response.status_code} {user_response.text[:200]}'
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        user_data = user_response.json()
        username = user_data.get('name', 'unknown')
        print(f"[DEBUG] Token is valid for Notion user: {username}")
        
        # Get search results for pages and databases
        print(f"[DEBUG] Searching for Notion pages and databases")
        search_response = requests.post(
            "https://api.notion.com/v1/search",
            headers=headers,
            json={
                "page_size": 100,
                "sort": {
                    "direction": "descending",
                    "timestamp": "last_edited_time"
                }
            }
        )
        
        if search_response.status_code != 200:
            print(f"[ERROR] Notion API error when searching: {search_response.status_code}")
            return Response({
                'status': 'error',
                'message': f'Notion API error: {search_response.status_code} {search_response.text[:200]}'
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        search_data = search_response.json()
        results = search_data.get('results', [])
        print(f"[DEBUG] Found {len(results)} Notion objects")
        
        # Create resource objects for each Notion object
        resource_count = 0
        
        for item in results:
            try:
                item_id = item.get('id')
                item_type = item.get('object')  # 'page' or 'database'
                
                # Get title based on object type
                title = ""
                if item_type == 'page':
                    title_prop = item.get('properties', {}).get('title', {})
                    if title_prop and 'title' in title_prop and len(title_prop['title']) > 0:
                        title = title_prop['title'][0].get('plain_text', '')
                    else:
                        # Fallback for untitled pages
                        title = f"Untitled Page ({item_id[:8]})"
                elif item_type == 'database':
                    title = item.get('title', [{}])[0].get('plain_text', f"Database {item_id[:8]}")
                
                item_url = item.get('url', '')
                
                print(f"[DEBUG] Creating resource for Notion {item_type}: {title} (ID: {item_id})")
                
                MCPResourceDiscovery.objects.create(
                    connection=connection,
                    resource_uri=f"notion://{item_type}/{item_id}",
                    resource_name=title or f"Notion {item_type} {item_id[:8]}",
                    resource_type=item_type,
                    description=f"Notion {item_type}",
                    schema={
                        'notion_id': item_id,
                        'url': item_url,
                        'last_edited': item.get('last_edited_time', ''),
                        'created_time': item.get('created_time', '')
                    },
                    operations=["read", "query"] if item_type == 'database' else ["read"],
                    external_id=item_id,
                    is_available=True
                )
                resource_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to create resource for Notion item {item.get('id')}: {str(e)}")
                # Continue with other resources
        
        # Update connection last_health_check
        connection.last_health_check = timezone.now()
        connection.save(update_fields=['last_health_check'])
        
        if resource_count > 0:
            print(f"[DEBUG] Successfully discovered {resource_count} Notion resources")
            return Response({
                'status': 'success',
                'message': f'Successfully discovered {resource_count} Notion resources',
                'resource_count': resource_count
            })
        else:
            print(f"[DEBUG] No Notion resources found for user {username}")
            return Response({
                'status': 'warning',
                'message': f'No Notion resources found. Check token permissions.',
                'resource_count': 0
            }, status=status.HTTP_200_OK)

class MCPResourceDiscoveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing discovered MCP resources
    """
    serializer_class = MCPResourceDiscoverySerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    
    def get_queryset_mvp(self):
        """Optimized resource filtering for MVP"""
        user = self.request.user
        # Simplified query with basic filters
        queryset = MCPResourceDiscovery.objects.filter(
            connection__organization=user.organization,
            is_available=True
        ).select_related('connection').order_by('-last_verified')
        
        # Basic filtering
        connection_id = self.request.query_params.get('connection')
        if connection_id:
            queryset = queryset.filter(connection_id=connection_id)
            
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # Apply limit after all filters
        queryset = queryset[:100]  # Limit to 100 most recently verified resources
            
        return queryset
    
    def get_queryset(self):
        """Filter resources by connection, type, etc."""
        # For MVP, use the optimized version
        return self.get_queryset_mvp()
        
        # The following is the full implementation that will be enabled after MVP
        """
        user = self.request.user
        queryset = MCPResourceDiscovery.objects.filter(
            connection__organization=user.organization,
            is_available=True
        ).select_related('connection', 'connection__server', 'parent_resource')
        """
        
        # Filter by connection
        connection_id = self.request.query_params.get('connection')
        if connection_id:
            queryset = queryset.filter(connection_id=connection_id)
        
        # Filter by resource type
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # Filter by parent resource
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            if parent_id == 'null':
                queryset = queryset.filter(parent_resource__isnull=True)
            else:
                queryset = queryset.filter(parent_resource_id=parent_id)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(resource_name__icontains=search)
        
        return queryset
        
    @action(detail=False, methods=['get'])
    def accessible(self, request):
        """List resources accessible to a specific workspace - MVP version"""
        workspace_id = request.query_params.get('workspace')
        if not workspace_id:
            return Response({"error": "workspace parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if user is a member of the workspace
        workspace = get_object_or_404(Workspace, id=workspace_id)
        if not workspace.members.filter(id=request.user.id).exists():
            return Response({"error": "You are not a member of this workspace"}, status=status.HTTP_403_FORBIDDEN)
            
        # Get all access configurations for this workspace
        access_configs = MCPWorkspaceAccess.objects.filter(workspace=workspace, is_active=True)
        
        # Get all accessible resources using the MVP method
        resources = []
        for access in access_configs:
            # Use the simplified MVP method
            resources.extend(access.get_accessible_resources_mvp())
            
        serializer = MCPResourceDiscoverySerializer(resources, many=True)
        return Response(serializer.data)


class MCPWorkspaceAccessViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing workspace-level access to MCP resources
    """
    serializer_class = MCPWorkspaceAccessSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember, CanManageWorkspaceAccess]
    
    def get_queryset(self):
        """Filter access configurations by workspace"""
        user = self.request.user
        print(f"MCPWorkspaceAccessViewSet.get_queryset called by user: {user.email}")
        
        # Start with a base queryset that doesn't filter by workspace membership yet
        base_queryset = MCPWorkspaceAccess.objects.all().select_related('workspace', 'connection', 'created_by')
        
        # Filter by workspace ID if provided in query params
        workspace_id = self.request.query_params.get('workspace')
        if workspace_id:
            print(f"Filtering by workspace_id: {workspace_id}")
            try:
                # First check if the user has access to this workspace
                from workspaces.models import Workspace
                
                # Check if user is the owner of the workspace
                is_owner = Workspace.objects.filter(id=workspace_id, owner=user).exists()
                
                # Check if user is a collaborator in the workspace
                is_collaborator = user.collaborated_workspaces.filter(id=workspace_id).exists()
                
                if not (is_owner or is_collaborator):
                    print(f"User {user.username} does not have access to workspace {workspace_id}")
                    return MCPWorkspaceAccess.objects.none()  # Return empty queryset
                
                # User has access, filter by workspace_id
                queryset = base_queryset.filter(workspace_id=workspace_id)
                print(f"Found {queryset.count()} MCPWorkspaceAccess objects for workspace {workspace_id}")
                return queryset
                
            except Exception as e:
                print(f"Error filtering MCPWorkspaceAccess by workspace_id: {e}")
                return MCPWorkspaceAccess.objects.none()  # Return empty queryset on error
        else:
            # No workspace_id provided, filter by workspaces the user has access to
            print("No workspace_id provided, filtering by user's workspaces")
            try:
                # Get all workspaces where the user is either owner or collaborator
                owned_workspaces = user.owned_workspaces.values_list('id', flat=True)
                collaborated_workspaces = user.collaborated_workspaces.values_list('id', flat=True)
                accessible_workspace_ids = list(owned_workspaces) + list(collaborated_workspaces)
                
                queryset = base_queryset.filter(workspace_id__in=accessible_workspace_ids)
                print(f"Found {queryset.count()} MCPWorkspaceAccess objects across all user's workspaces")
                return queryset
                
            except Exception as e:
                print(f"Error filtering MCPWorkspaceAccess by user's workspaces: {e}")
                return MCPWorkspaceAccess.objects.none()  # Return empty queryset on error
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a new access configuration"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def resources(self, request, pk=None):
        """Get resources accessible through this access configuration"""
        access = self.get_object()
        resources = access.get_accessible_resources()
        
        # Optional filtering by resource type
        resource_type = request.query_params.get('resource_type')
        if resource_type:
            resources = resources.filter(resource_type=resource_type)
        
        serializer = MCPResourceDiscoverySerializer(resources, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_resource(self, request, pk=None):
        """Add a resource to this access configuration"""
        access = self.get_object()
        resource_id = request.data.get('resource_id')
        
        if not resource_id:
            return Response(
                {'error': 'Resource ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            resource = MCPResourceDiscovery.objects.get(
                id=resource_id,
                connection=access.connection,
                is_available=True
            )
            access.allowed_resources.add(resource)
            return Response({'status': 'success', 'message': f'Resource {resource.resource_name} added'})
        except MCPResourceDiscovery.DoesNotExist:
            return Response(
                {'error': 'Resource not found or not available'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_resource(self, request, pk=None):
        """Remove a resource from this access configuration"""
        access = self.get_object()
        resource_id = request.data.get('resource_id')
        
        if not resource_id:
            return Response(
                {'error': 'Resource ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            resource = access.allowed_resources.get(id=resource_id)
            access.allowed_resources.remove(resource)
            return Response({'status': 'success', 'message': f'Resource {resource.resource_name} removed'})
        except MCPResourceDiscovery.DoesNotExist:
            return Response(
                {'error': 'Resource not found in this access configuration'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['put'])
    def update_resources(self, request, pk=None):
        """Update the list of allowed resources for this access configuration"""
        access = self.get_object()
        resource_ids = request.data.get('resource_ids', [])
        
        if not isinstance(resource_ids, list):
            return Response(
                {'error': 'resource_ids must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get all valid resources from the provided IDs that belong to this connection
            valid_resources = MCPResourceDiscovery.objects.filter(
                id__in=resource_ids,
                connection=access.connection,
                is_available=True
            )
            
            # Clear existing resources and set the new ones
            access.allowed_resources.clear()
            access.allowed_resources.add(*valid_resources)
            
            # Return the updated resources
            serializer = MCPResourceDiscoverySerializer(valid_resources, many=True)
            return Response({
                'status': 'success',
                'message': f'{len(valid_resources)} resources updated',
                'resources': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to update resources: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MCPResourceUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing resource usage analytics
    """
    serializer_class = MCPResourceUsageSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    
    def get_queryset(self):
        """Filter usage data by workspace, resource, user, etc."""
        user = self.request.user
        return MCPResourceUsage.objects.filter(
            workspace_access__workspace__members=user
        ).select_related('workspace_access', 'workspace_access__workspace', 'resource', 'user')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get usage summary statistics"""
        queryset = self.get_queryset()
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # Get summary statistics
        total_requests = queryset.count()
        successful_requests = queryset.filter(success=True).count()
        total_cost = sum(usage.cost for usage in queryset)
        avg_response_time = queryset.values_list('response_time', flat=True).aggregate(
            avg_response_time=models.Avg('response_time')
        )['avg_response_time'] or 0
        
        return Response({
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': successful_requests / total_requests if total_requests else 0,
            'total_cost': total_cost,
            'avg_response_time': avg_response_time
        })


class MCPResourceMappingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing mappings between MCP resources and internal components
    """
    serializer_class = MCPResourceMappingSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember, CanAccessResource]
    
    def get_queryset(self):
        """Filter mappings by workspace access"""
        user = self.request.user
        return MCPResourceMapping.objects.filter(
            workspace_access__workspace__members=user
        ).select_related('workspace_access', 'workspace_access__workspace', 'resource')
    
    @action(detail=False, methods=['get'])
    def by_component(self, request):
        """Get mappings by component type and ID"""
        component_type = request.query_params.get('component_type')
        component_id = request.query_params.get('component_id')
        
        queryset = self.get_queryset()
        
        if component_type:
            queryset = queryset.filter(component_type=component_type)
        
        if component_id:
            queryset = queryset.filter(workflow_component=component_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync the mapping with the external resource"""
        mapping = self.get_object()
        # Here you would implement the sync logic
        
        mapping.last_sync = timezone.now()
        mapping.save(update_fields=['last_sync'])
        
        return Response({
            'status': 'success',
            'message': 'Resource mapping synced',
            'last_sync': mapping.last_sync
        })
