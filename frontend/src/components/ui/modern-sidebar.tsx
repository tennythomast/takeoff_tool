"use client"

import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
// Using a simple div with overflow instead of ScrollArea component

interface NavItem {
  title: string
  href: string
  icon: React.ReactNode
  label?: string
  variant?: "default" | "ghost"
}

interface SidebarProps {
  isCollapsed: boolean
  links: NavItem[]
  className?: string
}

export function Sidebar({ links, isCollapsed, className }: SidebarProps) {
  const pathname = usePathname()

  return (
    <div
      data-collapsed={isCollapsed}
      className={cn(
        "group border-r bg-background flex flex-col h-full data-[collapsed=true]:w-16 w-64 transition-all duration-300 ease-in-out",
        className
      )}
    >
      <div className="flex h-14 items-center border-b px-4">
        {!isCollapsed && (
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <img
              src="/assets/brand/logos/dataelan-logo-primary-dark.svg"
              alt="Dataelan"
              width={140}
              height={28}
              className="h-7 w-auto"
            />
          </Link>
        )}
        {isCollapsed && (
          <Link href="/dashboard" className="flex items-center justify-center">
            <Image
              src="/assets/brand/logos/dataelan-icon.svg"
              alt="Dataelan"
              width={32}
              height={32}
              className="h-8 w-8 transition-transform hover:scale-105"
              priority
            />
          </Link>
        )}
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className={cn("flex flex-col gap-2 p-2")}>
          {links.map((link, index) => (
            <Tooltip key={index} delayDuration={0}>
              <TooltipTrigger asChild>
                <Button
                  variant={pathname === link.href ? "default" : "ghost"}
                  className={cn(
                    "h-10 justify-start",
                    isCollapsed && "h-10 w-10 justify-center",
                    pathname === link.href && "bg-primary text-primary-foreground"
                  )}
                  asChild
                >
                  <Link href={link.href}>
                    {link.icon}
                    {!isCollapsed && (
                      <span className="ml-2">{link.title}</span>
                    )}
                    {!isCollapsed && link.label && (
                      <span className="ml-auto bg-primary/10 text-primary text-xs py-0.5 px-2 rounded-full">
                        {link.label}
                      </span>
                    )}
                  </Link>
                </Button>
              </TooltipTrigger>
              {isCollapsed && (
                <TooltipContent side="right" className="flex items-center gap-2">
                  {link.title}
                  {link.label && (
                    <span className="ml-auto text-muted-foreground">
                      {link.label}
                    </span>
                  )}
                </TooltipContent>
              )}
            </Tooltip>
          ))}
        </div>
      </div>
      <div className="mt-auto p-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "h-10 justify-start",
                isCollapsed && "h-10 w-10 justify-center"
              )}
              asChild
            >
              <Link href="/settings">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4"
                >
                  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                {!isCollapsed && <span className="ml-2">Settings</span>}
              </Link>
            </Button>
          </TooltipTrigger>
          {isCollapsed && (
            <TooltipContent side="right">Settings</TooltipContent>
          )}
        </Tooltip>
      </div>
    </div>
  )
}
