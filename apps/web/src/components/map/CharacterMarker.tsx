'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';

interface CharacterMarkerProps {
  systemId: number;
  characterName: string;
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

export const CharacterMarker = React.memo(function CharacterMarker({
  systemId,
  characterName,
  systems,
  viewport,
}: CharacterMarkerProps) {
  const pos = useMemo(() => {
    const system = systems.get(systemId);
    if (!system) return null;
    const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
    const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;
    if (x < -50 || x > viewport.width + 50 || y < -50 || y > viewport.height + 50) return null;
    return { x, y };
  }, [systemId, systems, viewport]);

  if (!pos) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 10 }}
    >
      <defs>
        <filter id="char-glow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {/* Pulsing ring */}
      <circle cx={pos.x} cy={pos.y} r={8} fill="none" stroke="#22d3ee" strokeWidth={2} opacity={0.6} filter="url(#char-glow)">
        <animate attributeName="r" values="8;14;8" dur="2s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.6;0.2;0.6" dur="2s" repeatCount="indefinite" />
      </circle>
      {/* Solid dot */}
      <circle cx={pos.x} cy={pos.y} r={5} fill="#22d3ee" stroke="#0e7490" strokeWidth={1.5} />
      {/* Character name label */}
      {viewport.zoom > 1 && (
        <>
          <rect
            x={pos.x + 10}
            y={pos.y - 8}
            width={characterName.length * 6 + 8}
            height={16}
            rx={3}
            fill="rgba(0,0,0,0.85)"
          />
          <text
            x={pos.x + 14}
            y={pos.y + 4}
            fill="#22d3ee"
            fontSize={10}
            fontFamily="monospace"
            fontWeight="bold"
          >
            {characterName}
          </text>
        </>
      )}
    </svg>
  );
});

export default CharacterMarker;
