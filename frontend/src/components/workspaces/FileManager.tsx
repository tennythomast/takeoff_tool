"use client"

import React, { useState, useEffect, useCallback } from 'react'
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { 
  Upload, 
  FolderPlus, 
  Search, 
  Filter, 
  Grid, 
  List, 
  MoreHorizontal, 
  Folder, 
  FileText, 
  Image, 
  FileArchive, 
  File, 
  Download, 
  Trash, 
  Share, 
  Star,
  ChevronRight,
  SortAsc,
  Loader2,
  AlertCircle,
  ArrowLeft,
  RefreshCw
} from "lucide-react"
import { FileUploadModal } from "./FileUploadModal"
import { NewFolderModal } from "./NewFolderModal"
import { fileApiService, FileUpload, FileFolder } from "@/lib/api/file-api"
import { toast } from "@/components/ui/use-toast"
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

// File types and their corresponding icons
const fileTypeIcons = {
  folder: <Folder className="h-10 w-10 text-blue-500" />,
  pdf: <FileText className="h-10 w-10 text-red-500" />,
  image: <Image className="h-10 w-10 text-green-500" />,
  zip: <FileArchive className="h-10 w-10 text-yellow-500" />,
  default: <File className="h-10 w-10 text-gray-500" />
}

// Helper function to get icon based on file type
const getFileIcon = (type: string) => {
  if (type === 'folder') return fileTypeIcons.folder
  if (type === 'pdf') return fileTypeIcons.pdf
  if (type.includes('image')) return fileTypeIcons.image
  if (type === 'zip' || type === 'archive') return fileTypeIcons.zip
  return fileTypeIcons.default
}

// Helper function to format file size
const formatFileSize = (sizeInBytes: number | undefined) => {
  if (!sizeInBytes) return '—'
  
  if (sizeInBytes < 1024) {
    return `${sizeInBytes} B`
  } else if (sizeInBytes < 1024 * 1024) {
    return `${(sizeInBytes / 1024).toFixed(1)} KB`
  } else {
    return `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`
  }
}

// Combined file/folder item interface
export interface FileItem {
  id: string
  name: string
  type: string
  size?: number
  lastModified?: string
  starred?: boolean
  isFolder?: boolean
  parentFolder?: string
  fileCount?: number
  status?: string
  accessLevel?: string
}

// Convert API file to UI FileItem
const convertApiFileToFileItem = (file: FileUpload): FileItem => {
  return {
    id: file.id,
    name: file.original_filename,
    type: file.file_extension.replace('.', '') || 'default',
    size: file.file_size_bytes,
    lastModified: file.updated_at,
    isFolder: false,
    starred: false, // This would come from user preferences in a real app
    status: file.status,
    accessLevel: file.access_level
  };
};

// Convert API folder to UI FileItem
const convertApiFolderToFileItem = (folder: FileFolder): FileItem => {
  return {
    id: folder.id,
    name: folder.name,
    type: 'folder',
    lastModified: folder.updated_at,
    isFolder: true,
    parentFolder: folder.parent_folder,
    fileCount: folder.file_count,
    starred: false // This would come from user preferences in a real app
  };
};

interface FileManagerProps {
  workspaceId?: string;
  initialFiles?: FileItem[];
  currentFolderId?: string;
  onFolderChange?: (folderId: string | undefined) => void;
  onFileSelected?: (file: FileItem) => void;
}

export function FileManager({
  workspaceId,
  initialFiles = [],
  currentFolderId,
  onFolderChange,
  onFileSelected
}: FileManagerProps) {
  // State for files and folders
  const [files, setFiles] = useState<FileItem[]>(initialFiles);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentFolder, setCurrentFolder] = useState<string | undefined>(currentFolderId);
  const [breadcrumbs, setBreadcrumbs] = useState<{id: string, name: string}[]>([]);
  
  // Add a forcedRefresh state to trigger refreshes
  const [forcedRefresh, setForcedRefresh] = useState<number>(0);
  
  // Modal states
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isNewFolderModalOpen, setIsNewFolderModalOpen] = useState<boolean>(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState<boolean>(false);
  const [fileToDelete, setFileToDelete] = useState<FileItem | null>(null);
  
  // UI states
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'size'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Update breadcrumbs when folder changes
  const updateBreadcrumbs = (folderId: string, allFolders: FileFolder[]) => {
    const breadcrumbItems: {id: string, name: string}[] = [];
    let currentId = folderId;
    
    // Build breadcrumbs by traversing parent folders
    while (currentId) {
      const folder = allFolders.find(f => f.id === currentId);
      if (folder) {
        breadcrumbItems.unshift({ id: folder.id, name: folder.name });
        currentId = folder.parent_folder || '';
      } else {
        break;
      }
    }
    
    setBreadcrumbs(breadcrumbItems);
  };

  // Load files and folders
  const loadFilesAndFolders = async () => {
    console.log('Loading files and folders, workspace:', workspaceId, 'folder:', currentFolder);
    
    if (!workspaceId) {
      console.log('No workspace ID, using initial files');
      setFiles(initialFiles);
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Use mock data if the API endpoints are not available yet
      let apiFiles: FileUpload[] = [];
      let apiFolders: FileFolder[] = [];
      
      try {
        console.log('Fetching files for workspace:', workspaceId, 'folder:', currentFolder);
        // Get files for the current workspace and folder
        apiFiles = await fileApiService.getFiles({
          workspace: workspaceId,
          parent_folder: currentFolder
        });
        console.log('Files fetched successfully:', apiFiles.length);
      } catch (fileErr) {
        console.warn('Error fetching files, using mock data:', fileErr);
        // Use mock data for development
        apiFiles = [];
      }
      
      try {
        console.log('Fetching folders for workspace:', workspaceId);
        // Get folders for the current workspace and parent folder
        apiFolders = await fileApiService.getFolders(workspaceId);
        console.log('Folders fetched successfully:', apiFolders.length);
      } catch (folderErr) {
        console.warn('Error fetching folders, using mock data:', folderErr);
        // Use mock data for development
        apiFolders = [];
      }
      
      // Filter folders by current folder
      const filteredFolders = apiFolders.filter(folder => 
        folder.parent_folder === currentFolder
      );
      console.log('Filtered folders for current location:', filteredFolders.length);
      
      // Convert API responses to UI items
      const fileItems = apiFiles.map(convertApiFileToFileItem);
      const folderItems = filteredFolders.map(convertApiFolderToFileItem);
      
      console.log('UI items prepared:', {
        files: fileItems.length,
        folders: folderItems.length,
        total: fileItems.length + folderItems.length
      });
      
      // Always use actual data from the API, no mock fallback
      // Combine files and folders
      setFiles([...folderItems, ...fileItems]);
      
      // Update breadcrumbs
      if (currentFolder) {
        updateBreadcrumbs(currentFolder, apiFolders);
      } else {
        setBreadcrumbs([]);
      }
    } catch (err: unknown) {
      console.error('Error loading files and folders:', err);
      setError('Failed to load files. Please try again.');
      setFiles([]);
      // Re-throw the error so the retry mechanism can handle it
      throw err;
    } finally {
      setLoading(false);
    }
  };
  
  // Load files when component mounts or when currentFolder/workspaceId changes or forcedRefresh is triggered
  useEffect(() => {
    // Prevent infinite retries if the API endpoint is not available
    let retryCount = 0;
    const maxRetries = 3;
    let isMounted = true;
    
    console.log('FileManager useEffect triggered. Workspace:', workspaceId, 'Folder:', currentFolder, 'Refresh:', forcedRefresh);
    
    const loadWithRetry = async () => {
      if (!isMounted) return;
      
      try {
        await loadFilesAndFolders();
      } catch (err) {
        if (!isMounted) return;
        
        if (retryCount < maxRetries) {
          retryCount++;
          console.log(`Retrying file load (${retryCount}/${maxRetries})...`);
          // Add exponential backoff to prevent rate limiting
          const delayMs = 1000 * Math.pow(2, retryCount - 1); // 1s, 2s, 4s
          setTimeout(loadWithRetry, delayMs);
        } else {
          console.error('Max retries reached for loading files');
          setError('Failed to load files after multiple attempts. The file API may not be available.');
          setLoading(false);
        }
      }
    };
    
    // Add a small delay before initial load to prevent rate limiting
    // when multiple components initialize at the same time
    const timer = setTimeout(() => {
      loadWithRetry();
    }, 300);
    
    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [workspaceId, currentFolder, forcedRefresh]); // Re-run when workspace, folder, or forcedRefresh changes
  
  // Handle folder navigation
  const handleFolderClick = (folder: FileItem) => {
    if (folder.isFolder) {
      setCurrentFolder(folder.id);
      if (onFolderChange) {
        onFolderChange(folder.id);
      }
    } else if (onFileSelected) {
      onFileSelected(folder);
    }
  };
  
  // Handle navigation to parent folder
  const handleNavigateUp = () => {
    if (breadcrumbs.length > 1) {
      // Go to parent folder (second last in breadcrumbs)
      const parentFolder = breadcrumbs[breadcrumbs.length - 2];
      setCurrentFolder(parentFolder.id);
      if (onFolderChange) {
        onFolderChange(parentFolder.id);
      }
    } else {
      // Go to root
      setCurrentFolder(undefined);
      if (onFolderChange) {
        onFolderChange(undefined);
      }
    }
  };
  
  // Handle breadcrumb navigation
  const handleBreadcrumbClick = (folderId: string) => {
    setCurrentFolder(folderId);
    if (onFolderChange) {
      onFolderChange(folderId);
    }
  };
  
  // Handle file upload
  const handleFileUpload = () => {
    setIsUploadModalOpen(true);
  };
  
  // Handle new folder creation
  const handleNewFolder = () => {
    setIsNewFolderModalOpen(true);
  };
  
  // Handle file deletion
  const handleDeleteFile = (file: FileItem) => {
    setFileToDelete(file);
    setIsDeleteDialogOpen(true);
  };
  
  // Confirm file deletion
  const confirmDeleteFile = async () => {
    if (!fileToDelete) return;
    
    try {
      if (fileToDelete.isFolder) {
        await fileApiService.deleteFolder(fileToDelete.id);
        toast({
          title: "Folder deleted",
          description: `${fileToDelete.name} has been deleted.`,
        });
      } else {
        await fileApiService.deleteFile(fileToDelete.id);
        toast({
          title: "File deleted",
          description: `${fileToDelete.name} has been deleted.`,
        });
      }
      
      // Refresh files
      loadFilesAndFolders();
    } catch (err: unknown) {
      console.error('Error deleting file:', err);
      toast({
        title: "Error",
        description: `Failed to delete ${fileToDelete.isFolder ? 'folder' : 'file'}. Please try again.`,
        variant: "destructive"
      });
    } finally {
      setIsDeleteDialogOpen(false);
      setFileToDelete(null);
    }
  };
  
  // Handle file download
  const handleDownloadFile = async (file: FileItem) => {
    if (file.isFolder) return;
    
    try {
      await fileApiService.downloadFile(file.id, file.name);
    } catch (err: unknown) {
      console.error('Error downloading file:', err);
      toast({
        title: "Error",
        description: "Failed to download file. Please try again.",
        variant: "destructive"
      });
    }
  };
  
  // Handle file star/unstar
  const handleStarFile = (file: FileItem) => {
    // In a real app, this would update user preferences
    toast({
      title: file.starred ? "Removed from favorites" : "Added to favorites",
      description: `${file.name} has been ${file.starred ? 'removed from' : 'added to'} your favorites.`,
    });
    
    // Update local state
    setFiles(prevFiles => 
      prevFiles.map(f => 
        f.id === file.id ? { ...f, starred: !f.starred } : f
      )
    );
  };
  
  // Filter files based on search query
  const filteredFiles = files.filter(file => 
    file.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Sort files
  const sortedFiles = [...filteredFiles].sort((a, b) => {
    // Folders always come first
    if (a.isFolder && !b.isFolder) return -1;
    if (!a.isFolder && b.isFolder) return 1;
    
    // Then sort by the selected criteria
    if (sortBy === 'name') {
      return sortOrder === 'asc' 
        ? a.name.localeCompare(b.name) 
        : b.name.localeCompare(a.name);
    } else if (sortBy === 'date' && a.lastModified && b.lastModified) {
      return sortOrder === 'asc' 
        ? new Date(a.lastModified).getTime() - new Date(b.lastModified).getTime()
        : new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime();
    } else if (sortBy === 'size') {
      const aSize = a.size || 0;
      const bSize = b.size || 0;
      return sortOrder === 'asc' ? aSize - bSize : bSize - aSize;
    }
    return 0;
  });

  // Toggle sort order
  const toggleSort = (newSortBy: 'name' | 'date' | 'size') => {
    if (sortBy === newSortBy) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(newSortBy);
      setSortOrder('asc');
    }
  };

  return (
    <div className="bg-white rounded-lg border shadow-sm">
      {/* File Manager Header */}
      <div className="p-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold">Files</h2>
            <Badge variant="outline" className="ml-2">
              {filteredFiles.length} items
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="icon" onClick={() => setViewMode('grid')}>
                    <Grid className={`h-4 w-4 ${viewMode === 'grid' ? 'text-primary' : 'text-muted-foreground'}`} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Grid view</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="icon" onClick={() => setViewMode('list')}>
                    <List className={`h-4 w-4 ${viewMode === 'list' ? 'text-primary' : 'text-muted-foreground'}`} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>List view</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
        
        {/* Breadcrumbs */}
        {breadcrumbs.length > 0 && (
          <div className="flex items-center gap-1 text-sm">
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 px-2" 
              onClick={() => {
                setCurrentFolder(undefined);
                if (onFolderChange) onFolderChange(undefined);
              }}
            >
              <Folder className="h-4 w-4 mr-1" /> Root
            </Button>
            
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={crumb.id}>
                <ChevronRight className="h-4 w-4 text-gray-400" />
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-8 px-2" 
                  onClick={() => handleBreadcrumbClick(crumb.id)}
                >
                  {crumb.name}
                </Button>
              </React.Fragment>
            ))}
          </div>
        )}
        
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search files..."
              className="pl-9"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <SortAsc className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => toggleSort('name')}>
                Sort by name {sortBy === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => toggleSort('date')}>
                Sort by date {sortBy === 'date' && (sortOrder === 'asc' ? '↑' : '↓')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => toggleSort('size')}>
                Sort by size {sortBy === 'size' && (sortOrder === 'asc' ? '↑' : '↓')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          
          <Button variant="outline" onClick={() => loadFilesAndFolders()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>

          <Button variant="outline" onClick={handleNewFolder}>
            <FolderPlus className="h-4 w-4 mr-2" />
            New Folder
          </Button>
          
          <Button onClick={handleFileUpload}>
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </Button>
        </div>
      </div>
      
      <Separator />
      
      {/* File List */}
      <ScrollArea className="h-[calc(100vh-320px)] min-h-[400px]">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-64">
            <Loader2 className="h-8 w-8 text-primary animate-spin mb-4" />
            <p className="text-gray-500">Loading files...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64">
            <AlertCircle className="h-8 w-8 text-red-500 mb-4" />
            <p className="text-red-500 mb-2">{error}</p>
            <Button variant="outline" onClick={() => loadFilesAndFolders()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        ) : sortedFiles.length > 0 ? (
          <div className={viewMode === 'grid' ? "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4" : "space-y-2 p-4"}>
            {/* Back button when in a folder */}
            {currentFolder && (
              <div 
                className={`
                  ${viewMode === 'list' ? 
                    "flex items-center justify-between p-3 rounded-md hover:bg-gray-50 transition-colors border border-dashed" : 
                    "hidden"
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0">
                    <ArrowLeft className="h-6 w-6 text-gray-500" />
                  </div>
                  <div>
                    <p className="font-medium">Go back</p>
                  </div>
                </div>
                <Button variant="ghost" size="sm" onClick={handleNavigateUp}>
                  Up
                </Button>
              </div>
            )}
            
            {sortedFiles.map((file) => (
              viewMode === 'grid' ? (
                <Card key={file.id} className={`overflow-hidden hover:shadow-md transition-shadow ${file.isFolder ? 'cursor-pointer' : ''}`} onClick={() => file.isFolder && handleFolderClick(file)}>
                  <div className="p-4 flex flex-col items-center">
                    <div className="mb-2">
                      {getFileIcon(file.type)}
                    </div>
                    <div className="w-full text-center">
                      <div className="flex items-center justify-center">
                        {file.starred && <Star className="h-3 w-3 text-yellow-500 mr-1 fill-yellow-500" />}
                        <p className="font-medium text-sm truncate" title={file.name}>{file.name}</p>
                      </div>
                      {file.isFolder ? (
                        <p className="text-xs text-gray-500">{file.fileCount || 0} items</p>
                      ) : (
                        <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                      )}
                    </div>
                  </div>
                  <div className="bg-gray-50 p-2 flex justify-center space-x-1">
                    {!file.isFolder && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                              e.stopPropagation();
                              handleDownloadFile(file);
                            }}>
                              <Download className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Download</TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                    
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                            e.stopPropagation();
                            // Share functionality would go here
                            toast({
                              title: "Share",
                              description: `Sharing functionality for ${file.name} would go here.`,
                            });
                          }}>
                            <Share className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Share</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                            e.stopPropagation();
                            handleStarFile(file);
                          }}>
                            <Star className={`h-4 w-4 ${file.starred ? 'fill-yellow-500 text-yellow-500' : ''}`} />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>{file.starred ? 'Unstar' : 'Star'}</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteFile(file);
                          }}>
                            <Trash className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Delete</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </Card>
              ) : (
                <div 
                  key={file.id} 
                  className={`flex items-center justify-between p-3 rounded-md hover:bg-gray-50 transition-colors ${file.isFolder ? 'cursor-pointer' : ''}`}
                  onClick={() => file.isFolder && handleFolderClick(file)}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0">
                      {file.isFolder ? 
                        <Folder className="h-6 w-6 text-blue-500" /> : 
                        getFileIcon(file.type)
                      }
                    </div>
                    <div>
                      <div className="flex items-center">
                        {file.starred && <Star className="h-3 w-3 text-yellow-500 mr-1 fill-yellow-500" />}
                        <p className="font-medium">{file.name}</p>
                      </div>
                      <div className="flex items-center text-xs text-gray-500 gap-2">
                        {file.isFolder ? (
                          <span>{file.fileCount || 0} items</span>
                        ) : (
                          <span>{formatFileSize(file.size)}</span>
                        )}
                        {file.lastModified && (
                          <>
                            <span>•</span>
                            <span>{new Date(file.lastModified).toLocaleDateString()}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-1">
                    {!file.isFolder && (
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                        e.stopPropagation();
                        handleDownloadFile(file);
                      }}>
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                      e.stopPropagation();
                      // Share functionality would go here
                      toast({
                        title: "Share",
                        description: `Sharing functionality for ${file.name} would go here.`,
                      });
                    }}>
                      <Share className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                      e.stopPropagation();
                      handleStarFile(file);
                    }}>
                      <Star className={`h-4 w-4 ${file.starred ? 'fill-yellow-500 text-yellow-500' : ''}`} />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteFile(file);
                    }}>
                      <Trash className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-64 p-4">
            <File className="h-16 w-16 text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-700">No files found</h3>
            <p className="text-gray-500 mb-4">Upload files or create a new folder to get started</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleNewFolder}>
                <FolderPlus className="h-4 w-4 mr-2" />
                New Folder
              </Button>
              <Button onClick={handleFileUpload}>
                <Upload className="h-4 w-4 mr-2" />
                Upload
              </Button>
            </div>
          </div>
        )}
      </ScrollArea>
      
      {/* Modals */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        workspaceId={workspaceId}
        onUploadSuccess={() => {
          console.log('File upload success, triggering refresh');
          // Increment forcedRefresh to trigger the useEffect
          setForcedRefresh(prev => prev + 1);
          // Also call loadFilesAndFolders directly
          loadFilesAndFolders();
        }}
      />
      
      <NewFolderModal
        isOpen={isNewFolderModalOpen}
        onClose={() => setIsNewFolderModalOpen(false)}
        workspaceId={workspaceId}
        parentFolderId={currentFolder}
        onFolderCreated={() => {
          console.log('Folder created, triggering refresh');
          // Increment forcedRefresh to trigger the useEffect
          setForcedRefresh(prev => prev + 1);
          // Also call loadFilesAndFolders directly
          loadFilesAndFolders();
        }}
      />
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {fileToDelete?.isFolder ? 'Folder' : 'File'}</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{fileToDelete?.name}"? This action cannot be undone.
              {fileToDelete?.isFolder && ' All files within this folder will also be deleted.'}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDeleteFile}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}