'use client';

import { cn } from '@/lib/utils';

interface SecurityBadgeProps {
  security: number;
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function SecurityBadge({
  security,
  showValue = true,
  size = 'md',
}: SecurityBadgeProps) {
  // Handle undefined/null security values
  const sec = security ?? 0;

  const getSecurityColor = (s: number): string => {
    if (s >= 0.5) return 'text-high-sec';
    if (s > 0) return 'text-low-sec';
    return 'text-null-sec';
  };

  const getSecurityBg = (s: number): string => {
    if (s >= 0.5) return 'bg-high-sec/20 border-high-sec/30';
    if (s > 0) return 'bg-low-sec/20 border-low-sec/30';
    return 'bg-null-sec/20 border-null-sec/30';
  };

  const sizes = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-0.5 text-sm',
    lg: 'px-2.5 py-1 text-base',
  };

  const displayValue = sec.toFixed(1);

  return (
    <span
      className={cn(
        'inline-flex items-center font-mono font-semibold rounded border',
        getSecurityColor(sec),
        getSecurityBg(sec),
        sizes[size]
      )}
    >
      {showValue ? displayValue : sec >= 0.5 ? 'H' : sec > 0 ? 'L' : 'N'}
    </span>
  );
}
