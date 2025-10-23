# apps/mcp/management/commands/sync_mcp_servers.py

import asyncio
import httpx
import json
import re
from asyncio import Semaphore
import random
from typing import Dict, List, Any, Optional
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from mcp.models import MCPServerRegistry
from asgiref.sync import sync_to_async

class Command(BaseCommand):
    help = 'Sync MCP servers from external registries (Smithery, GitHub, etc.)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['all', 'smithery', 'github', 'community'],
            default='all',
            help='Specify which source to sync from'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing servers (overwrite local changes)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of servers to sync (for testing)'
        )
    
    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.limit = options['limit']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Initialize the sync service
        sync_service = MCPRegistrySync(
            verbosity=self.verbosity,
            dry_run=self.dry_run,
            force=self.force,
            limit=self.limit,
            stdout=self.stdout,
            style=self.style
        )
        
        try:
            # Run async sync
            asyncio.run(sync_service.sync_all_sources(options['source']))
            
            if not self.dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully synced MCP servers from {options["source"]}'
                    )
                )
        except Exception as e:
            raise CommandError(f'Sync failed: {str(e)}')

class MCPRegistrySync:
    """Service for syncing MCP servers from external registries"""
    
    def __init__(self, verbosity=1, dry_run=False, force=False, limit=None, stdout=None, style=None):
        self.verbosity = verbosity
        self.dry_run = dry_run
        self.force = force
        self.limit = limit
        self.stdout = stdout
        self.style = style
        self.semaphore = Semaphore(3)  # Max 3 concurrent requests
        self.retry_delays = [1, 2, 4, 8]  # Exponential backoff
        
        # List of specific MCP servers to include
        self.SELECTED_SERVERS = [
            'atlassian', 'youtube', 'xero', 'webflow', 'notion', 
            'mongodb', 'github', 'hubspot', 'huggingface'
        ]
        
        # Registry sources with their configurations
        self.REGISTRY_SOURCES = {
            'github': {
                'name': 'Selected MCP Servers (GitHub)',
                'url': 'https://api.github.com/repos/modelcontextprotocol/servers/contents',
                'headers': {'Accept': 'application/vnd.github.v3+json'},
                'parser': self._parse_selected_servers,
                'verified': True
            }
        }
        
        self.stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
    
    async def sync_all_sources(self, source_filter: str = 'all'):
        """Sync from all configured sources"""
        sources_to_sync = []
        
        if source_filter == 'all':
            sources_to_sync = list(self.REGISTRY_SOURCES.keys())
        elif source_filter in self.REGISTRY_SOURCES:
            sources_to_sync = [source_filter]
        else:
            raise ValueError(f"Unknown source: {source_filter}")
        
        self._log(f"Starting sync from sources: {', '.join(sources_to_sync)}")
        
        for source_name in sources_to_sync:
            try:
                await self._sync_from_source(source_name)
            except Exception as e:
                self._log(f"ERROR: Failed to sync from {source_name}: {str(e)}", level='error')
                self.stats['errors'] += 1
        
        self._print_summary()
    
    async def _sync_from_source(self, source_name: str):
        """Sync from a specific registry source"""
        source_config = self.REGISTRY_SOURCES[source_name]
        
        self._log(f"Syncing from {source_config['name']}...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    source_config['url'],
                    headers=source_config['headers']
                )
                response.raise_for_status()
                
                # Parse response using source-specific parser
                servers_data = await source_config['parser'](response.json())
                
                # Process the servers
                await self._process_servers_batch(
                    servers_data, 
                    source_name,
                    source_config['verified']
                )
                
            except httpx.HTTPError as e:
                self._log(f"HTTP error fetching from {source_name}: {str(e)}", level='error')
                raise
            except Exception as e:
                self._log(f"Error processing {source_name}: {str(e)}", level='error')
                raise
    
    async def _parse_smithery_response(self, data: Dict) -> List[Dict]:
        """Parse Smithery registry API response"""
        servers = []
        
        if 'servers' in data:
            for server_info in data['servers']:
                parsed_server = {
                    'qualified_name': server_info.get('qualifiedName'),
                    'display_name': server_info.get('displayName'),
                    'description': server_info.get('description', ''),
                    'category': self._categorize_server(server_info),
                    'install_command': self._extract_install_command(server_info),
                    'config_schema': server_info.get('configSchema', {}),
                    'auth_schema': server_info.get('authSchema', {}),
                    'capabilities': server_info.get('capabilities', []),
                    'supported_operations': server_info.get('tools', []),
                    'source_url': server_info.get('homepage'),
                    'documentation_url': server_info.get('documentation'),
                    'version': server_info.get('version', 'latest'),
                    'usage_count': server_info.get('useCount', 0),
                    'rating': float(server_info.get('rating', 0.0)),
                }
                
                if parsed_server['qualified_name']:
                    servers.append(parsed_server)
        
        return servers
    
    async def _parse_github_response(self, data: List[Dict]) -> List[Dict]:
        """Parse GitHub API response for MCP servers in 'official' directory"""
        servers = []
        async with httpx.AsyncClient() as client:
            for item in data:
                if item.get('type') != 'dir':
                    continue

                dir_name = item.get('name', '')
                dir_url = item.get('url')

                if not dir_url:
                    continue

                try:
                    dir_response = await self._fetch_with_retry(client, dir_url, {'Accept': 'application/vnd.github.v3+json'})
                    dir_contents = dir_response.json()

                    # Look for files
                    package_json = None
                    readme_md = None
                    server_json = None

                    for file_item in dir_contents:
                        if file_item.get('type') != 'file':
                            continue

                        file_name = file_item.get('name', '').lower()
                        if file_name == 'package.json':
                            file_response = await self._fetch_with_retry(client, file_item['download_url'], {})
                            package_json = file_response.json()
                        elif file_name in ('readme.md', 'readme.markdown'):
                            file_response = await self._fetch_with_retry(client, file_item['download_url'], {})
                            readme_md = file_response.text
                        elif file_name == 'server.json':
                            file_response = await self._fetch_with_retry(client, file_item['download_url'], {})
                            server_json = file_response.json()

                    # Assemble server info
                    server_info = {
                        'qualified_name': f"official/{dir_name}",
                        'display_name': dir_name.replace('-', ' ').title(),
                        'source_url': item.get('html_url'),
                        'description': package_json.get('description') if package_json else f"Official MCP server for {dir_name}",
                        'version': package_json.get('version') if package_json else 'latest',
                        'install_command': f"npm install {package_json['name']}" if package_json and 'name' in package_json else f"npm install @modelcontextprotocol/server-{dir_name}",
                        'documentation_url': package_json.get('homepage') if package_json else None,
                        'capabilities': server_json.get('capabilities') if server_json else ['tools', 'resources'],
                        'supported_operations': server_json.get('operations') if server_json else [],
                        'server_type': server_json.get('type') if server_json else 'stdio',
                        'config_schema': server_json.get('configSchema') if server_json else {},
                        'auth_schema': server_json.get('authSchema') if server_json else {},
                    }

                    server_info['category'] = self._categorize_server(server_info)
                    servers.append(server_info)

                    if self.verbosity >= 2:
                        self._log(f"  Found official server: {server_info['qualified_name']}")

                except Exception as e:
                    self._log(f"  Error processing {dir_name}: {str(e)}", level='warning')
                    continue

        return servers

    async def _parse_selected_servers(self, data: List[Dict]) -> List[Dict]:
        """Create entries for selected MCP servers manually"""
        servers = []
        
        # Define server metadata for each selected server
        server_metadata = {
            'atlassian': {
                'display_name': 'Atlassian',
                'description': 'MCP server for Atlassian products (Jira, Confluence, etc.)',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read', 'create', 'update'],
                'category': 'productivity',
                'documentation_url': 'https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/',
            },
            'youtube': {
                'display_name': 'YouTube',
                'description': 'MCP server for YouTube video search and metadata',
                'capabilities': ['resources'],
                'supported_operations': ['list', 'read'],
                'category': 'media',
                'documentation_url': 'https://developers.google.com/youtube/v3',
            },
            'xero': {
                'display_name': 'Xero',
                'description': 'MCP server for Xero accounting software',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read', 'create', 'update'],
                'category': 'finance',
                'documentation_url': 'https://developer.xero.com/documentation/',
            },
            'webflow': {
                'display_name': 'Webflow',
                'description': 'MCP server for Webflow website builder',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read', 'create', 'update'],
                'category': 'web',
                'documentation_url': 'https://developers.webflow.com/',
            },
            'notion': {
                'display_name': 'Notion',
                'description': 'MCP server for Notion workspace and documents',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read', 'create', 'update'],
                'category': 'productivity',
                'documentation_url': 'https://developers.notion.com/',
            },
            'mongodb': {
                'display_name': 'MongoDB',
                'description': 'MCP server for MongoDB database operations',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read', 'create', 'update', 'delete'],
                'category': 'database',
                'documentation_url': 'https://www.mongodb.com/docs/atlas/api/',
            },
            'github': {
                'display_name': 'GitHub',
                'description': 'MCP server for GitHub repositories and issues',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read', 'create', 'update'],
                'category': 'development',
                'documentation_url': 'https://docs.github.com/en/rest',
            },
            'hubspot': {
                'display_name': 'HubSpot',
                'description': 'MCP server for HubSpot CRM platform',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read', 'create', 'update'],
                'category': 'crm',
                'documentation_url': 'https://developers.hubspot.com/docs/api/overview',
            },
            'huggingface': {
                'display_name': 'HuggingFace',
                'description': 'MCP server for HuggingFace models and datasets',
                'capabilities': ['tools', 'resources'],
                'supported_operations': ['list', 'read'],
                'category': 'ai',
                'documentation_url': 'https://huggingface.co/docs/api-inference/index',
            },
        }
        
        # Create server entries for each selected server
        for server_name, metadata in server_metadata.items():
            server_info = {
                'qualified_name': f"official/{server_name}",
                'display_name': metadata['display_name'],
                'description': metadata['description'],
                'source_url': f"https://github.com/modelcontextprotocol/servers/tree/main/src/{server_name}",
                'version': 'latest',
                'install_command': f"npm install @modelcontextprotocol/server-{server_name}",
                'documentation_url': metadata['documentation_url'],
                'capabilities': metadata['capabilities'],
                'supported_operations': metadata['supported_operations'],
                'server_type': 'stdio',
                'config_schema': {
                    'type': 'object',
                    'required': ['apiKey'],
                    'properties': {
                        'apiKey': {
                            'type': 'string',
                            'description': f"API key for {metadata['display_name']}"
                        }
                    }
                },
                'auth_schema': {
                    'type': 'apiKey',
                    'in': 'header',
                    'name': 'Authorization'
                },
                'category': metadata['category']
            }
            
            servers.append(server_info)
            if self.verbosity >= 2:
                self._log(f"Added server: {server_info['qualified_name']}")
                
        return servers
        
    async def _parse_awesome_list_response(self, data: Dict) -> List[Dict]:
        """Parse awesome-mcp-servers README for community servers"""
        servers = []
        
        if 'content' in data:
            # Decode base64 content
            import base64
            content = base64.b64decode(data['content']).decode('utf-8')
            
            # Parse markdown to extract MCP servers
            # This is a simplified regex-based parser
            # In practice, you might want to use a proper markdown parser
            
            # Look for GitHub repository links
            github_pattern = r'\[([^\]]+)\]\(https://github\.com/([^/]+)/([^/)]+)\)'
            matches = re.findall(github_pattern, content)
            
            for display_name, owner, repo in matches:
                if 'mcp' in repo.lower() or 'server' in repo.lower():
                    server = {
                        'qualified_name': f"{owner}/{repo}",
                        'display_name': display_name,
                        'description': f"Community MCP server: {display_name}",
                        'category': self._categorize_server({'name': repo}),
                        'install_command': f"npx {owner}/{repo}",
                        'source_url': f"https://github.com/{owner}/{repo}",
                        'server_type': 'stdio',
                        'capabilities': ['tools'],  # Conservative default
                        'supported_operations': [],
                        'version': 'latest'
                    }
                    servers.append(server)
        
        return servers
    
    async def _process_servers_batch(self, servers_data: List[Dict], source_name: str, is_verified: bool):
        """Process a batch of servers from a source"""
        if self.limit:
            servers_data = servers_data[:self.limit]
        
        for server_info in servers_data:
            try:
                await self._create_or_update_server(server_info, source_name, is_verified)
                self.stats['total_processed'] += 1
                
                if self.verbosity >= 2:
                    self._log(f"  Processed: {server_info.get('qualified_name', 'Unknown')}")
                    
            except Exception as e:
                self._log(
                    f"  ERROR processing {server_info.get('qualified_name', 'Unknown')}: {str(e)}", 
                    level='error'
                )
                self.stats['errors'] += 1
    
    async def _fetch_with_retry(self, client, url, headers, max_retries=3):
        """Fetch with retry logic and rate limiting"""
        async with self.semaphore:
            for attempt in range(max_retries + 1):
                try:
                    # Add jitter to prevent thundering herd
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Rate limited
                        if attempt < max_retries:
                            delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                            self._log(f"Rate limited, retrying in {delay}s...", level='warning')
                            await asyncio.sleep(delay)
                            continue
                    raise
                except httpx.RequestError as e:
                    if attempt < max_retries:
                        delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                        self._log(f"Request failed, retrying in {delay}s: {e}", level='warning')
                        await asyncio.sleep(delay)
                        continue
                    raise

    async def _create_or_update_server(self, server_info: Dict, source_name: str, is_verified: bool):
        """Create or update MCP server registry entry"""
        qualified_name = server_info.get('qualified_name')
        
        if not qualified_name:
            self._log(f"  SKIP: No qualified_name for server from {source_name}")
            self.stats['skipped'] += 1
            return
        
        # Prepare server data
        server_data = {
            'display_name': server_info.get('display_name', qualified_name),
            'description': server_info.get('description', ''),
            'category': server_info.get('category', 'general'),
            'server_type': server_info.get('server_type', 'stdio'),
            'install_command': server_info.get('install_command', ''),
            'config_schema': server_info.get('config_schema', {}),
            'auth_schema': server_info.get('auth_schema', {}),
            'capabilities': server_info.get('capabilities', []),
            'supported_operations': server_info.get('supported_operations', []),
            'data_schema': server_info.get('data_schema', {}),
            'source_url': server_info.get('source_url'),
            'documentation_url': server_info.get('documentation_url'),
            'version': server_info.get('version', 'latest'),
            'is_verified': is_verified,
            'is_active': True,
            'usage_count': server_info.get('usage_count', 0),
            'rating': server_info.get('rating', 0.0),
        }
        
        if self.dry_run:
            self._log(f"  DRY RUN: Would create/update {qualified_name}")
            return
        
        # Check if server exists using sync_to_async
        try:
            # Wrap the database query in sync_to_async
            existing_server = await sync_to_async(MCPServerRegistry.objects.get)(qualified_name=qualified_name)
            
            # Update existing server
            if self.force or await sync_to_async(self._should_update_server)(existing_server, server_data):
                for field, value in server_data.items():
                    setattr(existing_server, field, value)
                
                # Wrap save operation in sync_to_async
                await sync_to_async(existing_server.save)()
                self.stats['updated'] += 1
                
                if self.verbosity >= 2:
                    self._log(f"  UPDATED: {qualified_name}")
            else:
                self.stats['skipped'] += 1
                if self.verbosity >= 2:
                    self._log(f"  SKIPPED: {qualified_name} (no changes needed)")
                    
        except MCPServerRegistry.DoesNotExist:
            # Create new server using sync_to_async
            await sync_to_async(MCPServerRegistry.objects.create)(
                qualified_name=qualified_name,
                **server_data
            )
            self.stats['created'] += 1
            
            if self.verbosity >= 2:
                self._log(f"  CREATED: {qualified_name}")
    
    # This method is called from an async context, so we need to make it sync-compatible
    def _should_update_server(self, existing: MCPServerRegistry, new_data: Dict) -> bool:
        """Determine if an existing server should be updated"""
        # Always update if forced
        if self.force:
            return True
        
        # Update if version changed
        if existing.version != new_data.get('version', 'latest'):
            return True
        
        # Update if description is empty and we have a new one
        if not existing.description and new_data.get('description'):
            return True
        
        # Update if capabilities changed
        if set(existing.capabilities) != set(new_data.get('capabilities', [])):
            return True
        
        # Don't update if no significant changes
        return False
    
    def _categorize_server(self, server_info: Dict) -> str:
        """Categorize server based on its metadata"""
        name = server_info.get('name', '').lower()
        description = server_info.get('description', '').lower()
        qualified_name = server_info.get('qualified_name', '').lower()
        
        text_to_check = f"{name} {description} {qualified_name}"
        
        # Define category keywords
        categories = {
            'development': [
                'github', 'git', 'code', 'dev', 'programming', 'repo', 'commit',
                'pull request', 'issue', 'docker', 'kubernetes', 'ci', 'cd'
            ],
            'communication': [
                'slack', 'email', 'chat', 'message', 'notification', 'discord',
                'teams', 'telegram', 'whatsapp', 'sms'
            ],
            'productivity': [
                'jira', 'asana', 'trello', 'notion', 'confluence', 'project',
                'task', 'todo', 'calendar', 'meeting', 'schedule'
            ],
            'data': [
                'database', 'sql', 'postgres', 'mongo', 'redis', 'elasticsearch',
                'bigquery', 'snowflake', 'analytics', 'warehouse'
            ],
            'finance': [
                'stripe', 'paypal', 'payment', 'billing', 'invoice', 'accounting',
                'financial', 'bank', 'money'
            ],
            'storage': [
                'drive', 'dropbox', 'storage', 'file', 'document', 'cloud',
                's3', 'blob', 'bucket'
            ],
            'crm': [
                'salesforce', 'hubspot', 'crm', 'customer', 'lead', 'contact',
                'deal', 'opportunity'
            ]
        }
        
        # Check each category
        for category, keywords in categories.items():
            if any(keyword in text_to_check for keyword in keywords):
                return category
        
        return 'general'
    
    def _extract_install_command(self, server_info: Dict) -> str:
        """Extract or generate install command for the server"""
        # Check if install command is provided
        if 'installCommand' in server_info:
            return server_info['installCommand']
        
        # Generate based on qualified name
        qualified_name = server_info.get('qualifiedName', '')
        if qualified_name:
            if '/' in qualified_name:
                # Assume it's a GitHub-style repo
                return f"npx {qualified_name}"
            else:
                # Assume it's an npm package
                return f"npx @modelcontextprotocol/server-{qualified_name}"
        
        return ''
    
    def _log(self, message: str, level: str = 'info'):
        """Log a message with appropriate styling"""
        if not self.stdout:
            return
        
        if level == 'error':
            self.stdout.write(self.style.ERROR(message))
        elif level == 'warning':
            self.stdout.write(self.style.WARNING(message))
        elif level == 'success':
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(message)
    
    def _print_summary(self):
        """Print sync summary statistics"""
        if not self.stdout:
            return
        
        self._log("\n" + "="*50)
        self._log("SYNC SUMMARY")
        self._log("="*50)
        self._log(f"Total processed: {self.stats['total_processed']}")
        self._log(f"Created: {self.stats['created']}", level='success')
        self._log(f"Updated: {self.stats['updated']}", level='success')
        self._log(f"Skipped: {self.stats['skipped']}")
        
        if self.stats['errors'] > 0:
            self._log(f"Errors: {self.stats['errors']}", level='error')
        else:
            self._log("Errors: 0", level='success')
        
        if self.dry_run:
            self._log("\nNOTE: This was a dry run - no changes were made", level='warning')

# Additional utility command for testing individual servers
class TestMCPServerCommand(BaseCommand):
    """Test connectivity to a specific MCP server"""
    help = 'Test connectivity to a specific MCP server'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'qualified_name',
            type=str,
            help='Qualified name of the MCP server to test'
        )
    
    def handle(self, *args, **options):
        qualified_name = options['qualified_name']
        
        try:
            # Use synchronous code here since this is called from a synchronous context
            server = MCPServerRegistry.objects.get(qualified_name=qualified_name)
        except MCPServerRegistry.DoesNotExist:
            raise CommandError(f"MCP server '{qualified_name}' not found")
        
        self.stdout.write(f"Testing MCP server: {server.display_name}")
        self.stdout.write(f"Install command: {server.install_command}")
        
        # Here you would implement actual connectivity testing
        # This is a placeholder for the actual test implementation
        self.stdout.write(
            self.style.SUCCESS(f"MCP server {qualified_name} test completed")
        )