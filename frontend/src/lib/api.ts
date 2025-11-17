// API utility functions for authentication and requests

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface LoginResponse {
  access: string
  refresh: string
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
}

/**
 * Login with email and password
 */
export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/api/auth/token/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

/**
 * Refresh access token using refresh token
 */
export async function refreshToken(refresh: string): Promise<{ access: string }> {
  const response = await fetch(`${API_URL}/api/auth/token/refresh/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh }),
  })

  if (!response.ok) {
    throw new Error('Token refresh failed')
  }

  return response.json()
}

/**
 * Get current user information
 */
export async function getCurrentUser(): Promise<User> {
  const token = localStorage.getItem('access_token')
  
  if (!token) {
    throw new Error('No access token found')
  }

  const response = await fetch(`${API_URL}/api/v1/users/me/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch user')
  }

  return response.json()
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('access_token')
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  })

  // If unauthorized, try to refresh token
  if (response.status === 401) {
    const refreshTokenValue = localStorage.getItem('refresh_token')
    if (refreshTokenValue) {
      try {
        const { access } = await refreshToken(refreshTokenValue)
        localStorage.setItem('access_token', access)
        
        // Retry the original request with new token
        headers['Authorization'] = `Bearer ${access}`
        const retryResponse = await fetch(`${API_URL}${endpoint}`, {
          ...options,
          headers,
        })
        
        if (!retryResponse.ok) {
          throw new Error('Request failed after token refresh')
        }
        
        return retryResponse.json()
      } catch {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        throw new Error('Session expired')
      }
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }

  return response.json()
}

/**
 * Logout user
 */
export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/login'
}
