import { useLocation, useNavigate } from 'react-router-dom'
import {
    LayoutDashboard,
    FolderKanban,
    Sparkles,
    Library,
    BarChart3,
    Bot,
    Settings,
    Minus,
    Square,
    Pentagon,
    Pencil,
    Eraser,
    MousePointer2,
    Ruler,
    Maximize2,
    Hash,
    Layers,
    Undo2,
    Redo2,
    ChevronRight,
} from 'lucide-react'
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
} from '@/components/ui/sidebar'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

// Navigation items for standard pages
const navigationItems = [
    { title: 'Dashboard', icon: LayoutDashboard, url: '/dashboard' },
    { title: 'Projects', icon: FolderKanban, url: '/projects' },
    { title: 'Workspace', icon: Sparkles, url: '/workspace' },
    { title: 'Library', icon: Library, url: '/library' },
    { title: 'Analytics', icon: BarChart3, url: '/analytics' },
    { title: 'AI Assistant', icon: Bot, url: '/ai-assistant' },
    { title: 'Settings', icon: Settings, url: '/settings' },
]

// Workspace toolkit items
const workspaceTools = {
    drawing: [
        { title: 'Line', icon: Minus },
        { title: 'Rectangle', icon: Square },
        { title: 'Polygon', icon: Pentagon },
        { title: 'Freehand', icon: Pencil },
        { title: 'Eraser', icon: Eraser },
        { title: 'Selection', icon: MousePointer2 },
    ],
    ai: [
        { title: 'Auto-detect', icon: Sparkles },
        { title: 'Smart Measure', icon: Ruler },
        { title: 'Material Recognition', icon: Library },
        { title: 'Quantity Extract', icon: Hash },
        { title: 'AI Suggestions', icon: Bot },
    ],
    measurement: [
        { title: 'Linear', icon: Ruler },
        { title: 'Area', icon: Maximize2 },
        { title: 'Count', icon: Hash },
        { title: 'Scale', icon: Ruler },
    ],
    layers: [
        { title: 'Layers', icon: Layers },
        { title: 'Objects', icon: Square },
    ],
    quickActions: [
        { title: 'Undo', icon: Undo2 },
        { title: 'Redo', icon: Redo2 },
    ],
}

export function AppSidebar() {
    const location = useLocation()
    const navigate = useNavigate()

    // Check if we're in workspace mode
    const isWorkspaceMode = location.pathname.startsWith('/workspace')

    return (
        <Sidebar collapsible="icon" variant="floating">
            <SidebarHeader className="border-b border-sidebar-border">
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg" className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground">
                            <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                                <Sparkles className="size-4" />
                            </div>
                            <div className="grid flex-1 text-left text-sm leading-tight">
                                <span className="truncate font-semibold">Takeoff Tool</span>
                                <span className="truncate text-xs text-muted-foreground">
                                    {isWorkspaceMode ? 'Workspace' : 'Navigation'}
                                </span>
                            </div>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>

            <SidebarContent>
                {!isWorkspaceMode ? (
                    // Navigation Mode
                    <SidebarGroup>
                        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
                        <SidebarGroupContent>
                            <SidebarMenu>
                                {navigationItems.map((item) => (
                                    <SidebarMenuItem key={item.title}>
                                        <SidebarMenuButton
                                            onClick={() => navigate(item.url)}
                                            isActive={location.pathname === item.url}
                                            tooltip={item.title}
                                        >
                                            <item.icon className="size-4" />
                                            <span>{item.title}</span>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                ))}
                            </SidebarMenu>
                        </SidebarGroupContent>
                    </SidebarGroup>
                ) : (
                    // Workspace Toolkit Mode
                    <>
                        {/* Drawing Tools */}
                        <Collapsible defaultOpen className="group/collapsible">
                            <SidebarGroup>
                                <SidebarGroupLabel asChild>
                                    <CollapsibleTrigger className="flex w-full items-center justify-between">
                                        Drawing Tools
                                        <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                                    </CollapsibleTrigger>
                                </SidebarGroupLabel>
                                <CollapsibleContent>
                                    <SidebarGroupContent>
                                        <SidebarMenu>
                                            {workspaceTools.drawing.map((tool) => (
                                                <SidebarMenuItem key={tool.title}>
                                                    <SidebarMenuButton tooltip={tool.title}>
                                                        <tool.icon className="size-4" />
                                                        <span>{tool.title}</span>
                                                    </SidebarMenuButton>
                                                </SidebarMenuItem>
                                            ))}
                                        </SidebarMenu>
                                    </SidebarGroupContent>
                                </CollapsibleContent>
                            </SidebarGroup>
                        </Collapsible>

                        {/* AI Tools */}
                        <Collapsible defaultOpen className="group/collapsible">
                            <SidebarGroup>
                                <SidebarGroupLabel asChild>
                                    <CollapsibleTrigger className="flex w-full items-center justify-between">
                                        AI Tools
                                        <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                                    </CollapsibleTrigger>
                                </SidebarGroupLabel>
                                <CollapsibleContent>
                                    <SidebarGroupContent>
                                        <SidebarMenu>
                                            {workspaceTools.ai.map((tool) => (
                                                <SidebarMenuItem key={tool.title}>
                                                    <SidebarMenuButton tooltip={tool.title}>
                                                        <tool.icon className="size-4" />
                                                        <span>{tool.title}</span>
                                                    </SidebarMenuButton>
                                                </SidebarMenuItem>
                                            ))}
                                        </SidebarMenu>
                                    </SidebarGroupContent>
                                </CollapsibleContent>
                            </SidebarGroup>
                        </Collapsible>

                        {/* Measurement Tools */}
                        <Collapsible defaultOpen className="group/collapsible">
                            <SidebarGroup>
                                <SidebarGroupLabel asChild>
                                    <CollapsibleTrigger className="flex w-full items-center justify-between">
                                        Measurement
                                        <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                                    </CollapsibleTrigger>
                                </SidebarGroupLabel>
                                <CollapsibleContent>
                                    <SidebarGroupContent>
                                        <SidebarMenu>
                                            {workspaceTools.measurement.map((tool) => (
                                                <SidebarMenuItem key={tool.title}>
                                                    <SidebarMenuButton tooltip={tool.title}>
                                                        <tool.icon className="size-4" />
                                                        <span>{tool.title}</span>
                                                    </SidebarMenuButton>
                                                </SidebarMenuItem>
                                            ))}
                                        </SidebarMenu>
                                    </SidebarGroupContent>
                                </CollapsibleContent>
                            </SidebarGroup>
                        </Collapsible>

                        {/* Layers & Objects */}
                        <Collapsible defaultOpen className="group/collapsible">
                            <SidebarGroup>
                                <SidebarGroupLabel asChild>
                                    <CollapsibleTrigger className="flex w-full items-center justify-between">
                                        Layers & Objects
                                        <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                                    </CollapsibleTrigger>
                                </SidebarGroupLabel>
                                <CollapsibleContent>
                                    <SidebarGroupContent>
                                        <SidebarMenu>
                                            {workspaceTools.layers.map((tool) => (
                                                <SidebarMenuItem key={tool.title}>
                                                    <SidebarMenuButton tooltip={tool.title}>
                                                        <tool.icon className="size-4" />
                                                        <span>{tool.title}</span>
                                                    </SidebarMenuButton>
                                                </SidebarMenuItem>
                                            ))}
                                        </SidebarMenu>
                                    </SidebarGroupContent>
                                </CollapsibleContent>
                            </SidebarGroup>
                        </Collapsible>

                        {/* Quick Actions - Always Visible */}
                        <SidebarGroup>
                            <SidebarGroupLabel>Quick Actions</SidebarGroupLabel>
                            <SidebarGroupContent>
                                <SidebarMenu>
                                    {workspaceTools.quickActions.map((tool) => (
                                        <SidebarMenuItem key={tool.title}>
                                            <SidebarMenuButton tooltip={tool.title}>
                                                <tool.icon className="size-4" />
                                                <span>{tool.title}</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    ))}
                                </SidebarMenu>
                            </SidebarGroupContent>
                        </SidebarGroup>
                    </>
                )}
            </SidebarContent>
        </Sidebar>
    )
}
