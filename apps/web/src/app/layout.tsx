import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';
import { Navbar } from '@/components/layout';
import { Providers } from '@/components/Providers';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'EVE Gatekeeper - Intel & Route Planning',
  description:
    'EVE Online route planning and intelligence tool. Find safe routes, analyze fittings, and track kill activity.',
  keywords: ['EVE Online', 'route planner', 'intel', 'zkillboard', 'navigation'],
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="min-h-screen bg-background">
        <NextIntlClientProvider messages={messages}>
          <Providers>
            <Navbar />
            <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
