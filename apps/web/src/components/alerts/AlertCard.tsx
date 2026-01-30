'use client';

import { Card, Badge, Toggle, Button } from '@/components/ui';
import { formatRelativeTime } from '@/lib/utils';
import type { AlertSubscription } from '@/lib/types';
import { Trash2, Bell, BellOff, MessageSquare } from 'lucide-react';

interface AlertCardProps {
  subscription: AlertSubscription;
  onToggle: (id: string, enabled: boolean) => void;
  onDelete: (id: string) => void;
}

export function AlertCard({ subscription, onToggle, onDelete }: AlertCardProps) {
  const webhookIcon =
    subscription.webhook_type === 'discord' ? (
      <Badge variant="info" size="sm">
        Discord
      </Badge>
    ) : (
      <Badge variant="warning" size="sm">
        Slack
      </Badge>
    );

  return (
    <Card className={!subscription.enabled ? 'opacity-60' : ''}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            {subscription.enabled ? (
              <Bell className="h-4 w-4 text-primary" />
            ) : (
              <BellOff className="h-4 w-4 text-text-secondary" />
            )}
            <span className="font-medium text-text truncate">
              {subscription.name || `Alert ${subscription.id.slice(0, 8)}`}
            </span>
            {webhookIcon}
          </div>

          {/* Filters */}
          <div className="space-y-1 text-sm text-text-secondary">
            {subscription.systems.length > 0 && (
              <p>
                Systems: {subscription.systems.slice(0, 3).join(', ')}
                {subscription.systems.length > 3 &&
                  ` +${subscription.systems.length - 3} more`}
              </p>
            )}
            {subscription.regions.length > 0 && (
              <p>Regions: {subscription.regions.length} selected</p>
            )}
            {subscription.min_value && (
              <p>Min Value: {(subscription.min_value / 1_000_000).toFixed(0)}M ISK</p>
            )}
            {subscription.ship_types.length > 0 && (
              <p>
                Ships: {subscription.ship_types.slice(0, 3).join(', ')}
                {subscription.ship_types.length > 3 &&
                  ` +${subscription.ship_types.length - 3} more`}
              </p>
            )}
            {subscription.include_pods && <p>Including pod kills</p>}
          </div>

          {/* Created */}
          <p className="text-xs text-text-secondary mt-2">
            Created {formatRelativeTime(subscription.created_at)}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col items-end gap-2">
          <Toggle
            checked={subscription.enabled}
            onChange={(enabled) => onToggle(subscription.id, enabled)}
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(subscription.id)}
            className="text-risk-red hover:bg-risk-red/10"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
