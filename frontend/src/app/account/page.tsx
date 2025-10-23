"use client"

import { useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ProfileForm } from "@/components/account/profile-form"
import { PasswordForm } from "@/components/account/password-form"
import { OrganizationSettings } from "@/components/account/organization-settings"
import { NotificationsForm } from "@/components/account/notifications-form"
import { Loader2 } from "lucide-react"
import { getUserData } from "@/lib/auth/auth-api"
// Debug component removed

export default function AccountPage() {
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const searchParams = useSearchParams()
  const activeTab = searchParams.get("tab")

  useEffect(() => {
    // Add a small delay to ensure client-side environment is ready
    const timer = setTimeout(() => {
      async function fetchUserData() {
        try {
          // Check if user has authentication tokens in either storage location
          const sessionTokens = sessionStorage.getItem('dataelan_auth_tokens');
          const localTokens = localStorage.getItem('dataelan_auth_tokens');
          
          // If no tokens in either storage, redirect to login
          if (!sessionTokens && !localTokens) {
            console.error("No authentication tokens found in any storage")
            setError("Authentication required")
            setLoading(false)
            // Redirect to login page with return URL
            const currentPath = window.location.pathname + window.location.search
            window.location.href = `/login?returnUrl=${encodeURIComponent(currentPath)}`
            return
          }
          
          // Try to fetch user data with tokens
          try {
            const userData = await getUserData()
            console.log("User data fetched successfully:", userData)
            setUser(userData)
            setLoading(false)
          } catch (err) {
            console.error("Error fetching user data:", err)
            setError("Could not verify your account. Please try logging in again.")
            setLoading(false)
            // Clear invalid tokens from both storages
            sessionStorage.removeItem('dataelan_auth_tokens')
            localStorage.removeItem('dataelan_auth_tokens')
            const currentPath = window.location.pathname + window.location.search
            window.location.href = `/login?returnUrl=${encodeURIComponent(currentPath)}`
          }
        } catch (err) {
          console.error("Unexpected error:", err)
          setError("An unexpected error occurred")
          setLoading(false)
        }
      }

      fetchUserData()
    }, 200) // Small delay to ensure client-side code runs properly
    
    return () => clearTimeout(timer)
  }, [])

  if (loading) {
    return (
      <div className="flex h-[80vh] w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-lg">Loading account information...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-[50vh] w-full flex-col items-center justify-center gap-4">
        <div className="rounded-md bg-destructive/15 p-6 text-destructive max-w-md text-center">
          <p className="text-lg font-medium mb-2">{error}</p>
          <p className="text-sm text-muted-foreground">Redirecting to login page...</p>
        </div>
      </div>
    )
  }
  
  // Determine which tab to show based on URL parameter
  const defaultTab = activeTab === 'notifications' ? 'notifications' : 
                    activeTab === 'organization' ? 'organization' : 
                    activeTab === 'password' ? 'password' : 'profile';

  return (
    <div>
      
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Account Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and preferences.
        </p>
      </div>
      
      <Tabs defaultValue={defaultTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="profile" onClick={() => router.push('/account?tab=profile')}>Profile</TabsTrigger>
          <TabsTrigger value="password" onClick={() => router.push('/account?tab=password')}>Password</TabsTrigger>
          <TabsTrigger value="organization" onClick={() => router.push('/account?tab=organization')}>Organization</TabsTrigger>
          <TabsTrigger value="notifications" onClick={() => router.push('/account?tab=notifications')}>Notifications</TabsTrigger>
        </TabsList>
        
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Update your personal information and email address.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {user && <ProfileForm user={user} setUser={setUser} />}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="password">
          <Card>
            <CardHeader>
              <CardTitle>Password</CardTitle>
              <CardDescription>
                Update your password to keep your account secure.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <PasswordForm />
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="organization">
          <Card>
            <CardHeader>
              <CardTitle>Organization Settings</CardTitle>
              <CardDescription>
                Manage your organization preferences and API key strategy.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {user && <OrganizationSettings user={user} />}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you receive notifications and alerts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <NotificationsForm user={user} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
