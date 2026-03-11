'use client';

import { useCookieConsent } from '@/contexts/CookieConsentContext';

export function CookieConsentBanner() {
  const { hasConsented, acceptAll, acceptNecessaryOnly } = useCookieConsent();

  if (hasConsented) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 p-4 bg-surface border-t border-border">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center gap-4">
        <p className="text-sm text-text-secondary flex-1">
          We use cookies for authentication and, with your consent, analytics to improve your
          experience. Auth cookies are strictly necessary and always active.
        </p>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={acceptNecessaryOnly}
            className="px-4 py-2 text-sm rounded border border-border text-text-secondary hover:bg-surface-hover transition-colors"
          >
            Necessary Only
          </button>
          <button
            onClick={acceptAll}
            className="px-4 py-2 text-sm rounded bg-primary text-white hover:bg-primary/90 transition-colors"
          >
            Accept All
          </button>
        </div>
      </div>
    </div>
  );
}
