'use client';

import { cn } from '@/lib/utils';
import { AlertCircle, RefreshCw, XCircle } from 'lucide-react';
import { Card } from './Card';
import { Button } from './Button';

interface ErrorMessageProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * The error title
   */
  title?: string;
  /**
   * The error message to display
   */
  message: string;
  /**
   * Variant affects styling
   */
  variant?: 'error' | 'warning';
  /**
   * Optional retry callback
   */
  onRetry?: () => void;
  /**
   * Optional dismiss callback
   */
  onDismiss?: () => void;
  /**
   * Is retry in progress
   */
  isRetrying?: boolean;
}

/**
 * User-friendly error message mappings
 */
const ERROR_MESSAGES: Record<string, string> = {
  'Failed to fetch': 'Unable to connect to the server. Please check your connection and try again.',
  'Network Error': 'Network connection lost. Please check your internet connection.',
  'NetworkError': 'Network connection lost. Please check your internet connection.',
  '401': 'Your session has expired. Please refresh the page.',
  '403': 'You do not have permission to access this resource.',
  '404': 'The requested resource was not found.',
  '500': 'An internal server error occurred. Please try again later.',
  '502': 'The server is temporarily unavailable. Please try again later.',
  '503': 'The service is currently unavailable. Please try again later.',
};

/**
 * Transform technical error messages to user-friendly ones
 */
export function getUserFriendlyError(error: unknown): string {
  if (error instanceof Error) {
    // Check for known error patterns
    for (const [pattern, friendlyMessage] of Object.entries(ERROR_MESSAGES)) {
      if (error.message.includes(pattern)) {
        return friendlyMessage;
      }
    }
    // Return original message if no pattern matches
    return error.message;
  }
  if (typeof error === 'string') {
    for (const [pattern, friendlyMessage] of Object.entries(ERROR_MESSAGES)) {
      if (error.includes(pattern)) {
        return friendlyMessage;
      }
    }
    return error;
  }
  return 'An unexpected error occurred. Please try again.';
}

export function ErrorMessage({
  title,
  message,
  variant = 'error',
  onRetry,
  onDismiss,
  isRetrying = false,
  className,
  ...props
}: ErrorMessageProps) {
  const Icon = variant === 'error' ? XCircle : AlertCircle;
  const colorClass = variant === 'error' ? 'text-risk-red' : 'text-risk-orange';
  const bgClass = variant === 'error' ? 'bg-risk-red/10' : 'bg-risk-orange/10';
  const borderClass = variant === 'error' ? 'border-risk-red' : 'border-risk-orange';

  return (
    <Card
      role="alert"
      aria-live="assertive"
      className={cn(borderClass, bgClass, className)}
      {...props}
    >
      <div className="flex items-start gap-3">
        <Icon className={cn('h-5 w-5 flex-shrink-0 mt-0.5', colorClass)} aria-hidden="true" />
        <div className="flex-1 min-w-0">
          {title && (
            <p className={cn('font-medium', colorClass)}>{title}</p>
          )}
          <p className={cn('text-sm', title ? 'opacity-80' : '', colorClass)}>
            {message}
          </p>
          {(onRetry || onDismiss) && (
            <div className="flex gap-2 mt-3">
              {onRetry && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={onRetry}
                  loading={isRetrying}
                  aria-label="Retry loading"
                >
                  <RefreshCw className="h-3 w-3 mr-1" aria-hidden="true" />
                  Retry
                </Button>
              )}
              {onDismiss && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onDismiss}
                  aria-label="Dismiss error"
                >
                  Dismiss
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
