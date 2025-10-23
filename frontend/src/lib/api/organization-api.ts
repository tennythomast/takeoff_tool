import { API_BASE_URL } from "@/lib/config"
import { getAuthHeaders } from "@/lib/auth/auth-api"

/**
 * Fetch organization details including budget information
 */
export async function fetchOrganizationDetails(orgId: string | undefined) {
  if (!orgId) {
    throw new Error("Organization ID is required")
  }
  
  const response = await fetch(`${API_BASE_URL}/api/v1/organizations/${orgId}/`, {
    method: "GET",
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to fetch organization details")
  }

  const orgData = await response.json()
  
  // Also fetch budget info
  const budgetResponse = await fetch(`${API_BASE_URL}/api/v1/organizations/${orgId}/budget_info/`, {
    method: "GET",
    headers: getAuthHeaders(),
  })

  if (budgetResponse.ok) {
    const budgetData = await budgetResponse.json()
    return { ...orgData, budget_status: budgetData }
  }
  
  return orgData
}

/**
 * Update organization settings
 */
export async function updateOrganization(orgData: {
  id: string
  name: string
  api_key_strategy: string
  monthly_ai_budget: number | null
  default_optimization_strategy: string
}) {
  const response = await fetch(`${API_BASE_URL}/api/v1/organizations/${orgData.id}/`, {
    method: "PATCH",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: orgData.name,
      api_key_strategy: orgData.api_key_strategy,
      monthly_ai_budget: orgData.monthly_ai_budget,
      default_optimization_strategy: orgData.default_optimization_strategy,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to update organization settings")
  }

  return await response.json()
}

/**
 * Fetch all organizations the current user has access to
 */
export async function fetchUserOrganizations() {
  const response = await fetch(`${API_BASE_URL}/api/v1/organizations/`, {
    method: "GET",
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || "Failed to fetch user organizations")
  }

  const data = await response.json()
  console.log('Organization API response:', data)
  
  // Check if the response has a results property (paginated response)
  if (data && data.results && Array.isArray(data.results)) {
    return data.results
  }
  
  // If the response is already an array
  if (Array.isArray(data)) {
    return data
  }
  
  // If we have a single organization object
  if (data && typeof data === 'object' && data.id) {
    return [data]
  }
  
  // Return empty array as fallback
  return []
}

/**
 * Fetch users in an organization, optionally filtering out users who are already
 * collaborators in a specific workspace
 */
export async function fetchOrganizationUsers(orgId: string, options?: {
  workspaceId?: string
  search?: string
}) {
  if (!orgId) {
    throw new Error("Organization ID is required")
  }
  
  let url = `${API_BASE_URL}/api/v1/organizations/${orgId}/users/`
  
  // Add query parameters if provided
  const params = new URLSearchParams()
  if (options?.workspaceId) {
    params.append('workspace_id', options.workspaceId)
  }
  if (options?.search) {
    params.append('search', options.search)
  }
  
  const queryString = params.toString()
  if (queryString) {
    url += `?${queryString}`
  }
  
  const response = await fetch(url, {
    method: "GET",
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    try {
      const error = await response.json()
      throw new Error(error.detail || "Failed to fetch organization users")
    } catch (jsonError) {
      // If response is not valid JSON (e.g., HTML error page)
      console.error('Non-JSON error response:', response.status, response.statusText)
      throw new Error(`Failed to fetch organization users: ${response.status} ${response.statusText}`)
    }
  }

  return await response.json()
}
