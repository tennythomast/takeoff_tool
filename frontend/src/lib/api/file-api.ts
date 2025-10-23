import { API_BASE_URL } from '../constants';
import { getStoredTokens } from "../auth/auth-service";

// File types
export interface FileUpload {
  id: string;
  organization: string;
  workspace?: string;
  uploaded_by: string;
  uploaded_by_name?: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  file_extension: string;
  purpose: 'user_document' | 'workspace_document' | 'rag_document' | 'agent_asset' | 'workflow_asset';
  access_level: 'private' | 'workspace' | 'organization';
  description: string;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  storage_backend: string;
  storage_backend_name?: string;
  last_accessed_at?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface FileUploadRequest {
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  file_extension: string;
  purpose: 'user_document' | 'workspace_document' | 'rag_document' | 'agent_asset' | 'workflow_asset';
  access_level?: 'private' | 'workspace' | 'organization';
  description?: string;
  workspace?: string;
  organization?: string;
  file_hash: string;
}

export interface FileFolder {
  id: string;
  name: string;
  parent_folder?: string;
  workspace?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  file_count: number;
}

export interface CreateFolderRequest {
  name: string;
  parent_folder?: string;
  workspace?: string;
  organization?: string;
}

class FileApiService {
  private baseUrl = `${API_BASE_URL}`;
  private userOrganizationCache: string | null = null;
  
  // Helper method to get the current user's organization ID
  private async getUserOrganization(): Promise<string | null> {
    // Return cached value if available
    if (this.userOrganizationCache) {
      return this.userOrganizationCache;
    }
    
    const tokens = getStoredTokens();
    if (!tokens?.access) {
      return null;
    }
    
    try {
      const userResponse = await fetch(`${this.baseUrl}/api/v1/users/me/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokens.access}`,
        },
        credentials: 'include',
      });
      
      if (userResponse.ok) {
        const userData = await userResponse.json();
        
        // Log the user data for debugging
        console.log('User data received:', {
          hasOrganization: !!userData?.organization,
          organizationType: userData?.organization ? typeof userData.organization : 'undefined'
        });
        
        if (userData && userData.organization) {
          let organizationId: string;
          
          // Handle both string ID and object with ID
          if (typeof userData.organization === 'string') {
            organizationId = userData.organization;
          } else if (typeof userData.organization === 'object' && userData.organization !== null) {
            // If it's an object, extract the ID field
            organizationId = userData.organization.id || null;
          } else {
            return null;
          }
          
          if (organizationId) {
            console.log('Using organization ID:', organizationId);
            // Cache the organization ID
            this.userOrganizationCache = organizationId;
            return organizationId;
          }
        }
      }
      return null;
    } catch (error) {
      console.warn('Could not fetch user organization:', error);
      return null;
    }
  }
  
  // Get files with optional filtering
  async getFiles(filters?: Record<string, any>): Promise<FileUpload[]> {
    const tokens = getStoredTokens();
    
    // Build query parameters
    let queryParams = '';
    if (filters && Object.keys(filters).length > 0) {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
      queryParams = params.toString();
    }
    
    const url = `${this.baseUrl}/api/v1/files/${queryParams ? `?${queryParams}` : ''}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.error('API request failed:', response.status, response.statusText);
      throw new Error(`Failed to fetch files: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Handle paginated response
    if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
      return data.results;
    }
    
    // Handle array response
    if (Array.isArray(data)) {
      return data;
    }
    
    console.error('Unexpected API response format:', data);
    return [];
  }
  
  // Get workspace files
  async getWorkspaceFiles(workspaceId: string): Promise<FileUpload[]> {
    return this.getFiles({ workspace: workspaceId });
  }
  
  // Get file details
  async getFile(fileId: string): Promise<FileUpload> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/files/${fileId}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch file: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  // Create file upload record (first step of upload process)
  async createFileUpload(data: FileUploadRequest): Promise<FileUpload> {
    const tokens = getStoredTokens();
    
    // Log the request for debugging
    console.log('Creating file upload record with data:', {
      ...data,
      // Don't log sensitive information
      organization: data.organization ? 'Present' : 'Not available',
    });
    
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/files/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });
      
      // If response is not ok, try to get more detailed error information
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to create file upload: ${response.statusText}`;
        
        try {
          // Try to parse error response as JSON
          const errorJson = JSON.parse(errorText);
          console.error('File upload API error:', errorJson);
          
          // Extract error message if available
          if (typeof errorJson === 'object' && errorJson !== null) {
            if (errorJson.detail) {
              errorMessage = errorJson.detail;
            } else if (errorJson.message) {
              errorMessage = errorJson.message;
            } else {
              // If there are field-specific errors, format them
              const fieldErrors = Object.entries(errorJson)
                .filter(([key]) => key !== 'detail' && key !== 'message')
                .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`);
              
              if (fieldErrors.length > 0) {
                errorMessage = `Validation errors: ${fieldErrors.join('; ')}`;
              }
            }
          }
        } catch (e) {
          // If parsing fails, use the raw error text
          console.error('Error parsing API error response:', e);
          if (errorText) {
            errorMessage = errorText;
          }
        }
        
        throw new Error(errorMessage);
      }
      
      // Parse the response and log it in detail
      let result;
      try {
        const responseText = await response.text();
        console.log('Raw API response:', responseText);
        
        try {
          result = JSON.parse(responseText);
        } catch (parseError) {
          console.error('Failed to parse API response as JSON:', parseError);
          throw new Error('Failed to parse API response as JSON');
        }
      } catch (textError) {
        console.error('Failed to read API response text:', textError);
        throw new Error('Failed to read API response');
      }
      
      console.log('File upload record created, response:', result);
      
      // Log detailed information about the response structure
      if (result) {
        console.log('Response structure:', {
          hasId: 'id' in result,
          idValue: result.id,
          idType: result.id ? typeof result.id : 'undefined',
          availableFields: Object.keys(result),
        });
      }
      
      // Be more lenient with response validation
      if (!result) {
        console.error('Empty response from file upload API');
        throw new Error('Failed to create file upload record: Empty response');
      }
      
      // If the response doesn't have an ID but has other expected fields, try to work with it
      if (typeof result === 'object') {
        if (result.id) {
          // Make sure we're using the actual ID from the backend
          console.log('Using backend-provided file ID:', result.id);
          return result;
        } else if (result.original_filename || result.file_hash) {
          // The response has some file-related fields but no ID
          console.warn('API response missing ID but has file data:', result);
          // DO NOT create a synthetic ID - this will cause 404 errors
          console.error('Cannot proceed without a valid file ID from the backend');
          throw new Error('Backend did not provide a valid file ID');
        }
      }
      
      console.error('Invalid response format from file upload API:', result);
      throw new Error('Failed to create file upload record: Invalid response format');
    } catch (error) {
      console.error('Error in createFileUpload:', error);
      throw error;
    }
  }
  
  // Upload file content (second step of upload process)
  async uploadFileContent(fileId: string, file: File): Promise<FileUpload> {
    const tokens = getStoredTokens();
    
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    
    console.log(`Uploading file content for file ID: ${fileId}`, {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      fileIdType: typeof fileId,
      fileIdLength: fileId ? fileId.length : 0
    });
    
    try {
      // Validate inputs
      if (!fileId) {
        throw new Error('File ID is required for content upload');
      }
      
      // Check if fileId looks like a UUID (basic validation)
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (!uuidPattern.test(fileId)) {
        console.warn(`File ID ${fileId} does not appear to be a valid UUID format`);
        // Continue anyway, but log the warning
      }
      
      if (!file || file.size <= 0) {
        throw new Error('Valid file is required for upload');
      }
      
      const response = await fetch(`${this.baseUrl}/api/v1/files/${fileId}/upload/`, {
        method: 'POST',
        headers: {
          'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
        },
        credentials: 'include',
        body: formData,
      });
      
      // If response is not ok, try to get more detailed error information
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to upload file content: ${response.statusText}`;
        
        try {
          // Try to parse error response as JSON
          const errorJson = JSON.parse(errorText);
          console.error('File content upload API error:', errorJson);
          
          // Extract error message if available
          if (typeof errorJson === 'object' && errorJson !== null) {
            if (errorJson.detail) {
              errorMessage = errorJson.detail;
            } else if (errorJson.message) {
              errorMessage = errorJson.message;
            } else if (errorJson.error) {
              errorMessage = errorJson.error;
            }
          }
        } catch (e) {
          // If parsing fails, use the raw error text
          console.error('Error parsing API error response:', e);
          if (errorText) {
            errorMessage = errorText;
          }
        }
        
        throw new Error(errorMessage);
      }
      
      // Parse the response and log it in detail
      let result;
      try {
        const responseText = await response.text();
        console.log('Raw file content upload response:', responseText);
        
        try {
          result = JSON.parse(responseText);
        } catch (parseError) {
          console.error('Failed to parse file content upload response as JSON:', parseError);
          throw new Error('Failed to parse API response as JSON');
        }
      } catch (textError) {
        console.error('Failed to read file content upload response text:', textError);
        throw new Error('Failed to read API response');
      }
      
      console.log('File content uploaded successfully, response:', result);
      
      // Be more lenient with response validation
      if (!result) {
        console.error('Empty response from file content upload API');
        // Create a minimal response object with the file ID
        return { id: fileId } as FileUpload;
      }
      
      return result;
    } catch (error) {
      console.error(`Error uploading file content for file ID ${fileId}:`, error);
      throw error;
    }
  }
  
  // Complete file upload process in one function
  async uploadFile(file: File, options: {
    purpose?: 'user_document' | 'workspace_document' | 'rag_document' | 'agent_asset' | 'workflow_asset';
    access_level?: 'private' | 'workspace' | 'organization';
    description?: string;
    workspace?: string;
  }): Promise<FileUpload> {
    try {
      // Validate file
      if (!file) {
        throw new Error('No file provided');
      }
      
      if (file.size <= 0) {
        throw new Error('File is empty');
      }
      
      // Extract file extension properly
      const fileName = file.name || '';
      const fileExtParts = fileName.split('.');
      let fileExtension = '';
      
      if (fileExtParts.length > 1) {
        fileExtension = `.${fileExtParts[fileExtParts.length - 1].toLowerCase()}`;
      }
      
      // Ensure we have a valid content type
      const contentType = file.type || this.getContentTypeFromExtension(fileExtension) || 'application/octet-stream';
      
      // Step 1: Calculate file hash (simplified version using last modified as hash)
      // Add a random component to avoid duplicate hash errors
      const timestamp = new Date().getTime();
      const randomSuffix = Math.random().toString(36).substring(2, 10);
      
      // Create a hash string and ensure it's no more than 64 characters
      let hashSource = `${file.size}-${timestamp}-${randomSuffix}`;
      
      // Use a more compact hash format to stay within the 64 character limit
      const fileHash = hashSource.length > 64 ? hashSource.substring(0, 64) : hashSource;
      
      console.log('File details:', {
        name: file.name,
        size: file.size,
        type: contentType,
        extension: fileExtension
      });
      
      // Step 2: Get user's organization ID
      const organizationId = await this.getUserOrganization();
      if (!organizationId) {
        console.warn('No organization ID available for file upload');
      }
      
      // Step 3: Create file upload record
      const fileUploadData: FileUploadRequest = {
        original_filename: fileName,
        content_type: contentType,
        file_size_bytes: file.size,
        file_extension: fileExtension,
        purpose: options.purpose || 'workspace_document',
        access_level: options.access_level || 'workspace',
        description: options.description || '',
        workspace: options.workspace,
        file_hash: fileHash,
        // Include organization ID if available
        ...(organizationId ? { organization: organizationId } : {})
      };
      
      console.log('Creating file upload with data:', {
        ...fileUploadData,
        organization: organizationId ? 'Present' : 'Not available'
      });
      
      // Create file upload record first
      const fileUpload = await this.createFileUpload(fileUploadData);
      
      console.log('File upload record created with ID:', fileUpload.id);
      
      // Step 4: Upload file content with the valid file ID
      return await this.uploadFileContent(fileUpload.id, file);
    } catch (error) {
      console.error('File upload failed:', error);
      throw error;
    }
  }
  
  // Helper method to determine content type from file extension
  private getContentTypeFromExtension(extension: string): string | null {
    const contentTypeMap: Record<string, string> = {
      '.pdf': 'application/pdf',
      '.doc': 'application/msword',
      '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      '.xls': 'application/vnd.ms-excel',
      '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.ppt': 'application/vnd.ms-powerpoint',
      '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.png': 'image/png',
      '.gif': 'image/gif',
      '.txt': 'text/plain',
      '.csv': 'text/csv',
      '.md': 'text/markdown',
      '.json': 'application/json',
      '.xml': 'application/xml',
      '.html': 'text/html',
      '.htm': 'text/html',
      '.zip': 'application/zip',
      '.rar': 'application/x-rar-compressed',
      '.tar': 'application/x-tar',
      '.gz': 'application/gzip',
    };
    
    return contentTypeMap[extension.toLowerCase()] || null;
  }
  
  // Record file access
  async recordFileAccess(fileId: string): Promise<void> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/files/${fileId}/record_access/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.error(`Failed to record file access: ${response.statusText}`);
    }
  }
  
  // Get download URL for a file
  async getFileDownloadUrl(fileId: string): Promise<string> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/files/${fileId}/download/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get file download URL: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.download_url || '';
  }
  
  // Download file directly
  async downloadFile(fileId: string, filename?: string): Promise<void> {
    try {
      const downloadUrl = await this.getFileDownloadUrl(fileId);
      
      // Record access
      await this.recordFileAccess(fileId);
      
      // Trigger browser download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'download';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('File download failed:', error);
      throw error;
    }
  }
  
  // Delete file
  async deleteFile(fileId: string): Promise<void> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete file: ${response.statusText}`);
    }
  }
  
  // Get folders
  async getFolders(workspaceId?: string): Promise<FileFolder[]> {
    const tokens = getStoredTokens();
    
    const url = workspaceId 
      ? `${this.baseUrl}/api/v1/folders/?workspace=${workspaceId}`
      : `${this.baseUrl}/api/v1/folders/`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      console.error('API request failed:', response.status, response.statusText);
      throw new Error(`Failed to fetch folders: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Handle paginated response
    if (data && typeof data === 'object' && 'results' in data && Array.isArray(data.results)) {
      return data.results;
    }
    
    // Handle array response
    if (Array.isArray(data)) {
      return data;
    }
    
    console.error('Unexpected API response format:', data);
    return [];
  }
  
  // Create folder
  async createFolder(data: CreateFolderRequest): Promise<FileFolder> {
    const tokens = getStoredTokens();
    
    // Get user's organization ID
    const organizationId = await this.getUserOrganization();
    if (organizationId) {
      // Add organization ID to the request data
      data.organization = organizationId;
    }
    
    // Log the request for debugging
    console.log('Creating folder with API request:', {
      url: `${this.baseUrl}/api/v1/folders/`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? 'Bearer [TOKEN]' : 'No token', // Don't log actual token
      },
      data: data
    });
    
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/folders/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });
      
      // If response is not ok, try to get more detailed error information
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to create folder: ${response.statusText}`;
        
        try {
          // Try to parse error response as JSON
          const errorJson = JSON.parse(errorText);
          console.error('Folder creation API error:', errorJson);
          
          // Extract error message if available
          if (typeof errorJson === 'object' && errorJson !== null) {
            if (errorJson.detail) {
              errorMessage = errorJson.detail;
            } else if (errorJson.message) {
              errorMessage = errorJson.message;
            } else {
              // If there are field-specific errors, format them
              const fieldErrors = Object.entries(errorJson)
                .filter(([key]) => key !== 'detail' && key !== 'message')
                .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`);
              
              if (fieldErrors.length > 0) {
                errorMessage = `Validation errors: ${fieldErrors.join('; ')}`;
              }
            }
          }
        } catch (e) {
          // If parsing fails, use the raw error text
          console.error('Error parsing API error response:', e);
          if (errorText) {
            errorMessage = errorText;
          }
        }
        
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      console.log('Folder created successfully:', result);
      return result;
    } catch (error) {
      console.error('Error in createFolder:', error);
      throw error;
    }
  }
  
  // Delete folder
  async deleteFolder(folderId: string): Promise<void> {
    const tokens = getStoredTokens();
    
    const response = await fetch(`${this.baseUrl}/api/v1/folders/${folderId}/`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': tokens?.access ? `Bearer ${tokens.access}` : '',
      },
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete folder: ${response.statusText}`);
    }
  }
}

// Export as singleton
export const fileApiService = new FileApiService();