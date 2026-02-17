'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { GatekeeperAPI } from '@/lib/api';
import { Card, CardTitle, CardDescription, Button, Input, Badge } from '@/components/ui';
import { Settings, CheckCircle, AlertCircle, Loader2, RefreshCw, CreditCard, ExternalLink } from 'lucide-react';
import { LanguageSwitcher } from '@/components/layout';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const tc = useTranslations('common');
  const [apiUrl, setApiUrl] = useState('');
  const [savedUrl, setSavedUrl] = useState('');

  useEffect(() => {
    const url = GatekeeperAPI.getBaseUrl();
    setApiUrl(url);
    setSavedUrl(url);
  }, []);

  const testConnection = useMutation({
    mutationFn: async (url: string) => {
      const originalUrl = GatekeeperAPI.getBaseUrl();
      GatekeeperAPI.setBaseUrl(url);
      try {
        const result = await GatekeeperAPI.testConnection();
        if (!result) {
          GatekeeperAPI.setBaseUrl(originalUrl);
          throw new Error('Connection failed');
        }
        return result;
      } catch (error) {
        GatekeeperAPI.setBaseUrl(originalUrl);
        throw error;
      }
    },
  });

  const handleSave = () => {
    GatekeeperAPI.setBaseUrl(apiUrl);
    setSavedUrl(apiUrl);
    testConnection.reset();
  };

  const handleTest = () => {
    testConnection.mutate(apiUrl);
  };

  const handleReset = () => {
    const defaultUrl = 'http://localhost:8000';
    setApiUrl(defaultUrl);
    GatekeeperAPI.setBaseUrl(defaultUrl);
    setSavedUrl(defaultUrl);
    testConnection.reset();
  };

  const hasChanges = apiUrl !== savedUrl;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">{t('title')}</h1>
        <p className="text-text-secondary mt-1">
          {t('subtitle')}
        </p>
      </div>

      {/* Language */}
      <Card>
        <CardTitle>{t('language')}</CardTitle>
        <CardDescription>{t('languageDesc')}</CardDescription>
        <div className="mt-4">
          <LanguageSwitcher />
        </div>
      </Card>

      {/* API Configuration */}
      <Card>
        <CardTitle>{t('apiConfig')}</CardTitle>
        <CardDescription>
          {t('apiConfigDesc')}
        </CardDescription>

        <div className="mt-4 space-y-4">
          <Input
            label={t('apiUrl')}
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />

          {testConnection.isPending && (
            <div className="flex items-center gap-2 text-text-secondary">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('testingConnection')}
            </div>
          )}

          {testConnection.isSuccess && (
            <div className="flex items-center gap-2 text-risk-green">
              <CheckCircle className="h-4 w-4" />
              {t('connectionSuccess')}
            </div>
          )}

          {testConnection.isError && (
            <div className="flex items-center gap-2 text-risk-red">
              <AlertCircle className="h-4 w-4" />
              {t('connectionFailed')}
            </div>
          )}

          <div className="flex gap-3">
            <Button
              onClick={handleSave}
              disabled={!hasChanges}
              variant={hasChanges ? 'primary' : 'secondary'}
            >
              {tc('save')}
            </Button>
            <Button
              variant="secondary"
              onClick={handleTest}
              disabled={testConnection.isPending}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('testConnection')}
            </Button>
            <Button variant="ghost" onClick={handleReset}>
              {t('resetToDefault')}
            </Button>
          </div>
        </div>
      </Card>

      {/* Subscription */}
      <SubscriptionCard />

      {/* About */}
      <Card>
        <CardTitle>{t('about')}</CardTitle>
        <div className="mt-4 space-y-2 text-sm text-text-secondary">
          <p>{t('aboutText')}</p>
          <p className="pt-2">
            <strong className="text-text">{t('features')}</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>{t('feature1')}</li>
            <li>{t('feature2')}</li>
            <li>{t('feature3')}</li>
            <li>{t('feature4')}</li>
            <li>{t('feature5')}</li>
          </ul>
        </div>
      </Card>

      {/* Keyboard Shortcuts */}
      <Card>
        <CardTitle>{t('shortcuts')}</CardTitle>
        <div className="mt-4 space-y-2">
          {[
            { keys: ['/', 'Ctrl', 'K'], action: t('searchSystems') },
            { keys: ['G', 'H'], action: t('goToDashboard') },
            { keys: ['G', 'R'], action: t('goToRoute') },
            { keys: ['G', 'F'], action: t('goToFitting') },
            { keys: ['G', 'A'], action: t('goToAlerts') },
            { keys: ['G', 'I'], action: t('goToIntel') },
          ].map(({ keys, action }) => (
            <div
              key={action}
              className="flex items-center justify-between py-2 border-b border-border last:border-0"
            >
              <span className="text-text-secondary text-sm">{action}</span>
              <div className="flex gap-1">
                {keys.map((key, i) => (
                  <span key={i}>
                    <kbd className="px-2 py-1 bg-background border border-border rounded text-xs font-mono text-text">
                      {key}
                    </kbd>
                    {i < keys.length - 1 && (
                      <span className="text-text-secondary mx-1">+</span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SubscriptionCard() {
  const t = useTranslations('settings');
  // TODO: Replace 0 with actual character_id from auth context
  const characterId = 0;

  const { data: subscription, isLoading } = useQuery({
    queryKey: ['subscription-status', characterId],
    queryFn: () => GatekeeperAPI.getSubscriptionStatus(characterId),
    enabled: characterId > 0,
  });

  const manageSubscription = useMutation({
    mutationFn: () => GatekeeperAPI.createPortal(characterId),
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });

  const isActive = subscription?.subscribed;
  const planLabel = subscription?.plan === 'annual' ? 'Annual' : 'Monthly';

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <CardTitle>
            <span className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              {t('subscription')}
            </span>
          </CardTitle>
          <CardDescription>
            {t('subscriptionDesc')}
          </CardDescription>
        </div>
        {isActive && (
          <Badge variant="success">
            {planLabel} - {t('active')}
          </Badge>
        )}
      </div>

      <div className="mt-4">
        {isLoading ? (
          <div className="flex items-center gap-2 text-text-secondary">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('loadingSub')}
          </div>
        ) : isActive ? (
          <div className="space-y-3">
            {subscription?.current_period_end && (
              <p className="text-sm text-text-secondary">
                {subscription.cancel_at_period_end
                  ? t('accessUntil', { date: new Date(subscription.current_period_end).toLocaleDateString() })
                  : t('renewsOn', { date: new Date(subscription.current_period_end).toLocaleDateString() })}
              </p>
            )}
            <Button
              variant="secondary"
              onClick={() => manageSubscription.mutate()}
              loading={manageSubscription.isPending}
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              {t('manageSub')}
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-text-secondary">
              {t('subscribePrompt')}
            </p>
            <Link href="/pricing">
              <Button variant="primary">
                {t('viewPlans')}
              </Button>
            </Link>
          </div>
        )}
      </div>
    </Card>
  );
}
