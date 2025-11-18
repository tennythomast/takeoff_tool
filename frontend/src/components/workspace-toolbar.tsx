import { useNavigate } from 'react-router-dom'
import { ChevronRight, Save, Share2, Download, Settings, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'

export function WorkspaceToolbar() {
    const navigate = useNavigate()

    const handleExitWorkspace = () => {
        navigate('/dashboard')
    }

    return (
        <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />

            {/* Breadcrumb Navigation */}
            <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Project Name</span>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Drawing Set</span>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Sheet 1</span>
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Active Tool Indicator */}
            <div className="flex items-center gap-2 rounded-md border border-border bg-muted px-3 py-1.5 text-sm">
                <div className="h-2 w-2 rounded-full bg-primary" />
                <span className="text-muted-foreground">Selection Tool</span>
            </div>

            {/* Quick Settings */}
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                        <Settings className="h-4 w-4" />
                        <span className="ml-2 hidden sm:inline">Settings</span>
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>Quick Settings</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem>
                        <span>Units: Imperial</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                        <span>Scale: 1/4" = 1'-0"</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                        <span>Snap to Grid: On</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                        <span>Show Dimensions: On</span>
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
                <Button variant="outline" size="sm">
                    <Save className="h-4 w-4" />
                    <span className="ml-2 hidden sm:inline">Save</span>
                </Button>
                <Button variant="outline" size="sm">
                    <Share2 className="h-4 w-4" />
                    <span className="ml-2 hidden sm:inline">Share</span>
                </Button>
                <Button variant="outline" size="sm">
                    <Download className="h-4 w-4" />
                    <span className="ml-2 hidden sm:inline">Export</span>
                </Button>
            </div>

            <Separator orientation="vertical" className="mx-2 h-4" />

            {/* Exit Workspace */}
            <Button variant="ghost" size="sm" onClick={handleExitWorkspace}>
                <X className="h-4 w-4" />
                <span className="ml-2">Exit</span>
            </Button>
        </header>
    )
}
