/**
 * Formatting utility functions for consistent data display
 */

/**
 * Format a number with thousands separators
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat().format(num);
}

/**
 * Format a date string to a more readable format
 * @param dateString ISO date string or any valid date string
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(date);
}

/**
 * Format a duration in seconds to a human-readable string
 * @param seconds Duration in seconds
 */
export function formatDuration(seconds: number): string {
  if (seconds < 0.01) {
    return `${Math.round(seconds * 1000)}ms`;
  }
  
  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)}ms`;
  }
  
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

/**
 * Format a cost value as currency
 * @param value Cost value
 * @param currency Currency code (default: USD)
 */
export function formatCost(value: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  }).format(value);
}

/**
 * Format a percentage value
 * @param value Percentage value (0-100)
 * @param decimals Number of decimal places
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}
