import type { Metadata, Viewport } from 'next';
import { Footer, Navbar } from '@/components/layout';
import { Providers } from '@/components/Providers';
import { ErrorBoundaryWrapper } from '@/components/ErrorBoundaryWrapper';
import { Analytics } from '@/components/Analytics';
import { ConsentGatedVercelAnalytics } from '@/components/ConsentGatedVercelAnalytics';
import { SpeedInsights } from '@vercel/speed-insights/next';
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
  title: 'Gatekeeper - Intel & Route Planning',
  description:
    'Route planning and intelligence tool. Find safe routes, analyze fittings, and track kill activity.',
  keywords: ['route planner', 'intel', 'zkillboard', 'navigation', 'gatekeeper', 'new eden'],
  openGraph: {
    title: 'Gatekeeper - Intel & Route Planning',
    description: 'Route planning, intel, and kill tracking.',
    url: 'https://edengk.com',
    siteName: 'Gatekeeper',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Gatekeeper',
    description: 'Route planning, intel, and kill tracking.',
  },
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/manifest.json',
  metadataBase: new URL('https://edengk.com'),
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
          <SpeedInsights />
          <CookieConsentBanner />
          <ServiceWorkerRegistration />
        </Providers>
      </body>
    </html>
  );
}
