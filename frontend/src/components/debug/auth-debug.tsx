"use client"

import { useState, useEffect } from "react"
import { getAuthHeaders } from "@/lib/auth/auth-api"
import { API_BASE_URL } from "@/lib/config"

export function AuthDebug() {
  const [authStatus, setAuthStatus] = useState<{
    hasTokens: boolean
    tokenContent: string
    apiResponse: string
  }>({
    hasTokens: false,
    tokenContent: "",
    apiResponse: "Not checked yet"
  })

  useEffect(() => {
    // Check for tokens in localStorage
    const tokenData = localStorage.getItem('dataelan_auth_tokens')
    const hasTokens = !!tokenData
    
    // Update state with token info
    setAuthStatus(prev => ({
      ...prev,
      hasTokens,
      tokenContent: tokenData ? JSON.stringify(JSON.parse(tokenData), null, 2) : "No tokens found"
    }))
    
    // Test API call
    async function testAuthApi() {
      try {
        console.log("Testing auth API with headers:", getAuthHeaders())
        const response = await fetch(`${API_BASE_URL}/api/v1/users/me/`, {
          method: "GET",
          headers: getAuthHeaders(),
        })
        
        if (response.ok) {
          const userData = await response.json()
          setAuthStatus(prev => ({
            ...prev,
            apiResponse: `Success: ${JSON.stringify(userData, null, 2)}`
          }))
        } else {
          setAuthStatus(prev => ({
            ...prev,
            apiResponse: `Error: ${response.status} - ${response.statusText}`
          }))
        }
      } catch (error) {
        setAuthStatus(prev => ({
          ...prev,
          apiResponse: `Exception: ${error instanceof Error ? error.message : String(error)}`
        }))
      }
    }
    
    testAuthApi()
  }, [])

  return (
    <div className="p-4 bg-gray-100 rounded-lg mb-4">
      <h3 className="text-lg font-bold mb-2">Authentication Debug</h3>
      <div className="space-y-2">
        <div>
          <span className="font-medium">Has Tokens:</span> {authStatus.hasTokens ? "Yes" : "No"}
        </div>
        <div>
          <span className="font-medium">Token Content:</span>
          <pre className="bg-gray-200 p-2 rounded text-xs mt-1 max-h-40 overflow-auto">
            {authStatus.tokenContent}
          </pre>
        </div>
        <div>
          <span className="font-medium">API Response:</span>
          <pre className="bg-gray-200 p-2 rounded text-xs mt-1 max-h-40 overflow-auto">
            {authStatus.apiResponse}
          </pre>
        </div>
      </div>
    </div>
  )
}
