import { 
    Home, 
    Bot, 
    Library, 
    Building,
    BarChart3,
    CreditCard,
    Settings,
    User,
    Plus,
    Users,
    CheckSquare,
    Folder,
    MessageSquare,
    Hammer,
    FileCode,
    TestTube,
    Briefcase,
    PanelRight,
    Archive,
    Clock
  } from "lucide-react"
  import { LucideIcon } from "lucide-react"
  
  export interface NavItem {
    title: string
    url: string
    icon: LucideIcon
    badge?: string | number
    items?: NavItem[]
    permission?: string[]
  }
  
  export const sidebarNavigation: NavItem[] = [
    {
      title: "Dashboard",
      url: "/dashboard",
      icon: Home,
    },
    {
      title: "Workspaces",
      url: "/workspaces",
      icon: Briefcase,
      items: [
        {
          title: "All Workspaces",
          url: "/workspaces",
          icon: Briefcase,
        },
        {
          title: "Active",
          url: "/workspaces/active",
          icon: PanelRight,
        },
        {
          title: "Archived",
          url: "/workspaces/archived",
          icon: Archive,
        },
        {
          title: "Completed",
          url: "/workspaces/completed",
          icon: CheckSquare,
        },
        {
          title: "Recent",
          url: "/workspaces/recent",
          icon: Clock,
        },
      ],
    },
    {
      title: "Build & Create",
      url: "/build",
      icon: Hammer,
      items: [
        {
          title: "Agent Builder",
          url: "/build/agent/builder-selection",
          icon: Bot,
        },
        {
          title: "Template Creator",
          url: "/build/template",
          icon: FileCode,
        },
        {
          title: "Test & Debug",
          url: "/build/test",
          icon: TestTube,
        },
      ],
    },
    {
      title: "Manage & Monitor",
      url: "/manage",
      icon: BarChart3,
      items: [
        {
          title: "AI Agents",
          url: "/agents/",
          icon: Bot,
        },
        {
          title: "Analytics",
          url: "/manage/analytics",
          icon: BarChart3,
        },
        {
          title: "Usage & Billing",
          url: "/manage/usage",
          icon: CreditCard,
        },
      ],
    },
    {
      title: "Settings",
      url: "/settings",
      icon: Settings,
      items: [
        {
          title: "Profile",
          url: "/settings/profile",
          icon: User,
        },
        {
          title: "Team",
          url: "/settings/team",
          icon: Users,
        },
        {
          title: "Integrations",
          url: "/settings/integrations",
          icon: FileCode,
        },
        {
          title: "Security",
          url: "/settings/security",
          icon: Settings,
        },
      ],
    },
  ]
  
  // Top navbar power tools (role-based access)
  export const navbarTools = [
    {
      title: "Analytics",
      icon: BarChart3,
      permission: ["admin", "power_user"],
      items: [
        {
          title: "Cost Overview",
          url: "/analytics/cost",
          icon: BarChart3,
        },
        {
          title: "Savings Report",
          url: "/analytics/savings",
          icon: BarChart3,
        },
        {
          title: "Usage Metrics",
          url: "/analytics/usage",
          icon: BarChart3,
        },
        {
          title: "Performance Analytics",
          url: "/analytics/performance",
          icon: BarChart3,
        },
      ],
    },
    {
      title: "Billing",
      icon: CreditCard,
      permission: ["admin", "billing_manager"],
      items: [
        {
          title: "Current Plan",
          url: "/billing/plan",
          icon: CreditCard,
        },
        {
          title: "Usage & Credits",
          url: "/billing/usage",
          icon: CreditCard,
        },
        {
          title: "Cost Forecasting",
          url: "/billing/forecast",
          icon: BarChart3,
        },
        {
          title: "Payment History",
          url: "/billing/history",
          icon: CreditCard,
        },
      ],
    },
    {
      title: "Settings",
      icon: Settings,
      items: [
        {
          title: "Profile",
          url: "/settings/profile",
          icon: User,
        },
        {
          title: "Preferences",
          url: "/settings/preferences",
          icon: Settings,
        },
        {
          title: "Integrations",
          url: "/settings/integrations",
          icon: Settings,
        },
        {
          title: "Security",
          url: "/settings/security",
          icon: Settings,
        },
      ],
    },
  ]
  
  // User roles for permission checking
  export const UserRoles = {
    ADMIN: "admin",
    POWER_USER: "power_user", 
    BILLING_MANAGER: "billing_manager",
    MANAGER: "manager",
    USER: "user"
  } as const
  
  export type UserRole = typeof UserRoles[keyof typeof UserRoles]