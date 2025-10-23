/**
 * Application configuration constants
 */

// API URL Configuration
// Make sure we're using localhost instead of 'backend' hostname
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Authentication constants
export const TOKEN_STORAGE_KEY = 'takeoff_auth_tokens';
export const USER_STORAGE_KEY = 'takeoff_user';
export const DEFAULT_TIMEOUT = 15000; // 15 seconds
