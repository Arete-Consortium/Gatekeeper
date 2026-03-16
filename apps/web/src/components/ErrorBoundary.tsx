'use client';

import React, { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Error Boundary that catches render errors, logs structured data,
 * and optionally reports to the backend error collection endpoint.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const timestamp = new Date().toISOString();

    // Structured console logging
    console.error('[ErrorBoundary]', {
      timestamp,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
    });

    // Fire-and-forget report to backend
    this.reportError(error, errorInfo, timestamp);
  }

  private reportError(error: Error, errorInfo: ErrorInfo, timestamp: string): void {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    try {
      fetch(`${apiUrl}/api/v1/errors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: error.message,
          stack: `${error.stack || ''}\n\nComponent Stack:${errorInfo.componentStack || ''}`,
          url: typeof window !== 'undefined' ? window.location.href : '',
          timestamp,
          user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
        }),
      }).catch(() => {
        // Silently swallow - don't let error reporting cause more errors
      });
    } catch {
      // Silently swallow
    }
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] gap-4 p-8">
          <div className="text-center max-w-md">
            <h2 className="text-xl font-semibold text-red-400 mb-2">Something went wrong</h2>
            <p className="text-gray-400 mb-4">
              An unexpected error occurred. This has been logged for investigation.
            </p>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <pre className="text-left text-xs text-red-300 bg-red-900/20 p-3 rounded mb-4 overflow-auto max-h-48">
                {this.state.error.message}
              </pre>
            )}
            <div className="flex items-center gap-3">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
              >
                Try Again
              </button>
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- class component can't use next/link */}
              <a
                href="/"
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
              >
                Go Home
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
