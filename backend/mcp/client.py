import asyncio
import json
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp
import websockets
from django.conf import settings
from .models import MCPServerConnection, MCPResourceDiscovery

@dataclass
class MCPRequest:
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

@dataclass
class MCPResponse:
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

class MCPClient:
    """Universal MCP client that handles different server types"""
    
    def __init__(self, connection: MCPServerConnection):
        self.connection = connection
        self.server_config = connection.server
        self.auth_data = connection.decrypt_auth_data()
        self._process = None
        self._session = None
        
    async def connect(self) -> bool:
        """Establish connection to MCP server"""
        try:
            if self.server_config.server_type == 'stdio':
                return await self._connect_stdio()
            elif self.server_config.server_type == 'http':
                return await self._connect_http()
            elif self.server_config.server_type == 'websocket':
                return await self._connect_websocket()
            else:
                raise ValueError(f"Unsupported server type: {self.server_config.server_type}")
        except Exception as e:
            print(f"Failed to connect to MCP server {self.connection.connection_name}: {e}")
            return False
    
    async def _connect_stdio(self) -> bool:
        """Connect to stdio-based MCP server"""
        try:
            # Parse install command to get executable and args
            cmd_parts = self.server_config.install_command.split()
            
            # Start the MCP server process
            self._process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize MCP protocol
            init_request = MCPRequest(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {"listChanged": True},
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "dataelan",
                        "version": "1.0.0"
                    }
                },
                id="init"
            )
            
            response = await self._send_stdio_request(init_request)
            return response and not response.error
            
        except Exception as e:
            print(f"stdio connection error: {e}")
            return False
    
    async def _send_stdio_request(self, request: MCPRequest) -> Optional[MCPResponse]:
        """Send request via stdio"""
        if not self._process:
            return None
            
        try:
            # Prepare JSON-RPC request
            rpc_request = {
                "jsonrpc": "2.0",
                "method": request.method,
                "params": request.params,
                "id": request.id
            }
            
            # Send request
            request_json = json.dumps(rpc_request) + "\n"
            self._process.stdin.write(request_json.encode())
            await self._process.stdin.drain()
            
            # Read response
            response_line = await self._process.stdout.readline()
            response_data = json.loads(response_line.decode().strip())
            
            return MCPResponse(
                result=response_data.get("result"),
                error=response_data.get("error"),
                id=response_data.get("id")
            )
            
        except Exception as e:
            print(f"stdio request error: {e}")
            return None
    
    async def list_resources_mvp(self) -> List[Dict[str, Any]]:
        """Optimized resource listing for MVP - uses caching and limits results"""
        # Check if we have cached resources in the database
        cached_resources = list(MCPResourceDiscovery.objects.filter(
            connection=self.connection,
            is_available=True
        ).values('resource_uri', 'resource_name', 'resource_type', 'external_id')[:100])  # Limit to 100 resources for MVP
        
        # If we have cached resources, return them directly
        if cached_resources:
            return cached_resources
            
        # Otherwise, fetch from server but with a limit
        return await self.list_resources(limit=100)
    
    async def list_resources(self, limit=None) -> List[Dict[str, Any]]:
        """List available resources from MCP server"""
        params = {}
        if limit:
            params['limit'] = limit
            
        request = MCPRequest(
            method="resources/list",
            params=params,
            id="list_resources"
        )
        
        response = await self._send_request(request)
        if response and response.result:
            return response.result.get("resources", [])
        return []
    
    async def get_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get specific resource from MCP server"""
        request = MCPRequest(
            method="resources/read",
            params={"uri": uri},
            id="get_resource"
        )
        
        response = await self._send_request(request)
        if response and response.result:
            return response.result
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call a tool provided by the MCP server"""
        request = MCPRequest(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            },
            id="call_tool"
        )
        
        response = await self._send_request(request)
        if response and response.result:
            return response.result
        return None
    
    async def _send_request(self, request: MCPRequest) -> Optional[MCPResponse]:
        """Route request to appropriate sender based on server type"""
        if self.server_config.server_type == 'stdio':
            return await self._send_stdio_request(request)
        elif self.server_config.server_type == 'http':
            return await self._send_http_request(request)
        elif self.server_config.server_type == 'websocket':
            return await self._send_websocket_request(request)
        return None
    
    async def disconnect(self):
        """Clean up connection"""
        if self._process:
            self._process.terminate()
            await self._process.wait()
        if self._session:
            await self._session.close()