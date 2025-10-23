import { API_BASE_URL } from '@/lib/config';
import { getTokens } from './auth-api';

/**
 * Refresh the authentication token
 */
export async function refreshToken(): Promise<boolean> {
  try {
    // Get current tokens
    const tokens = getTokens();
    if (!tokens || !tokens.refresh) {
      console.error('No refresh token available');
      return false;
    }
    
    // Make refresh token request
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        refresh: tokens.refresh
      })
    });
    
    if (!response.ok) {
      console.error('Failed to refresh token:', response.status);
      return false;
    }
    
    // Parse the response
    const newTokens = await response.json();
    
    // Store the new tokens
    if (newTokens && newTokens.access) {
      // Update the access token but keep the refresh token
      const updatedTokens = {
        ...tokens,
        access: newTokens.access
      };
      
      // Store in both session and local storage
      sessionStorage.setItem('dataelan_auth_tokens', JSON.stringify(updatedTokens));
      localStorage.setItem('dataelan_auth_tokens', JSON.stringify(updatedTokens));
      
      console.log('Token refreshed successfully');
      return true;
    }
    
    return false;
  } catch (error) {
    console.error('Error refreshing token:', error);
    return false;
  }
}
