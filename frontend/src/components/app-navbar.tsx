import { Bell, Settings, Search, LayoutGrid, FolderKanban } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Link, useLocation } from 'react-router-dom'

export function AppNavbar() {
    const location = useLocation()

    const navLinks = [
        { name: 'Home', href: '/dashboard', icon: LayoutGrid },
        { name: 'Projects', href: '/projects', icon: FolderKanban },
    ]

    return (
        <nav className="flex h-20 items-center justify-between px-8 bg-[#e9eaec]">
            {/* Left: Logo */}
            <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500 text-white font-bold">
                    T
                </div>
                <span className="text-xl font-bold text-gray-800">Takeoff</span>
            </div>

            {/* Center: Navigation Links */}
            <div className="hidden md:flex items-center gap-8">
                {navLinks.map((link) => {
                    const isActive = location.pathname === link.href
                    return (
                        <Link
                            key={link.name}
                            to={link.href}
                            className={`text-sm font-medium transition-colors hover:text-primary ${isActive ? 'text-gray-900 font-semibold border-b-2 border-gray-900 pb-1' : 'text-gray-500'
                                }`}
                        >
                            {link.name}
                        </Link>
                    )
                })}
            </div>

            {/* Right: Utilities */}
            <div className="flex items-center gap-4">
                {/* Search Bar */}
                <div className="relative w-64 hidden lg:block">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                        placeholder="Enter your search request..."
                        className="pl-10 rounded-full bg-white border-none shadow-sm h-10"
                    />
                </div>

                {/* Settings */}
                <Button variant="ghost" size="icon" className="rounded-full bg-white shadow-sm hover:bg-gray-100">
                    <Settings className="h-5 w-5 text-gray-600" />
                </Button>

                {/* Notifications */}
                <Button variant="ghost" size="icon" className="rounded-full bg-white shadow-sm hover:bg-gray-100">
                    <Bell className="h-5 w-5 text-gray-600" />
                </Button>

                {/* Profile */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                            <Avatar className="h-10 w-10 border-2 border-white shadow-sm">
                                <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
                                <AvatarFallback>CN</AvatarFallback>
                            </Avatar>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-56" align="end" forceMount>
                        <DropdownMenuLabel className="font-normal">
                            <div className="flex flex-col space-y-1">
                                <p className="text-sm font-medium leading-none">shadcn</p>
                                <p className="text-xs leading-none text-muted-foreground">
                                    m@example.com
                                </p>
                            </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>
                            Profile
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                            Settings
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => window.location.href = '/login'}>
                            Log out
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </nav>
    )
}
