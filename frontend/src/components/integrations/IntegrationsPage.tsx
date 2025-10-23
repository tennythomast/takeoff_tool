"use client"

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Settings, Plus, RefreshCw, Link, ExternalLink, Check, AlertCircle,
  ChevronRight, Search, Filter, MoreHorizontal, Shield, Key, Database,
  Grid, List, SlidersHorizontal, X, Loader2, Star
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { integrationService, MCPServerRegistry, MCPServerConnection } from "@/lib/services/integration-service";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

// Types
interface IntegrationsPageProps {
  params?: {
    id?: string;
  };
}

export default function IntegrationsPage({ params }: IntegrationsPageProps) {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Search and filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  
  // Data states
  const [availableServers, setAvailableServers] = useState<MCPServerRegistry[]>([]);
  const [connections, setConnections] = useState<MCPServerConnection[]>([]);
  const [filteredServers, setFilteredServers] = useState<MCPServerRegistry[]>([]);
  
  // Predefined categories for filtering
  const categories = [
    { id: 'all', label: 'All Integrations' },
    { id: 'productivity', label: 'Productivity' },
    { id: 'development', label: 'Development' },
    { id: 'ai', label: 'AI & ML' },
    { id: 'crm', label: 'CRM & Sales' },
    { id: 'database', label: 'Databases' },
    { id: 'finance', label: 'Finance' },
    { id: 'media', label: 'Media' },
    { id: 'web', label: 'Web Services' },
  ];
  
  // Extract unique categories from actual servers for dynamic filtering
  const availableCategories = useMemo(() => {
    const uniqueCategories = Array.from(new Set(availableServers.map(server => server.category)));
    return uniqueCategories;
  }, [availableServers]);
  
  // Filter servers based on search query, category, and status
  useEffect(() => {
    if (!availableServers.length) return;
    
    let filtered = [...availableServers];
    
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(server => 
        server.display_name.toLowerCase().includes(query) || 
        server.description.toLowerCase().includes(query) ||
        server.category.toLowerCase().includes(query) ||
        server.capabilities.some(cap => cap.toLowerCase().includes(query))
      );
    }
    
    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(server => server.category.toLowerCase() === selectedCategory.toLowerCase());
    }
    
    // Filter by connection status
    if (selectedStatus !== 'all') {
      const isConnected = selectedStatus === 'connected';
      filtered = filtered.filter(server => {
        const connected = connections.some(conn => conn.server === server.id);
        return connected === isConnected;
      });
    }
    
    setFilteredServers(filtered);
  }, [availableServers, searchQuery, selectedCategory, selectedStatus, connections]);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch available MCP servers from registry
        const serversData = await integrationService.getAvailableMCPServers();
        setAvailableServers(serversData);
        setFilteredServers(serversData);
        
        // Fetch existing connections
        const connectionsData = await integrationService.getMCPConnections();
        setConnections(connectionsData);
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching integration data:', err);
        setError('Failed to load integrations. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  // This effect is now redundant as we have a more comprehensive filter effect above
  // The previous effect that referenced activeTab and activeFilter has been removed
  
  // Check if a server is already connected
  const isConnected = (serverId: string) => {
    return connections.some(conn => conn.server === serverId);
  };
  
  // Get connection status for a server
  const getConnectionStatus = (serverId: string) => {
    const connection = connections.find(conn => conn.server === serverId);
    return connection ? connection.health_status : null;
  };
  
  // Handle connect button click
  const handleConnect = (server: MCPServerRegistry) => {
    router.push(`/settings/integrations/connect/${server.id}`);
  };
  
  // Handle manage connection click
  const handleManageConnection = (serverId: string) => {
    const connection = connections.find(conn => conn.server === serverId);
    if (connection) {
      router.push(`/settings/integrations/manage/${connection.id}`);
    }
  };
  
  // Handle test connection
  const handleTestConnection = async (connectionId: string) => {
    try {
      await integrationService.testConnection(connectionId);
      // Refresh connections after testing
      const connectionsData = await integrationService.getMCPConnections();
      setConnections(connectionsData);
    } catch (err) {
      console.error('Error testing connection:', err);
    }
  };
  
  // Render server card based on view mode
  const renderServerCard = (server: MCPServerRegistry) => {
    return viewMode === "grid" 
      ? renderGridCard(server) 
      : renderListCard(server);
  };
  
  // Render server card in grid view
  const renderGridCard = (server: MCPServerRegistry) => {
    const connected = isConnected(server.id);
    const status = getConnectionStatus(server.id);
    const connection = connections.find(conn => conn.server === server.id);
    const lastSyncTime = connection?.last_health_check ? new Date(connection.last_health_check) : null;
    const rating = server.rating || 0;
    
    // Get gradient color based on category
    const getCategoryGradient = (category: string) => {
      const categories: Record<string, string> = {
        'productivity': 'from-blue-500 to-indigo-600',
        'development': 'from-green-500 to-emerald-600',
        'ai': 'from-purple-500 to-violet-600',
        'crm': 'from-orange-500 to-amber-600',
        'database': 'from-cyan-500 to-blue-600',
        'finance': 'from-emerald-500 to-green-600',
        'media': 'from-pink-500 to-rose-600',
        'web': 'from-indigo-500 to-blue-600',
      };
      return categories[category.toLowerCase()] || 'from-gray-500 to-slate-600';
    };
    
    return (
      <Card className="group h-full flex flex-col overflow-hidden border border-border/40 hover:border-border/80 hover:shadow-lg transition-all duration-300 rounded-lg">
        <CardHeader className="pb-2 pt-4 px-4 relative">
          {/* Status indicator dot - absolute positioned in corner */}
          {connected && (
            <div className={cn(
              "absolute top-2 right-2 w-2 h-2 rounded-full",
              status === 'healthy' ? "bg-green-500 animate-pulse" :
              status === 'error' ? "bg-red-500" :
              status === 'warning' ? "bg-amber-500" :
              "bg-gray-400"
            )} />
          )}
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                "rounded-md p-1 bg-gradient-to-br", 
                getCategoryGradient(server.category)
              )}>
                <Avatar className="h-8 w-8 ring-2 ring-white/20">
                  {server.icon ? (
                    <AvatarImage src={server.icon} alt={server.display_name} className="object-cover" />
                  ) : (
                    <AvatarFallback className="text-xs font-medium text-white">
                      {server.display_name.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  )}
                </Avatar>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-sm font-medium group-hover:text-primary transition-colors">
                    {server.display_name}
                  </CardTitle>
                  {server.is_verified && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge variant="outline" className="text-xs h-5 px-1 border-blue-200 text-blue-700 bg-blue-50">
                            <Check size={10} className="mr-1" /> Verified
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-xs">Verified by Dataelan team</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
                <CardDescription className="line-clamp-2 text-xs mt-1">
                  {server.description}
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="pt-0 pb-3 px-4 flex-grow">
          <div className="flex flex-wrap gap-1.5 mt-2">
            <Badge variant="secondary" className="text-xs px-2 py-0.5 h-5 bg-muted/50">
              {server.category}
            </Badge>
            {server.capabilities.map((capability, index) => (
              <Badge key={index} variant="outline" className="text-xs px-2 py-0.5 h-5 bg-background hover:bg-muted/30 transition-colors">
                {capability}
              </Badge>
            ))}
          </div>
          
          {/* Usage statistics */}
          <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              {rating > 0 && (
                <div className="flex items-center">
                  <div className="flex">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <svg 
                        key={star}
                        className={cn("w-3 h-3", star <= rating ? "text-amber-500" : "text-gray-300")}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {lastSyncTime && (
              <div className="flex items-center gap-1">
                <RefreshCw size={10} />
                <span>Last sync: {lastSyncTime.toLocaleDateString()}</span>
              </div>
            )}
          </div>
        </CardContent>
        
        <CardFooter className="pt-3 pb-3 px-4 flex items-center justify-between border-t mt-auto bg-muted/5">
          <div>
            {connected ? (
              <div className="flex items-center gap-2">
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  status === 'healthy' ? "bg-green-500 animate-pulse" :
                  status === 'error' ? "bg-red-500" :
                  status === 'warning' ? "bg-amber-500" :
                  "bg-gray-400"
                )} />
                <Badge className={cn(
                  "text-xs flex items-center h-5 px-2 transition-colors",
                  status === 'healthy' ? "bg-green-100 text-green-800 border-green-200 hover:bg-green-200" :
                  status === 'error' ? "bg-red-100 text-red-800 border-red-200 hover:bg-red-200" :
                  status === 'warning' ? "bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-200" :
                  "bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-200"
                )}>
                  {status === 'healthy' && <Check size={10} className="mr-1" />}
                  {status === 'error' && <AlertCircle size={10} className="mr-1" />}
                  {status === 'warning' && <AlertCircle size={10} className="mr-1" />}
                  {status === 'healthy' ? 'Connected' : status === 'error' ? 'Error' : status === 'warning' ? 'Warning' : 'Unknown'}
                </Badge>
              </div>
            ) : (
              <Badge variant="outline" className="text-xs h-5 px-2 bg-background">
                Not Connected
              </Badge>
            )}
          </div>
          
          <div className="flex gap-2">
            {connected && connection ? (
              <Button 
                size="sm" 
                variant="outline"
                className="h-7 px-3 text-xs font-medium hover:bg-muted transition-colors"
                onClick={() => handleManageConnection(server.id)}
              >
                <Settings size={12} className="mr-1" /> Manage
              </Button>
            ) : (
              <Button 
                size="sm"
                variant="default" 
                className="h-7 px-3 text-xs font-medium hover:opacity-90 transition-opacity"
                onClick={() => handleConnect(server)}
              >
                <Plus size={12} className="mr-1" /> Connect
              </Button>
            )}
          </div>
        </CardFooter>
      </Card>
    );
  };
  
  // Render server card in list view
  const renderListCard = (server: MCPServerRegistry) => {
    const connected = isConnected(server.id);
    const status = getConnectionStatus(server.id);
    const connection = connections.find(conn => conn.server === server.id);
    const lastSyncTime = connection?.last_health_check ? new Date(connection.last_health_check) : null;
    const rating = server.rating || 0;
    
    // Get gradient color based on category
    const getCategoryGradient = (category: string) => {
      const categories: Record<string, string> = {
        'productivity': 'from-blue-500 to-indigo-600',
        'development': 'from-green-500 to-emerald-600',
        'ai': 'from-purple-500 to-violet-600',
        'crm': 'from-orange-500 to-amber-600',
        'database': 'from-cyan-500 to-blue-600',
        'finance': 'from-emerald-500 to-green-600',
        'media': 'from-pink-500 to-rose-600',
        'web': 'from-indigo-500 to-blue-600',
      };
      return categories[category.toLowerCase()] || 'from-gray-500 to-slate-600';
    };
    
    return (
      <Card className="group border border-border/40 hover:border-border/80 hover:shadow-lg transition-all duration-300 rounded-lg mb-3">
        <div className="flex items-center p-4 relative">
          {/* Status indicator dot - absolute positioned */}
          {connected && (
            <div className={cn(
              "absolute top-4 right-4 w-2 h-2 rounded-full",
              status === 'healthy' ? "bg-green-500 animate-pulse" :
              status === 'error' ? "bg-red-500" :
              status === 'warning' ? "bg-amber-500" :
              "bg-gray-400"
            )} />
          )}
          
          <div className="flex items-center gap-4 flex-grow">
            {/* Icon with gradient background */}
            <div className={cn(
              "rounded-md p-1 bg-gradient-to-br", 
              getCategoryGradient(server.category)
            )}>
              <Avatar className="h-10 w-10 ring-2 ring-white/20">
                {server.icon ? (
                  <AvatarImage src={server.icon} alt={server.display_name} className="object-cover" />
                ) : (
                  <AvatarFallback className="text-sm font-medium text-white">
                    {server.display_name.substring(0, 2).toUpperCase()}
                  </AvatarFallback>
                )}
              </Avatar>
            </div>
            
            {/* Main content */}
            <div className="flex-grow">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium group-hover:text-primary transition-colors">{server.display_name}</h3>
                {server.is_verified && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Badge variant="outline" className="text-xs h-5 px-1 border-blue-200 text-blue-700 bg-blue-50">
                          <Check size={10} className="mr-1" /> Verified
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">Verified by Dataelan team</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
              </div>
              <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{server.description}</p>
              
              {/* Capability tags */}
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                <Badge variant="secondary" className="text-xs px-2 py-0.5 h-5 bg-muted/50">
                  {server.category}
                </Badge>
                {server.capabilities.slice(0, 3).map((capability, index) => (
                  <Badge key={index} variant="outline" className="text-xs px-2 py-0.5 h-5 bg-background hover:bg-muted/30 transition-colors">
                    {capability}
                  </Badge>
                ))}
                {server.capabilities.length > 3 && (
                  <Badge variant="outline" className="text-xs px-2 py-0.5 h-5 bg-background hover:bg-muted/30 transition-colors">
                    +{server.capabilities.length - 3} more
                  </Badge>
                )}
              </div>
            </div>
            
            {/* Right side - status and actions */}
            <div className="flex flex-col items-end gap-2 min-w-[180px]">
              {/* Usage statistics */}
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {rating > 0 && (
                  <div className="flex items-center gap-1">
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <svg 
                          key={star}
                          className={cn("w-3 h-3", star <= rating ? "text-amber-500" : "text-gray-300")}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                    </div>
                  </div>
                )}
                {lastSyncTime && (
                  <div className="flex items-center gap-1">
                    <RefreshCw size={10} />
                    <span>Last sync: {lastSyncTime.toLocaleDateString()}</span>
                  </div>
                )}
              </div>
              
              {/* Status and actions */}
              <div className="flex items-center gap-2">
                {connected ? (
                  <div className="flex items-center gap-1.5">
                    <Badge className={cn(
                      "text-xs flex items-center h-5 px-2 transition-colors",
                      status === 'healthy' ? "bg-green-100 text-green-800 border-green-200 hover:bg-green-200" :
                      status === 'error' ? "bg-red-100 text-red-800 border-red-200 hover:bg-red-200" :
                      status === 'warning' ? "bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-200" :
                      "bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-200"
                    )}>
                      <div className={cn(
                        "w-2 h-2 rounded-full mr-1.5",
                        status === 'healthy' ? "bg-green-500 animate-pulse" :
                        status === 'error' ? "bg-red-500" :
                        status === 'warning' ? "bg-amber-500" :
                        "bg-gray-400"
                      )} />
                      {status === 'healthy' ? 'Connected' : status === 'error' ? 'Error' : status === 'warning' ? 'Warning' : 'Unknown'}
                    </Badge>
                    
                    <Button 
                      size="sm" 
                      variant="outline"
                      className="h-7 px-3 text-xs font-medium hover:bg-muted transition-colors"
                      onClick={() => handleManageConnection(server.id)}
                    >
                      <Settings size={12} className="mr-1" /> Manage
                    </Button>
                  </div>
                ) : (
                  <Button 
                    size="sm"
                    variant="default" 
                    className="h-7 px-3 text-xs font-medium hover:opacity-90 transition-opacity"
                    onClick={() => handleConnect(server)}
                  >
                    <Plus size={12} className="mr-1" /> Connect
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </Card>
    );
  };
  
  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header with title and actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Integrations</h1>
          <p className="text-muted-foreground">Connect with external tools and services</p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center gap-3">
          {/* Search bar with icon */}
          <div className="relative w-full sm:w-[280px]">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search integrations..." 
              className="pl-9 w-full" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2.5 h-4 w-4 text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            )}
          </div>
          
          {/* View toggle and filter buttons */}
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm"
                  className="h-9 px-2.5"
                >
                  <Filter size={16} className="mr-1.5" />
                  <span className="hidden sm:inline">Filter</span>
                  {selectedCategory !== 'all' && (
                    <Badge className="ml-1.5 h-5 w-5 p-0 flex items-center justify-center">
                      1
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="p-2">
                  <h4 className="mb-2 text-sm font-medium">Categories</h4>
                  {categories.map((category) => (
                    <DropdownMenuItem 
                      key={category.id} 
                      className={cn(selectedCategory === category.id && "bg-accent")} 
                      onClick={() => setSelectedCategory(category.id)}
                    >
                      {category.label}
                    </DropdownMenuItem>
                  ))}
                </div>
              </DropdownMenuContent>
            </DropdownMenu>
            
            <div className="border rounded-md flex">
              <Button 
                variant="ghost" 
                size="sm" 
                className={cn("rounded-none px-2 h-9", viewMode === "grid" && "bg-accent")} 
                onClick={() => setViewMode("grid")}
              >
                <Grid size={16} />
              </Button>
              <Separator orientation="vertical" />
              <Button 
                variant="ghost" 
                size="sm" 
                className={cn("rounded-none px-2 h-9", viewMode === "list" && "bg-accent")} 
                onClick={() => setViewMode("list")}
              >
                <List size={16} />
              </Button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Status filter tabs */}
      <div className="flex border-b">
        <Button 
          variant="ghost" 
          className={cn(
            "rounded-none border-b-2 -mb-px pb-2", 
            selectedStatus === 'all' ? "border-primary" : "border-transparent hover:border-muted"
          )}
          onClick={() => setSelectedStatus('all')}
        >
          All Integrations
        </Button>
        <Button 
          variant="ghost" 
          className={cn(
            "rounded-none border-b-2 -mb-px pb-2", 
            selectedStatus === 'connected' ? "border-primary" : "border-transparent hover:border-muted"
          )}
          onClick={() => setSelectedStatus('connected')}
        >
          Connected
        </Button>
        <Button 
          variant="ghost" 
          className={cn(
            "rounded-none border-b-2 -mb-px pb-2", 
            selectedStatus === 'not-connected' ? "border-primary" : "border-transparent hover:border-muted"
          )}
          onClick={() => setSelectedStatus('not-connected')}
        >
          Not Connected
        </Button>
      </div>
      
      {/* Active filters display */}
      {(selectedCategory !== 'all' || selectedStatus !== 'all') && (
        <div className="flex flex-wrap gap-2">
          {selectedCategory !== 'all' && (
            <Badge variant="secondary" className="flex items-center gap-1 px-2 py-1">
              Category: {categories.find(c => c.id === selectedCategory)?.label || selectedCategory}
              <X 
                size={14} 
                className="cursor-pointer ml-1" 
                onClick={() => setSelectedCategory('all')} 
              />
            </Badge>
          )}
          {selectedStatus !== 'all' && (
            <Badge variant="secondary" className="flex items-center gap-1 px-2 py-1">
              Status: {selectedStatus === 'connected' ? 'Connected' : 'Not Connected'}
              <X 
                size={14} 
                className="cursor-pointer ml-1" 
                onClick={() => setSelectedStatus('all')} 
              />
            </Badge>
          )}
        </div>
      )}
      
      {/* Main content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <span className="ml-3 text-lg text-muted-foreground">Loading integrations...</span>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <AlertCircle className="h-12 w-12 text-destructive mb-4" />
          <h3 className="text-lg font-medium">Failed to load integrations</h3>
          <p className="text-muted-foreground mt-2">{error}</p>
          <Button 
            variant="outline" 
            className="mt-4"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={16} className="mr-2" /> Try Again
          </Button>
        </div>
      ) : filteredServers.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Search className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium">No integrations found</h3>
          <p className="text-muted-foreground mt-2">
            {searchQuery 
              ? `No results for "${searchQuery}"`
              : selectedCategory !== 'all' 
                ? `No integrations in the ${categories.find(c => c.id === selectedCategory)?.label || selectedCategory} category`
                : 'No integrations match your filters'}
          </p>
          <Button 
            variant="outline" 
            className="mt-4"
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory('all');
              setSelectedStatus('all');
            }}
          >
            <RefreshCw size={16} className="mr-2" /> Clear Filters
          </Button>
        </div>
      ) : (
        <AnimatePresence>
          <div className={cn(
            viewMode === "grid" 
              ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" 
              : "space-y-3"
          )}>
            {filteredServers.map(server => (
              <motion.div 
                key={server.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
              >
                {renderServerCard(server)}
              </motion.div>
            ))}
          </div>
        </AnimatePresence>
      )}
    </div>
  );
}
