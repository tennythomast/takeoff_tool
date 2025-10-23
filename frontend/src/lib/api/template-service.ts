// src/lib/api/template-service.ts - Clean version with single getTemplateById function

import { TemplateCardProps } from '@/components/marketplace/template-card'
import { API_BASE_URL } from '@/lib/config'
import { getAuthHeaders } from '@/lib/auth/auth-api'

// Define TemplateDetailProps interface here instead of importing it
export interface TemplateDetailProps extends TemplateCardProps {
  createdBy: string
  version: string
  configuration?: Record<string, any>
  reviews?: Array<{
    id: string
    user: string
    rating: number
    comment: string
    date: string
  }>
}

// Base API URL - adjusted to match the backend structure
const API_URL = `${API_BASE_URL}/api/v1/template-library/api/v1/templates`

// Always use real API data from the database

// Template categories
export const templateCategories = [
  { value: 'customer-support', label: 'Customer Support' },
  { value: 'content-creation', label: 'Content Creation' },
  { value: 'data-analysis', label: 'Data Analysis' },
  { value: 'sales-marketing', label: 'Sales & Marketing' },
  { value: 'operations', label: 'Operations' },
  { value: 'development', label: 'Development' },
]

// Template types
export const templateTypes = [
  { value: 'workflow', label: 'Workflow' },
  { value: 'agent', label: 'Agent' },
]

// Sort options
export const sortOptions = [
  { value: 'featured', label: 'Featured' },
  { value: 'newest', label: 'Newest' },
  { value: 'popular', label: 'Most Popular' },
  { value: 'rating', label: 'Highest Rated' },
]

// Fetch templates with filters
export async function fetchTemplates(filters: {
  category?: string[]
  type?: string[]
  sort?: string
  search?: string
  featured?: boolean
  page?: number
  limit?: number
}): Promise<{ templates: TemplateCardProps[]; total: number }> {
  
  try {
    // Get auth headers for API request
    const authHeaders = getAuthHeaders()
    // Build query string from filters
    const queryParams = new URLSearchParams()
    
    if (filters.category && filters.category.length > 0) {
      filters.category.forEach(cat => queryParams.append('category', cat))
    }
    
    if (filters.type && filters.type.length > 0) {
      filters.type.forEach(type => queryParams.append('type', type))
    }
    
    if (filters.sort) {
      queryParams.append('sort', filters.sort)
    }
    
    if (filters.search) {
      queryParams.append('search', filters.search)
    }
    
    if (filters.featured !== undefined) {
      queryParams.append('featured', filters.featured.toString())
    }
    
    if (filters.page) {
      queryParams.append('page', filters.page.toString())
    }
    
    if (filters.limit) {
      queryParams.append('limit', filters.limit.toString())
    }
    
    const queryString = queryParams.toString()
    
    // Always use the marketplace endpoint for listing templates
    const endpoint = '/marketplace/'
    
    // Build the URL with query parameters
    const url = `${API_URL}${endpoint}${queryString ? `?${queryString}` : ''}`
    
    console.log('API URL for templates:', url)
    
    try {
      console.log('Fetching templates from API:', url)
      console.log('📡 Final headers to be sent:', {
        ...authHeaders,
        'Content-Type': 'application/json'
      })
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          ...authHeaders,
          'Content-Type': 'application/json',
        },
      })
      
      if (!response.ok) {
        console.error(`API responded with status: ${response.status}`)
        // Return empty results if API call fails
        return { templates: [], total: 0 }
      }
      
      const data = await response.json()
      console.log('API response data:', data)
      
      // Map the API response to our frontend data structure
      const templates = (data.results || []).map((item: any) => ({
        id: item.id,
        name: item.name,
        description: item.short_description || item.description || '',
        icon: item.icon || (item.type === 'workflow' ? 'workflow' : 'agent'),
        category: item.category?.name || '',
        type: item.type,
        rating: item.average_rating || 0,
        usageCount: item.usage_count || 0,
        featured: item.featured || false,
        createdAt: item.published_at || new Date().toISOString(),
        tags: item.tags || []
      }));
      
      return {
        templates,
        total: data.count || templates.length,
      }
    } catch (apiError) {
      console.error('API request failed:', apiError)
      // Return empty results if API call fails
      return { templates: [], total: 0 }
    }
  } catch (error) {
    console.error('Error fetching templates:', error)
    return { templates: [], total: 0 }
  }
}

// SINGLE getTemplateById function - no duplicates
export async function getTemplateById(id: string, type: 'workflow' | 'agent'): Promise<TemplateDetailProps | null> {
  try {
    // Get auth headers for API request
    const authHeaders = getAuthHeaders()
    
    // Get template from API
    try {
      // Try multiple approaches to get the template
      const detailUrl = `${API_URL}/marketplace/${id}/template_detail/`
      
      const detailResponse = await fetch(detailUrl, {
        method: 'GET',
        headers: {
          ...authHeaders,
          'Content-Type': 'application/json',
        },
      })
      
      if (detailResponse.ok) {
        const template = await detailResponse.json()
        // Successfully retrieved template from detail endpoint
        
        return {
          id: template.id || id,
          type: template.type || type,
          name: template.name || '',
          description: template.description || template.short_description || '',
          icon: template.icon || (type === 'workflow' ? 'workflow' : 'agent'),
          category: template.category?.name || '',
          rating: template.average_rating || 0,
          usageCount: template.usage_count || 0,
          featured: template.featured || false,
          createdAt: template.published_at || new Date().toISOString(),
          createdBy: template.created_by_name || 'Unknown',
          version: template.version || '1.0.0',
          configuration: template.configuration || (type === 'workflow' ? {
            nodes: [],
            edges: []
          } : {
            primaryRole: template.primary_role || '',
            communicationStyle: template.communication_style || '',
            outputFormat: template.output_format || '',
            qualityPreference: template.quality_preference || 1,
            defaultTools: template.default_tools || [],
            defaultParameters: template.default_parameters || []
          }),
          reviews: template.reviews || [],
          // Add agent-specific fields if it's an agent
          ...(type === 'agent' ? {
            primary_role: template.primary_role || '',
            communication_style: template.communication_style || '',
            output_format: template.output_format || '',
            quality_preference: template.quality_preference || 1
          } : {})
        }
      }
    } catch (detailError) {
      // Detail endpoint failed, trying search approach
    }
    
    // Approach 2: Search the marketplace for the template
    try {
      const searchUrl = `${API_URL}/marketplace/?limit=50`  // Get more results to search through
      // Searching marketplace for template
      
      const searchResponse = await fetch(searchUrl, {
        method: 'GET',
        headers: {
          ...authHeaders,
          'Content-Type': 'application/json',
        },
      })
      
      if (searchResponse.ok) {
        const data = await searchResponse.json()
        // Retrieved marketplace search response
        
        // Find the template with matching ID in the results
        const templates = data.results || []
        const template = templates.find((t: any) => t.id === id)
        
        if (template) {
          // Found template in marketplace search
          
          return {
            id: template.id || id,
            type: template.type || type,
            name: template.name || '',
            description: template.description || template.short_description || '',
            icon: template.icon || (type === 'workflow' ? 'workflow' : 'agent'),
            category: template.category?.name || '',
            rating: template.average_rating || 0,
            usageCount: template.usage_count || 0,
            featured: template.featured || false,
            createdAt: template.published_at || new Date().toISOString(),
            createdBy: template.created_by_name || 'Unknown',
            version: template.version || '1.0.0',
            configuration: template.configuration || (type === 'workflow' ? {
              nodes: [],
              edges: []
            } : {
              primaryRole: template.primary_role || '',
              communicationStyle: template.communication_style || '',
              outputFormat: template.output_format || '',
              qualityPreference: template.quality_preference || 1,
              defaultTools: template.default_tools || [],
              defaultParameters: template.default_parameters || []
            }),
            reviews: template.reviews || [],
            // Add agent-specific fields if it's an agent
            ...(type === 'agent' ? {
              primary_role: template.primary_role || '',
              communication_style: template.communication_style || '',
              output_format: template.output_format || '',
              quality_preference: template.quality_preference || 1
            } : {})
          }
        }
      }
    } catch (searchError) {
      console.log('⚠️ Marketplace search failed:', searchError)
    }
    
    // Approach 3: Try direct endpoint access
    try {
      const directUrl = `${API_URL}/${type === 'workflow' ? 'workflows' : 'agents'}/${id}/`
      console.log('🔍 Trying direct endpoint:', directUrl)
      
      const directResponse = await fetch(directUrl, {
        method: 'GET',
        headers: {
          ...authHeaders,
          'Content-Type': 'application/json',
        },
      })
      
      if (directResponse.ok) {
        const template = await directResponse.json()
        console.log('✅ Got template from direct endpoint:', template)
        
        return {
          id: template.id || id,
          type: type,
          name: template.name || '',
          description: template.description || template.short_description || '',
          icon: template.icon || (type === 'workflow' ? 'workflow' : 'agent'),
          category: template.category?.name || '',
          rating: template.average_rating || 0,
          usageCount: template.usage_count || 0,
          featured: template.featured || false,
          createdAt: template.published_at || template.created_at || new Date().toISOString(),
          createdBy: template.created_by_name || template.created_by || 'Unknown',
          version: template.version || '1.0.0',
          configuration: template.configuration || {},
          reviews: template.reviews || []
        }
      }
    } catch (directError) {
      // Direct endpoint failed
    }
    
    // All approaches failed, return null
    // All API approaches failed, returning null
    return null
    
  } catch (error) {
    // Error fetching template
    return null
  }
}

/**
 * Create a new template
 */
export async function createTemplate(templateData: Omit<TemplateDetailProps, 'id' | 'createdAt'>): Promise<TemplateDetailProps | null> {
  try {
    // Use the appropriate endpoint based on template type
    const endpoint = templateData.type === 'workflow' ? '/workflows' : '/agents'
    const url = `${API_URL}${endpoint}`
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: templateData.name,
        description: templateData.description,
        icon: templateData.icon,
        category: templateData.category,
        type: templateData.type,
        featured: templateData.featured || false,
        configuration: templateData.configuration || {},
        version: templateData.version || '1.0.0',
      }),
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new Error(errorData?.detail || `API error: ${response.status}`)
    }
    
    const data = await response.json()
    return {
      ...templateData,
      id: data.id,
      createdAt: data.created_at || new Date().toISOString(),
      createdBy: data.created_by || templateData.createdBy,
    }
  } catch (error) {
    // Error creating template
    return null
  }
}

/**
 * Update an existing template
 */
export async function updateTemplate(id: string, templateData: Partial<TemplateDetailProps>): Promise<TemplateDetailProps | null> {
  try {
    // Use the appropriate endpoint based on template type
    const endpoint = templateData.type === 'workflow' ? '/workflows' : '/agents'
    const url = `${API_URL}${endpoint}/${id}`
    
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: templateData.name,
        description: templateData.description,
        icon: templateData.icon,
        category: templateData.category,
        featured: templateData.featured,
        configuration: templateData.configuration,
        version: templateData.version,
      }),
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => null)
      throw new Error(errorData?.detail || `API error: ${response.status}`)
    }
    
    const data = await response.json()
    return await getTemplateById(id, templateData.type as 'workflow' | 'agent')
  } catch (error) {
    console.error(`Error updating template ${id}:`, error)
    return null
  }
}

/**
 * Fetch user's favorite templates
 */
export async function fetchFavoriteTemplates(): Promise<{ templates: TemplateCardProps[]; total: number }> {
  try {
    const url = `${API_URL}/marketplace/favorites`
    
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
      })
      
      if (!response.ok) {
        console.error(`API error ${response.status} when fetching favorite templates from ${url}`)
        // Try to get more details about the error
        try {
          const errorData = await response.json()
          console.error('Error details:', errorData)
        } catch (parseError) {
          console.error('Could not parse error response')
        }
        
        // Return empty results when API fails
        console.warn('API error when fetching favorites, returning empty results')
        return { templates: [], total: 0 }

      }
      
      const data = await response.json()
      return {
        templates: data.results || [],
        total: data.count || 0,
      }
    } catch (apiError) {
      console.error('API request failed:', apiError)
      // Return empty results if API call fails
      console.warn('API error when fetching favorites')
      return { templates: [], total: 0 }
    }
  } catch (error) {
    console.error('Error fetching favorite templates:', error)
    return { templates: [], total: 0 }
  }
}

/**
 * Add a template to favorites
 */
export async function addTemplateToFavorites(templateId: string): Promise<boolean> {
  try {
    const url = `${API_URL}/marketplace/favorites/${templateId}`
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return true
  } catch (error) {
    console.error('Error adding template to favorites:', error)
    return false
  }
}

/**
 * Remove a template from favorites
 */
export async function removeTemplateFromFavorites(templateId: string): Promise<boolean> {
  try {
    const url = `${API_URL}/marketplace/favorites/${templateId}`
    
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        ...getAuthHeaders(),
      },
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return true
  } catch (error) {
    console.error('Error removing template from favorites:', error)
    return false
  }
}