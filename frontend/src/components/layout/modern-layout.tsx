"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import { 
  Home, 
  Bot, 
  Workflow, 
  Library, 
  Building,
  BarChart3,
  CreditCard,
  Settings,
  Users,
  CheckSquare
} from "lucide-react"

import { Sidebar } from "@/components/ui/modern-sidebar"
import { ModernHeader } from "@/components/ui/modern-header"
import { sidebarNavigation } from "@/lib/navigation/sidebar-config"
import { checkAuthentication, decodeJwtToken, fetchUserDataWithFallback } from "@/lib/auth/auth-service"

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  name?: string
  role: string
  avatar?: string
}

export function ModernLayout({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = React.useState(false)
  const [currentUser, setCurrentUser] = React.useState<User>({
    id: '',
    email: '...',
    firstName: 'Loading',
    lastName: '...',
    role: 'user',
    name: 'Loading...'
  })

  // Convert the sidebar navigation config to the format needed by the new Sidebar component
  const sidebarLinks = sidebarNavigation.map(item => ({
    title: item.title,
    href: item.url,
    icon: <item.icon className="h-4 w-4" />,
    label: item.badge?.toString(),
    variant: "ghost" as const
  }))

  // Fetch user data from API using auth service
  React.useEffect(() => {
    const fetchUserData = async () => {
      try {
        // Use custom authentication check that works with both storage mechanisms
        const isAuth = checkAuthentication()
        
        if (!isAuth) {
          console.warn("User not authenticated in ModernLayout")
          // Set default guest user if not authenticated
          setCurrentUser({
            id: 'guest',
            name: "Guest User",
            email: "guest@example.com",
            firstName: 'Guest',
            lastName: 'User',
            avatar: undefined,
            role: "user"
          })
          return
        }
        
        // Try to fetch user data with fallback
        const userData = await fetchUserDataWithFallback()
        
        if (userData) {
          setCurrentUser({
            ...userData,
            name: userData.firstName ? `${userData.firstName} ${userData.lastName}` : userData.email.split('@')[0],
            role: userData.role || 'user' // Ensure role is set
          })
        } else {
          console.error("Failed to fetch user data in ModernLayout")
          // Set default guest user if fetch fails
          setCurrentUser({
            id: 'guest',
            email: 'guest@example.com',
            firstName: 'Guest',
            lastName: 'User',
            role: 'user',
            name: 'Guest User'
          })
        }
      } catch (error) {
        console.error("Error fetching user data in ModernLayout:", error)
        // Set default guest user on error
        setCurrentUser({
          id: 'guest',
          email: 'guest@example.com',
          firstName: 'Guest',
          lastName: 'User',
          role: 'user',
          name: 'Guest User'
        })
      }
    }
    
    fetchUserData()
  }, [])

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar 
        links={sidebarLinks} 
        isCollapsed={isCollapsed} 
        className="hidden md:flex"
      />
      <div className="flex flex-col flex-1 overflow-hidden">
        <ModernHeader 
          toggleSidebar={toggleSidebar} 
          user={{
            name: currentUser.name || 'User',
            email: currentUser.email,
            role: currentUser.role,
            avatar: currentUser.avatar
          }}
        />
        <main className="flex-1 overflow-y-auto p-6 bg-[#F7F7F7]">
          <div className="max-w-7xl mx-auto w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
