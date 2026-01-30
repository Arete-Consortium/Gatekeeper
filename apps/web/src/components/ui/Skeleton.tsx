'use client';

import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Width of the skeleton. Can be Tailwind class or CSS value.
   */
  width?: string;
  /**
   * Height of the skeleton. Can be Tailwind class or CSS value.
   */
  height?: string;
  /**
   * Shape variant
   */
  variant?: 'rectangular' | 'circular' | 'text';
}

export function Skeleton({
  width,
  height,
  variant = 'rectangular',
  className,
  ...props
}: SkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading..."
      className={cn(
        'animate-pulse bg-card-hover',
        variant === 'circular' && 'rounded-full',
        variant === 'rectangular' && 'rounded-lg',
        variant === 'text' && 'rounded h-4',
        className
      )}
      style={{
        width: width,
        height: height,
      }}
      {...props}
    />
  );
}

interface SkeletonCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Number of text lines to show
   */
  lines?: number;
  /**
   * Show a header area
   */
  showHeader?: boolean;
}

export function SkeletonCard({
  lines = 2,
  showHeader = true,
  className,
  ...props
}: SkeletonCardProps) {
  return (
    <div
      role="status"
      aria-label="Loading content..."
      className={cn(
        'bg-card rounded-lg border border-border p-4 space-y-3',
        className
      )}
      {...props}
    >
      {showHeader && (
        <Skeleton variant="text" className="h-5 w-1/3" />
      )}
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          className={cn('h-4', i === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  );
}

interface SkeletonTableProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Number of rows to show
   */
  rows?: number;
  /**
   * Number of columns to show
   */
  columns?: number;
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  className,
  ...props
}: SkeletonTableProps) {
  return (
    <div
      role="status"
      aria-label="Loading table..."
      className={cn(
        'border border-border rounded-lg overflow-hidden',
        className
      )}
      {...props}
    >
      {/* Header */}
      <div className="grid gap-4 px-4 py-3 bg-card" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} variant="text" className="h-4" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="grid gap-4 px-4 py-3 border-t border-border"
          style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              variant="text"
              className="h-4"
            />
          ))}
        </div>
      ))}
    </div>
  );
}
