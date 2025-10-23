"use client"

import { SidebarProvider } from "@/components/ui/sidebar"
import { DashboardLayout } from "@/components/sidebar/app-sidebar"
import { AuthGuard } from "@/components/auth/auth-guard"
import { useEffect } from "react"
import { initActivityTracker } from "@/lib/auth/activity-tracker"

// Import User type from app-sidebar
import { User } from "@/components/sidebar/app-sidebar"

interface MainLayoutProps {
  children: React.ReactNode
  user?: User
  title?: string
  subtitle?: string
}

export function MainLayout({ children, user, title, subtitle }: MainLayoutProps) {
  // Initialize activity tracker when the app loads
  useEffect(() => {
    // Initialize the activity tracker to monitor user activity
    initActivityTracker();
    
    // No cleanup needed as the activity tracker handles its own cleanup
  }, []);
  
  return (
    <AuthGuard>
      <SidebarProvider>
        <DashboardLayout user={user}>
          <div className="p-0">
            {title && (
              <div className="mb-6 px-6 pt-6">
                <h1 className="text-2xl font-bold text-[#0E1036]">{title}</h1>
                {subtitle && <p className="text-gray-600 mt-1">{subtitle}</p>}
              </div>
            )}
            {children}
          </div>
        </DashboardLayout>
      </SidebarProvider>
    </AuthGuard>
  )
}