import '@testing-library/jest-dom/extend-expect';

// Mock fetch globally
global.fetch = jest.fn();

// Setup global mocks
jest.mock('./src/lib/auth/auth-api', () => ({
  getAuthHeaders: jest.fn().mockResolvedValue({ 'Authorization': 'Bearer test-token' })
}));
