'use client';

import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { CookieConsent } from '@/lib/cookies';
import { getConsent, setConsent } from '@/lib/cookies';

interface CookieConsentContextValue {
  consent: CookieConsent | null;
  hasConsented: boolean;
  acceptAll: () => void;
  acceptNecessaryOnly: () => void;
}

const CookieConsentContext = createContext<CookieConsentContextValue | null>(null);

export function CookieConsentProvider({ children }: { children: React.ReactNode }) {
  const [consent, setConsentState] = useState<CookieConsent | null>(() => getConsent());

  const acceptAll = useCallback(() => {
    const c: CookieConsent = { necessary: true, analytics: true };
    setConsent(c);
    setConsentState(c);
  }, []);

  const acceptNecessaryOnly = useCallback(() => {
    const c: CookieConsent = { necessary: true, analytics: false };
    setConsent(c);
    setConsentState(c);
  }, []);

  const value = useMemo<CookieConsentContextValue>(
    () => ({
      consent,
      hasConsented: consent !== null,
      acceptAll,
      acceptNecessaryOnly,
    }),
    [consent, acceptAll, acceptNecessaryOnly]
  );

  return (
    <CookieConsentContext.Provider value={value}>
      {children}
    </CookieConsentContext.Provider>
  );
}

export function useCookieConsent(): CookieConsentContextValue {
  const ctx = useContext(CookieConsentContext);
  if (!ctx) {
    throw new Error('useCookieConsent must be used within a CookieConsentProvider');
  }
  return ctx;
}
