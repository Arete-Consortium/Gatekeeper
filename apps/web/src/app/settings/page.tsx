'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { GatekeeperAPI } from '@/lib/api';
import { Card, CardTitle, CardDescription, Button, Input, Badge } from '@/components/ui';
import { Settings, CheckCircle, AlertCircle, Loader2, RefreshCw, CreditCard, ExternalLink } from 'lucide-react';

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState('');
  const [savedUrl, setSavedUrl] = useState('');

  useEffect(() => {
    const url = GatekeeperAPI.getBaseUrl();
    setApiUrl(url);
    setSavedUrl(url);
  }, []);

  const testConnection = useMutation({
    mutationFn: async (url: string) => {
      // Temporarily set the URL to test
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
        <h1 className="text-2xl font-bold text-text">Settings</h1>
        <p className="text-text-secondary mt-1">
          Configure EVE Gatekeeper application settings
        </p>
      </div>

      {/* API Configuration */}
      <Card>
        <CardTitle>API Configuration</CardTitle>
        <CardDescription>
          Configure the Gatekeeper backend API URL
        </CardDescription>

        <div className="mt-4 space-y-4">
          <Input
            label="API URL"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />

          {/* Connection Status */}
          {testConnection.isPending && (
            <div className="flex items-center gap-2 text-text-secondary">
              <Loader2 className="h-4 w-4 animate-spin" />
              Testing connection...
            </div>
          )}

          {testConnection.isSuccess && (
            <div className="flex items-center gap-2 text-risk-green">
              <CheckCircle className="h-4 w-4" />
              Connection successful!
            </div>
          )}

          {testConnection.isError && (
            <div className="flex items-center gap-2 text-risk-red">
              <AlertCircle className="h-4 w-4" />
              Connection failed. Please check the URL.
            </div>
          )}

          <div className="flex gap-3">
            <Button
              onClick={handleSave}
              disabled={!hasChanges}
              variant={hasChanges ? 'primary' : 'secondary'}
            >
              Save
            </Button>
            <Button
              variant="secondary"
              onClick={handleTest}
              disabled={testConnection.isPending}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Test Connection
            </Button>
            <Button variant="ghost" onClick={handleReset}>
              Reset to Default
            </Button>
          </div>
        </div>
      </Card>

      {/* Subscription */}
      <SubscriptionCard />

      {/* About */}
      <Card>
        <CardTitle>About EVE Gatekeeper</CardTitle>
        <div className="mt-4 space-y-2 text-sm text-text-secondary">
          <p>
            EVE Gatekeeper is an intel and route planning tool for EVE Online
            pilots. It provides safe routing recommendations based on recent
            kill activity from zKillboard.
          </p>
          <p className="pt-2">
            <strong className="text-text">Features:</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Risk-aware route planning with multiple profiles</li>
            <li>Ship fitting analysis for travel recommendations</li>
            <li>Kill alerts via Discord and Slack webhooks</li>
            <li>Real-time hot systems tracking</li>
            <li>Jump bridge and Thera connection support</li>
          </ul>
        </div>
      </Card>

      {/* Keyboard Shortcuts */}
      <Card>
        <CardTitle>Keyboard Shortcuts</CardTitle>
        <div className="mt-4 space-y-2">
          {[
            { keys: ['/', 'Ctrl', 'K'], action: 'Search systems' },
            { keys: ['G', 'H'], action: 'Go to Dashboard' },
            { keys: ['G', 'R'], action: 'Go to Route Planner' },
            { keys: ['G', 'F'], action: 'Go to Fitting Analyzer' },
            { keys: ['G', 'A'], action: 'Go to Alerts' },
            { keys: ['G', 'I'], action: 'Go to Intel' },
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
              Subscription
            </span>
          </CardTitle>
          <CardDescription>
            Manage your EVE Gatekeeper Pro subscription
          </CardDescription>
        </div>
        {isActive && (
          <Badge variant="success">
            {planLabel} - Active
          </Badge>
        )}
      </div>

      <div className="mt-4">
        {isLoading ? (
          <div className="flex items-center gap-2 text-text-secondary">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading subscription status...
          </div>
        ) : isActive ? (
          <div className="space-y-3">
            {subscription?.current_period_end && (
              <p className="text-sm text-text-secondary">
                {subscription.cancel_at_period_end
                  ? `Access until ${new Date(subscription.current_period_end).toLocaleDateString()}`
                  : `Renews on ${new Date(subscription.current_period_end).toLocaleDateString()}`}
              </p>
            )}
            <Button
              variant="secondary"
              onClick={() => manageSubscription.mutate()}
              loading={manageSubscription.isPending}
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Manage Subscription
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-text-secondary">
              Subscribe to unlock all premium features including AI analysis,
              priority alerts, and more.
            </p>
            <Link href="/pricing">
              <Button variant="primary">
                View Plans
              </Button>
            </Link>
          </div>
        )}
      </div>
    </Card>
  );
}
