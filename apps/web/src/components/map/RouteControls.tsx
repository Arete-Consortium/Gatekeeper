'use client';

import { memo } from 'react';
import type { RouteProfile } from '@/lib/types';
import type { RouteSelectionMode, MapRouteState, RouteComparison } from './useMapRoute';

/**
 * Props for RouteControls component
 */
export interface RouteControlsProps {
  /** Current route state */
  state: MapRouteState;
  /** System name lookup */
  getSystemName: (systemId: number) => string | null;
  /** Whether route is loading */
  isLoading: boolean;
  /** Route error if any */
  error: Error | null;
  /** Route comparisons for multi-profile display */
  comparisons?: RouteComparison[];
  /** Route summary (jumps, risk) from primary route */
  routeSummary?: {
    jumps: number;
    maxRisk: number;
    avgRisk: number;
  } | null;

  /** Actions */
  onModeChange: (mode: RouteSelectionMode) => void;
  onProfileChange: (profile: RouteProfile) => void;
  onBridgesChange: (enabled: boolean) => void;
  onTheraChange: (enabled: boolean) => void;
  onClearRoute: () => void;
  onSwapRoute: () => void;
}

/**
 * Profile display info
 */
const PROFILES: { value: RouteProfile; label: string; description: string; color: string }[] = [
  {
    value: 'safer',
    label: 'Safer',
    description: 'Balanced - avoids high risk',
    color: '#32d74b',
  },
  {
    value: 'shortest',
    label: 'Shortest',
    description: 'Fewest jumps, ignores risk',
    color: '#ffd60a',
  },
  {
    value: 'paranoid',
    label: 'Paranoid',
    description: 'Maximum risk avoidance',
    color: '#30b0ff',
  },
];

/**
 * Get risk color for display
 */
function getRiskDisplayColor(risk: number): string {
  if (risk < 3) return '#32d74b';
  if (risk < 5) return '#ffd60a';
  if (risk < 7) return '#ff9f0a';
  return '#ff453a';
}

/**
 * Selection button component
 */
const SelectionButton = memo(function SelectionButton({
  mode,
  currentMode,
  label,
  systemId,
  systemName,
  onClick,
}: {
  mode: RouteSelectionMode;
  currentMode: RouteSelectionMode;
  label: string;
  systemId: number | null;
  systemName: string | null;
  onClick: () => void;
}) {
  const isActive = currentMode === mode;
  const hasSelection = systemId !== null;

  return (
    <button
      onClick={onClick}
      className={`
        flex-1 px-3 py-2 rounded-lg border-2 transition-all duration-200
        ${isActive
          ? 'border-blue-500 bg-blue-500/20 text-blue-400'
          : hasSelection
            ? 'border-green-500/50 bg-green-500/10 text-green-400'
            : 'border-gray-600 bg-gray-800/50 text-gray-400 hover:border-gray-500'
        }
      `}
    >
      <div className="text-xs font-medium uppercase tracking-wider mb-1">
        {isActive ? `Click ${label}` : label}
      </div>
      <div className="text-sm font-semibold truncate">
        {systemName || (isActive ? 'Waiting...' : 'Not set')}
      </div>
    </button>
  );
});

/**
 * RouteControls Component
 * UI for route planning on the map
 */
export function RouteControls({
  state,
  getSystemName,
  isLoading,
  error,
  comparisons,
  routeSummary,
  onModeChange,
  onProfileChange,
  onBridgesChange,
  onTheraChange,
  onClearRoute,
  onSwapRoute,
}: RouteControlsProps) {
  const originName = state.originId ? getSystemName(state.originId) : null;
  const destinationName = state.destinationId ? getSystemName(state.destinationId) : null;
  const hasRoute = state.originId !== null && state.destinationId !== null;

  return (
    <div
      className="route-controls absolute top-3 left-3 sm:top-4 sm:left-4 w-[calc(100%-24px)] sm:w-80 max-w-[320px] z-[100] pointer-events-auto"
      style={{
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        borderRadius: 12,
        border: '1px solid rgba(75, 85, 99, 0.5)',
        padding: 16,
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">Route Planner</h3>
        {hasRoute && (
          <button
            onClick={onClearRoute}
            className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Origin/Destination Selection */}
      <div className="flex gap-2 mb-4">
        <SelectionButton
          mode="origin"
          currentMode={state.mode}
          label="Origin"
          systemId={state.originId}
          systemName={originName}
          onClick={() => onModeChange(state.mode === 'origin' ? 'idle' : 'origin')}
        />
        <button
          onClick={onSwapRoute}
          disabled={!hasRoute}
          className="px-2 py-2 rounded-lg border border-gray-600 bg-gray-800/50 text-gray-400 hover:bg-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Swap origin and destination"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M7 16V4M7 4L3 8M7 4L11 8" />
            <path d="M17 8V20M17 20L21 16M17 20L13 16" />
          </svg>
        </button>
        <SelectionButton
          mode="destination"
          currentMode={state.mode}
          label="Destination"
          systemId={state.destinationId}
          systemName={destinationName}
          onClick={() => onModeChange(state.mode === 'destination' ? 'idle' : 'destination')}
        />
      </div>

      {/* Profile Selector */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
          Route Profile
        </label>
        <div className="grid grid-cols-3 gap-2">
          {PROFILES.map(({ value, label, description, color }) => (
            <button
              key={value}
              onClick={() => onProfileChange(value)}
              className={`
                px-2 py-2 rounded-lg border transition-all duration-200 text-left
                ${state.profile === value
                  ? 'border-current bg-current/10'
                  : 'border-gray-600 bg-gray-800/30 hover:border-gray-500'
                }
              `}
              style={{ color: state.profile === value ? color : undefined }}
              title={description}
            >
              <div className="text-xs font-bold">{label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Route Options */}
      <div className="flex gap-4 mb-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={state.bridges}
            onChange={(e) => onBridgesChange(e.target.checked)}
            className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          />
          <span className="text-sm text-gray-300">Jump Bridges</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={state.thera}
            onChange={(e) => onTheraChange(e.target.checked)}
            className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          />
          <span className="text-sm text-gray-300">Thera</span>
        </label>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center gap-2 py-3 text-blue-400">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span className="text-sm">Calculating route...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="py-3 px-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error.message || 'Failed to calculate route'}
        </div>
      )}

      {/* Route Summary */}
      {routeSummary && !isLoading && !error && (
        <div className="py-3 px-3 rounded-lg bg-gray-800/50 border border-gray-700">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-white">{routeSummary.jumps}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Jumps</div>
            </div>
            <div>
              <div
                className="text-2xl font-bold"
                style={{ color: getRiskDisplayColor(routeSummary.maxRisk) }}
              >
                {routeSummary.maxRisk.toFixed(1)}
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Max Risk</div>
            </div>
            <div>
              <div
                className="text-2xl font-bold"
                style={{ color: getRiskDisplayColor(routeSummary.avgRisk) }}
              >
                {routeSummary.avgRisk.toFixed(1)}
              </div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Avg Risk</div>
            </div>
          </div>
        </div>
      )}

      {/* Route Comparisons */}
      {comparisons && comparisons.length > 0 && hasRoute && !isLoading && (
        <div className="mt-4">
          <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            Compare Profiles
          </div>
          <div className="space-y-2">
            {comparisons.map((comparison) => {
              const profileInfo = PROFILES.find((p) => p.value === comparison.profile);
              return (
                <button
                  key={comparison.profile}
                  onClick={() => onProfileChange(comparison.profile)}
                  className={`
                    w-full px-3 py-2 rounded-lg border transition-all duration-200 text-left
                    flex items-center justify-between
                    ${state.profile === comparison.profile
                      ? 'border-current bg-current/10'
                      : 'border-gray-700 bg-gray-800/30 hover:border-gray-600'
                    }
                  `}
                  style={{
                    color: state.profile === comparison.profile ? profileInfo?.color : undefined,
                  }}
                >
                  <span className="font-medium">{profileInfo?.label}</span>
                  {comparison.isLoading ? (
                    <span className="text-xs text-gray-500">Loading...</span>
                  ) : comparison.route ? (
                    <span className="text-sm">
                      <span className="font-bold">{comparison.route.total_jumps}</span>
                      <span className="text-gray-500 ml-1">jumps</span>
                      <span className="mx-2 text-gray-600">|</span>
                      <span
                        className="font-bold"
                        style={{ color: getRiskDisplayColor(comparison.route.max_risk) }}
                      >
                        {comparison.route.max_risk.toFixed(1)}
                      </span>
                      <span className="text-gray-500 ml-1">risk</span>
                    </span>
                  ) : comparison.error ? (
                    <span className="text-xs text-red-400">Error</span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Instructions when no route */}
      {!hasRoute && state.mode === 'idle' && (
        <div className="text-center py-4 text-gray-500 text-sm">
          Click <span className="text-blue-400">Origin</span> or{' '}
          <span className="text-blue-400">Destination</span> above, then click a system on the map
        </div>
      )}
    </div>
  );
}

export default RouteControls;
