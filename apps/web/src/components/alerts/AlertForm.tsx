'use client';

import { useState, useRef, useCallback } from 'react';
import { Card, CardTitle, Button, Input, Select, Toggle } from '@/components/ui';
import type { CreateAlertSubscriptionRequest } from '@/lib/types';
import { Plus, Send, X } from 'lucide-react';
import { RegionFilter, EVE_REGIONS } from './RegionFilter';

const ALLOWED_WEBHOOK_HOSTS = ['discord.com', 'hooks.slack.com', 'api.slack.com'];

function validateWebhookUrl(url: string): string | undefined {
  if (!url.trim()) return undefined;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:') {
      return 'Webhook URL must use HTTPS';
    }
    if (!ALLOWED_WEBHOOK_HOSTS.some((host) => parsed.hostname.endsWith(host))) {
      return 'Only Discord and Slack webhook URLs are supported';
    }
    return undefined;
  } catch {
    return 'Invalid URL format';
  }
}

const SHIP_TYPES = [
  'Frigate',
  'Destroyer',
  'Cruiser',
  'Battlecruiser',
  'Battleship',
  'Capital',
  'Supercapital',
  'Industrial',
  'Mining',
  'Shuttle',
  'Capsule',
  'Titan',
  'Supercarrier',
  'Dreadnought',
  'Carrier',
  'Force Auxiliary',
] as const;

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
  const [regionName, setRegionName] = useState('');
  const [shipTypes, setShipTypes] = useState<string[]>([]);
  const [shipTypeQuery, setShipTypeQuery] = useState('');
  const [showShipTypeDropdown, setShowShipTypeDropdown] = useState(false);
  const shipTypeInputRef = useRef<HTMLInputElement>(null);

  const filteredShipTypes = SHIP_TYPES.filter(
    (type) =>
      type.toLowerCase().includes(shipTypeQuery.toLowerCase()) &&
      !shipTypes.includes(type)
  );

  const addShipType = useCallback((type: string) => {
    setShipTypes((prev) => [...prev, type]);
    setShipTypeQuery('');
    setShowShipTypeDropdown(false);
    shipTypeInputRef.current?.focus();
  }, []);

  const removeShipType = useCallback((type: string) => {
    setShipTypes((prev) => prev.filter((t) => t !== type));
  }, []);

  const handleShipTypeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredShipTypes.length > 0) {
        addShipType(filteredShipTypes[0]);
      }
    }
    if (e.key === 'Backspace' && shipTypeQuery === '' && shipTypes.length > 0) {
      removeShipType(shipTypes[shipTypes.length - 1]);
    }
    if (e.key === 'Escape') {
      setShowShipTypeDropdown(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Resolve region name to region ID if it matches a known region
    const matchedRegion = regionName.trim()
      ? EVE_REGIONS.find(
          (r) => r.name.toLowerCase() === regionName.trim().toLowerCase()
        )
      : undefined;

    const data: CreateAlertSubscriptionRequest = {
      webhook_url: webhookUrl,
      webhook_type: webhookType,
      name: name || undefined,
      systems: systems
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      regions: matchedRegion ? [matchedRegion.id] : undefined,
      region_name: regionName.trim() || undefined,
      min_value: minValue ? parseInt(minValue) * 1_000_000 : undefined,
      include_pods: includePods,
      ship_types: shipTypes.length > 0 ? shipTypes : undefined,
    };

    onSubmit(data);
  };

  const webhookError = validateWebhookUrl(webhookUrl);
  const isValid = webhookUrl.trim().length > 0 && !webhookError;

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
          error={webhookUrl ? webhookError : undefined}
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

        <RegionFilter value={regionName} onChange={setRegionName} />

        <Input
          label="Minimum Value (millions ISK, optional)"
          value={minValue}
          onChange={(e) => setMinValue(e.target.value)}
          placeholder="100"
          type="number"
        />

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1.5">
            Ship Types (optional)
          </label>
          <div className="relative">
            <div className="flex flex-wrap gap-1.5 p-2 bg-card border border-border rounded-lg min-h-[42px]">
              {shipTypes.map((type) => (
                <span
                  key={type}
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md bg-primary/20 text-primary border border-primary/30"
                >
                  {type}
                  <button
                    type="button"
                    onClick={() => removeShipType(type)}
                    className="hover:text-risk-red transition-colors"
                    aria-label={`Remove ${type}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              <input
                ref={shipTypeInputRef}
                type="text"
                value={shipTypeQuery}
                onChange={(e) => {
                  setShipTypeQuery(e.target.value);
                  setShowShipTypeDropdown(true);
                }}
                onFocus={() => setShowShipTypeDropdown(true)}
                onBlur={() => {
                  // Delay to allow click on dropdown items
                  setTimeout(() => setShowShipTypeDropdown(false), 150);
                }}
                onKeyDown={handleShipTypeKeyDown}
                placeholder={shipTypes.length === 0 ? 'Type to search ship types...' : ''}
                className="flex-1 min-w-[120px] bg-transparent text-text placeholder:text-text-secondary text-sm outline-none"
                aria-label="Ship type search"
              />
            </div>
            {showShipTypeDropdown && filteredShipTypes.length > 0 && (
              <ul
                role="listbox"
                className="absolute z-10 mt-1 w-full max-h-48 overflow-auto bg-card border border-border rounded-lg shadow-lg"
              >
                {filteredShipTypes.map((type) => (
                  <li
                    key={type}
                    role="option"
                    aria-selected={false}
                    className="px-3 py-2 text-sm text-text hover:bg-primary/10 cursor-pointer transition-colors"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      addShipType(type);
                    }}
                  >
                    {type}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

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
