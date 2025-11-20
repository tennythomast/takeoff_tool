import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PageContainerProps {
    children: ReactNode
    className?: string
    title?: string
    description?: string
    maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | 'full'
}

const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    full: 'max-w-full',
}

export function PageContainer({
    children,
    className,
    title,
    description,
    maxWidth = '4xl',
}: PageContainerProps) {
    return (
        <div className={cn('w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8', maxWidthClasses[maxWidth], className)}>
            {(title || description) && (
                <div className="mb-6 sm:mb-8">
                    {title && (
                        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
                            {title}
                        </h1>
                    )}
                    {description && (
                        <p className="text-muted-foreground mt-2 text-sm sm:text-base">
                            {description}
                        </p>
                    )}
                </div>
            )}
            {children}
        </div>
    )
}
