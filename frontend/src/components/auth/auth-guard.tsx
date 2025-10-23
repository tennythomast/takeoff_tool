"use client"

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated, logout } from '@/lib/auth/auth-service'
import { initActivityTracker } from '@/lib/auth/activity-tracker'

interface AuthGuardProps {
  children: React.ReactNode
}

/**
 * AuthGuard component to protect routes from unauthorized access
 * Redirects to login page if user is not authenticated
 * Enforces global sign-out on token expiry regardless of user activity
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter()
  const [isChecking, setIsChecking] = useState(true)
  
  useEffect(() => {
    // Initialize activity tracker
    initActivityTracker()
    
    // Check authentication status
    const checkAuth = () => {
      // Check authentication without considering activity
      // This enforces token validation regardless of user activity
      const authenticated = isAuthenticated(false)
      
      if (!authenticated) {
        // Token is invalid or expired, sign out user and redirect to login
        console.log('[AuthGuard] Authentication invalid, signing out user')
        logout()
        router.push('/login')
        return false
      }
      
      return true
    }
    
    // Initial check
    const isAuth = checkAuth()
    setIsChecking(false)
    
    // Set up periodic token validation check
    const intervalId = setInterval(() => {
      checkAuth()
    }, 30000) // Check every 30 seconds for faster response to token expiry
    
    return () => {
      clearInterval(intervalId)
    }
  }, [router])
  
  // Show nothing while checking authentication
  if (isChecking) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          <p>Verifying authentication...</p>
        </div>
      </div>
    )
  }
  
  // Render children if authenticated
  return <>{children}</>
}
