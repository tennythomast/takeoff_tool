"use client"

import { Bell, Search } from "lucide-react"
import { usePathname } from "next/navigation"
import { MainNav } from "./main-nav"

import { SidebarTrigger } from "@/components/ui/sidebar"
import { Input } from "@/components/ui/input"
import { navbarTools, sidebarNavigation, NavItem } from "@/lib/navigation/sidebar-config"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface TopNavbarProps {
  user?: {
    name: string
    email: string
    avatar?: string
    role: string
  }
  title?: string
  subtitle?: string
}

export function TopNavbar({ user }: TopNavbarProps) {
  const userRole = user?.role || "user"
  const pathname = usePathname()
  
  // Determine the current page title based on pathname
  const getPageTitle = (): string => {
    // Check for exact matches first
    if (pathname === "/dashboard") return "Dashboard"
    
    // Check for section matches
    if (pathname?.startsWith("/agents")) return "AI Agents"
    if (pathname?.startsWith("/workflows")) return "Workflows"
    if (pathname?.startsWith("/templates")) return "Template Gallery"
    if (pathname?.startsWith("/organization")) return "Organization"
    if (pathname?.startsWith("/analytics")) return "Analytics"
    if (pathname?.startsWith("/billing")) return "Billing"
    if (pathname?.startsWith("/settings")) return "Settings"
    
    // For more specific pages, find the matching navigation item
    const findTitleFromNavItems = (items: NavItem[]): string | null => {
      for (const item of items) {
        if (pathname === item.url) return item.title
        if (item.items) {
          const subTitle: string | null = findTitleFromNavItems(item.items)
          if (subTitle) return subTitle
        }
      }
      return null
    }
    
    const navTitle = findTitleFromNavItems(sidebarNavigation)
    if (navTitle) return navTitle
    
    // Default fallback
    return "Dashboard"
  }
  
  const pageTitle = getPageTitle()
  
  // Filter tools based on user role
  const availableTools = navbarTools.filter(tool => 
    !tool.permission || tool.permission.includes(userRole)
  )

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 sticky top-0 z-40">
      <div className="flex items-center gap-4">
        <SidebarTrigger className="-ml-1 text-[#192026]/70 hover:text-[#192026]" />
        <div>
          <h1 className="text-xl font-bold font-magnetik">{pageTitle}</h1>
        </div>
        
        {/* Main Navigation */}
        <div className="ml-8">
          <MainNav />
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#192026]/70" />
          <Input
            placeholder="Search agents, workflows, templates..."
            className="pl-10 w-80 bg-white border-gray-300 shadow-sm text-gray-800 focus:bg-white focus:border-blue-500"
          />
        </div>


        {/* Power Tools Dropdowns */}
        {availableTools.map((tool) => (
          <DropdownMenu key={tool.title}>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                size="sm" 
                className="gap-2 text-[#192026]/70 hover:text-[#192026]"
              >
                <tool.icon className="h-4 w-4" />
                {tool.title}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48 text-[#192026]">
              {tool.items?.map((item) => (
                <DropdownMenuItem key={item.title} asChild>
                  <a href={item.url} className="flex items-center gap-2">
                    <item.icon className="h-4 w-4" />
                    {item.title}
                  </a>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ))}

        {/* Notifications */}
        <Button 
          variant="ghost" 
          size="sm" 
          className="relative text-[#192026]/70 hover:text-[#192026]"
        >
          <Bell className="h-4 w-4" />
          <Badge 
            variant="destructive" 
            className="absolute -top-1 -right-1 h-5 w-5 text-xs flex items-center justify-center p-0"
          >
            3
          </Badge>
        </Button>
      </div>
    </header>
  )
}