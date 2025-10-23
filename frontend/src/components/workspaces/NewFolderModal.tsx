"use client"

import React, { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { toast } from "@/components/ui/use-toast"
import { FolderPlus, Check } from "lucide-react"
import { fileApiService } from '@/lib/api/file-api'

interface NewFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId?: string;
  parentFolderId?: string;
  onFolderCreated?: () => void;
}

export function NewFolderModal({
  isOpen,
  onClose,
  workspaceId,
  parentFolderId,
  onFolderCreated
}: NewFolderModalProps) {
  // Form state
  const [folderName, setFolderName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  // Handle folder creation
  const handleCreateFolder = async () => {
    // Validate folder name
    if (!folderName.trim()) {
      setError('Folder name is required');
      return;
    }
    
    // Validate workspace ID
    if (!workspaceId) {
      setError('Workspace ID is required');
      return;
    }
    
    setIsCreating(true);
    setError(null);
    
    try {
      // Log request data for debugging
      const folderData = {
        name: folderName.trim(),
        workspace: workspaceId,
        // Only include parent_folder if it exists (undefined is acceptable for the API)
        ...(parentFolderId ? { parent_folder: parentFolderId } : {})
      };
      
      // Note: The organization ID will be fetched in the API service
      
      console.log('Creating folder with data:', folderData);
      
      // Create folder
      const createdFolder = await fileApiService.createFolder(folderData);
      
      console.log('Folder created successfully:', createdFolder);
      
      // Show success state
      setSuccess(true);
      
      // Show success toast
      toast({
        title: "Folder created",
        description: `${folderName} has been created successfully.`,
      });
      
      console.log('Calling onFolderCreated callback to refresh folder list');
      
      // Notify parent component IMMEDIATELY to refresh the folder list
      if (onFolderCreated) {
        onFolderCreated();
      }
      
      // Reset form and close modal after a delay
      setTimeout(() => {
        // Call onFolderCreated again just to be sure the list is refreshed
        if (onFolderCreated) {
          console.log('Calling onFolderCreated callback again after delay');
          onFolderCreated();
        }
        
        resetForm();
        onClose();
      }, 1500);
    } catch (error) {
      console.error('Folder creation error:', error);
      
      // More detailed error logging
      if (error instanceof Error) {
        console.error('Error message:', error.message);
      } else if (typeof error === 'object' && error !== null) {
        console.error('Error object:', JSON.stringify(error));
      }
      
      setError(error instanceof Error ? error.message : 'Failed to create folder');
    } finally {
      setIsCreating(false);
    }
  };
  
  // Reset form
  const resetForm = () => {
    setFolderName('');
    setError(null);
    setSuccess(false);
  };
  
  // Handle modal close
  const handleClose = () => {
    if (!isCreating) {
      resetForm();
      onClose();
    }
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Create New Folder</DialogTitle>
          <DialogDescription>
            Create a new folder to organize your files.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="folder-name">Folder Name</Label>
            <Input
              id="folder-name"
              placeholder="Enter folder name"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              disabled={isCreating || success}
              autoFocus
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
          </div>
          
          {/* Parent folder info (if applicable) */}
          {parentFolderId && (
            <div className="text-sm text-gray-500">
              This folder will be created inside the current folder.
            </div>
          )}
          
          {/* Success message */}
          {success && (
            <div className="text-green-500 text-sm flex items-center">
              <Check className="h-4 w-4 mr-1" /> Folder created successfully!
            </div>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isCreating}>
            Cancel
          </Button>
          <Button 
            onClick={handleCreateFolder} 
            disabled={!folderName.trim() || isCreating || success}
          >
            <FolderPlus className="h-4 w-4 mr-2" />
            {isCreating ? 'Creating...' : 'Create Folder'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
