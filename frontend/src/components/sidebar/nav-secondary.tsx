"use client"

import * as React from "react"
import { type LucideIcon } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

interface NavSecondaryItem {
  title: string
  url: string
  icon: LucideIcon
  badge?: string
}

interface NavSecondaryProps extends React.ComponentProps<typeof SidebarGroup> {
  items: NavSecondaryItem[]
  isCompressed?: boolean
}

export function NavSecondary({ items, isCompressed = false, ...props }: NavSecondaryProps) {
  const pathname = usePathname()

  return (
    <SidebarGroup {...props}>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            const isActive = pathname === item.url
            
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton 
                  asChild 
                  size="sm"
                  tooltip={item.title}
                  className={`
                    transition-all duration-200 group
                    ${isActive 
                      ? 'bg-[#17B2FF]/10 text-[#17B2FF] border-r-2 border-[#17B2FF]' 
                      : 'text-[#98C0D9] hover:bg-[#3D5B81]/20 hover:text-white'
                    }
                    ${isCompressed ? 'justify-center' : ''}
                  `}
                >
                  <Link href={item.url} className="flex items-center w-full">
                    <item.icon className={`
                      h-4 w-4 transition-colors duration-200
                      ${isActive ? 'text-[#17B2FF]' : 'text-[#98C0D9] group-hover:text-white'}
                      ${isCompressed ? 'mx-auto' : ''}
                    `} />
                    {!isCompressed && (
                      <span className="font-medium">{item.title}</span>
                    )}
                    
                    {/* Badge */}
                    {!isCompressed && item.badge && (
                      <span className="ml-auto bg-[#3D5B81] text-[#E0E1E1] text-xs px-2 py-0.5 rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}