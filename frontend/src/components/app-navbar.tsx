import { useLocation, useNavigate } from 'react-router-dom'
import { Home, User as UserIcon, HelpCircle, LogOut, Settings, Moon, Sun, Search, Bell } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbLink,
    BreadcrumbList,
    BreadcrumbPage,
    BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { getCurrentUser, logout, type User } from '@/lib/api'
import { useEffect, useState } from 'react'

// Map routes to breadcrumb labels
const routeLabels: Record<string, string> = {
    '/dashboard': 'Dashboard',
    '/projects': 'Projects',
    '/workspace': 'Workspace',
    '/library': 'Library',
    '/analytics': 'Analytics',
    '/ai-assistant': 'AI Assistant',
    '/settings': 'Settings',
}

export function AppNavbar() {
    const location = useLocation()
    const navigate = useNavigate()
    const [user, setUser] = useState<User | null>(null)
    const [isDarkMode, setIsDarkMode] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')
    const notificationCount = 3 // Example count - will be dynamic later

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const userData = await getCurrentUser()
                setUser(userData)
            } catch (error) {
                console.error('Failed to load user data')
            }
        }
        fetchUser()
    }, [])

    const getUserInitials = () => {
        if (user?.first_name && user?.last_name) {
            return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
        }
        if (user?.email) {
            return user.email.substring(0, 2).toUpperCase()
        }
        return 'U'
    }

    const getUserDisplayName = () => {
        if (user?.first_name && user?.last_name) {
            return `${user.first_name} ${user.last_name}`
        }
        if (user?.first_name) {
            return user.first_name
        }
        return user?.email || 'User'
    }

    const handleLogout = () => {
        logout()
    }

    const toggleTheme = () => {
        setIsDarkMode(!isDarkMode)
        document.documentElement.classList.toggle('dark')
    }

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            console.log('Searching for:', searchQuery)
            // TODO: Implement search functionality
        }
    }

    // Generate breadcrumbs from current path
    const generateBreadcrumbs = () => {
        const pathSegments = location.pathname.split('/').filter(Boolean)
        const breadcrumbs: Array<{ label: string; href: string; isLast: boolean }> = []

        // Always start with home
        breadcrumbs.push({
            label: 'Home',
            href: '/dashboard',
            isLast: pathSegments.length === 0,
        })

        // Build breadcrumbs from path segments
        let currentPath = ''
        pathSegments.forEach((segment, index) => {
            currentPath += `/${segment}`
            const label = routeLabels[currentPath] || segment.charAt(0).toUpperCase() + segment.slice(1)
            const isLast = index === pathSegments.length - 1

            breadcrumbs.push({
                label,
                href: currentPath,
                isLast,
            })
        })

        return breadcrumbs
    }

    const breadcrumbs = generateBreadcrumbs()

    return (
        <header className="flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />

            {/* Breadcrumbs */}
            <Breadcrumb>
                <BreadcrumbList>
                    {breadcrumbs.map((crumb, index) => (
                        <div key={crumb.href} className="flex items-center gap-2">
                            {index > 0 && <BreadcrumbSeparator />}
                            <BreadcrumbItem>
                                {crumb.isLast ? (
                                    <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                                ) : (
                                    <BreadcrumbLink href={crumb.href}>
                                        {index === 0 && <Home className="h-4 w-4" />}
                                        {index > 0 && crumb.label}
                                    </BreadcrumbLink>
                                )}
                            </BreadcrumbItem>
                        </div>
                    ))}
                </BreadcrumbList>
            </Breadcrumb>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="hidden md:block">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        type="search"
                        placeholder="Search..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-64 rounded-full pl-9 pr-4"
                    />
                </div>
            </form>

            {/* Notification Bell */}
            <Button variant="ghost" size="icon" className="relative" onClick={() => console.log('Notifications clicked')}>
                <Bell className="h-5 w-5" />
                {notificationCount > 0 && (
                    <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-medium text-primary-foreground">
                        {notificationCount}
                    </span>
                )}
                <span className="sr-only">Notifications</span>
            </Button>

            {/* User Profile Dropdown */}
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                        <Avatar className="h-9 w-9">
                            <AvatarFallback className="bg-primary text-primary-foreground">
                                {getUserInitials()}
                            </AvatarFallback>
                        </Avatar>
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                    <DropdownMenuLabel className="font-normal">
                        <div className="flex flex-col space-y-1">
                            <p className="text-sm font-medium leading-none">{getUserDisplayName()}</p>
                            <p className="text-xs leading-none text-muted-foreground">
                                {user?.email}
                            </p>
                        </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate('/settings')}>
                        <UserIcon className="mr-2 h-4 w-4" />
                        <span>Profile Settings</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => navigate('/settings')}>
                        <Settings className="mr-2 h-4 w-4" />
                        <span>Account Settings</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => window.open('/help', '_blank')}>
                        <HelpCircle className="mr-2 h-4 w-4" />
                        <span>Help & Documentation</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={toggleTheme}>
                        {isDarkMode ? (
                            <>
                                <Sun className="mr-2 h-4 w-4" />
                                <span>Light Mode</span>
                            </>
                        ) : (
                            <>
                                <Moon className="mr-2 h-4 w-4" />
                                <span>Dark Mode</span>
                            </>
                        )}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                        <LogOut className="mr-2 h-4 w-4" />
                        <span>Logout</span>
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </header>
    )
}
