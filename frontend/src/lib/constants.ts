// API base URL - make sure we're using localhost instead of 'backend' hostname
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// WebSocket URL
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 
  (typeof window !== 'undefined' ? 
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8001` : 
    'ws://localhost:8001');

// Project status options
export const PROJECT_STATUS = {
  ACTIVE: 'ACTIVE',
  ARCHIVED: 'ARCHIVED',
  COMPLETED: 'COMPLETED',
};

// Session status options
export const SESSION_STATUS = {
  DRAFT: 'DRAFT',
  ACTIVE: 'ACTIVE',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
};

// Model types
export const MODEL_TYPES = {
  TEXT: 'TEXT',
  CODE: 'CODE',
  IMAGE: 'IMAGE',
  VOICE: 'VOICE',
  VIDEO: 'VIDEO',
};
