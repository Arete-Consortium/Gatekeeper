import type { Metadata, Viewport } from 'next';
import { Footer, Navbar } from '@/components/layout';
import { Providers } from '@/components/Providers';
import { ErrorBoundaryWrapper } from '@/components/ErrorBoundaryWrapper';
import { Analytics } from '@/components/Analytics';
import { ConsentGatedVercelAnalytics } from '@/components/ConsentGatedVercelAnalytics';
import { CookieConsentBanner } from '@/components/CookieConsentBanner';
import { ServiceWorkerRegistration } from '@/components/ServiceWorkerRegistration';
import '@/styles/globals.css';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0e7490',
};

export const metadata: Metadata = {
  title: 'EVE Gatekeeper - Intel & Route Planning',
  description:
    'EVE Online route planning and intelligence tool. Find safe routes, analyze fittings, and track kill activity.',
  keywords: ['EVE Online', 'route planner', 'intel', 'zkillboard', 'navigation'],
  openGraph: {
    title: 'EVE Gatekeeper - Intel & Route Planning',
    description: 'Route planning, intel, and kill tracking for EVE Online pilots.',
    url: 'https://gatekeeper.aretedriver.dev',
    siteName: 'EVE Gatekeeper',
    type: 'website',
  },
  twitter: {
    card: 'summary',
    title: 'EVE Gatekeeper',
    description: 'Route planning, intel, and kill tracking for EVE Online pilots.',
  },
  icons: {
    icon: '/favicon.ico',
  },
  manifest: '/manifest.json',
  metadataBase: new URL('https://gatekeeper.aretedriver.dev'),
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Gatekeeper',
  },
  formatDetection: {
    telephone: false,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href={process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'} />
        <link rel="dns-prefetch" href={process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'} />
      </head>
      <body className="min-h-screen bg-background">
        <Providers>
          <ErrorBoundaryWrapper>
            <Navbar />
            <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
            <Footer />
          </ErrorBoundaryWrapper>
          <Analytics />
          <ConsentGatedVercelAnalytics />
          <CookieConsentBanner />
          <ServiceWorkerRegistration />
        </Providers>
      </body>
    </html>
  );
}
