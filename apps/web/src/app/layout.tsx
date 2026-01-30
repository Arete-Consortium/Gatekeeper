import type { Metadata } from 'next';
import { Navbar } from '@/components/layout';
import { Providers } from '@/components/Providers';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'EVE Gatekeeper - Intel & Route Planning',
  description:
    'EVE Online route planning and intelligence tool. Find safe routes, analyze fittings, and track kill activity.',
  keywords: ['EVE Online', 'route planner', 'intel', 'zkillboard', 'navigation'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background">
        <Providers>
          <Navbar />
          <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
