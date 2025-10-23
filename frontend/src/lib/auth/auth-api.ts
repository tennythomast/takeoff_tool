import { API_BASE_URL } from "@/lib/config";

/**
 * Get tokens from storage (checks both sessionStorage and localStorage)
 */
export function getTokens() {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') {
    // Not available in server environment
    return null;
  }
  
  try {
    // First check sessionStorage (where tokens are actually stored)
    let tokenData = sessionStorage.getItem('dataelan_auth_tokens');
    
    // If not in sessionStorage, try localStorage as fallback
    if (!tokenData) {
      tokenData = localStorage.getItem('dataelan_auth_tokens');
    }
    
    if (!tokenData) {
      // No auth tokens found in storage
      return null;
    }
    
    const tokens = JSON.parse(tokenData);
    if (!tokens || !tokens.access) {
      // Invalid token format in storage
      return null;
    }
    
    // Successfully retrieved tokens from storage
    return tokens;
  } catch (error) {
    // Error accessing or parsing auth tokens
    return null;
  }
}

/**
 * Get authentication headers for API requests
 */
export function getAuthHeaders(): Record<string, string> {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') {
    // Not available in server environment
    return { 'Content-Type': 'application/json' };
  }
  
  // Get token from localStorage (only in browser)
  try {
    const tokens = getTokens();
    
    if (!tokens || !tokens.access) {
      return { 'Content-Type': 'application/json' };
    }
    
    // Found valid access token
    return {
      'Authorization': `Bearer ${tokens.access}`,
      'Content-Type': 'application/json'
    };
  } catch (error) {
    // Error accessing or parsing auth tokens
    return { 'Content-Type': 'application/json' };
  }
}

/**
 * Get current user data with organization information
 */
export async function getUserData() {
  try {
    // Attempting to fetch user data
    
    // First try to get the token
    const tokens = getTokens();
    if (!tokens) {
      throw new Error('No authentication tokens found');
    }
    
    // Use the dedicated user endpoint to get complete user data
    const userResponse = await fetch(`${API_BASE_URL}/api/v1/users/me/`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    
    if (!userResponse.ok) {
      // User data fetch failed
      throw new Error('Failed to fetch user data');
    }
    
    const userData = await userResponse.json();
    // User data fetched successfully
    
    // Return user data directly from the API
    return {
      id: userData.id,
      email: userData.email,
      first_name: userData.first_name || '',
      last_name: userData.last_name || '',
      organization: userData.organization || { 
        name: 'Your Organization' 
      }
    };
    
  } catch (error) {
    // Error fetching user data
    throw new Error('Failed to fetch user data');
  }
}
