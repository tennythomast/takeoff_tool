import httpx
import asyncio
from typing import List, Dict, Any
from django.db import transaction
from .models import MCPServerRegistry

class MCPRegistrySync:
    """Sync MCP servers from external registries"""
    
    REGISTRY_SOURCES = [
        "https://registry.smithery.ai/servers",
        "https://api.github.com/repos/modelcontextprotocol/servers/contents",
        # Add more registry sources
    ]
    
    async def sync_from_registries(self):
        """Sync MCP servers from all configured registries"""
        for source in self.REGISTRY_SOURCES:
            try:
                await self._sync_from_source(source)
            except Exception as e:
                print(f"Failed to sync from {source}: {e}")
    
    async def _sync_from_source(self, source_url: str):
        """Sync from a specific registry source"""
        async with httpx.AsyncClient() as client:
            response = await client.get(source_url)
            response.raise_for_status()
            
            servers_data = response.json()
            await self._process_servers_data(servers_data, source_url)
    
    async def _process_servers_data(self, servers_data: Dict, source_url: str):
        """Process and store server data from registry"""
        if "servers" in servers_data:
            servers = servers_data["servers"]
        else:
            servers = servers_data
        
        for server_info in servers:
            await self._create_or_update_server(server_info, source_url)
    
    @transaction.atomic
    async def _create_or_update_server(self, server_info: Dict, source_url: str):
        """Create or update MCP server registry entry"""
        qualified_name = server_info.get("qualifiedName") or server_info.get("name")
        
        if not qualified_name:
            return
        
        defaults = {
            "display_name": server_info.get("displayName", qualified_name),
            "description": server_info.get("description", ""),
            "category": self._categorize_server(server_info),
            "server_type": "stdio",  # Default, can be updated
            "install_command": server_info.get("installCommand", ""),
            "config_schema": server_info.get("configSchema", {}),
            "auth_schema": server_info.get("authSchema", {}),
            "capabilities": server_info.get("capabilities", []),
            "supported_operations": server_info.get("operations", []),
            "source_url": server_info.get("repository") or source_url,
            "documentation_url": server_info.get("documentation"),
            "version": server_info.get("version", "latest"),
            "is_verified": source_url.startswith("https://registry.smithery.ai"),
        }
        
        server, created = MCPServerRegistry.objects.update_or_create(
            qualified_name=qualified_name,
            defaults=defaults
        )
        
        if created:
            print(f"Created MCP server: {qualified_name}")
        else:
            print(f"Updated MCP server: {qualified_name}")
    
    def _categorize_server(self, server_info: Dict) -> str:
        """Categorize server based on its metadata"""
        name = server_info.get("name", "").lower()
        description = server_info.get("description", "").lower()
        
        if any(term in name or term in description for term in ["github", "git", "code", "dev"]):
            return "development"
        elif any(term in name or term in description for term in ["slack", "email", "chat", "communication"]):
            return "communication"
        elif any(term in name or term in description for term in ["jira", "asana", "project", "task"]):
            return "productivity"
        elif any(term in name or term in description for term in ["database", "sql", "postgres", "mongo"]):
            return "data"
        else:
            return "general"