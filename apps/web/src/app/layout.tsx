import type { Metadata, Viewport } from 'next';
import { Analytics as VercelAnalytics } from '@vercel/analytics/next';
import { Navbar } from '@/components/layout';
import { Providers } from '@/components/Providers';
import { ErrorBoundaryWrapper } from '@/components/ErrorBoundaryWrapper';
import { Analytics } from '@/components/Analytics';
import '@/styles/globals.css';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: '#0f172a',
};

export const metadata: Metadata = {
  title: 'EVE Gatekeeper - Intel & Route Planning',
  description:
    'EVE Online route planning and intelligence tool. Find safe routes, analyze fittings, and track kill activity.',
  keywords: ['EVE Online', 'route planner', 'intel', 'zkillboard', 'navigation'],
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
          </ErrorBoundaryWrapper>
        </Providers>
        <Analytics />
        <VercelAnalytics />
      </body>
    </html>
  );
}
