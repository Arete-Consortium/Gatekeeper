'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { GatekeeperAPI } from '@/lib/api';
import { Card } from '@/components/ui';
import { AlertCard, AlertForm } from '@/components/alerts';
import type {
  AlertSubscriptionListResponse,
  AlertSubscription,
  CreateAlertSubscriptionRequest,
} from '@/lib/types';
import { Bell, Loader2 } from 'lucide-react';
import { ErrorMessage, SkeletonCard, getUserFriendlyError } from '@/components/ui';

export default function AlertsPage() {
  const queryClient = useQueryClient();

  const {
    data: subscriptionsData,
    isLoading,
    error,
    refetch,
  } = useQuery<AlertSubscriptionListResponse>({
    queryKey: ['alertSubscriptions'],
    queryFn: () => GatekeeperAPI.listAlertSubscriptions(),
  });

  const createMutation = useMutation({
    mutationFn: (data: CreateAlertSubscriptionRequest) =>
      GatekeeperAPI.createAlertSubscription(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertSubscriptions'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => GatekeeperAPI.deleteAlertSubscription(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertSubscriptions'] });
    },
  });

  const testMutation = useMutation({
    mutationFn: () => GatekeeperAPI.sendTestAlert(),
  });

  const handleToggle = (id: string, enabled: boolean) => {
    // Note: The API would need to support updating subscriptions
    // For now this is a placeholder
    console.log('Toggle subscription', id, enabled);
  };

  const subscriptions = subscriptionsData?.subscriptions || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text">Kill Alerts</h1>
        <p className="text-text-secondary mt-1">
          Get notified about kills via Discord or Slack webhooks
        </p>
      </div>

      {/* Create Form */}
      <AlertForm
        onSubmit={(data) => createMutation.mutate(data)}
        onTest={() => testMutation.mutate()}
        isSubmitting={createMutation.isPending}
        isTesting={testMutation.isPending}
      />

      {/* Success/Error Messages */}
      {createMutation.isSuccess && (
        <Card className="border-risk-green bg-risk-green/10" role="status" aria-live="polite">
          <p className="text-risk-green">Alert subscription created successfully!</p>
        </Card>
      )}

      {createMutation.isError && (
        <ErrorMessage
          title="Unable to create subscription"
          message="Please verify your webhook URL is correct and accessible. Make sure it starts with https:// for Discord or Slack."
          onRetry={() => createMutation.reset()}
        />
      )}

      {testMutation.isSuccess && (
        <Card className="border-primary bg-primary/10" role="status" aria-live="polite">
          <p className="text-primary">Test alert sent! Check your webhook destination.</p>
        </Card>
      )}

      {testMutation.isError && (
        <ErrorMessage
          title="Test alert failed"
          message="Could not send the test alert. Please verify your webhook configuration."
          variant="warning"
        />
      )}

      {/* Subscriptions List */}
      <section aria-labelledby="subscriptions-heading">
        <h2 id="subscriptions-heading" className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-4">
          Active Subscriptions ({subscriptions.length})
        </h2>

        {isLoading ? (
          <div className="space-y-3" aria-busy="true" aria-label="Loading subscriptions">
            {[...Array(2)].map((_, i) => (
              <SkeletonCard key={i} lines={3} />
            ))}
          </div>
        ) : error ? (
          <ErrorMessage
            title="Unable to load subscriptions"
            message={getUserFriendlyError(error)}
            onRetry={() => refetch()}
          />
        ) : subscriptions.length > 0 ? (
          <div className="space-y-3" role="list" aria-label="Alert subscriptions">
            {subscriptions.map((sub) => (
              <AlertCard
                key={sub.id}
                subscription={sub}
                onToggle={handleToggle}
                onDelete={(id) => deleteMutation.mutate(id)}
              />
            ))}
          </div>
        ) : (
          <Card className="text-center py-12">
            <Bell className="h-12 w-12 text-text-secondary mx-auto mb-4" aria-hidden="true" />
            <p className="text-text-secondary">
              No alert subscriptions yet. Create one above to get started.
            </p>
          </Card>
        )}
      </section>
    </div>
  );
}
