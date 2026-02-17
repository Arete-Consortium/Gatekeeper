'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Badge } from '@/components/ui';
import { Check, Loader2, Zap, Shield, Star } from 'lucide-react';

const FEATURES = [
  'Risk-aware route planning',
  'Real-time kill feed & alerts',
  'Ship fitting analysis',
  'Jump bridge & Thera routing',
  'Discord & Slack webhooks',
  'Multi-character support',
  'AI-powered intel analysis',
  'Priority support',
];

export default function PricingPage() {
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  const { data: plansData, isLoading } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => GatekeeperAPI.getPlans(),
  });

  const checkout = useMutation({
    mutationFn: async (plan: string) => {
      // TODO: Replace with actual character data from auth
      const result = await GatekeeperAPI.createCheckout(0, 'Capsuleer', plan);
      return result;
    },
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
  });

  const handleSubscribe = (planId: string) => {
    setSelectedPlan(planId);
    checkout.mutate(planId);
  };

  const monthlyPlan = plansData?.plans.find((p) => p.id === 'monthly');
  const annualPlan = plansData?.plans.find((p) => p.id === 'annual');

  const annualMonthly = annualPlan ? (annualPlan.price / 12).toFixed(2) : '2.50';
  const savingsPercent = monthlyPlan && annualPlan
    ? Math.round((1 - annualPlan.price / (monthlyPlan.price * 12)) * 100)
    : 16;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-text">
          Upgrade to EVE Gatekeeper Pro
        </h1>
        <p className="text-text-secondary mt-2 max-w-2xl mx-auto">
          Get full access to all premium intel and navigation features.
          Stay ahead of threats and fly smarter.
        </p>
      </div>

      {/* Pricing Cards */}
      <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
        {/* Monthly Plan */}
        <Card className="relative flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-text">Monthly</h2>
          </div>

          <div className="mb-6">
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-bold text-text">
                ${monthlyPlan?.price ?? '2.99'}
              </span>
              <span className="text-text-secondary">/month</span>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              Billed monthly. Cancel anytime.
            </p>
          </div>

          <ul className="space-y-3 mb-8 flex-1">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-2 text-sm text-text-secondary">
                <Check className="h-4 w-4 text-risk-green mt-0.5 shrink-0" />
                {feature}
              </li>
            ))}
          </ul>

          <Button
            variant="secondary"
            size="lg"
            className="w-full"
            loading={checkout.isPending && selectedPlan === 'monthly'}
            disabled={checkout.isPending || isLoading}
            onClick={() => handleSubscribe('monthly')}
          >
            Subscribe Monthly
          </Button>
        </Card>

        {/* Annual Plan */}
        <Card className="relative flex flex-col border-primary/50">
          <Badge variant="info" className="absolute -top-3 right-4">
            Save {savingsPercent}%
          </Badge>

          <div className="flex items-center gap-2 mb-4">
            <Star className="h-5 w-5 text-risk-yellow" />
            <h2 className="text-lg font-semibold text-text">Annual</h2>
          </div>

          <div className="mb-6">
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-bold text-text">
                ${annualPlan?.price ?? '29.99'}
              </span>
              <span className="text-text-secondary">/year</span>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              Just ${annualMonthly}/month. Best value.
            </p>
          </div>

          <ul className="space-y-3 mb-8 flex-1">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-2 text-sm text-text-secondary">
                <Check className="h-4 w-4 text-risk-green mt-0.5 shrink-0" />
                {feature}
              </li>
            ))}
          </ul>

          <Button
            variant="primary"
            size="lg"
            className="w-full"
            loading={checkout.isPending && selectedPlan === 'annual'}
            disabled={checkout.isPending || isLoading}
            onClick={() => handleSubscribe('annual')}
          >
            <Zap className="mr-2 h-4 w-4" />
            Subscribe Annually
          </Button>
        </Card>
      </div>

      {/* Error */}
      {checkout.isError && (
        <div className="text-center text-risk-red text-sm">
          Something went wrong. Please try again or contact support.
        </div>
      )}

      {/* FAQ */}
      <div className="max-w-2xl mx-auto space-y-4">
        <h2 className="text-xl font-semibold text-text text-center">
          Frequently Asked Questions
        </h2>

        {[
          {
            q: 'Can I cancel anytime?',
            a: 'Yes. Cancel through the subscription management portal and you\'ll keep access until the end of your billing period.',
          },
          {
            q: 'What payment methods are accepted?',
            a: 'We accept all major credit cards, debit cards, Apple Pay, and Google Pay through our secure Stripe payment processing.',
          },
          {
            q: 'Is there a free trial?',
            a: 'The base features are free. Subscribe to unlock premium intel analysis, AI-powered routing, and priority support.',
          },
        ].map(({ q, a }) => (
          <Card key={q}>
            <h3 className="font-medium text-text">{q}</h3>
            <p className="text-sm text-text-secondary mt-1">{a}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
