"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { MessageSquare, Home, BarChart2, Settings, Database } from "lucide-react";

export function MainNav() {
  const pathname = usePathname();

  const navItems = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: Home
    },
    {
      name: "Analytics",
      href: "/analytics",
      icon: BarChart2
    },
    {
      name: "Data",
      href: "/data",
      icon: Database
    },
    {
      name: "Settings",
      href: "/settings",
      icon: Settings
    }
  ];

  return (
    <nav className="flex items-center space-x-4 lg:space-x-6">
      {navItems.map((item) => {
        const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
        
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-2 px-3 py-2 text-sm font-medium transition-colors rounded-md",
              isActive
                ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
                : "text-gray-700 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400"
            )}
          >
            <item.icon size={18} />
            <span>{item.name}</span>
          </Link>
        );
      })}
    </nav>
  );
}
