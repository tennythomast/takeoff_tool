/**
 * Authentication Service for Dataelan
 * Handles login, signup, token management, and API communication
 * Designed to work with Docker and local development environments
 */

// Constants
const TOKEN_STORAGE_KEY = 'dataelan_auth_tokens';
const USER_STORAGE_KEY = 'dataelan_user';
const DEFAULT_TIMEOUT = 15000; // 15 seconds

// API URL Configuration
const getApiBaseUrl = (useInternalUrl = false): string => {
  // For internal Docker network communication (container to container)
  if (useInternalUrl && process.env.NEXT_PUBLIC_INTERNAL_API_URL) {
    return process.env.NEXT_PUBLIC_INTERNAL_API_URL.replace(/\/+$/, '');
  }

  // Check if we're in the browser
  if (typeof window !== 'undefined') {
    // Use environment variable if available
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
    }
    
    // In development, try to determine the best URL based on hostname
    if (process.env.NODE_ENV === 'development') {
      // When accessing from browser in Docker, use the host's address
      const hostname = window.location.hostname;
      
      // Check if we're running in a Docker container
      const isInDocker = hostname !== 'localhost' && hostname !== '127.0.0.1';
      
      if (isInDocker) {
        // When running in Docker, use the hostname
        return `http://${hostname}:8000`;
      } else {
        // Local development
        return 'http://localhost:8000';
      }
    }
    
    // In production with no env var, use relative URL (same-origin)
    return window.location.origin;
  }
  
  // Server-side rendering - use Docker service name
  return process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';
};

// Helper to construct API URLs correctly
const getApiUrl = (endpoint: string, useInternalUrl = false): string => {
  const baseUrl = getApiBaseUrl(useInternalUrl);
  
  // Clean the endpoint
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  
  // Ensure we don't duplicate '/api' in the URL
  if (baseUrl.endsWith('/api') || baseUrl.endsWith('/api/')) {
    return `${baseUrl}/${cleanEndpoint}`;
  }
  
  return `${baseUrl}/api/${cleanEndpoint}`;
};

// Helper to try both regular and internal URLs for API calls
const getApiUrlWithFallback = async (endpoint: string): Promise<{url: string, isInternal: boolean}> => {
  // First check if the standard URL is reachable
  try {
    const standardUrl = getApiUrl(endpoint);
    const response = await fetch(`${standardUrl.split('/').slice(0, -1).join('/')}/health/`, {
      method: 'HEAD',
      cache: 'no-store',
      headers: { 'Accept': 'application/json' },
    });
    
    if (response.ok) {
      return { url: standardUrl, isInternal: false };
    }
  } catch (error) {
    console.warn('[Auth] Standard API URL not reachable, will try internal URL');
  }
  
  // If standard URL fails and we have an internal URL, use that
  if (process.env.NEXT_PUBLIC_INTERNAL_API_URL) {
    return { url: getApiUrl(endpoint, true), isInternal: true };
  }
  
  // Fall back to standard URL if internal isn't available
  return { url: getApiUrl(endpoint), isInternal: false };
};

// Authentication service configuration initialized

// Types and Interfaces
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user?: User;
}

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface TokenPayload {
  user_id: string;
  email: string;
  exp: number;
  iat: number;
}

export interface StoredTokens {
  access: string;
  refresh: string;
  expiresAt: number;
}

// Custom Error Classes
export class AuthError extends Error {
  statusCode: number;
  errors?: Record<string, any>;
  
  constructor(message: string, statusCode = 401, errors?: Record<string, any>) {
    super(message);
    this.name = 'AuthError';
    this.statusCode = statusCode;
    this.errors = errors;
    
    // Maintain proper prototype chain for TypeScript
    Object.setPrototypeOf(this, AuthError.prototype);
  }
  
  // For backward compatibility
  get status() {
    return this.statusCode;
  }
}

export class NetworkError extends AuthError {
  constructor(message = 'Network request failed', statusCode = 0, errors?: Record<string, any>) {
    super(message, statusCode, errors);
    this.name = 'NetworkError';
    
    // Maintain proper prototype chain for TypeScript
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

export class ValidationError extends AuthError {
  constructor(message: string, errors: Record<string, any>) {
    super(message, 400, errors);
    this.name = 'ValidationError';
    
    // Maintain proper prototype chain for TypeScript
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

// Utility Functions
/**
 * Enhanced fetch with timeout and comprehensive error handling
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = DEFAULT_TIMEOUT): Promise<Response> {
  // Fetch request to URL
  
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
    console.error(`[fetchWithTimeout] Request to ${url} timed out after ${timeout}ms`);
  }, timeout);
  
  try {
    // Prepare headers
    const headers = new Headers(options.headers);
    if (!headers.has('Content-Type') && options.body) {
      headers.set('Content-Type', 'application/json');
    }
    
    // Add CORS headers if not already present
    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }
    
    // Log request (with sensitive data redacted)
    const loggableOptions = {
      ...options,
      headers: Object.fromEntries(headers.entries()),
      body: options.body && typeof options.body === 'string' && options.body.includes('password') 
        ? '[REDACTED]' 
        : options.body
    };
    // Request with configured options
    
    // Make the request with CORS support
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      mode: 'cors',
      credentials: 'include', // Send cookies for cross-origin requests
      headers
    });
    
    // Response received
    
    // If we get a successful response, return it
    if (response.ok) {
      return response;
    }
    
    // For non-2xx responses, parse the error details
    let errorData: any = {};
    const contentType = response.headers.get('content-type');
    
    try {
      if (contentType && contentType.includes('application/json')) {
        errorData = await response.json();
      } else {
        errorData = { message: await response.text() };
      }
    } catch (parseError) {
      console.error('[fetchWithTimeout] Failed to parse error response:', parseError);
      errorData = { message: 'Failed to parse error response' };
    }
    
    const status = response.status;
    
    // Handle specific error cases
    switch (status) {
      case 400:
        throw new ValidationError(
          errorData.detail || errorData.message || 'Validation error',
          errorData
        );
        
      case 401:
        throw new AuthError(
          errorData.detail || errorData.message || 'Authentication required',
          status,
          errorData
        );
        
      case 403:
        throw new AuthError(
          errorData.detail || errorData.message || 'Forbidden: You do not have permission',
          status,
          errorData
        );
        
      case 404:
        throw new NetworkError(
          errorData.detail || errorData.message || 'Resource not found',
          status,
          errorData
        );
        
      default:
        if (status >= 400 && status < 500) {
          throw new AuthError(
            errorData.detail || errorData.message || `Request failed with status ${status}`,
            status,
            errorData
          );
        } else {
          throw new NetworkError(
            errorData.detail || errorData.message || `Server error (${status})`,
            status,
            errorData
          );
        }
    }
  } catch (error: any) {
    // Handle network errors
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      throw new NetworkError(
        'Network error: Failed to connect to the server', 
        0,
        { url }
      );
    } else if (error instanceof DOMException && error.name === 'AbortError') {
      throw new NetworkError(
        `Request to ${url} timed out after ${timeout}ms`,
        0,
        { url, timeout }
      );
    } else if (!(error instanceof AuthError)) {
      // If it's not already one of our custom errors, wrap it
      throw new NetworkError(
        `Request failed: ${error.message}`,
        0,
        { url, originalError: error.message }
      );
    }
    
    // Re-throw AuthError instances as-is
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Parse JWT token payload
 */
function parseJWTPayload(token: string): TokenPayload | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error('Failed to parse JWT token:', e);
    return null;
  }
}

// Get user data with organization information for account page
async function getUserData() {
  // First get the basic user information
  const user = await getCurrentUser();
  
  if (!user) {
    throw new AuthError('User not authenticated');
  }
  
  try {
    // Get user's organizations
    const response = await authenticatedFetch(getApiUrl('v1/organizations/'));
    
    if (!response.ok) {
      throw new AuthError('Failed to fetch user organizations', response.status);
    }
    
    const organizations = await response.json();
    
    // Find the default organization
    const defaultOrg = organizations.find((org: any) => org.is_default) || organizations[0];
    
    return {
      ...user,
      default_org: defaultOrg?.id,
      organizations: organizations
    };
  } catch (error) {
    console.error('Error fetching user data with organizations:', error);
    // Return basic user info even if org fetch fails
    return user;
  }
}

/**
 * Check if token is valid and not expired
 * @param {string} token - JWT token to validate
 * @param {number} bufferSeconds - Buffer time in seconds before expiration to consider token invalid
 * @returns {boolean} True if token is valid and not expired
 */
function isTokenValid(token: string, bufferSeconds: number = 60): boolean {
  if (!token) {
    // No token provided for validation
    return false;
  }
  
  try {
    const payload = parseJWTPayload(token);
    if (!payload) {
      // Could not parse token payload
      return false;
    }
    
    if (!payload.exp) {
      // Token has no expiration claim
      return false;
    }
    
    const currentTime = Math.floor(Date.now() / 1000);
    const isValid = payload.exp > (currentTime + bufferSeconds);
    
    if (!isValid) {
      // Token expired or will expire soon
    }
    
    return isValid;
  } catch (error) {
    console.error('[Auth] Error validating token:', error);
    return false;
  }
}

/**
 * Store tokens securely
 */
function setTokens(access: string, refresh: string): void {
  try {
    const payload = parseJWTPayload(access);
    if (!payload) throw new Error('Invalid access token');
    
    const tokens: StoredTokens = {
      access,
      refresh,
      expiresAt: payload.exp * 1000 // Convert to milliseconds
    };
    
    sessionStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
    // Tokens stored successfully

    // Notify the app of the authentication change
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('auth-login'));
    }
  } catch (e) {
    console.error('[Auth] Failed to store tokens:', e);
  }
}

/**
 * Get stored tokens
 */
export function getStoredTokens(): StoredTokens | null {
  try {
    const tokensJson = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (!tokensJson) return null;
    
    return JSON.parse(tokensJson) as StoredTokens;
  } catch (e) {
    console.error('[Auth] Failed to retrieve tokens:', e);
    return null;
  }
}

/**
 * Remove stored tokens
 */
function clearTokens(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    // Tokens cleared

    // Notify the app of the authentication change
    dispatchAuthStateChange();
  } catch (e) {
    console.error('[Auth] Failed to clear tokens:', e);
  }
}

/**
 * Store user data
 */
function setCurrentUser(user: User): void {
  try {
    sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch (e) {
    console.error('[Auth] Failed to store user data:', e);
  }
}

/**
 * Get current user from storage
 */
function getStoredUser(): User | null {
  try {
    const userJson = sessionStorage.getItem(USER_STORAGE_KEY);
    if (!userJson) return null;
    
    return JSON.parse(userJson) as User;
  } catch (e) {
    console.error('[Auth] Failed to retrieve user data:', e);
    return null;
  }
}

/**
 * Clear user data
 */
function clearUser(): void {
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem(USER_STORAGE_KEY);
      sessionStorage.removeItem(USER_STORAGE_KEY);
    } catch (error) {
      console.error('[Auth] Error clearing user data:', error);
    }
  }
}

// Get authentication headers for API requests
function getAuthHeaders(): Record<string, string> {
  const tokens = getStoredTokens();
  if (!tokens || !tokens.access) {
    return {};
  }
  return {
    'Authorization': `Bearer ${tokens.access}`,
    'Content-Type': 'application/json'
  };
}

// Core Authentication Functions

/**
 * Handle user login
 */
export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  try {
    const loginUrl = getApiUrl('auth/token/');
    // Attempting login
    
    // Send credentials directly - backend expects email and password
    // Sending credentials for authentication
    
    const response = await fetchWithTimeout(loginUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(credentials), // Send email and password directly
    });
    
    const data = await response.json();
    // Login successful
    
    // Store tokens and user data
    setTokens(data.access, data.refresh);
    if (data.user) {
      setCurrentUser(data.user);
    }
    
    // Dispatch authentication state change event
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('authStateChanged', {
        detail: { timestamp: Date.now() }
      }));
    }
    
    return data;
  } catch (error) {
    console.error('[Auth] Login error:', error);
    throw error;
  }
}

/**
 * Handle user registration
 */
export async function signup(userData: SignupData): Promise<User> {
  try {
    const signupUrl = getApiUrl('auth/register/');
    // Attempting signup
    
    // Map frontend fields to backend field names
    const payload = {
      email: userData.email,
      password: userData.password,
      first_name: userData.firstName,
      last_name: userData.lastName
    };
    
    // Sending signup data
    // Processing payload
    
    const response = await fetchWithTimeout(signupUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(payload),
    });
    
    const data = await response.json();
    // Signup successful
    
    return data.user;
  } catch (error) {
    console.error('[Auth] Signup error:', error);
    throw error;
  }
}

/**
 * Refresh access token using refresh token
 * @param {boolean} clearOnError - Whether to clear tokens on error (default: false)
 * @returns {Promise<string | null>} - New access token or null
 */
export async function refreshToken(clearOnError: boolean = false): Promise<string | null> {
  try {
    const tokens = getStoredTokens();
    if (!tokens || !tokens.refresh) {
      console.error('[Auth] No refresh token available');
      return null;
    }
    
    const refreshUrl = getApiUrl('auth/token/refresh/');
    const response = await fetchWithTimeout(refreshUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });
    
    const data = await response.json();
    // Token refresh successful
    
    // Update stored tokens
    setTokens(data.access, tokens.refresh);
    
    return data.access;
  } catch (error) {
    console.error('[Auth] Token refresh error:', error);
    if (clearOnError) {
      clearTokens(); // Only clear tokens if clearOnError is true
    }
    return null;
  }
}

/**
 * Make authenticated API request with automatic token refresh
 * @param {string} url - URL to fetch
 * @param {RequestInit} options - Fetch options
 * @param {boolean} forceSignOut - Whether to force sign out on auth errors (default: false)
 * @returns {Promise<Response>} - Fetch response
 */
export async function authenticatedFetch(
  url: string, 
  options: RequestInit = {}, 
  forceSignOut: boolean = false
): Promise<Response> {
  try {
    // Get stored tokens
    const tokens = getStoredTokens();
    if (!tokens || !tokens.access) {
      // No tokens available, user is not authenticated
      if (forceSignOut) {
        console.warn('[Auth] No tokens available, signing out user');
        logout(); // Force logout
      }
      throw new AuthError('Not authenticated', 401);
    }
    
    // Check if token is expired and refresh if needed
    if (!isTokenValid(tokens.access)) {
      // Access token expired, attempting refresh
      const newToken = await refreshToken(forceSignOut);
      if (!newToken) {
        // If refresh fails and forceSignOut is true, sign out the user
        if (forceSignOut) {
          console.warn('[Auth] Failed to refresh token, signing out user');
          logout(); // Force logout
        }
        throw new AuthError('Session expired', 401);
      }
    }
    
    // Get the latest tokens after potential refresh
    const currentTokens = getStoredTokens();
    if (!currentTokens || !currentTokens.access) {
      // If tokens are missing and forceSignOut is true, sign out
      if (forceSignOut) {
        console.warn('[Auth] Authentication tokens missing, signing out user');
        logout(); // Force logout
      }
      throw new AuthError('Authentication failed', 401);
    }
    
    // Add authorization header
    const headers = new Headers(options.headers);
    if (currentTokens && currentTokens.access) {
      headers.set('Authorization', `Bearer ${currentTokens.access}`);
    }
    
    // Add CORS headers if not already present
    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }
    
    const response = await fetchWithTimeout(url, {
      ...options,
      headers,
    });
    
    // Handle 401 Unauthorized errors
    if (response.status === 401) {
      // Try to refresh the token
      const newToken = await refreshToken(forceSignOut);
      if (!newToken) {
        // If refresh fails and forceSignOut is true, sign out the user
        if (forceSignOut) {
          console.warn('[Auth] Failed to refresh token on 401, signing out user');
          logout(); // Force logout
        }
        throw new AuthError('Session expired', 401);
      }
      
      // Retry the request with the new token
      const retryHeaders = new Headers(options.headers);
      retryHeaders.set('Authorization', `Bearer ${newToken}`);
      
      return fetchWithTimeout(url, {
        ...options,
        headers: retryHeaders,
      });
    }
    
    return response;
  } catch (error) {
    console.error('[Auth] Authenticated fetch error:', error);
    
    // Clear tokens on auth errors only if forceSignOut is true
    if (error instanceof AuthError && typeof window !== 'undefined' && forceSignOut) {
      console.log('[Auth] Authentication error, signing out user');
      logout(); // Force logout
    }
    
    throw error;
  }
}

/**
 * Get current user information
 */
export async function getCurrentUser(): Promise<User | null> {
  // First check if we have the user in storage
  const storedUser = getStoredUser();
  if (storedUser) {
    return storedUser;
  }
  
  // If not, try to fetch from API
  try {
    const tokens = getStoredTokens();
    if (!tokens || !tokens.access) {
      return null;
    }
    
    // Use the correct endpoint for getting the current user
    const userUrl = getApiUrl('v1/users/me/');
    const response = await authenticatedFetch(userUrl);
    const rawUserData = await response.json();
    
    // Map snake_case field names from API to camelCase for frontend
    const userData: User = {
      id: rawUserData.id,
      email: rawUserData.email,
      firstName: rawUserData.first_name, // Map from snake_case to camelCase
      lastName: rawUserData.last_name,   // Map from snake_case to camelCase
      role: rawUserData.role || 'user'
    };
    
    console.log('[Auth] Mapped user data:', userData);
    
    // Store the user data
    setCurrentUser(userData);
    
    return userData;
  } catch (error) {
    console.error('[Auth] Failed to get current user:', error);
    return null;
  }
}

/**
 * Logout user by clearing tokens and user data
 */
export function logout(): void {
  clearTokens();
  clearUser();
  // User logged out
  
  // Dispatch authentication state change event
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('authStateChanged', {
      detail: { timestamp: Date.now() }
    }));
  }
}

/**
 * Check if user is currently authenticated
 * @param {boolean} considerActivity - Whether to consider user activity when determining authentication
 * @returns {boolean} True if user is authenticated with a valid token
 */
export function isAuthenticated(considerActivity: boolean = false): boolean {
  try {
    // Check if we have tokens
    const tokens = getStoredTokens();
    if (!tokens) {
      return false;
    }

    // Check if access token is valid
    if (isTokenValid(tokens.access)) {
      return true;
    }

    // If access token is invalid, check if we have a valid refresh token
    // We don't actually refresh here to avoid side effects
    if (isTokenValid(tokens.refresh, 60 * 60 * 24)) { // 1 day buffer for refresh tokens
      return true;
    }
    
    // If we're considering activity and tokens exist but are expired,
    // we'll still consider the user authenticated if they're actively using the app
    if (considerActivity && tokens.access && tokens.refresh) {
      // The actual activity check is done in the AuthGuard component
      // Here we just acknowledge that expired tokens might still be considered valid
      // if the user is active
      return true;
    }

    return false;
  } catch (error) {
    console.error("Error checking authentication status:", error);
    return false;
  }
}

// Custom function to check authentication using both localStorage and sessionStorage
export function checkAuthentication(): boolean {
  // First check using the auth service (which uses sessionStorage)
  if (isAuthenticated()) {
    return true;
  }
  
  // If that fails, check if we have a token in localStorage
  if (typeof window !== 'undefined') {
    const localToken = localStorage.getItem('authToken');
    return !!localToken;
  }
  
  return false;
}

/**
 * Helper function to dispatch authentication state change event
 * This allows components to react to auth changes in the same tab
 */
function dispatchAuthStateChange(): void {
  if (typeof window !== 'undefined') {
    console.log('[Auth] Dispatching auth state change event');
    // Custom event that components can listen for
    window.dispatchEvent(new CustomEvent('authStateChanged', {
      detail: { authenticated: isAuthenticated() }
    }));
    
    // For backward compatibility
    window.dispatchEvent(new Event('auth-logout'));
  }
}

/**
 * Decode JWT token
 */
export function decodeJwtToken(token: string) {
  try {
    // Get the payload part of the JWT (second part)
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error("Error decoding JWT token:", error);
    return null;
  }
}

// Custom function to fetch user data with localStorage token fallback
export async function fetchUserDataWithFallback(): Promise<User | null> {
  try {
    // Try the standard auth service first
    const userData = await getCurrentUser();
    if (userData) {
      // User data retrieved
      return userData;
    }
    
    // Trying fallback for user data
    
    // If that fails, try using the localStorage token
    if (typeof window !== 'undefined') {
      const localToken = localStorage.getItem('authToken');
      if (!localToken) {
        // No token in localStorage
        return null;
      }
      
      // Since the /api/auth/user/ endpoint doesn't exist, decode the token instead
      const tokenData = decodeJwtToken(localToken);
      // Token data decoded
      
      if (tokenData) {
        // Create a user object from the token data
        return {
          id: tokenData.user_id || tokenData.sub || '',
          email: tokenData.email || '',
          // We don't have first/last name in the token, so we'll use email
          firstName: '',
          lastName: '',
          role: tokenData.role || (tokenData.email && tokenData.email.includes('admin') ? 'admin' : 'user')
        };
      }
    }
    
    return null;
  } catch (error) {
    console.error("Error in fetchUserDataWithFallback:", error);
    return null;
  }
}

/**
 * Initialize authentication on app start
 * Call this in your app initialization
 */
export async function initializeAuth(): Promise<User | null> {
  try {
    // Check if we have valid tokens
    const tokens = getStoredTokens();
    if (!tokens || !isTokenValid(tokens.access)) {
      // Try to refresh the token
      const newToken = await refreshToken();
      if (!newToken) {
        return null;
      }
    }
    
    // Get the current user
    return await getCurrentUser();
  } catch (error) {
    console.error('[Auth] Failed to initialize auth:', error);
    return null;
  }
}

/**
 * Check if the API server is reachable
 * Useful for diagnosing connection issues
 */
export async function checkApiConnection(): Promise<{success: boolean, message: string, internalUrl?: boolean}> {
  // First try the standard API URL
  try {
    const healthUrl = getApiUrl('health/');
    // Checking API connection
    
    const response = await fetchWithTimeout(healthUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }, 3000); // 3 second timeout for health check
    
    const data = await response.json();
    // API connection check completed
    
    return { success: true, message: 'Connected to API server' };
  } catch (error) {
    console.warn('[Auth] Standard API connection failed, trying internal URL:', error);
    
    // If we're in a Docker environment, try the internal URL
    if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_INTERNAL_API_URL) {
      try {
        const internalUrl = `${process.env.NEXT_PUBLIC_INTERNAL_API_URL.replace(/\/+$/, '')}/health/`;
        // Trying internal Docker network URL
        
        const response = await fetchWithTimeout(internalUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        }, 3000);
        
        const data = await response.json();
        // Internal API connection successful
        
        return { 
          success: true, 
          message: 'Connected to API server via internal Docker network',
          internalUrl: true
        };
      } catch (internalError) {
        console.error('[Auth] Both API connection attempts failed:', internalError);
        return { 
          success: false, 
          message: 'Failed to connect to API server via both public and internal URLs'
        };
      }
    }
    
    return { 
      success: false, 
      message: 'Failed to connect to API server' 
    };
  }
}