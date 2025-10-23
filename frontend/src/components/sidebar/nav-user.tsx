"use client"

import * as React from "react"
import Link from "next/link"
import {
  BadgeCheck,
  Bell,
  ChevronsUpDown,
  CreditCard,
  LogOut,
  Settings,
  Sparkles,
  User,
} from "lucide-react"

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"

interface User {
  name: string
  firstName?: string
  lastName?: string
  email: string
  avatar?: string
  role: string
}

interface NavUserProps {
  user: User
  isCompressed?: boolean
}

export function NavUser({ user, isCompressed = false }: NavUserProps) {
  const { isMobile } = useSidebar()
  
  // Debug user info
  console.log('[NavUser] Received user prop:', user);
  
  // Set a default user if none is provided
  const displayUser = user || {
    name: "Guest User",
    email: "guest@example.com",
    avatar: undefined,
    role: "user"
  };

  // Generate initials from user name
  const getInitials = (name: string) => {
    if (!name) return 'GU';
    return name
      .split(' ')
      .map(part => part.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  // Get role badge color
  const getRoleBadgeColor = (role: string) => {
    switch (role.toLowerCase()) {
      case 'admin':
        return 'bg-red-500/10 text-red-400'
      case 'manager':
        return 'bg-blue-500/10 text-blue-400'
      case 'user':
        return 'bg-green-500/10 text-green-400'
      default:
        return 'bg-gray-500/10 text-gray-400'
    }
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className={`group data-[state=open]:bg-[#3D5B81]/20 hover:bg-[#3D5B81]/20 transition-all duration-200 ${isCompressed ? 'justify-center' : ''}`}
            >
              <Avatar className="h-8 w-8 rounded-lg border border-[#3D5B81]/30">
                <AvatarImage 
                  src={displayUser.avatar} 
                  alt={displayUser.name}
                  className="object-cover" 
                />
                <AvatarFallback className="rounded-lg bg-[#17B2FF] text-white font-semibold">
                  {getInitials(displayUser.name)}
                </AvatarFallback>
              </Avatar>
              
              {!isCompressed && (
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold text-[#E0E1E1] group-hover:text-white transition-colors">
                    {displayUser.firstName || displayUser.name.split(' ')[0]}
                  </span>
                  <span className="truncate text-xs text-[#98C0D9] group-hover:text-[#E0E1E1] transition-colors">
                    {displayUser.email}
                  </span>
                </div>
              )}
              
              {!isCompressed && (
                <div className="ml-auto flex h-4 items-center gap-1">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-sm font-medium ${getRoleBadgeColor(displayUser.role)}`}>
                    {displayUser.role.toUpperCase()}
                  </span>
                  <ChevronsUpDown className="h-3 w-3 text-[#98C0D9] group-hover:text-[#E0E1E1] transition-colors" />
                </div>
              )}
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          
          <DropdownMenuContent
            className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg bg-[#1a1d23] border-[#3D5B81]/30"
            side={isMobile ? "bottom" : "right"}
            align="end"
            sideOffset={4}
          >
            {/* User Info Header */}
            <DropdownMenuLabel className="p-0 font-normal">
              <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                <Avatar className="h-8 w-8 rounded-lg border border-[#3D5B81]/30">
                  <AvatarImage 
                    src={user.avatar} 
                    alt={user.name}
                    className="object-cover" 
                  />
                  <AvatarFallback className="rounded-lg bg-[#17B2FF] text-white font-semibold">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold text-[#E0E1E1]">
                    {user.firstName || user.name.split(' ')[0]}
                  </span>
                  <span className="truncate text-xs text-[#98C0D9]">
                    {user.email}
                  </span>
                </div>
              </div>
            </DropdownMenuLabel>
            
            {/* Role Badge */}
            <div className="px-2 pb-2">
              <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium capitalize ${getRoleBadgeColor(user.role)}`}>
                <BadgeCheck className="w-3 h-3 mr-1" />
                {user.role}
              </span>
            </div>
            
            <DropdownMenuSeparator className="bg-[#3D5B81]/30" />
            
            {/* Account Actions */}
            <DropdownMenuGroup>
              <DropdownMenuItem className="text-[#E0E1E1] hover:bg-[#3D5B81]/20 hover:text-white focus:bg-[#3D5B81]/20 focus:text-white">
                <Sparkles className="mr-2 h-4 w-4" />
                Upgrade to Pro
              </DropdownMenuItem>
              <DropdownMenuItem className="text-[#E0E1E1] hover:bg-[#3D5B81]/20 hover:text-white focus:bg-[#3D5B81]/20 focus:text-white" asChild>
                <Link href="/account">
                  <div className="flex items-center">
                    <User className="mr-2 h-4 w-4" />
                    Account
                  </div>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem className="text-[#E0E1E1] hover:bg-[#3D5B81]/20 hover:text-white focus:bg-[#3D5B81]/20 focus:text-white" asChild>
                <Link href="/billing">
                  <div className="flex items-center">
                    <CreditCard className="mr-2 h-4 w-4" />
                    Billing
                  </div>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem className="text-[#E0E1E1] hover:bg-[#3D5B81]/20 hover:text-white focus:bg-[#3D5B81]/20 focus:text-white" asChild>
                <Link href="/account?tab=notifications">
                  <div className="flex items-center">
                    <Bell className="mr-2 h-4 w-4" />
                    Notifications
                  </div>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem className="text-[#E0E1E1] hover:bg-[#3D5B81]/20 hover:text-white focus:bg-[#3D5B81]/20 focus:text-white" asChild>
                <Link href="/settings">
                  <div className="flex items-center">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </div>
                </Link>
              </DropdownMenuItem>
            </DropdownMenuGroup>
            
            <DropdownMenuSeparator className="bg-[#3D5B81]/30" />
            
            {/* Logout */}
            <DropdownMenuItem className="text-red-400 hover:bg-red-500/20 hover:text-red-300 focus:bg-red-500/20 focus:text-red-300">
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}