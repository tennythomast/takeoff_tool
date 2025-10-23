import type { NextConfig } from "next";

// Log environment variables during build for debugging
console.log('Next.js config loaded with environment:', {
  NODE_ENV: process.env.NODE_ENV,
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_INTERNAL_API_URL: process.env.NEXT_PUBLIC_INTERNAL_API_URL,
  NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  NEXT_DEBUG: process.env.NEXT_DEBUG
});

const nextConfig: NextConfig = {
  output: 'standalone',
  
  // Configure API routes proxy
  async rewrites() {
    const isDev = process.env.NODE_ENV !== 'production';
    // For Docker: use NEXT_PUBLIC_INTERNAL_API_URL for container-to-container communication
    // For local dev: use NEXT_PUBLIC_API_URL for direct browser-to-backend communication
    const apiUrl = process.env.NEXT_PUBLIC_INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    console.log(`Configuring rewrites for ${isDev ? 'development' : 'production'} with API URL: ${apiUrl}`);

    return [
      // API proxy - forward API requests to backend
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
      // Remove the problematic fallback rewrite
      // Next.js handles client-side routing automatically
    ];
  },
  
  // Configure headers for security and CORS
  async headers() {
    return [
      // API routes CORS headers
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' },
        ],
      },
      // Security headers for all routes
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
        ],
      },
    ];
  },
  
  // Enable runtime configuration
  publicRuntimeConfig: {
    apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
    basePath: process.env.NEXT_PUBLIC_BASE_PATH || '',
  },
  
  // Disable X-Powered-By header
  poweredByHeader: false,
  
  // Development settings
  eslint: {
    ignoreDuringBuilds: process.env.NODE_ENV === 'production',
  },
  
  typescript: {
    ignoreBuildErrors: process.env.NODE_ENV === 'production',
  },
  
  // Enable React strict mode in development
  reactStrictMode: process.env.NODE_ENV !== 'production',
  
  // Enable webpack 5
  webpack: (config, { isServer }) => {
    return config;
  },
  
  // Configure images
  images: {
    domains: ['localhost'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
  
  // Configure logging
  logging: {
    fetches: {
      fullUrl: true,
    },
  },
};

export default nextConfig;