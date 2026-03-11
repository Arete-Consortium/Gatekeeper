'use client';

import { Analytics as VercelAnalytics } from '@vercel/analytics/next';
import { useCookieConsent } from '@/contexts/CookieConsentContext';

/**
 * Renders Vercel Analytics only when the user has consented to analytics cookies.
 */
export function ConsentGatedVercelAnalytics() {
  const { consent } = useCookieConsent();
  if (!consent?.analytics) return null;
  return <VercelAnalytics />;
}
