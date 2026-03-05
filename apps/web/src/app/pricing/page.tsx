'use client';

import { useAuth } from '@/contexts/AuthContext';
import { Card, CardTitle, CardDescription, Button } from '@/components/ui';
import { Check, Zap } from 'lucide-react';
import Link from 'next/link';

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
  const { isAuthenticated, isPro, token } = useAuth();

  const handleUpgrade = async () => {
    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }

    const apiUrl =
      localStorage.getItem('gatekeeper_api_url') ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';

    const currentUrl = window.location.origin;

    const response = await fetch(`${apiUrl}/api/v1/billing/create-checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        success_url: `${currentUrl}/account?checkout=success`,
        cancel_url: `${currentUrl}/pricing?checkout=cancelled`,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      window.location.href = data.checkout_url;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center py-8">
        <h1 className="text-3xl font-bold text-text">Choose Your Plan</h1>
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
            $4.99<span className="text-sm font-normal text-text-secondary">/mo</span>
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
            <Button className="glow-primary w-full" onClick={handleUpgrade}>
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
