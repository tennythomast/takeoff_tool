"use client"

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Filter, 
  Check, 
  ArrowUpDown, 
  BarChart3, 
  FileText, 
  MessageSquare, 
  Activity, 
  FileIcon as FileIconLucide, 
  Wrench as ToolIcon, 
  Plus, 
  Search,
  LineChart
} from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import CreateWorkspaceDialog from './CreateWorkspaceDialog';
import { formatDate } from '@/lib/utils/formatting';
import { useWorkspaces } from '@/hooks/use-workspaces';

interface WorkspaceListingPageProps {
  status?: string;
  pathname?: string;
}

export default function WorkspaceListingPage({ status: statusProp, pathname }: WorkspaceListingPageProps = {}) {
  const router = useRouter();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(statusProp?.toLowerCase() || null);
  
  // Use filters based on the status prop, but handle 'recent' specially
  const { workspaces, isLoading, error, fetchWorkspaces } = useWorkspaces({
    initialFilters: statusProp && statusProp !== 'recent' ? { status: statusProp.toString().toUpperCase() } : {},
    autoFetch: true,
  });

  // Debug workspace data
  console.log('WorkspaceListingPage received workspaces:', workspaces);
  
  // Filter workspaces by search query
  const filteredWorkspaces = Array.isArray(workspaces) 
    ? workspaces.filter(workspace => 
        (workspace.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        workspace.description?.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : [];

  const handleOpenCreateDialog = () => {
    setIsCreateDialogOpen(true);
  };

  const handleCloseCreateDialog = () => {
    setIsCreateDialogOpen(false);
  };
  
  // Update filters when status changes
  useEffect(() => {
    if (status) {
      setStatusFilter(status.toString().toLowerCase());
    }
  }, [status]);
  
  // Apply status filter
  const handleStatusFilterChange = (newStatus: string | null) => {
    console.log('Status filter changing from', statusFilter, 'to', newStatus);
    setStatusFilter(newStatus);
    
    // Fetch workspaces with the new filter
    if (newStatus) {
      // Handle 'recent' filter differently - don't send it as a status filter to the backend
      if (newStatus === 'recent') {
        console.log('Applying recent filter - fetching without status filter');
        // For recent, we'll just fetch the most recent workspaces without a status filter
        // and sort by updated_at on the frontend
        fetchWorkspaces({});
      } else {
        // Use the exact status string as defined in the backend model
        const statusFilter = { status: newStatus.toUpperCase() };
        console.log('Applying filter:', statusFilter);
        
        // Debug: Log the filter object
        console.log('Filter object type:', typeof statusFilter);
        console.log('Filter object keys:', Object.keys(statusFilter));
        console.log('Filter object values:', Object.values(statusFilter));
        
        // Call fetchWorkspaces with the filter
        fetchWorkspaces(statusFilter);
      }
      
      // Update URL to reflect the filter
      router.push(`/workspaces/${newStatus}`);
    } else {
      console.log('Clearing filters');
      fetchWorkspaces({});
      
      // Update URL to reflect no filter
      router.push('/workspaces');
    }
  };

  const handleWorkspaceClick = (workspaceId: string) => {
    router.push(`/workspaces/${workspaceId}`);
  };

  // Determine the page title based on the status filter
  const getPageTitle = () => {
    if (!status) return 'All Workspaces';
    
    switch (status.toString().toLowerCase()) {
      case 'active': return 'Active Workspaces';
      case 'archived': return 'Archived Workspaces';
      case 'completed': return 'Completed Workspaces';
      case 'recent': return 'Recent Workspaces';
      default: return 'All Workspaces';
    }
  };

  return (
    <div className="container mx-auto px-4 pt-2 pb-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{getPageTitle()}</h1>
        <Button onClick={handleOpenCreateDialog}>
          <Plus className="h-4 w-4 mr-2" /> New Workspace
        </Button>
      </div>

      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 mb-4">
        <div className="relative flex-grow">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search workspaces..."
            className="pl-10"
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4 mr-2" /> Filter
                {statusFilter && <span className="ml-1 text-xs bg-blue-100 text-blue-800 rounded px-1">{statusFilter}</span>}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleStatusFilterChange(null)}>
                <div className="flex items-center w-full">
                  All Workspaces
                  {!statusFilter && <Check className="ml-auto h-4 w-4" />}
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleStatusFilterChange('active')}>
                <div className="flex items-center w-full">
                  Active
                  {statusFilter === 'active' && <Check className="ml-auto h-4 w-4" />}
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleStatusFilterChange('archived')}>
                <div className="flex items-center w-full">
                  Archived
                  {statusFilter === 'archived' && <Check className="ml-auto h-4 w-4" />}
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleStatusFilterChange('completed')}>
                <div className="flex items-center w-full">
                  Completed
                  {statusFilter === 'completed' && <Check className="ml-auto h-4 w-4" />}
                </div>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" size="sm">
            <ArrowUpDown className="h-4 w-4 mr-2" /> Sort
          </Button>
        </div>
      </div>

      {/* Workspaces Grid */}
      {isLoading ? (
        <div className="text-center py-10">Loading workspaces...</div>
      ) : error ? (
        <div className="text-center py-10 text-red-500">
          Error loading workspaces: {error.message}
        </div>
      ) : filteredWorkspaces.length === 0 ? (
        <div className="text-center py-10">
          {searchQuery ? 'No workspaces match your search' : 'No workspaces found'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredWorkspaces.map((workspace) => (
            <div 
              key={workspace.id} 
              className="cursor-pointer hover:shadow-lg transition-all duration-200 group relative overflow-hidden"
              onClick={() => handleWorkspaceClick(workspace.id)}
            >
              <Card className="overflow-hidden border border-gray-100 hover:shadow-md transition-all duration-200 group relative">
                {/* Status Badge - Absolute top right corner */}
                <Badge 
                  className="absolute top-2 right-2 text-xs py-0 px-2 rounded-md z-10"
                  variant={workspace.status === 'ACTIVE' ? 'default' : workspace.status === 'ARCHIVED' ? 'outline' : 'secondary'}
                >
                  {workspace.status.charAt(0) + workspace.status.slice(1).toLowerCase()}
                </Badge>
                
                {/* Card Content */}
                <div className="p-4">
                  {/* Title and Description */}
                  <div className="mb-4">
                    <h2 className="text-lg font-semibold group-hover:text-blue-600 transition-colors">
                      {workspace.name}
                    </h2>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {workspace.description || 'Auto-created workspace for AI chat sessions'}
                    </p>
                  </div>
                  
                  {/* Key Metrics Row */}
                  <div className="flex justify-between mb-4">
                    <div className="text-center bg-blue-50 rounded-md px-3 py-1 w-[30%]">
                      <div className="text-sm font-medium text-blue-700">
                        {workspace.metadata?.collaboratorCount || 0}/{workspace.metadata?.maxCollaborators || 5}
                      </div>
                      <div className="text-xs text-blue-600">Agents</div>
                    </div>
                    
                    <div className="text-center bg-green-50 rounded-md px-3 py-1 w-[30%]">
                      <div className="text-sm font-medium text-green-700">
                        -{workspace.metadata?.savingsPercentage || '67'}%
                      </div>
                      <div className="text-xs text-green-600">Savings</div>
                    </div>
                    
                    <div className="text-center bg-amber-50 rounded-md px-3 py-1 w-[30%]">
                      <div className="text-sm font-medium text-amber-700">
                        {workspace.metadata?.healthScore || '94'}%
                      </div>
                      <div className="text-xs text-amber-600">Health</div>
                    </div>
                  </div>

                  {/* Recent Activity */}
                  <div className="mb-4">
                    <h4 className="text-xs font-medium text-gray-700 mb-1 flex items-center">
                      <Activity className="w-3 h-3 mr-1" />
                      Recent Activity
                    </h4>
                    {workspace.metadata?.recentActivities && workspace.metadata.recentActivities.length > 0 ? (
                      workspace.metadata.recentActivities.slice(0, 1).map((activity: { type: string; description: string; time: string }, index: number) => (
                        <div key={index} className="text-xs text-gray-600">
                          {activity.description}
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-gray-400">No recent activity</div>
                    )}
                  </div>

                  {/* Resources Summary */}
                  <div className="flex justify-between text-xs text-gray-500 py-2 border-t border-gray-100 mb-4">
                    <span className="flex items-center">
                      <FileIconLucide className="w-3 h-3 mr-1" />
                      {workspace.metadata?.fileCount || 24} files
                    </span>
                    <span className="flex items-center">
                      <ToolIcon className="w-3 h-3 mr-1" />
                      {workspace.metadata?.toolCount || 8} tools
                    </span>
                    <span className="flex items-center">
                      <MessageSquare className="w-3 h-3 mr-1" />
                      {workspace.metadata?.chatCount || 432} chats
                    </span>
                  </div>
                    
                  {/* Context-specific Primary Button */}
                  {/* TO DO: Update this to reflec the workspace context */}
                  <div>
                    <Button 
                      size="sm" 
                      className="w-full bg-blue-600 hover:bg-blue-700 text-xs py-1 h-8"
                    >
                      {workspace.status === 'ACTIVE' ? (
                        <>
                          <MessageSquare className="w-3 h-3 mr-1" />
                          Continue Working
                        </>
                      ) : workspace.status === 'COMPLETED' ? (
                        <>
                          <FileText className="w-3 h-3 mr-1" />
                          View Results
                        </>
                      ) : (
                        <>
                          <Plus className="w-3 h-3 mr-1" />
                          Set Up Workspace
                        </>
                      )}
                    </Button>
                  </div>
                </div>
                
                {/* Status Badge moved to top right */}
              </Card>
            </div>
          ))}
        </div>
      )}
      
      {/* Create Workspace Dialog */}
      <CreateWorkspaceDialog 
        isOpen={isCreateDialogOpen} 
        onClose={handleCloseCreateDialog} 
      />
    </div>
  );
}
