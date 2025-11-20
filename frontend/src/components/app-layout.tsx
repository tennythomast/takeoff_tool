import { type ReactNode } from 'react'
import { AppNavbar } from '@/components/app-navbar'

interface AppLayoutProps {
    children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
    return (
        <div className="min-h-screen bg-[#e9eaec]">
            <AppNavbar />
            <main className="container mx-auto px-8 py-8">
                {children}
            </main>
        </div>
    )
}
