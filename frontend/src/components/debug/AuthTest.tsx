import React, { useState, useEffect } from 'react';
import { getAuthHeaders } from '@/lib/auth/auth-api';
import { API_BASE_URL } from '@/lib/config';
import { Button } from '@/components/ui/button';

/**
 * A debug component to test authentication and API endpoints
 */
export function AuthTest() {
  const [authStatus, setAuthStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');
  const [authHeaders, setAuthHeaders] = useState<Record<string, string>>({});
  const [apiResponse, setApiResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Check authentication status on mount
  useEffect(() => {
    const headers = getAuthHeaders();
    setAuthHeaders(headers);
    
    if (headers.Authorization) {
      setAuthStatus('authenticated');
    } else {
      setAuthStatus('unauthenticated');
    }
  }, []);

  // Test API endpoint
  const testEndpoint = async (endpoint: string) => {
    setError(null);
    setApiResponse(null);
    
    try {
      console.log(`Testing endpoint: ${endpoint}`);
      console.log('Using headers:', getAuthHeaders());
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(`API Error (${response.status}): ${JSON.stringify(errorData)}`);
        } catch (jsonError) {
          throw new Error(`API Error (${response.status}): ${response.statusText}`);
        }
      }
      
      const data = await response.json();
      console.log('API Response:', data);
      setApiResponse(data);
    } catch (err: any) {
      console.error('Error testing endpoint:', err);
      setError(err.message || 'Unknown error');
    }
  };

  return (
    <div className="p-4 border rounded-md">
      <h2 className="text-xl font-bold mb-4">Authentication Test</h2>
      
      <div className="mb-4">
        <p>
          <strong>Auth Status:</strong>{' '}
          <span className={authStatus === 'authenticated' ? 'text-green-600' : 'text-red-600'}>
            {authStatus}
          </span>
        </p>
        
        <p className="mt-2"><strong>Auth Headers:</strong></p>
        <pre className="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-20">
          {JSON.stringify(authHeaders, null, 2)}
        </pre>
      </div>
      
      <div className="flex flex-col gap-2 mb-4">
        <h3 className="font-semibold">Test Endpoints</h3>
        <Button onClick={() => testEndpoint('/api/v1/users/me/')}>
          Test Current User
        </Button>
        <Button onClick={() => testEndpoint('/api/v1/organizations/')}>
          Test Organizations
        </Button>
        <Button onClick={() => testEndpoint('/api/health/')}>
          Test Health Endpoint
        </Button>
      </div>
      
      {error && (
        <div className="p-2 bg-red-100 border border-red-300 rounded mb-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}
      
      {apiResponse && (
        <div className="mt-4">
          <h3 className="font-semibold mb-2">API Response:</h3>
          <pre className="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-60">
            {JSON.stringify(apiResponse, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default AuthTest;
