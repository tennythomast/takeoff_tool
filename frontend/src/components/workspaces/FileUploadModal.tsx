"use client"

import React, { useState, useRef, useCallback } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { toast } from "@/components/ui/use-toast"
import { Upload, File, X, Check } from "lucide-react"
import { fileApiService } from '@/lib/api/file-api'

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId?: string;
  onUploadSuccess?: () => void;
}

export function FileUploadModal({
  isOpen,
  onClose,
  workspaceId,
  onUploadSuccess
}: FileUploadModalProps) {
  // File selection state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDescription, setFileDescription] = useState('');
  const [purpose, setPurpose] = useState<'workspace_document' | 'rag_document' | 'agent_asset'>('workspace_document');
  const [accessLevel, setAccessLevel] = useState<'private' | 'workspace' | 'organization'>('workspace');
  
  // Upload progress state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  
  // File input reference
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Handle file selection
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      setUploadError(null);
      setUploadSuccess(false);
    }
  };
  
  // Handle file drop
  const handleDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    
    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      setUploadError(null);
      setUploadSuccess(false);
    }
  }, []);
  
  // Prevent default drag behavior
  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);
  
  // Handle file upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file to upload');
      return;
    }
    
    setIsUploading(true);
    setUploadProgress(0);
    setUploadError(null);
    
    try {
      // Simulate progress (since the actual API doesn't provide progress updates)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + 5;
          return newProgress < 90 ? newProgress : prev;
        });
      }, 200);
      
      // Upload file
      await fileApiService.uploadFile(selectedFile, {
        purpose,
        access_level: accessLevel,
        description: fileDescription,
        workspace: workspaceId,
      });
      
      // Complete progress and show success
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadSuccess(true);
      
      // Notify parent component
      if (onUploadSuccess) {
        onUploadSuccess();
      }
      
      // Show success toast
      toast({
        title: "File uploaded successfully",
        description: `${selectedFile.name} has been uploaded.`,
      });
      
      // Reset form after a delay
      setTimeout(() => {
        resetForm();
        onClose();
      }, 1500);
    } catch (error: unknown) {
      console.error('File upload error:', error);
      setUploadError(error instanceof Error ? error.message : 'Failed to upload file');
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };
  
  // Reset form
  const resetForm = () => {
    setSelectedFile(null);
    setFileDescription('');
    setPurpose('workspace_document');
    setAccessLevel('workspace');
    setUploadProgress(0);
    setUploadError(null);
    setUploadSuccess(false);
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  // Handle modal close
  const handleClose = () => {
    if (!isUploading) {
      resetForm();
      onClose();
    }
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Upload File</DialogTitle>
          <DialogDescription>
            Upload a file to your workspace. Supported file types include documents, images, and more.
          </DialogDescription>
        </DialogHeader>
        
        {/* File Drop Area */}
        <div 
          className={`
            border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
            ${selectedFile ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-gray-400'}
          `}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
          
          {selectedFile ? (
            <div className="flex flex-col items-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-green-100 mb-2">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <p className="text-sm font-medium">{selectedFile.name}</p>
              <p className="text-xs text-gray-500">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <Button 
                variant="ghost" 
                size="sm" 
                className="mt-2"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = '';
                  }
                }}
              >
                <X className="h-4 w-4 mr-1" /> Remove
              </Button>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-2">
                <Upload className="h-6 w-6 text-gray-600" />
              </div>
              <p className="text-sm font-medium">Drag and drop a file here, or click to browse</p>
              <p className="text-xs text-gray-500 mt-1">
                Maximum file size: 50MB
              </p>
            </div>
          )}
        </div>
        
        {/* File Details */}
        {selectedFile && (
          <div className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Enter a description for this file"
                value={fileDescription}
                onChange={(e) => setFileDescription(e.target.value)}
                disabled={isUploading}
              />
            </div>
            
            <div className="space-y-2">
              <Label>File Purpose</Label>
              <RadioGroup 
                value={purpose} 
                onValueChange={(value) => setPurpose(value as any)}
                disabled={isUploading}
                className="flex flex-col space-y-1"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="workspace_document" id="workspace_document" />
                  <Label htmlFor="workspace_document" className="cursor-pointer">Workspace Document</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="rag_document" id="rag_document" />
                  <Label htmlFor="rag_document" className="cursor-pointer">RAG Document (for AI context)</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="agent_asset" id="agent_asset" />
                  <Label htmlFor="agent_asset" className="cursor-pointer">Agent Asset</Label>
                </div>
              </RadioGroup>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="access_level">Access Level</Label>
              <Select 
                value={accessLevel} 
                onValueChange={(value) => setAccessLevel(value as any)}
                disabled={isUploading}
              >
                <SelectTrigger id="access_level">
                  <SelectValue placeholder="Select access level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">Private (Only you)</SelectItem>
                  <SelectItem value="workspace">Workspace (All collaborators)</SelectItem>
                  <SelectItem value="organization">Organization (All members)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
        
        {/* Upload Progress */}
        {isUploading && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Uploading...</span>
              <span>{uploadProgress}%</span>
            </div>
            <Progress value={uploadProgress} className="h-2" />
          </div>
        )}
        
        {/* Error Message */}
        {uploadError && (
          <div className="text-red-500 text-sm">{uploadError}</div>
        )}
        
        {/* Success Message */}
        {uploadSuccess && (
          <div className="text-green-500 text-sm flex items-center">
            <Check className="h-4 w-4 mr-1" /> Upload successful!
          </div>
        )}
        
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button 
            onClick={handleUpload} 
            disabled={!selectedFile || isUploading || uploadSuccess}
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
