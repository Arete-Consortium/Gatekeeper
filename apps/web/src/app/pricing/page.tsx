'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { GatekeeperAPI } from '@/lib/api';
import { Card, Button, Badge } from '@/components/ui';
import { Check, Loader2, Zap, Shield, Star } from 'lucide-react';

const FEATURE_KEYS = [
  'feature1', 'feature2', 'feature3', 'feature4',
  'feature5', 'feature6', 'feature7', 'feature8',
] as const;

export default function PricingPage() {
  const t = useTranslations('pricing');
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
          {t('title')}
        </h1>
        <p className="text-text-secondary mt-2 max-w-2xl mx-auto">
          {t('subtitle')}
        </p>
      </div>

      {/* Pricing Cards */}
      <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
        {/* Monthly Plan */}
        <Card className="relative flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-text">{t('monthly')}</h2>
          </div>

          <div className="mb-6">
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-bold text-text">
                ${monthlyPlan?.price ?? '2.99'}
              </span>
              <span className="text-text-secondary">{t('perMonth')}</span>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              {t('billedMonthly')}
            </p>
          </div>

          <ul className="space-y-3 mb-8 flex-1">
            {FEATURE_KEYS.map((key) => (
              <li key={key} className="flex items-start gap-2 text-sm text-text-secondary">
                <Check className="h-4 w-4 text-risk-green mt-0.5 shrink-0" />
                {t(key)}
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
            {t('subscribeMonthly')}
          </Button>
        </Card>

        {/* Annual Plan */}
        <Card className="relative flex flex-col border-primary/50">
          <Badge variant="info" className="absolute -top-3 right-4">
            {t('save', { percent: savingsPercent })}
          </Badge>

          <div className="flex items-center gap-2 mb-4">
            <Star className="h-5 w-5 text-risk-yellow" />
            <h2 className="text-lg font-semibold text-text">{t('annual')}</h2>
          </div>

          <div className="mb-6">
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-bold text-text">
                ${annualPlan?.price ?? '29.99'}
              </span>
              <span className="text-text-secondary">{t('perYear')}</span>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              {t('justPerMonth', { price: annualMonthly })}
            </p>
          </div>

          <ul className="space-y-3 mb-8 flex-1">
            {FEATURE_KEYS.map((key) => (
              <li key={key} className="flex items-start gap-2 text-sm text-text-secondary">
                <Check className="h-4 w-4 text-risk-green mt-0.5 shrink-0" />
                {t(key)}
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
            {t('subscribeAnnually')}
          </Button>
        </Card>
      </div>

      {/* Error */}
      {checkout.isError && (
        <div className="text-center text-risk-red text-sm">
          {t('error')}
        </div>
      )}

      {/* FAQ */}
      <div className="max-w-2xl mx-auto space-y-4">
        <h2 className="text-xl font-semibold text-text text-center">
          {t('faq')}
        </h2>

        {[
          { q: t('cancelQ'), a: t('cancelA') },
          { q: t('paymentQ'), a: t('paymentA') },
          { q: t('trialQ'), a: t('trialA') },
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
