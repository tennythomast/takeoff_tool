// Logo imports - organized by layout and variant
// When you add SVG files, uncomment and update these paths

// Horizontal logos
// import DataelanLogoHorizontalPrimary from '@/assets/brand/logos/dataelan-logo-horizontal-primary.svg'
// import DataelanLogoHorizontalWhite from '@/assets/brand/logos/dataelan-logo-horizontal-white.svg'
// import DataelanLogoHorizontalDark from '@/assets/brand/logos/dataelan-logo-horizontal-dark.svg'

// Stacked logos  
// import DataelanLogoStackedPrimary from '@/assets/brand/logos/dataelan-logo-stacked-primary.svg'
// import DataelanLogoStackedWhite from '@/assets/brand/logos/dataelan-logo-stacked-white.svg'
// import DataelanLogoStackedDark from '@/assets/brand/logos/dataelan-logo-stacked-dark.svg'

// Icon only
// import DataelanIconPrimary from '@/assets/brand/logos/dataelan-icon-primary.svg'
// import DataelanIconWhite from '@/assets/brand/logos/dataelan-icon-white.svg'
// import DataelanIconDark from '@/assets/brand/logos/dataelan-icon-dark.svg'

// Wordmark only
// import DataelanWordmarkPrimary from '@/assets/brand/logos/dataelan-wordmark-primary.svg'
// import DataelanWordmarkWhite from '@/assets/brand/logos/dataelan-wordmark-white.svg'
// import DataelanWordmarkDark from '@/assets/brand/logos/dataelan-wordmark-dark.svg'

export const BrandAssets = {
    logos: {
      horizontal: {
        primary: '/assets/brand/logos/dataelan-logo-primary-light.svg',
        white: '/assets/brand/logos/dataelan-logo-white.svg',
        dark: '/assets/brand/logos/dataelan-logo-dark.svg',
      },
      stacked: {
        primary: '/assets/brand/logos/stacked/dataelan-logo-stacked-primary-light.svg',
        white: '/assets/brand/logos/stacked/dataelan-logo-stacked-white.svg',
        dark: '/assets/brand/logos/stacked/dataelan-logo-stacked-dark.svg',
      },
      icon: {
        primary: '/assets/brand/logos/icons/dataelan-icon-primary.svg',
        white: '/assets/brand/logos/icons/dataelan-icon-white.svg',
        dark: '/assets/brand/logos/icons/dataelan-icon-dark.svg',
      },
      wordmark: {
        primary: '/assets/brand/logos/wordmark/dataelan-wordmark-primary.svg',
        white: '/assets/brand/logos/wordmark/dataelan-wordmark-white.svg',
        dark: '/assets/brand/logos/wordmark/dataelan-wordmark-dark.svg',
      }
    },
    
    // Icon variations for different sizes
    icons: {
      favicon: '/brand/favicons/favicon.ico',
      '16x16': '/brand/favicons/favicon-16x16.png',
      '32x32': '/brand/favicons/favicon-32x32.png',
      '192x192': '/brand/favicons/android-chrome-192x192.png',
      '512x512': '/brand/favicons/android-chrome-512x512.png',
      apple: '/brand/favicons/apple-touch-icon.png',
    },
    
    // Social media and Open Graph images
    social: {
      ogDefault: '/brand/og-images/dataelan-og-default.png',
      ogFeature: '/brand/og-images/dataelan-og-feature.png',
      twitterCard: '/brand/social/dataelan-twitter-card.png',
      linkedinBanner: '/brand/social/dataelan-linkedin-banner.png',
    },
    
    // Brand patterns and backgrounds
    patterns: {
      heroBackground: '/assets/brand/patterns/BrandPattern01.svg',
      dotPattern: '/assets/brand/patterns/BrandPattern02.svg',
      gridPattern: '/assets/brand/patterns/BrandPattern03.svg',
    }
  } as const
  
  export type LogoLayout = keyof typeof BrandAssets.logos
  export type LogoVariant = keyof typeof BrandAssets.logos.horizontal
  export type IconSize = keyof typeof BrandAssets.icons
  
  // Helper functions to get specific logo paths
  export function getLogoPath(layout: LogoLayout, variant: LogoVariant): string {
    return BrandAssets.logos[layout][variant]
  }
  
  export function getIconPath(size: IconSize): string {
    return BrandAssets.icons[size]
  }
  
  // Usage examples and recommendations
  export const LogoUsageGuide = {
    horizontal: {
      bestFor: ['Navigation bars', 'Website headers', 'Email signatures', 'Business cards'],
      minWidth: 100,
      maxWidth: 300,
      aspectRatio: '3.5:1'
    },
    stacked: {
      bestFor: ['Mobile apps', 'Square spaces', 'Social media profiles', 'App icons'],
      minWidth: 60,
      maxWidth: 200,
      aspectRatio: '4:5'
    },
    icon: {
      bestFor: ['Favicons', 'App icons', 'Small spaces', 'Loading indicators'],
      minWidth: 16,
      maxWidth: 128,
      aspectRatio: '1:1'
    },
    wordmark: {
      bestFor: ['Text-heavy layouts', 'Minimal designs', 'Secondary usage'],
      minWidth: 80,
      maxWidth: 200,
      aspectRatio: '5:1'
    }
  } as const