'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { CookieConsentProvider } from '@/contexts/CookieConsentContext';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000, // 30 seconds
            gcTime: 10 * 60 * 1000, // 10 min garbage collection
            retry: 1,
            refetchOnWindowFocus: false,
            refetchOnReconnect: 'always',
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <CookieConsentProvider>
        <AuthProvider>{children}</AuthProvider>
      </CookieConsentProvider>
    </QueryClientProvider>
  );
}
