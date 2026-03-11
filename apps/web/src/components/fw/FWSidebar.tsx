'use client';

import { Card, Badge } from '@/components/ui';
import type { HotSystem } from '@/lib/types';

const FACTION_COLORS: Record<number, { fill: string; name: string; shortName: string }> = {
  500001: { fill: '#c8aa00', name: 'Caldari State', shortName: 'Caldari' },
  500002: { fill: '#2a7fff', name: 'Minmatar Republic', shortName: 'Minmatar' },
  500003: { fill: '#c83232', name: 'Amarr Empire', shortName: 'Amarr' },
  500004: { fill: '#1e8c1e', name: 'Gallente Federation', shortName: 'Gallente' },
};

const FACTION_IDS = [500001, 500002, 500003, 500004] as const;

interface FWSystemNode {
  systemId: number;
  name: string;
  fw: {
    occupier_faction_id: number;
    owner_faction_id: number;
    contested: string;
    victory_points: number;
    victory_points_threshold: number;
  };
}

interface FWSidebarProps {
  fwSystems: FWSystemNode[];
  factionCounts: Record<number, number>;
  flippedCounts: Record<number, number>;
  contestedCount: number;
  vulnerableCount: number;
  fwKillCount: number;
  topHotSystems: HotSystem[];
  systemMap: Map<number, FWSystemNode>;
  onSystemClick: (systemId: number) => void;
}

export function FWSidebar({
  fwSystems,
  factionCounts,
  flippedCounts,
  contestedCount,
  vulnerableCount,
  fwKillCount,
  topHotSystems,
  systemMap,
  onSystemClick,
}: FWSidebarProps) {
  // Most contested systems (highest VP progress)
  const mostContested = fwSystems
    .filter((s) => s.fw.contested === 'contested' || s.fw.contested === 'vulnerable')
    .sort((a, b) => {
      const pa = a.fw.victory_points_threshold > 0
        ? a.fw.victory_points / a.fw.victory_points_threshold : 0;
      const pb = b.fw.victory_points_threshold > 0
        ? b.fw.victory_points / b.fw.victory_points_threshold : 0;
      return pb - pa;
    })
    .slice(0, 5);

  return (
    <div className="hidden lg:flex flex-col gap-3 w-64 shrink-0">
      {/* Overview stats */}
      <Card className="p-3 space-y-3">
        <h3 className="text-xs font-bold text-text uppercase tracking-wider">Warzone Overview</h3>
        <div className="grid grid-cols-2 gap-2">
          <StatBlock label="Total Systems" value={fwSystems.length} />
          <StatBlock label="Contested" value={contestedCount} color="#ffd60a" />
          <StatBlock label="Vulnerable" value={vulnerableCount} color="#ff453a" />
          <StatBlock label="Kills (24h)" value={fwKillCount} color="#ef4444" />
        </div>
      </Card>

      {/* Territory breakdown */}
      <Card className="p-3 space-y-2">
        <h3 className="text-xs font-bold text-text uppercase tracking-wider">Territory Control</h3>
        {FACTION_IDS.map((fid) => {
          const info = FACTION_COLORS[fid];
          const count = factionCounts[fid] || 0;
          const pct = fwSystems.length > 0 ? Math.round((count / fwSystems.length) * 100) : 0;
          const flipped = flippedCounts[fid] || 0;
          return (
            <div key={fid} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: info.fill }} />
                  <span className="text-xs text-text">{info.shortName}</span>
                </div>
                <span className="text-xs font-mono text-text-secondary">
                  {count} ({pct}%)
                </span>
              </div>
              {/* Territory bar */}
              <div className="h-1.5 bg-card-hover rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: info.fill }}
                />
              </div>
              {flipped > 0 && (
                <span className="text-[10px] text-text-secondary">
                  +{flipped} captured
                </span>
              )}
            </div>
          );
        })}
      </Card>

      {/* Most contested */}
      {mostContested.length > 0 && (
        <Card className="p-3 space-y-2">
          <h3 className="text-xs font-bold text-text uppercase tracking-wider">Most Contested</h3>
          <div className="space-y-1.5">
            {mostContested.map((sys) => {
              const faction = FACTION_COLORS[sys.fw.occupier_faction_id];
              const progress = sys.fw.victory_points_threshold > 0
                ? Math.round((sys.fw.victory_points / sys.fw.victory_points_threshold) * 100)
                : 0;
              return (
                <button
                  key={sys.systemId}
                  onClick={() => onSystemClick(sys.systemId)}
                  className="flex items-center justify-between w-full text-left hover:bg-card-hover rounded px-1.5 py-1 transition-colors"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span
                      className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: faction?.fill }}
                    />
                    <span className="text-xs text-text truncate">{sys.name}</span>
                  </div>
                  <Badge
                    variant="default"
                    className={`text-[10px] px-1 py-0 shrink-0 ${
                      sys.fw.contested === 'vulnerable'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-amber-500/20 text-amber-400'
                    }`}
                  >
                    {progress}%
                  </Badge>
                </button>
              );
            })}
          </div>
        </Card>
      )}

      {/* Hot systems (kill activity) */}
      {topHotSystems.length > 0 && (
        <Card className="p-3 space-y-2">
          <h3 className="text-xs font-bold text-text uppercase tracking-wider">Kill Activity (24h)</h3>
          <div className="space-y-1.5">
            {topHotSystems.map((hs) => {
              const sys = systemMap.get(hs.system_id);
              const faction = sys
                ? FACTION_COLORS[sys.fw.occupier_faction_id]
                : null;
              return (
                <button
                  key={hs.system_id}
                  onClick={() => onSystemClick(hs.system_id)}
                  className="flex items-center justify-between w-full text-left hover:bg-card-hover rounded px-1.5 py-1 transition-colors"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span
                      className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: faction?.fill || '#666' }}
                    />
                    <span className="text-xs text-text truncate">{hs.system_name}</span>
                  </div>
                  <span className="text-[10px] font-mono text-red-400 shrink-0">
                    {hs.recent_kills} kills
                  </span>
                </button>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

function StatBlock({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="text-center">
      <div className="text-lg font-bold font-mono" style={{ color: color || 'var(--text)' }}>
        {value}
      </div>
      <div className="text-[10px] text-text-secondary">{label}</div>
    </div>
  );
}
