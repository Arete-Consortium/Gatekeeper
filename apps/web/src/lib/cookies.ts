/**
 * Cookie consent utilities.
 *
 * Manages a JS-readable consent cookie (gk_consent) on the frontend domain.
 * Auth cookies (gk_session) are "strictly necessary" and exempt from consent.
 */

export interface CookieConsent {
  necessary: true; // Always true, can't be toggled
  analytics: boolean;
}

const CONSENT_KEY = 'gk_consent';

function parseCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function getConsent(): CookieConsent | null {
  const raw = parseCookie(CONSENT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CookieConsent;
  } catch {
    return null;
  }
}

export function setConsent(consent: CookieConsent): void {
  if (typeof document === 'undefined') return;
  const value = encodeURIComponent(JSON.stringify(consent));
  // 1 year, Lax, Secure
  document.cookie = `${CONSENT_KEY}=${value}; path=/; max-age=31536000; SameSite=Lax; Secure`;
}

export function hasConsented(): boolean {
  return getConsent() !== null;
}
