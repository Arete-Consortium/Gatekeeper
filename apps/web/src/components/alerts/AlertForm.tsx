'use client';

import { useState } from 'react';
import { Card, CardTitle, Button, Input, Select, Toggle } from '@/components/ui';
import type { CreateAlertSubscriptionRequest } from '@/lib/types';
import { Plus, Send } from 'lucide-react';

interface AlertFormProps {
  onSubmit: (data: CreateAlertSubscriptionRequest) => void;
  onTest: () => void;
  isSubmitting: boolean;
  isTesting: boolean;
}

export function AlertForm({
  onSubmit,
  onTest,
  isSubmitting,
  isTesting,
}: AlertFormProps) {
  const [name, setName] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookType, setWebhookType] = useState<'discord' | 'slack'>('discord');
  const [systems, setSystems] = useState('');
  const [minValue, setMinValue] = useState('');
  const [includePods, setIncludePods] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const data: CreateAlertSubscriptionRequest = {
      webhook_url: webhookUrl,
      webhook_type: webhookType,
      name: name || undefined,
      systems: systems
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      min_value: minValue ? parseInt(minValue) * 1_000_000 : undefined,
      include_pods: includePods,
    };

    onSubmit(data);
  };

  const isValid = webhookUrl.trim().length > 0;

  return (
    <Card>
      <CardTitle className="mb-4">Create Alert Subscription</CardTitle>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My kill alerts..."
        />

        <Input
          label="Webhook URL"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://discord.com/api/webhooks/..."
          type="url"
        />

        <Select
          label="Webhook Type"
          value={webhookType}
          onChange={(e) => setWebhookType(e.target.value as 'discord' | 'slack')}
          options={[
            { value: 'discord', label: 'Discord' },
            { value: 'slack', label: 'Slack' },
          ]}
        />

        <Input
          label="Systems (comma-separated, optional)"
          value={systems}
          onChange={(e) => setSystems(e.target.value)}
          placeholder="Jita, Amarr, Dodixie..."
        />

        <Input
          label="Minimum Value (millions ISK, optional)"
          value={minValue}
          onChange={(e) => setMinValue(e.target.value)}
          placeholder="100"
          type="number"
        />

        <Toggle
          checked={includePods}
          onChange={setIncludePods}
          label="Include pod kills"
        />

        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={!isValid || isSubmitting} loading={isSubmitting}>
            <Plus className="mr-2 h-4 w-4" />
            Create Subscription
          </Button>

          <Button
            type="button"
            variant="secondary"
            onClick={onTest}
            disabled={isTesting}
            loading={isTesting}
          >
            <Send className="mr-2 h-4 w-4" />
            Send Test
          </Button>
        </div>
      </form>
    </Card>
  );
}
