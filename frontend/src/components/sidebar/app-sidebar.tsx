"use client"

import * as React from "react"
import { 
  Search, 
  LifeBuoy,
  Send,
  PanelLeft
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { NavMain } from "@/components/sidebar/nav-main"
import { NavSecondary } from "@/components/sidebar/nav-secondary"
import { NavUser } from "@/components/sidebar/nav-user"
import { sidebarNavigation } from "@/lib/navigation/sidebar-config"
import { useSidebarContext } from "@/context/sidebar-context"
import { getCurrentUser, isAuthenticated, getStoredTokens } from "@/lib/auth/auth-service"

// Custom function to check authentication using both localStorage and sessionStorage
function checkAuthentication(): boolean {
  // First check using the auth service (which uses sessionStorage)
  if (isAuthenticated()) {
    return true;
  }
  
  // If that fails, check if we have a token in localStorage
  const localToken = localStorage.getItem('authToken');
  return !!localToken;
}

// Function to decode JWT token
function decodeJwtToken(token: string) {
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
async function fetchUserDataWithFallback(): Promise<User | null> {
  try {
    // Try the standard auth service first
    const userData = await getCurrentUser();
    if (userData) {
      console.log("Got user data from auth service:", userData);
      return userData as User;
    }
    
    console.log("Auth service failed to get user data, trying fallback...");
    
    // If that fails, try using the localStorage token
    const localToken = localStorage.getItem('authToken');
    if (!localToken) {
      console.log("No token in localStorage");
      return null;
    }
    
    // Since the /api/auth/user/ endpoint doesn't exist, decode the token instead
    const tokenData = decodeJwtToken(localToken);
    console.log("Decoded token data:", tokenData);
    
    if (tokenData) {
      // Create a user object from the token data
      return {
        id: tokenData.user_id || tokenData.sub || '',
        email: tokenData.email || '',
        // We don't have first/last name in the token, so we'll use email
        firstName: '',
        lastName: '',
        avatar: undefined,
        role: 'user'
      } as User;
    }
    
    return null;
  } catch (error) {
    console.error("Error in fetchUserDataWithFallback:", error);
    return null;
  }
}

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  user?: {
    name: string
    firstName?: string
    lastName?: string
    email: string
    avatar?: string
    role: string
  }
}

// Secondary navigation items
const secondaryNavItems = [
  {
    title: "Help & Support",
    url: "/support",
    icon: LifeBuoy
  },
  {
    title: "Send Feedback",
    url: "/feedback",
    icon: Send
  }
]

// Modern Navbar Component
function ModernNavbar() {
  // Get the sidebar context to access toggle function
  const { isCompressed, toggleSidebar } = useSidebarContext();
  
  // Debug logging
  console.log("Sidebar isCompressed state:", isCompressed);
  
  const handleToggle = () => {
    console.log("Toggle button clicked, current state:", isCompressed);
    toggleSidebar();
    // No need to log the new state here as it won't be updated until after the render
  };
  
  return (
    <div className="h-16 bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      {/* Left side - Toggle button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleToggle}
          className="p-2 rounded-md hover:bg-gray-100 transition-colors"
          aria-label={isCompressed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <PanelLeft 
            className={`h-5 w-5 text-gray-500 transition-transform duration-300 ${isCompressed ? 'rotate-180' : ''}`} 
          />
        </button>
      </div>
      
      {/* Right side - Search only */}
      <div className="flex items-center">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            type="search"
            placeholder="Search..."
            className="w-64 pl-10 pr-4 h-9 bg-white border-gray-300 rounded-full text-gray-800 shadow-sm focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 transition-all"
          />
        </div>
      </div>
    </div>
  )
}

export function AppSidebar({ user, ...props }: AppSidebarProps) {
  const { isCompressed } = useSidebarContext();
  const [currentUser, setCurrentUser] = React.useState<AppSidebarProps['user']>({
    name: "",
    email: "",
    role: "user"
  });

  // Effect to fetch user data
  React.useEffect(() => {
    if (user) {
      setCurrentUser(user);
    } else {
      const fetchUserData = async () => {
        const userData = await fetchUserDataWithFallback();
        
        if (userData) {
          setCurrentUser({
            name: userData.firstName ? `${userData.firstName} ${userData.lastName || ''}`.trim() : userData.email,
            firstName: userData.firstName || "",
            lastName: userData.lastName || "",
            email: userData.email || "",
            avatar: userData.avatar,
            role: userData.role || "user"
          });
        } else {
          // Fallback for demo/development
          setCurrentUser({
            name: "Tenny",
            firstName: "Tenny",
            lastName: "",
            email: "guest@example.com",
            avatar: undefined,
            role: "user"
          });
        }
      };
      
      fetchUserData();
    }
  }, [user])

  const secondaryNavItems = [
    {
      title: "Help & Support",
      url: "/help",
      icon: LifeBuoy,
    },
    {
      title: "Feedback",
      url: "/feedback",
      icon: Send,
    },
  ]

  return (
    <>
      {/* Modern Navbar */}
      <ModernNavbar />
      
      {/* Sidebar */}
      <Sidebar 
        variant="inset"
        className={`bg-[#192026] border-r border-[#3D5B81]/20 transition-all duration-300 ease-in-out ${
          isCompressed ? 'w-[4rem] min-w-[4rem] max-w-[4rem]' : 'w-[16rem] min-w-[16rem] max-w-[16rem]'
        }`}
        {...props}
      >
        <SidebarHeader className="border-b border-[#3D5B81]/20 bg-[#192026]">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" asChild>
                <Link href="/dashboard" className="flex items-center justify-center gap-2 group">
                  {isCompressed ? (
                    <Image
                      src="/assets/brand/logos/dataelan-icon-dark.svg"
                      alt="Dataelan"
                      width={32}
                      height={32}
                      className="h-8 w-8 transition-transform group-hover:opacity-90 group-hover:scale-105"
                    />
                  ) : (
                    <Image
                      src="/assets/brand/logos/dataelan-logo-primary-dark.svg"
                      alt="Dataelan"
                      width={160}
                      height={32}
                      className="h-8 w-auto transition-transform group-hover:opacity-90 group-hover:scale-105"
                    />
                  )}
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
        
        <SidebarContent className="text-[#E0E1E1] bg-[#192026]">
          <NavMain items={sidebarNavigation} userRole={currentUser?.role || "user"} isCompressed={isCompressed} />
          <NavSecondary 
            items={secondaryNavItems}
            isCompressed={isCompressed}
          />
        </SidebarContent>
        
        <SidebarFooter className="border-t border-[#3D5B81]/20 bg-[#192026]">
          {/* Pass user data with firstName properly extracted */}
          <NavUser user={{
            name: currentUser?.name || "",
            firstName: currentUser?.firstName || "",
            lastName: currentUser?.lastName || "",
            email: currentUser?.email || "",
            avatar: currentUser?.avatar,
            role: currentUser?.role || "user"
          }} isCompressed={isCompressed} />
        </SidebarFooter>
      </Sidebar>
    </>
  )
}

// User interface that matches our backend response
export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  name?: string; // Computed field from backend
  role: string;
  avatar?: string;
}

// Dashboard Layout Component
export function DashboardLayout({ 
  children, 
  user 
}: { 
  children: React.ReactNode
  user?: User
}) {
  // State for authenticated user with proper typing
  const [currentUser, setCurrentUser] = React.useState<User>(user || {
    id: '',
    email: '...',
    firstName: 'Loading',
    lastName: '...',
    role: 'user',
    name: 'Loading...'
  });
  
  // Fetch user data from API using auth service
  React.useEffect(() => {
    // Only fetch if no user was provided as prop
    if (!user) {
      const fetchUserData = async () => {
        try {
          // Use custom authentication check that works with both storage mechanisms
          const isAuth = checkAuthentication();
          console.log('[DashboardLayout] Custom authentication status:', isAuth);
          
          // Debug token storage
          const sessionToken = sessionStorage.getItem('dataelan_auth_tokens');
          const localToken = localStorage.getItem('authToken');
          console.log('[DashboardLayout] Session token exists:', !!sessionToken);
          console.log('[DashboardLayout] Local token exists:', !!localToken);
          
          if (!isAuth) {
            console.warn("User not authenticated in DashboardLayout");
            // Set default guest user if not authenticated
            setCurrentUser({
              id: 'guest',
              email: 'guest@example.com',
              firstName: 'Guest',
              lastName: 'User',
              role: 'user',
              name: 'Guest User'
            });
            return;
          }
          
          // Try to get user data from the API first
          try {
            // Use the getCurrentUser function from auth-service to get proper user data
            const userData = await getCurrentUser();
            console.log("[DashboardLayout] User data from API:", userData);
            
            if (userData) {
              // Set user info from API data which includes proper firstName and lastName
              setCurrentUser({
                id: userData.id,
                email: userData.email,
                firstName: userData.firstName,
                lastName: userData.lastName,
                name: `${userData.firstName} ${userData.lastName}`.trim(),
                role: userData.role || "user"
              });
              return; // Exit early if we successfully got user data
            }
          } catch (error) {
            console.error("[DashboardLayout] Error fetching user data from API:", error);
          }
          
          // Fallback to token approach if API call fails
          let userInfo = null;
          
          // Try sessionStorage first (where auth service stores tokens)
          const sessionTokenData = sessionStorage.getItem('dataelan_auth_tokens');
          if (sessionTokenData) {
            try {
              const tokens = JSON.parse(sessionTokenData);
              if (tokens && tokens.access) {
                const tokenPayload = decodeJwtToken(tokens.access);
                console.log("[DashboardLayout] Decoded session token:", tokenPayload);
                userInfo = tokenPayload;
              }
            } catch (e) {
              console.error("[DashboardLayout] Error parsing session token:", e);
            }
          }
          
          // If that fails, try localStorage
          if (!userInfo) {
            const localToken = localStorage.getItem('authToken');
            if (localToken) {
              const tokenPayload = decodeJwtToken(localToken);
              console.log("[DashboardLayout] Decoded local token:", tokenPayload);
              userInfo = tokenPayload;
            }
          }
          
          if (userInfo) {
            // Extract email from token
            const email = userInfo.email || '';
            
            // Set user info based on token data as fallback
            // Note: This is not ideal as we're splitting the email, but it's a fallback
            const username = email.split('@')[0];
            setCurrentUser({
              id: userInfo.user_id || userInfo.sub || 'user',
              email: email,
              firstName: username, // Fallback to username from email
              lastName: '',
              name: username,
              role: email.includes('admin') ? "admin" : 
                    email.includes('staff') ? "staff" : "user"
            });
          } else {
            console.error("Failed to fetch user data in DashboardLayout");
            // Set default guest user if fetch fails
            setCurrentUser({
              id: 'guest',
              email: 'guest@example.com',
              firstName: 'Guest',
              lastName: 'User',
              role: 'user',
              name: 'Guest User'
            });
          }
        } catch (error) {
          console.error("Error fetching user data in DashboardLayout:", error);
          // Set default guest user on error
          setCurrentUser({
            id: 'guest',
            email: 'guest@example.com',
            firstName: 'Guest',
            lastName: 'User',
            role: 'user',
            name: 'Guest User'
          });
        }
      };
      
      fetchUserData();
    }
  }, [user]);
  
  return (
    <div className="flex h-screen w-full bg-[#E0E1E1] relative">
      {/* Sidebar - Fixed position */}
      <aside className="w-64 h-screen fixed left-0 top-0 z-10 bg-[#192026] border-r border-[#3D5B81]/20">
        <div className="flex flex-col h-full">
          <SidebarHeader className="border-b border-[#3D5B81]/20 bg-[#192026] px-4 py-3">
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton size="lg" asChild>
                  <Link href="/dashboard" className="flex items-center gap-2 group">
                    <Image
                      src="/assets/brand/logos/dataelan-logo-primary-dark.svg"
                      alt="Dataelan"
                      width={160}
                      height={32}
                      className="h-8 w-auto transition-transform group-hover:opacity-90 group-hover:scale-105"
                      priority
                    />
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarHeader>
          
          <SidebarContent className="flex-1 overflow-y-auto">
            <div className="h-full flex flex-col">
              <div className="flex-1">
                <NavMain items={sidebarNavigation as any} userRole={currentUser?.role || 'user'} />
              </div>
              <div className="mt-auto">
                <NavSecondary 
                  items={secondaryNavItems}
                  className="border-t border-[#3D5B81]/20 pt-4" 
                />
              </div>
            </div>
          </SidebarContent>
          
          <SidebarFooter className="border-t border-[#3D5B81]/20 bg-[#192026] px-4 py-3">
            <NavUser user={{
              name: currentUser.name || currentUser.firstName || 'User',
              email: currentUser.email,
              role: currentUser.role || 'user'
            }} />
          </SidebarFooter>
        </div>
      </aside>
      
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col ml-64 w-[calc(100%-16rem)] min-h-screen">
        {/* Navbar - Sticky at the top */}
        <header className="sticky top-0 z-10 bg-white border-b border-gray-200">
          <ModernNavbar />
        </header>
        
        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}