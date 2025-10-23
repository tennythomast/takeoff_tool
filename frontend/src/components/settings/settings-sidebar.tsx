"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Settings,
  Users,
  Building,
  Key,
  Bell,
  Database,
  Layers,
  Network,
  Shield,
  FileText,
  HelpCircle
} from 'lucide-react';

interface SidebarItem {
  title: string;
  href: string;
  icon: React.ReactNode;
}

const sidebarItems: SidebarItem[] = [
  {
    title: 'General',
    href: '/settings',
    icon: <Settings className="h-4 w-4" />
  },
  {
    title: 'Users',
    href: '/settings/users',
    icon: <Users className="h-4 w-4" />
  },
  {
    title: 'Organization',
    href: '/settings/organization',
    icon: <Building className="h-4 w-4" />
  },
  {
    title: 'API Keys',
    href: '/settings/api-keys',
    icon: <Key className="h-4 w-4" />
  },
  {
    title: 'Notifications',
    href: '/settings/notifications',
    icon: <Bell className="h-4 w-4" />
  },
  {
    title: 'Data Sources',
    href: '/settings/data-sources',
    icon: <Database className="h-4 w-4" />
  },
  {
    title: 'Workflows',
    href: '/settings/workflows',
    icon: <Layers className="h-4 w-4" />
  },
  {
    title: 'Security',
    href: '/settings/security',
    icon: <Shield className="h-4 w-4" />
  },
  {
    title: 'Documentation',
    href: '/settings/documentation',
    icon: <FileText className="h-4 w-4" />
  },
  {
    title: 'Support',
    href: '/settings/support',
    icon: <HelpCircle className="h-4 w-4" />
  }
];

export function SettingsSidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 border-r bg-background h-full">
      <div className="py-4 px-3">
        <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
          Settings
        </h2>
        <div className="space-y-1">
          {sidebarItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center rounded-md px-4 py-2 text-sm font-medium transition-colors",
                pathname === item.href
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <span className="mr-2">{item.icon}</span>
              {item.title}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
