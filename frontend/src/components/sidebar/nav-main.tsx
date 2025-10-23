"use client"

import * as React from "react"
import { ChevronRight, type LucideIcon } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar"

interface NavMainItem {
  title: string
  url: string
  icon?: LucideIcon
  isActive?: boolean
  badge?: string | number
  items?: {
    title: string
    url: string
    badge?: string | number
  }[]
}

interface NavMainProps {
  items: NavMainItem[]
  userRole: string
  isCompressed?: boolean
}

export function NavMain({ items, userRole, isCompressed = false }: NavMainProps) {
  const pathname = usePathname()

  return (
    <SidebarGroup>
      <SidebarMenu>
        {items.map((item) => {
          const isActive = pathname === item.url || 
            (item.items && item.items.some(subItem => pathname === subItem.url))
          
          return (
            <Collapsible
              key={item.title}
              asChild
              defaultOpen={isActive}
              className="group/collapsible"
            >
              <SidebarMenuItem>
                <CollapsibleTrigger asChild>
                  <SidebarMenuButton 
                    tooltip={item.title}
                    className={`
                      w-full group relative transition-all duration-200
                      ${isActive 
                        ? 'bg-[#17B2FF]/10 text-[#17B2FF] border-r-2 border-[#17B2FF]' 
                        : 'text-[#E0E1E1] hover:bg-[#3D5B81]/20 hover:text-white'
                      }
                      ${isCompressed ? 'justify-center' : ''}
                    `}
                  >
                    {item.icon && (
                      <item.icon className={`
                        h-4 w-4 transition-colors duration-200
                        ${isActive ? 'text-[#17B2FF]' : 'text-[#98C0D9]'}
                        ${isCompressed ? 'mx-auto' : ''}
                      `} />
                    )}
                    {!isCompressed && (
                      <span className="font-medium">{item.title}</span>
                    )}
                    
                    {/* Badge */}
                    {!isCompressed && item.badge && (
                      <span className="ml-auto bg-[#17B2FF] text-white text-xs px-2 py-0.5 rounded-full">
                        {item.badge}
                      </span>
                    )}
                    
                    {/* Chevron for expandable items */}
                    {!isCompressed && item.items && (
                      <ChevronRight className="ml-auto h-4 w-4 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                    )}
                  </SidebarMenuButton>
                </CollapsibleTrigger>
                
                {/* Sub-items */}
                {item.items && (
                  <CollapsibleContent>
                    <SidebarMenuSub>
                      {item.items.map((subItem) => {
                        const isSubActive = pathname === subItem.url
                        
                        return (
                          <SidebarMenuSubItem key={subItem.title}>
                            <SidebarMenuSubButton 
                              asChild
                              className={`
                                transition-all duration-200
                                ${isSubActive 
                                  ? 'bg-[#17B2FF]/10 text-[#17B2FF] border-r-2 border-[#17B2FF]' 
                                  : 'text-[#98C0D9] hover:bg-[#3D5B81]/20 hover:text-white'
                                }
                              `}
                            >
                              <Link href={subItem.url} className="flex items-center w-full">
                                <span>{subItem.title}</span>
                                {subItem.badge && (
                                  <span className="ml-auto bg-[#3D5B81] text-[#E0E1E1] text-xs px-2 py-0.5 rounded-full">
                                    {subItem.badge}
                                  </span>
                                )}
                              </Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        )
                      })}
                    </SidebarMenuSub>
                  </CollapsibleContent>
                )}
                
                {/* Direct link for items without sub-items */}
                {!item.items && (
                  <Link href={item.url} className="absolute inset-0" />
                )}
              </SidebarMenuItem>
            </Collapsible>
          )
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}