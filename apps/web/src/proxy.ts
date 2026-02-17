import { NextRequest, NextResponse } from 'next/server';
import { locales, defaultLocale, type Locale } from '@/i18n/config';

const LOCALE_COOKIE = 'locale';

/**
 * Parse the Accept-Language header and return the best matching locale.
 * Example header: "ja,en-US;q=0.9,en;q=0.8,de;q=0.7"
 */
function getPreferredLocale(acceptLanguage: string | null): Locale {
  if (!acceptLanguage) return defaultLocale;

  const preferences = acceptLanguage
    .split(',')
    .map((part) => {
      const [lang, q] = part.trim().split(';q=');
      return { lang: lang.trim().toLowerCase(), quality: q ? parseFloat(q) : 1 };
    })
    .sort((a, b) => b.quality - a.quality);

  for (const { lang } of preferences) {
    // Exact match (e.g., "ja", "de")
    const exact = locales.find((l) => l === lang);
    if (exact) return exact;

    // Prefix match (e.g., "en-US" → "en", "zh-CN" → "zh")
    const prefix = lang.split('-')[0];
    const prefixMatch = locales.find((l) => l === prefix);
    if (prefixMatch) return prefixMatch;
  }

  return defaultLocale;
}

export function proxy(request: NextRequest) {
  const { cookies } = request;
  const existingLocale = cookies.get(LOCALE_COOKIE)?.value;

  // If a valid locale cookie already exists, do nothing
  if (existingLocale && locales.includes(existingLocale as Locale)) {
    return NextResponse.next();
  }

  // Detect preferred locale from Accept-Language header
  const acceptLanguage = request.headers.get('accept-language');
  const preferredLocale = getPreferredLocale(acceptLanguage);

  // Set the locale cookie so the server-side request config picks it up
  const response = NextResponse.next();
  response.cookies.set(LOCALE_COOKIE, preferredLocale, {
    path: '/',
    maxAge: 60 * 60 * 24 * 365, // 1 year
    sameSite: 'lax',
  });

  return response;
}

export const config = {
  // Run on all pages, skip static assets and API routes
  matcher: ['/((?!_next|api|favicon.ico|.*\\..*).*)'],
};
