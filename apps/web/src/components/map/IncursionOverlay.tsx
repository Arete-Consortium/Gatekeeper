'use client';

import React, { useMemo } from 'react';
import type { MapSystem, MapViewport } from './types';
import type { Incursion } from '@/lib/types';

interface IncursionOverlayProps {
  incursions: Incursion[];
  systems: Map<number, MapSystem>;
  viewport: MapViewport;
}

/** Color by incursion state. */
function stateColor(state: string): string {
  switch (state) {
    case 'established':
      return '#ef4444'; // red-500
    case 'mobilizing':
      return '#f97316'; // orange-500
    case 'withdrawing':
      return '#eab308'; // yellow-500
    default:
      return '#f97316';
  }
}

/** Human-readable state label. */
function stateLabel(state: string): string {
  switch (state) {
    case 'established':
      return 'Established';
    case 'mobilizing':
      return 'Mobilizing';
    case 'withdrawing':
      return 'Withdrawing';
    default:
      return state;
  }
}

interface StagingMarker {
  key: string;
  x: number;
  y: number;
  state: string;
  color: string;
  influence: number;
  hasBoss: boolean;
}

interface InfestedMarker {
  key: string;
  x: number;
  y: number;
  color: string;
}

/**
 * Renders incursion markers on the map.
 * Staging systems get a large pulsing ring with state label.
 * Infested systems get smaller markers in the constellation.
 */
export const IncursionOverlay = React.memo(function IncursionOverlay({
  incursions,
  systems,
  viewport,
}: IncursionOverlayProps) {
  const { stagingMarkers, infestedMarkers } = useMemo(() => {
    const staging: StagingMarker[] = [];
    const infested: InfestedMarker[] = [];

    for (const inc of incursions) {
      const color = stateColor(inc.state);

      // Staging system — large pulsing ring
      if (inc.staging_system_id) {
        const system = systems.get(inc.staging_system_id);
        if (system) {
          const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
          const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

          if (x >= -60 && x <= viewport.width + 60 && y >= -60 && y <= viewport.height + 60) {
            staging.push({
              key: `staging-${inc.staging_system_id}-${inc.constellation_id}`,
              x,
              y,
              state: inc.state,
              color,
              influence: inc.influence,
              hasBoss: inc.has_boss,
            });
          }
        }
      }

      // Infested systems — smaller markers
      for (const sid of inc.infested_systems) {
        // Skip the staging system (already rendered with big marker)
        if (sid === inc.staging_system_id) continue;

        const system = systems.get(sid);
        if (!system) continue;

        const x = (system.x - viewport.x) * viewport.zoom + viewport.width / 2;
        const y = (system.y - viewport.y) * viewport.zoom + viewport.height / 2;

        if (x >= -30 && x <= viewport.width + 30 && y >= -30 && y <= viewport.height + 30) {
          infested.push({
            key: `infested-${sid}-${inc.constellation_id}`,
            x,
            y,
            color,
          });
        }
      }
    }

    return { stagingMarkers: staging, infestedMarkers: infested };
  }, [incursions, systems, viewport]);

  if (stagingMarkers.length === 0 && infestedMarkers.length === 0) return null;

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={viewport.width}
      height={viewport.height}
      style={{ zIndex: 3 }}
    >
      <defs>
        <filter id="incursion-glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Infested system markers (smaller, underneath staging) */}
      {infestedMarkers.map((m) => (
        <g key={m.key}>
          {/* Pulsing diamond */}
          <rect
            x={m.x - 4}
            y={m.y - 4}
            width={8}
            height={8}
            fill={m.color}
            opacity={0.5}
            transform={`rotate(45 ${m.x} ${m.y})`}
            filter="url(#incursion-glow)"
          >
            <animate
              attributeName="opacity"
              values="0.5;0.2;0.5"
              dur="3s"
              repeatCount="indefinite"
            />
          </rect>
          {/* Outer ring */}
          <circle
            cx={m.x}
            cy={m.y}
            r={6}
            fill="none"
            stroke={m.color}
            strokeWidth={1}
            opacity={0.3}
          >
            <animate
              attributeName="r"
              values="5;8;5"
              dur="3s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.3;0.1;0.3"
              dur="3s"
              repeatCount="indefinite"
            />
          </circle>
        </g>
      ))}

      {/* Staging system markers (large, on top) */}
      {stagingMarkers.map((m) => (
        <g key={m.key}>
          {/* Outer pulsing ring */}
          <circle
            cx={m.x}
            cy={m.y}
            r={14}
            fill="none"
            stroke={m.color}
            strokeWidth={2}
            opacity={0.4}
            filter="url(#incursion-glow)"
          >
            <animate
              attributeName="r"
              values="12;18;12"
              dur="2s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.5;0.15;0.5"
              dur="2s"
              repeatCount="indefinite"
            />
          </circle>
          {/* Middle ring (steady) */}
          <circle
            cx={m.x}
            cy={m.y}
            r={10}
            fill="none"
            stroke={m.color}
            strokeWidth={1.5}
            opacity={0.6}
          />
          {/* Inner filled dot */}
          <circle
            cx={m.x}
            cy={m.y}
            r={5}
            fill={m.color}
            opacity={0.8}
            filter="url(#incursion-glow)"
          />
          {/* Sansha "S" marker */}
          <text
            x={m.x}
            y={m.y + 3}
            textAnchor="middle"
            fill="#0a0e17"
            fontSize={7}
            fontWeight="bold"
          >
            S
          </text>
          {/* State label (visible at zoom > 0.6) */}
          {viewport.zoom > 0.6 && (
            <>
              <text
                x={m.x}
                y={m.y - 16}
                textAnchor="middle"
                fill={m.color}
                fontSize={9}
                fontWeight="bold"
                opacity={0.9}
              >
                {stateLabel(m.state)}
              </text>
              {/* Influence percentage */}
              <text
                x={m.x}
                y={m.y + 22}
                textAnchor="middle"
                fill={m.color}
                fontSize={8}
                opacity={0.7}
              >
                {Math.round(m.influence * 100)}%{m.hasBoss ? ' BOSS' : ''}
              </text>
            </>
          )}
        </g>
      ))}
    </svg>
  );
});

export default IncursionOverlay;
