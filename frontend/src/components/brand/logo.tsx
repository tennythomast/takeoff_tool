import { cn } from '@/lib/utils'
import { DataelanColors } from '@/lib/brand/colors'

export type LogoVariant = 'primary' | 'white' | 'dark'
export type LogoLayout = 'horizontal' | 'stacked' | 'icon-only' | 'wordmark-only'
export type LogoSize = 'sm' | 'md' | 'lg' | 'xl'

interface LogoProps {
  variant?: LogoVariant
  layout?: LogoLayout
  size?: LogoSize | number
  className?: string
  width?: number
  height?: number
  alt?: string
}

const sizeMap = {
  horizontal: {
    sm: { width: 100, height: 32 },
    md: { width: 140, height: 44 },
    lg: { width: 180, height: 56 },
    xl: { width: 220, height: 68 },
  },
  stacked: {
    sm: { width: 60, height: 80 },
    md: { width: 80, height: 100 },
    lg: { width: 100, height: 120 },
    xl: { width: 120, height: 140 },
  },
  'icon-only': {
    sm: { width: 32, height: 32 },
    md: { width: 40, height: 40 },
    lg: { width: 48, height: 48 },
    xl: { width: 56, height: 56 },
  },
  'wordmark-only': {
    sm: { width: 80, height: 24 },
    md: { width: 100, height: 30 },
    lg: { width: 120, height: 36 },
    xl: { width: 140, height: 42 },
  }
}

export function Logo({ 
  variant = 'primary', 
  layout = 'horizontal',
  size = 'md',
  className,
  width,
  height,
  alt = 'Dataelan'
}: LogoProps) {
  // Calculate dimensions
  const dimensions = typeof size === 'number' 
    ? { width: size, height: size }
    : sizeMap[layout][size]
  
  const finalWidth = width || dimensions.width
  const finalHeight = height || dimensions.height
  
  const getTextColor = () => {
    switch (variant) {
      case 'white':
        return DataelanColors.softGraph
      case 'dark':
        return DataelanColors.obsidian
      default:
        return DataelanColors.claySignal
    }
  }
  
  const getIconBackground = () => {
    switch (variant) {
      case 'white':
        return DataelanColors.softGraph
      case 'dark':
        return DataelanColors.claySignal
      default:
        return DataelanColors.claySignal
    }
  }
  
  const getIconTextColor = () => {
    switch (variant) {
      case 'white':
        return DataelanColors.claySignal
      case 'dark':
        return DataelanColors.softGraph
      default:
        return DataelanColors.softGraph
    }
  }
  
  // Icon-only layout
  if (layout === 'icon-only') {
    return (
      <div 
        className={cn('flex items-center justify-center rounded-lg font-bold', className)}
        style={{ 
          width: finalWidth, 
          height: finalHeight,
          backgroundColor: getIconBackground(),
          color: getIconTextColor(),
          fontSize: `${finalHeight * 0.5}px`
        }}
        aria-label={alt}
      >
        D
      </div>
    )
  }
  
  // Wordmark-only layout
  if (layout === 'wordmark-only') {
    return (
      <span 
        className={cn('font-bold tracking-tight', className)}
        style={{ 
          color: getTextColor(),
          fontSize: `${finalHeight * 0.7}px`,
          lineHeight: `${finalHeight}px`
        }}
        aria-label={alt}
      >
        Dataelan
      </span>
    )
  }
  
  // Stacked layout
  if (layout === 'stacked') {
    const iconSize = finalWidth * 0.6
    const fontSize = finalWidth * 0.16
    
    return (
      <div 
        className={cn('flex flex-col items-center justify-center gap-1', className)}
        style={{ width: finalWidth, height: finalHeight }}
      >
        {/* Icon */}
        <div 
          className="flex items-center justify-center rounded-lg font-bold"
          style={{ 
            width: iconSize, 
            height: iconSize,
            backgroundColor: getIconBackground(),
            color: getIconTextColor(),
            fontSize: `${iconSize * 0.5}px`
          }}
        >
          D
        </div>
        
        {/* Wordmark */}
        <span 
          className="font-bold tracking-tight text-center"
          style={{ 
            color: getTextColor(),
            fontSize: `${fontSize}px`,
            lineHeight: `${fontSize * 1.1}px`
          }}
        >
          Dataelan
        </span>
      </div>
    )
  }
  
  // Horizontal layout (default)
  const iconSize = finalHeight * 0.7
  const fontSize = finalHeight * 0.45
  const gap = finalHeight * 0.15
  
  return (
    <div 
      className={cn('flex items-center', className)}
      style={{ 
        height: finalHeight,
        gap: `${gap}px`
      }}
    >
      {/* Icon */}
      <div 
        className="flex items-center justify-center rounded-lg font-bold"
        style={{ 
          width: iconSize, 
          height: iconSize,
          backgroundColor: getIconBackground(),
          color: getIconTextColor(),
          fontSize: `${iconSize * 0.5}px`
        }}
      >
        D
      </div>
      
      {/* Wordmark */}
      <span 
        className="font-bold tracking-tight"
        style={{ 
          color: getTextColor(),
          fontSize: `${fontSize}px`
        }}
      >
        Dataelan
      </span>
    </div>
  )
}

// Convenience components for specific use cases
export function LogoHorizontal({ variant = 'primary', size = 'md', className }: Omit<LogoProps, 'layout'>) {
  return <Logo variant={variant} layout="horizontal" size={size} className={className} />
}

export function LogoStacked({ variant = 'primary', size = 'md', className }: Omit<LogoProps, 'layout'>) {
  return <Logo variant={variant} layout="stacked" size={size} className={className} />
}

export function LogoIcon({ variant = 'primary', size = 'md', className }: Omit<LogoProps, 'layout'>) {
  return <Logo variant={variant} layout="icon-only" size={size} className={className} />
}

export function LogoWordmark({ variant = 'primary', size = 'md', className }: Omit<LogoProps, 'layout'>) {
  return <Logo variant={variant} layout="wordmark-only" size={size} className={className} />
}

// Specific use case components
export function LogoNavigation() {
  return <LogoHorizontal variant="white" size="sm" />
}

export function LogoHeader() {
  return <LogoHorizontal variant="primary" size="md" />
}

export function LogoFooter() {
  return <LogoStacked variant="white" size="sm" />
}

export function LogoSidebar() {
  return <LogoStacked variant="white" size="md" />
}

export function LogoMobile() {
  return <LogoIcon variant="white" size="sm" />
}