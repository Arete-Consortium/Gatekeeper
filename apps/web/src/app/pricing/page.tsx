'use client';

import { Suspense, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useSearchParams } from 'next/navigation';
import { Card, CardTitle, CardDescription, Button } from '@/components/ui';
import { Check, X, Zap } from 'lucide-react';
import Link from 'next/link';
import { GatekeeperAPI } from '@/lib/api';

const FREE_FEATURES = [
  'Route planning (all profiles)',
  'Universe map & visualization',
  'System risk scores',
  'Fitting analyzer',
  'Intel feed',
  '100 requests/min',
];

const PRO_FEATURES = [
  'Everything in Free',
  'AI route analysis & danger assessment',
  'Webhook alerts (Discord & Slack)',
  'Advanced kill stats & bulk queries',
  'Route sharing & collaboration',
  '300 requests/min',
  'Priority support',
];

export default function PricingPage() {
  return (
    <Suspense fallback={<div className="text-center py-8 text-text-secondary">Loading...</div>}>
      <PricingContent />
    </Suspense>
  );
}

function PricingContent() {
  const { isAuthenticated, isPro, token } = useAuth();
  const searchParams = useSearchParams();
  const checkoutStatus = searchParams.get('checkout');
  const [cancelDismissed, setCancelDismissed] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [upgrading, setUpgrading] = useState(false);

  const handleUpgrade = async () => {
    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }

    setCheckoutError(null);
    setUpgrading(true);
    try {
      const currentUrl = window.location.origin;
      const { checkout_url } = await GatekeeperAPI.createCheckoutSession(
        `${currentUrl}/account?checkout=success`,
        `${currentUrl}/pricing?checkout=cancelled`
      );
      window.location.href = checkout_url;
    } catch {
      setCheckoutError('Unable to start checkout. Please try again.');
    } finally {
      setUpgrading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Checkout cancelled notice */}
      {checkoutStatus === 'cancelled' && !cancelDismissed && (
        <Card className="border-risk-orange/40 bg-risk-orange/10 py-4 px-6 flex items-center justify-between">
          <p className="text-risk-orange text-sm font-medium">
            Checkout was cancelled. No charges were made. You can upgrade anytime.
          </p>
          <button
            onClick={() => setCancelDismissed(true)}
            className="text-risk-orange hover:text-text ml-4 flex-shrink-0"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </Card>
      )}

      {checkoutError && (
        <Card className="border-risk-red/40 bg-risk-red/10 py-4 px-6 flex items-center justify-between">
          <p className="text-risk-red text-sm font-medium">{checkoutError}</p>
          <button onClick={() => setCheckoutError(null)} className="text-risk-red hover:text-text ml-4 flex-shrink-0" aria-label="Dismiss">
            <X className="h-4 w-4" />
          </button>
        </Card>
      )}

      <div className="text-center py-8">
        <h1 className="text-3xl font-bold text-text">Navigate New Eden Safely</h1>
        <p className="text-text-secondary mt-2">
          Free for core navigation. Pro for the full tactical advantage.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Free Tier */}
        <Card className="p-6">
          <CardTitle className="text-xl mb-1">Free</CardTitle>
          <div className="text-3xl font-bold text-text mb-1">
            $0<span className="text-sm font-normal text-text-secondary">/mo</span>
          </div>
          <CardDescription className="mb-6">
            Full route planning and intel for all pilots.
          </CardDescription>
          <ul className="space-y-3 mb-8">
            {FREE_FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-2 text-sm text-text-secondary">
                <Check className="h-4 w-4 text-risk-green mt-0.5 flex-shrink-0" />
                {feature}
              </li>
            ))}
          </ul>
          {!isAuthenticated ? (
            <Link href="/login">
              <Button variant="secondary" className="w-full">
                Sign in to get started
              </Button>
            </Link>
          ) : !isPro ? (
            <Button variant="secondary" className="w-full" disabled>
              Current Plan
            </Button>
          ) : null}
        </Card>

        {/* Pro Tier */}
        <Card className="p-6 border-primary/40 relative">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-xs font-bold px-3 py-1 rounded-full">
            RECOMMENDED
          </div>
          <CardTitle className="text-xl mb-1 flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Pro
          </CardTitle>
          <div className="text-3xl font-bold text-text mb-1">
            $3<span className="text-sm font-normal text-text-secondary">/mo</span>
          </div>
          <CardDescription className="mb-6">
            Full tactical suite for serious pilots.
          </CardDescription>
          <ul className="space-y-3 mb-8">
            {PRO_FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-2 text-sm text-text">
                <Check className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                {feature}
              </li>
            ))}
          </ul>
          {isPro ? (
            <Button className="w-full" disabled>
              Current Plan
            </Button>
          ) : (
            <Button className="glow-primary w-full" onClick={handleUpgrade} loading={upgrading}>
              <Zap className="mr-2 h-4 w-4" />
              {isAuthenticated ? 'Upgrade to Pro' : 'Sign in & Upgrade'}
            </Button>
          )}
        </Card>
      </div>

      <p className="text-center text-xs text-text-secondary">
        Cancel anytime. Managed via Stripe. No ISK required.
      </p>
    </div>
  );
}
