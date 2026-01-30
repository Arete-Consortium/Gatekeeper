/**
 * Utility functions for EVE Gatekeeper Web
 */
import { clsx, type ClassValue } from 'clsx';

/**
 * Merge class names with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Format a timestamp as relative time (e.g., "5m ago")
 */
export function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

/**
 * Format ISK value with abbreviations
 */
export function formatIsk(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B ISK`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M ISK`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(2)}K ISK`;
  }
  return `${value.toFixed(0)} ISK`;
}

/**
 * Get security status CSS class
 */
export function getSecurityClass(security: number): string {
  if (security >= 0.5) return 'text-high-sec';
  if (security > 0) return 'text-low-sec';
  return 'text-null-sec';
}

/**
 * Get security status label
 */
export function getSecurityLabel(category: string): string {
  switch (category) {
    case 'high_sec':
      return 'High Sec';
    case 'low_sec':
      return 'Low Sec';
    case 'null_sec':
      return 'Null Sec';
    default:
      return category;
  }
}

/**
 * Get risk color class
 */
export function getRiskColorClass(
  riskColor: 'green' | 'yellow' | 'orange' | 'red'
): string {
  switch (riskColor) {
    case 'green':
      return 'text-risk-green';
    case 'yellow':
      return 'text-risk-yellow';
    case 'orange':
      return 'text-risk-orange';
    case 'red':
      return 'text-risk-red';
    default:
      return 'text-text-secondary';
  }
}

/**
 * Get risk background color class
 */
export function getRiskBgClass(
  riskColor: 'green' | 'yellow' | 'orange' | 'red'
): string {
  switch (riskColor) {
    case 'green':
      return 'bg-risk-green';
    case 'yellow':
      return 'bg-risk-yellow';
    case 'orange':
      return 'bg-risk-orange';
    case 'red':
      return 'bg-risk-red';
    default:
      return 'bg-text-secondary';
  }
}

/**
 * Route profile display info
 */
export const ROUTE_PROFILES = {
  shortest: {
    label: 'Shortest',
    description: 'Minimum jumps, ignores danger',
    color: 'text-risk-yellow',
    borderColor: 'border-risk-yellow',
  },
  safer: {
    label: 'Safer',
    description: 'Balanced route, avoids high-risk systems',
    color: 'text-risk-green',
    borderColor: 'border-risk-green',
  },
  paranoid: {
    label: 'Paranoid',
    description: 'Maximum safety, longest route',
    color: 'text-primary',
    borderColor: 'border-primary',
  },
} as const;

/**
 * Debounce function for search inputs
 */
export function debounce<T extends (...args: Parameters<T>) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}
