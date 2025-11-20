import { type ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ContentBlockProps {
    children: ReactNode
    className?: string
    title?: string
    description?: string
    footer?: ReactNode
    padding?: 'none' | 'sm' | 'md' | 'lg'
    variant?: 'default' | 'outline' | 'ghost'
}

const paddingClasses = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
}

export function ContentBlock({
    children,
    className,
    title,
    description,
    footer,
    padding = 'md',
    variant = 'default',
}: ContentBlockProps) {
    const cardClassName = cn(
        'transition-all duration-200',
        variant === 'outline' && 'border',
        variant === 'ghost' && 'border-0 shadow-none bg-transparent',
        variant === 'default' && 'border border-border/50 shadow-sm',
        className
    )

    return (
        <Card className={cardClassName}>
            {(title || description) && (
                <CardHeader>
                    {title && <CardTitle>{title}</CardTitle>}
                    {description && <CardDescription>{description}</CardDescription>}
                </CardHeader>
            )}
            <CardContent className={cn(paddingClasses[padding], title || description ? '' : 'pt-6')}>
                {children}
            </CardContent>
            {footer && (
                <CardFooter className="flex justify-end gap-2">
                    {footer}
                </CardFooter>
            )}
        </Card>
    )
}
