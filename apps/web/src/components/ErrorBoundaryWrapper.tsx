'use client';

import { type ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';

/**
 * Client component wrapper for ErrorBoundary.
 * Needed because layout.tsx is a server component and ErrorBoundary
 * is a class component that requires client-side rendering.
 */
export function ErrorBoundaryWrapper({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}
