'use client';

import React, { useMemo, useState } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { MarketHub } from '@/lib/types';

interface MarketHubsOverlayProps {
  hubs: MarketHub[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

/** Format ISK volume in trillions */
function formatVolume(value: number): string {
  const trillions = value / 1_000_000_000_000;
  if (trillions >= 1) {
    return `${trillions.toFixed(0)}T ISK/day`;
  }
  const billions = value / 1_000_000_000;
  return `${billions.toFixed(0)}B ISK/day`;
}

/** Format active order count with K suffix */
function formatOrders(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(0)}K orders`;
  }
  return `${count} orders`;
}

/** Scale diamond size based on volume relative to Jita */
function getDiamondSize(volume: number, maxVolume: number): number {
  const ratio = volume / maxVolume;
  // Range: 6px (smallest) to 14px (Jita)
  return 6 + ratio * 8;
}

export const MarketHubsOverlay = React.memo(function MarketHubsOverlay({
  hubs,
  systems,
  viewport,
}: MarketHubsOverlayProps) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  const maxVolume = useMemo(
    () => Math.max(...hubs.map((h) => h.daily_volume_estimate), 1),
    [hubs]
  );

  const markers = useMemo(() => {
    const result: Array<{
      hub: MarketHub;
      x: number;
      y: number;
      size: number;
    }> = [];

    for (const hub of hubs) {
      const system = systems.get(hub.system_id);
      if (!system) continue;

      const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
      const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

      // Skip if off screen (generous margin for labels)
      if (sx < -60 || sx > viewport.width + 60 || sy < -60 || sy > viewport.height + 60) continue;

      result.push({
        hub,
        x: sx,
        y: sy,
        size: getDiamondSize(hub.daily_volume_estimate, maxVolume),
      });
    }

    return result;
  }, [hubs, systems, viewport, maxVolume]);

  if (markers.length === 0) return null;

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 5 }}
      data-testid="market-hubs-overlay"
    >
      {markers.map((m) => (
        <div
          key={m.hub.system_id}
          className="absolute pointer-events-auto cursor-pointer"
          style={{
            left: m.x - m.size / 2,
            top: m.y - m.size / 2,
          }}
          onMouseEnter={() => setHoveredId(m.hub.system_id)}
          onMouseLeave={() => setHoveredId(null)}
        >
          {/* Diamond marker */}
          <div
            className={`rotate-45 border border-amber-400 bg-amber-500/30${m.hub.is_primary ? ' animate-pulse' : ''}`}
            style={{
              width: m.size,
              height: m.size,
            }}
          />

          {/* Label (visible at moderate zoom) */}
          {viewport.zoom > 0.8 && (
            <span
              className="absolute left-full ml-2 top-1/2 -translate-y-1/2 whitespace-nowrap text-amber-300 text-[10px] font-semibold select-none"
              style={{ textShadow: '0 0 4px rgba(0,0,0,0.9)' }}
            >
              {m.hub.system_name}
              <span className="text-amber-400/60 ml-1 font-normal">
                {formatVolume(m.hub.daily_volume_estimate)}
              </span>
            </span>
          )}

          {/* Tooltip on hover */}
          {hoveredId === m.hub.system_id && (
            <div
              className="absolute left-full ml-3 -top-3 bg-gray-900/95 border border-amber-400/40 rounded px-2.5 py-2 z-50 min-w-[180px]"
            >
              <div className="text-amber-300 text-xs font-semibold">{m.hub.system_name}</div>
              <div className="text-gray-400 text-[10px] mt-0.5">{m.hub.region_name}</div>
              <div className="text-amber-200 text-[11px] mt-1 font-medium">
                {formatVolume(m.hub.daily_volume_estimate)}
              </div>
              {(m.hub.active_orders ?? 0) > 0 && (
                <div className="text-gray-300 text-[10px] mt-0.5">
                  {formatOrders(m.hub.active_orders!)}
                </div>
              )}
              {m.hub.is_primary && (
                <div className="text-amber-500 text-[9px] mt-0.5 uppercase tracking-wider font-semibold">
                  Primary Trade Hub
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
});

export default MarketHubsOverlay;
