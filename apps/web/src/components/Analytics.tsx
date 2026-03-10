'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';

/**
 * Lightweight page view tracker. Sends pageview events to the backend
 * analytics endpoint on route changes. Fire-and-forget, never blocks.
 */
export function Analytics() {
  const pathname = usePathname();
  const prevPathname = useRef<string | null>(null);

  useEffect(() => {
    // Skip duplicate fires for same path
    if (pathname === prevPathname.current) return;
    prevPathname.current = pathname;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    try {
      fetch(`${apiUrl}/api/v1/analytics/pageview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: pathname,
          referrer: typeof document !== 'undefined' ? document.referrer : '',
          timestamp: new Date().toISOString(),
        }),
      }).catch(() => {
        // Silently swallow - analytics should never impact UX
      });
    } catch {
      // Silently swallow
    }
  }, [pathname]);

  return null;
}
