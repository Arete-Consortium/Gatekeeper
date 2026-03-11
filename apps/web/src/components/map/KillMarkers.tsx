'use client';

import { memo, useMemo, useState, useEffect } from 'react';
import React from 'react';
import type { KillFeedProps, MapKill, MapSystem, MapViewport } from './types';
import { formatIsk } from '@/lib/utils';

const KILL_COLORS = {
  ship: '#ff453a',
  pod: '#ff9f0a',
} as const;

function getMarkerRadius(value: number, zoom: number): number {
  const logValue = Math.log10(value + 1);
  const base = Math.max(3, Math.min(10, logValue * 1.5));
  return base * Math.max(0.8, Math.min(1.5, zoom * 0.5));
}

function getOpacity(timestamp: number, maxAge: number, now: number): number {
  const age = now - timestamp;
  return Math.max(0.3, 1 - (age / maxAge) * 0.7);
}

interface KillMarkerProps {
  kill: MapKill;
  system: MapSystem;
  viewport: MapViewport;
  maxAge: number;
  now: number;
}

const KillMarker = memo(function KillMarker({ kill, system, viewport, maxAge, now }: KillMarkerProps) {
  const sx = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
  const sy = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

  if (sx < -30 || sx > viewport.width + 30 || sy < -30 || sy > viewport.height + 30) return null;

  const r = getMarkerRadius(kill.value, viewport.zoom);
  const opacity = getOpacity(kill.timestamp, maxAge, now);
  const color = kill.isPod ? KILL_COLORS.pod : KILL_COLORS.ship;

  const ageMinutes = Math.floor((now - kill.timestamp) / 60000);
  const ageText = ageMinutes < 1 ? 'Just now' : `${ageMinutes}m ago`;

  return (
    <g opacity={opacity}>
      {/* Pulsing outer ring */}
      <circle cx={sx} cy={sy} r={r * 2.5} fill="none" stroke={color} strokeWidth={1} opacity={0.4}>
        <animate attributeName="r" from={String(r * 1.5)} to={String(r * 3)} dur="1.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" from="0.5" to="0" dur="1.5s" repeatCount="indefinite" />
      </circle>
      {/* Core blinking dot */}
      <circle cx={sx} cy={sy} r={r} fill={color} opacity={0.9}>
        <animate attributeName="opacity" values="0.9;0.4;0.9" dur="1s" repeatCount="indefinite" />
      </circle>
      {/* Glow */}
      <circle cx={sx} cy={sy} r={r * 1.5} fill={color} opacity={0.2}>
        <animate attributeName="opacity" values="0.3;0.1;0.3" dur="1s" repeatCount="indefinite" />
      </circle>
      <title>{kill.isPod ? 'Pod Kill' : kill.shipType} — {formatIsk(kill.value)} — {ageText} — {system.name}</title>
    </g>
  );
});

export function KillMarkers({
  kills,
  systems,
  viewport,
  maxAge = 60 * 60 * 1000,
}: KillFeedProps) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => { setNow(Date.now()); }, [kills.length]);

  const visibleKills = useMemo(() => {
    return kills.filter((kill) => {
      const system = systems.get(kill.systemId);
      if (!system) return false;
      if (now - kill.timestamp > maxAge) return false;
      return true;
    });
  }, [kills, systems, maxAge, now]);

  if (visibleKills.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 3 }}
    >
      {visibleKills.map((kill) => {
        const system = systems.get(kill.systemId);
        if (!system) return null;
        return (
          <KillMarker
            key={kill.killId}
            kill={kill}
            system={system}
            viewport={viewport}
            maxAge={maxAge}
            now={now}
          />
        );
      })}
    </svg>
  );
}

export default KillMarkers;
