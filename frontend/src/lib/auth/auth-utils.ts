import { getAuthHeaders } from "./auth-api";

/**
 * Check if user is authenticated by verifying if auth tokens exist
 */
export function isAuthenticated(): boolean {
  // In client-side code, check if tokens exist in localStorage
  if (typeof window !== 'undefined') {
    const tokenData = localStorage.getItem('dataelan_auth_tokens');
    
    if (!tokenData) {
      return false;
    }
    
    try {
      const tokens = JSON.parse(tokenData);
      return !!tokens && !!tokens.access;
    } catch (error) {
      console.error('[Auth Utils] Error parsing auth tokens:', error);
      return false;
    }
  }
  
  return false;
}

/**
 * Redirect to login if user is not authenticated
 */
export function redirectToLogin(): void {
  if (typeof window !== 'undefined') {
    // Store the current path to redirect back after login
    const currentPath = window.location.pathname;
    if (currentPath !== '/login') {
      localStorage.setItem('dataelan_redirect_after_login', currentPath);
    }
    
    // Redirect to login page
    window.location.href = '/login';
  }
}
