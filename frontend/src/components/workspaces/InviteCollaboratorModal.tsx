import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter,
  DialogDescription
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Search, Loader2 } from "lucide-react";
import { fetchOrganizationUsers } from '@/lib/api/organization-api';
import { workspaceService } from '@/lib/services/workspace-service';

interface User {
  id: string;
  name: string;
  email: string;
  first_name: string;
  last_name: string;
}

interface InviteCollaboratorModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
  organizationId: string;
  onInviteSuccess: () => void;
}

export function InviteCollaboratorModal({
  isOpen,
  onClose,
  workspaceId,
  organizationId,
  onInviteSuccess
}: InviteCollaboratorModalProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<Record<string, boolean>>({});
  const [selectedRole, setSelectedRole] = useState<'VIEWER' | 'EDITOR' | 'ADMIN'>('VIEWER');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch organization users who are not already collaborators
  useEffect(() => {
    if (isOpen && organizationId) {
      fetchUsers();
    }
  }, [isOpen, organizationId, searchQuery]);

  const fetchUsers = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('Fetching organization users with params:', {
        organizationId,
        workspaceId,
        searchQuery
      });
      
      const orgUsers = await fetchOrganizationUsers(organizationId, {
        workspaceId,
        search: searchQuery
      });
      
      console.log('Successfully fetched organization users:', orgUsers);
      setUsers(orgUsers);
    } catch (err: any) {
      console.error('Error fetching organization users:', err);
      // More detailed error message
      setError(`Failed to load organization users: ${err.message || 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectUser = (userId: string, checked: boolean) => {
    setSelectedUsers(prev => ({
      ...prev,
      [userId]: checked
    }));
  };

  const handleSelectAll = (checked: boolean) => {
    const newSelected: Record<string, boolean> = {};
    users.forEach(user => {
      newSelected[user.id] = checked;
    });
    setSelectedUsers(newSelected);
  };

  const handleInvite = async () => {
    const selectedUserIds = Object.entries(selectedUsers)
      .filter(([_, isSelected]) => isSelected)
      .map(([userId]) => userId);
    
    if (selectedUserIds.length === 0) {
      setError('Please select at least one user to invite');
      return;
    }
    
    setIsInviting(true);
    setError(null);
    
    try {
      // Invite each selected user
      for (const userId of selectedUserIds) {
        await workspaceService.addCollaborator(workspaceId, userId, selectedRole);
      }
      
      // Clear selections and close modal
      setSelectedUsers({});
      onInviteSuccess();
      onClose();
    } catch (err) {
      console.error('Error inviting collaborators:', err);
      setError('Failed to invite collaborators');
    } finally {
      setIsInviting(false);
    }
  };

  // Generate initials from name
  const getInitials = (user: User) => {
    if (user.first_name && user.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    }
    if (user.name) {
      const nameParts = user.name.split(' ');
      if (nameParts.length >= 2) {
        return `${nameParts[0][0]}${nameParts[1][0]}`.toUpperCase();
      }
      return user.name.substring(0, 2).toUpperCase();
    }
    if (user.email) {
      return user.email.substring(0, 2).toUpperCase();
    }
    return 'US';
  };

  const selectedCount = Object.values(selectedUsers).filter(Boolean).length;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md md:max-w-lg">
        <DialogHeader>
          <DialogTitle>Invite Team Members</DialogTitle>
          <DialogDescription>
            Invite members from your organization to collaborate on this workspace.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-2">
          {/* Search and role selection */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
              <Input
                placeholder="Search by name or email"
                className="pl-9"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Select value={selectedRole} onValueChange={(value: 'VIEWER' | 'EDITOR' | 'ADMIN') => setSelectedRole(value)}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="VIEWER">Viewer</SelectItem>
                <SelectItem value="EDITOR">Editor</SelectItem>
                <SelectItem value="ADMIN">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Error message */}
          {error && (
            <div className="text-sm text-red-500 p-2 bg-red-50 rounded-md">
              {error}
            </div>
          )}
          
          {/* User list */}
          <div className="border rounded-md overflow-hidden">
            {/* Header with select all */}
            <div className="flex items-center p-3 bg-gray-50 border-b">
              <div className="flex items-center">
                <Checkbox 
                  id="select-all" 
                  checked={users.length > 0 && users.every(user => selectedUsers[user.id])}
                  onCheckedChange={(checked) => handleSelectAll(!!checked)}
                  disabled={isLoading || users.length === 0}
                />
                <label htmlFor="select-all" className="ml-2 text-sm font-medium">
                  Select All
                </label>
              </div>
              <div className="ml-auto text-sm text-gray-500">
                {selectedCount} selected
              </div>
            </div>
            
            {/* User list */}
            <div className="max-h-[300px] overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                  <span className="ml-2 text-gray-500">Loading users...</span>
                </div>
              ) : users.length === 0 ? (
                <div className="text-center p-8 text-gray-500">
                  {searchQuery ? 'No users found matching your search' : 'No users available to invite'}
                </div>
              ) : (
                <div className="divide-y">
                  {users.map(user => (
                    <div key={user.id} className="flex items-center p-3 hover:bg-gray-50">
                      <Checkbox 
                        id={`user-${user.id}`}
                        checked={!!selectedUsers[user.id]}
                        onCheckedChange={(checked) => handleSelectUser(user.id, !!checked)}
                      />
                      <div className="ml-3 flex items-center flex-1 min-w-0">
                        <Avatar className="h-8 w-8 mr-3">
                          <AvatarFallback>{getInitials(user)}</AvatarFallback>
                        </Avatar>
                        <div className="truncate">
                          <div className="font-medium">{user.name || `${user.first_name} ${user.last_name}`}</div>
                          <div className="text-sm text-gray-500 truncate">{user.email}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button 
            onClick={handleInvite} 
            disabled={isInviting || selectedCount === 0}
          >
            {isInviting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Invite {selectedCount > 0 ? `(${selectedCount})` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default InviteCollaboratorModal;
