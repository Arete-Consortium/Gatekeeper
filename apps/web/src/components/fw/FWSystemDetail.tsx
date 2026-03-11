'use client';

import { Card, Badge } from '@/components/ui';
import type { FWSystem, MapConfigSystem } from '@/lib/types';

// Faction metadata
const FACTION_META: Record<number, { name: string; color: string; badgeClass: string }> = {
  500001: { name: 'Caldari State', color: '#c8aa00', badgeClass: 'bg-yellow-500/20 text-yellow-400' },
  500002: { name: 'Minmatar Republic', color: '#2a7fff', badgeClass: 'bg-blue-500/20 text-blue-400' },
  500003: { name: 'Amarr Empire', color: '#c83232', badgeClass: 'bg-red-500/20 text-red-400' },
  500004: { name: 'Gallente Federation', color: '#1e8c1e', badgeClass: 'bg-green-500/20 text-green-400' },
};

interface FWSystemDetailProps {
  systemName: string;
  systemData: MapConfigSystem;
  fwData: FWSystem;
  adjacentSystems: string[];
  killCount?: number;
  onClose: () => void;
}

export function FWSystemDetail({
  systemName,
  systemData,
  fwData,
  adjacentSystems,
  killCount = 0,
  onClose,
}: FWSystemDetailProps) {
  const occupier = FACTION_META[fwData.occupier_faction_id];
  const owner = FACTION_META[fwData.owner_faction_id];
  const progress = fwData.victory_points_threshold > 0
    ? fwData.victory_points / fwData.victory_points_threshold
    : 0;
  const progressPct = Math.round(progress * 100);
  const isContested = fwData.contested === 'contested' || fwData.contested === 'vulnerable';
  const isFlipped = fwData.occupier_faction_id !== fwData.owner_faction_id;

  return (
    <Card className="absolute top-4 right-4 z-20 w-72 p-4 space-y-3 bg-card/95 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-text">{systemName}</h3>
        <button
          onClick={onClose}
          className="text-text-secondary hover:text-text text-xs px-1"
          aria-label="Close detail panel"
        >
          &times;
        </button>
      </div>

      {/* Security */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-secondary">Security:</span>
        <span
          className="text-xs font-mono font-medium"
          style={{
            color: systemData.security >= 0.5 ? '#00ff00' : systemData.security > 0 ? '#ffaa00' : '#ff0000',
          }}
        >
          {systemData.security.toFixed(1)}
        </span>
        <span className="text-xs text-text-secondary">({systemData.category})</span>
      </div>

      {/* Controlling faction */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-secondary">Occupier:</span>
          {occupier && (
            <Badge variant="default" className={`text-[10px] px-1.5 py-0 ${occupier.badgeClass}`}>
              {occupier.name}
            </Badge>
          )}
        </div>
        {isFlipped && owner && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-secondary">Owner:</span>
            <Badge variant="default" className={`text-[10px] px-1.5 py-0 ${owner.badgeClass}`}>
              {owner.name}
            </Badge>
          </div>
        )}
      </div>

      {/* Contested status */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-secondary">Status:</span>
        <Badge
          variant="default"
          className={`text-[10px] px-1.5 py-0 ${
            fwData.contested === 'vulnerable'
              ? 'bg-red-500/20 text-red-400'
              : isContested
                ? 'bg-amber-500/20 text-amber-400'
                : 'bg-emerald-500/20 text-emerald-400'
          }`}
        >
          {fwData.contested}
        </Badge>
      </div>

      {/* VP Progress */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs text-text-secondary">Victory Points</span>
          <span className="text-xs text-text font-mono">
            {fwData.victory_points.toLocaleString()} / {fwData.victory_points_threshold.toLocaleString()}
          </span>
        </div>
        <div className="h-2 bg-card rounded-full overflow-hidden border border-border">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(progressPct, 100)}%`,
              backgroundColor: occupier?.color || '#666',
            }}
          />
        </div>
        <div className="text-right text-[10px] text-text-secondary">{progressPct}%</div>
      </div>

      {/* Kill activity */}
      {killCount > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-secondary">Kills (24h):</span>
          <span className="text-xs font-mono text-red-400 font-medium">{killCount}</span>
        </div>
      )}

      {/* Region / Constellation */}
      <div className="flex items-center gap-2 text-xs text-text-secondary">
        <span>{systemData.region_name}</span>
        <span>&middot;</span>
        <span>{systemData.constellation_name}</span>
      </div>

      {/* Adjacent systems */}
      {adjacentSystems.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-text-secondary">Adjacent FW Systems:</span>
          <div className="flex flex-wrap gap-1">
            {adjacentSystems.map((name) => (
              <span key={name} className="text-[10px] text-text bg-card-hover px-1.5 py-0.5 rounded">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
