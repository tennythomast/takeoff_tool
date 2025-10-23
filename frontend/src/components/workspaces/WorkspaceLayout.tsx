import React from 'react';
import { useRouter } from 'next/router';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Briefcase, PanelRight, Archive, Clock } from 'lucide-react';

interface WorkspaceLayoutProps {
  children: React.ReactNode;
}

export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  const router = useRouter();
  const { pathname } = router;
  
  const isActive = (path: string) => {
    if (path === '/workspaces' && pathname === '/workspaces') {
      return true;
    }
    return pathname === path;
  };
  
  const handleTabChange = (value: string) => {
    router.push(value);
  };
  
  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6">
        <Tabs 
          value={
            pathname === '/workspaces' ? '/workspaces' :
            pathname === '/workspaces/active' ? '/workspaces/active' :
            pathname === '/workspaces/archived' ? '/workspaces/archived' :
            pathname === '/workspaces/completed' ? '/workspaces/completed' :
            pathname === '/workspaces/recent' ? '/workspaces/recent' :
            '/workspaces'
          }
          onValueChange={handleTabChange}
          className="w-full"
        >
          <TabsList className="grid grid-cols-5 w-full max-w-2xl">
            <TabsTrigger value="/workspaces" className="flex items-center">
              <Briefcase className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">All Workspaces</span>
              <span className="sm:hidden">All</span>
            </TabsTrigger>
            <TabsTrigger value="/workspaces/active" className="flex items-center">
              <PanelRight className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Active</span>
              <span className="sm:hidden">Active</span>
            </TabsTrigger>
            <TabsTrigger value="/workspaces/archived" className="flex items-center">
              <Archive className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Archived</span>
              <span className="sm:hidden">Archived</span>
            </TabsTrigger>
            <TabsTrigger value="/workspaces/completed" className="flex items-center">
              <PanelRight className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Completed</span>
              <span className="sm:hidden">Done</span>
            </TabsTrigger>
            <TabsTrigger value="/workspaces/recent" className="flex items-center">
              <Clock className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Recent</span>
              <span className="sm:hidden">Recent</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      
      {children}
    </div>
  );
}
