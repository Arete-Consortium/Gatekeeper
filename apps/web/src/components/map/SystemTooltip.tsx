'use client';

import { memo, useEffect, useState, useRef } from 'react';
import type { MapSystem, MapViewport, SystemRisk } from './types';
import { getSecurityColor, RISK_COLORS } from './types';

/**
 * Props for SystemTooltip component
 */
export interface SystemTooltipProps {
  /** System to display (null to hide) */
  system: MapSystem | null;
  /** Risk data for the system (optional) */
  risk?: SystemRisk | null;
  /** Region name lookup */
  getRegionName?: (regionId: number) => string | null;
  /** Current viewport for positioning */
  viewport: MapViewport;
  /** Mouse position for tooltip placement */
  mousePosition: { x: number; y: number };
  /** Whether system is on current route */
  isOnRoute?: boolean;
  /** Whether origin selection mode is active */
  originMode?: boolean;
  /** Whether destination selection mode is active */
  destinationMode?: boolean;

  /** Actions */
  onSetOrigin?: (systemId: number) => void;
  onSetDestination?: (systemId: number) => void;
  onClose?: () => void;
}

/**
 * Format security status for display
 */
function formatSecurity(security: number): string {
  if (security >= 0) {
    return security.toFixed(1);
  }
  return security.toFixed(2);
}

/**
 * Get security label
 */
function getSecurityLabel(security: number): string {
  if (security >= 0.5) return 'High Sec';
  if (security > 0) return 'Low Sec';
  return 'Null Sec';
}

/**
 * SystemTooltip Component
 * Hover tooltip showing system information with route action buttons
 */
export const SystemTooltip = memo(function SystemTooltip({
  system,
  risk,
  getRegionName,
  viewport,
  mousePosition,
  isOnRoute = false,
  originMode = false,
  destinationMode = false,
  onSetOrigin,
  onSetDestination,
  onClose,
}: SystemTooltipProps) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  // Calculate tooltip position to stay within viewport
  useEffect(() => {
    if (!system || !tooltipRef.current) return;

    const tooltip = tooltipRef.current;
    const tooltipRect = tooltip.getBoundingClientRect();
    const padding = 16;

    let x = mousePosition.x + 16;
    let y = mousePosition.y + 16;

    // Adjust if tooltip would overflow right
    if (x + tooltipRect.width > viewport.width - padding) {
      x = mousePosition.x - tooltipRect.width - 16;
    }

    // Adjust if tooltip would overflow bottom
    if (y + tooltipRect.height > viewport.height - padding) {
      y = mousePosition.y - tooltipRect.height - 16;
    }

    // Ensure minimum bounds
    x = Math.max(padding, x);
    y = Math.max(padding, y);

    setPosition({ x, y });
  }, [system, mousePosition, viewport]);

  if (!system) return null;

  const securityColor = getSecurityColor(system.security);
  const regionName = getRegionName?.(system.regionId) ?? `Region ${system.regionId}`;

  return (
    <div
      ref={tooltipRef}
      className="system-tooltip"
      style={{
        position: 'absolute',
        left: position.x,
        top: position.y,
        backgroundColor: 'rgba(17, 24, 39, 0.98)',
        borderRadius: 10,
        border: '1px solid rgba(75, 85, 99, 0.6)',
        padding: 12,
        pointerEvents: 'auto',
        zIndex: 200,
        minWidth: 220,
        maxWidth: 280,
        backdropFilter: 'blur(8px)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-base font-bold text-white truncate">{system.name}</h4>
          <p className="text-xs text-gray-400 truncate">{regionName}</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors p-1"
            title="Close"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>

      {/* Security Status */}
      <div className="flex items-center gap-3 mb-3 py-2 px-3 rounded-lg bg-gray-800/50">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm"
          style={{
            backgroundColor: `${securityColor}20`,
            color: securityColor,
            border: `2px solid ${securityColor}`,
          }}
        >
          {formatSecurity(system.security)}
        </div>
        <div>
          <div className="text-sm font-medium text-white">
            {getSecurityLabel(system.security)}
          </div>
          <div className="text-xs text-gray-400">Security Status</div>
        </div>
      </div>

      {/* Risk Information */}
      {risk && (
        <div className="mb-3 py-2 px-3 rounded-lg bg-gray-800/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400 uppercase tracking-wider">Risk Level</span>
            <div
              className="px-2 py-0.5 rounded text-xs font-bold uppercase"
              style={{
                backgroundColor: `${RISK_COLORS[risk.riskColor]}20`,
                color: RISK_COLORS[risk.riskColor],
              }}
            >
              {risk.riskColor}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div
                className="text-lg font-bold"
                style={{ color: RISK_COLORS[risk.riskColor] }}
              >
                {risk.riskScore.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">Score</div>
            </div>
            <div>
              <div className="text-lg font-bold text-red-400">{risk.recentKills}</div>
              <div className="text-xs text-gray-500">Kills</div>
            </div>
            <div>
              <div className="text-lg font-bold text-orange-400">{risk.recentPods}</div>
              <div className="text-xs text-gray-500">Pods</div>
            </div>
          </div>
        </div>
      )}

      {/* Route Status */}
      {isOnRoute && (
        <div className="mb-3 py-2 px-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
          <div className="flex items-center gap-2 text-blue-400 text-sm">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span className="font-medium">On Current Route</span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {(onSetOrigin || onSetDestination) && (
        <div className="flex gap-2">
          {onSetOrigin && (
            <button
              onClick={() => onSetOrigin(system.systemId)}
              className={`
                flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${originMode
                  ? 'bg-green-500 text-white hover:bg-green-600'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }
              `}
            >
              <div className="flex items-center justify-center gap-1.5">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="10" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <span>Set Origin</span>
              </div>
            </button>
          )}
          {onSetDestination && (
            <button
              onClick={() => onSetDestination(system.systemId)}
              className={`
                flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${destinationMode
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }
              `}
            >
              <div className="flex items-center justify-center gap-1.5">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                <span>Set Dest</span>
              </div>
            </button>
          )}
        </div>
      )}

      {/* System ID (debug/info) */}
      <div className="mt-3 pt-2 border-t border-gray-700/50">
        <span className="text-xs text-gray-500">
          System ID: {system.systemId}
        </span>
      </div>
    </div>
  );
});

export default SystemTooltip;
