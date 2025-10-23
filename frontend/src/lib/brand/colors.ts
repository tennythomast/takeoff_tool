export const DataelanColors = {
    // Primary brand colors (exact hex values from your palette)
    claySignal: '#A76052',
    obsidian: '#192026', 
    skySync: '#98C0D9',
    deepSky: '#3D5B81',
    softGraph: '#E0E1E1',
    
    // Semantic color mappings for easy use
    primary: '#A76052',      // Clay Signal - PRIMARY BRAND
    secondary: '#3D5B81',    // Deep Sky
    accent: '#98C0D9',       // Sky Sync
    background: '#192026',   // Obsidian
    text: '#E0E1E1',        // Soft Graph
    
    // State colors
    success: '#98C0D9',     // Sky Sync for success states
    warning: '#A76052',     // Clay Signal for warnings
    error: '#DC2626',       // Standard red for errors
    info: '#3D5B81',        // Deep Sky for info
  } as const
  
  export type DataelanColor = keyof typeof DataelanColors