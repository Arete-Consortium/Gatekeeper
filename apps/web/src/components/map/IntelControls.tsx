'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Eye,
  EyeOff,
  Flame,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Wifi,
  WifiOff,
  Crosshair,
  Skull,
  MapPin,
} from 'lucide-react';
import { Toggle } from '@/components/ui/Toggle';
import { cn } from '@/lib/utils';
import { RiskHeatmapLegend } from './RiskHeatmap';
import { RISK_COLORS } from './types';
import type { TimeRange } from './useIntelData';
import { TIME_RANGE_OPTIONS } from './useIntelData';

interface IntelControlsProps {
  /** Current time range */
  timeRange: TimeRange;
  /** Handler for time range change */
  onTimeRangeChange: (range: TimeRange) => void;
  /** Show kill markers toggle */
  showKillMarkers: boolean;
  /** Handler for kill markers toggle */
  onShowKillMarkersChange: (show: boolean) => void;
  /** Show heatmap toggle */
  showHeatmap: boolean;
  /** Handler for heatmap toggle */
  onShowHeatmapChange: (show: boolean) => void;
  /** Total kills count */
  totalKills: number;
  /** Total pod kills count */
  totalPods: number;
  /** WebSocket connection status */
  isConnected: boolean;
  /** Loading state */
  isLoading: boolean;
  /** Refresh handler */
  onRefresh: () => void;
  /** Optional class name */
  className?: string;
}

/**
 * Time range selector dropdown
 */
function TimeRangeSelect({
  value,
  onChange,
}: {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);

  const currentOption = TIME_RANGE_OPTIONS.find((opt) => opt.value === value);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg',
          'bg-surface-elevated border border-border',
          'hover:border-border-hover transition-colors',
          'text-sm font-medium text-text'
        )}
      >
        <span>{currentOption?.label || value}</span>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-text-secondary" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text-secondary" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />
            {/* Dropdown */}
            <motion.div
              className={cn(
                'absolute top-full left-0 mt-1 z-50',
                'bg-surface-elevated border border-border rounded-lg shadow-lg',
                'overflow-hidden min-w-[120px]'
              )}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.15 }}
            >
              {TIME_RANGE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-left text-sm',
                    'hover:bg-surface transition-colors',
                    option.value === value
                      ? 'text-primary bg-primary/10'
                      : 'text-text'
                  )}
                >
                  {option.label}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Kill count summary display
 */
function KillSummary({
  totalKills,
  totalPods,
}: {
  totalKills: number;
  totalPods: number;
}) {
  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-1.5">
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: RISK_COLORS.red }}
        />
        <Skull className="w-4 h-4 text-text-secondary" />
        <span className="text-sm font-medium text-text">{totalKills}</span>
        <span className="text-xs text-text-secondary">kills</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: RISK_COLORS.orange }}
        />
        <Crosshair className="w-4 h-4 text-text-secondary" />
        <span className="text-sm font-medium text-text">{totalPods}</span>
        <span className="text-xs text-text-secondary">pods</span>
      </div>
    </div>
  );
}

/**
 * Connection status indicator
 */
function ConnectionStatus({ isConnected }: { isConnected: boolean }) {
  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
        isConnected
          ? 'bg-risk-green/20 text-risk-green'
          : 'bg-risk-red/20 text-risk-red'
      )}
    >
      {isConnected ? (
        <>
          <Wifi className="w-3 h-3" />
          <span>Live</span>
        </>
      ) : (
        <>
          <WifiOff className="w-3 h-3" />
          <span>Offline</span>
        </>
      )}
    </div>
  );
}

/**
 * Intel layer controls panel
 *
 * Provides UI for:
 * - Time range selection
 * - Kill markers toggle
 * - Heatmap toggle
 * - Kill count summary
 * - Activity legend
 *
 * Usage:
 * ```tsx
 * <IntelControls
 *   timeRange="24h"
 *   onTimeRangeChange={setTimeRange}
 *   showKillMarkers={showKills}
 *   onShowKillMarkersChange={setShowKills}
 *   showHeatmap={showHeatmap}
 *   onShowHeatmapChange={setShowHeatmap}
 *   totalKills={150}
 *   totalPods={23}
 *   isConnected={true}
 *   isLoading={false}
 *   onRefresh={refresh}
 * />
 * ```
 */
export function IntelControls({
  timeRange,
  onTimeRangeChange,
  showKillMarkers,
  onShowKillMarkersChange,
  showHeatmap,
  onShowHeatmapChange,
  totalKills,
  totalPods,
  isConnected,
  isLoading,
  onRefresh,
  className,
}: IntelControlsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div
      className={cn(
        'bg-surface-elevated/95 backdrop-blur-sm border border-border rounded-lg shadow-lg',
        'overflow-hidden',
        className
      )}
    >
      {/* Header - always visible */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-surface/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          <span className="font-medium text-text">Intel</span>
          <ConnectionStatus isConnected={isConnected} />
        </div>
        <div className="flex items-center gap-2">
          {/* Refresh button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRefresh();
            }}
            disabled={isLoading}
            className={cn(
              'p-1.5 rounded-lg hover:bg-surface transition-colors',
              'text-text-secondary hover:text-text',
              isLoading && 'animate-spin'
            )}
            title="Refresh intel data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {/* Expand/collapse */}
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-text-secondary" />
          ) : (
            <ChevronDown className="w-4 h-4 text-text-secondary" />
          )}
        </div>
      </div>

      {/* Expandable content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-4 border-t border-border pt-3">
              {/* Time range and summary row */}
              <div className="flex items-center justify-between flex-wrap gap-3">
                <TimeRangeSelect
                  value={timeRange}
                  onChange={onTimeRangeChange}
                />
                <KillSummary totalKills={totalKills} totalPods={totalPods} />
              </div>

              {/* Layer toggles */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-text-secondary uppercase tracking-wide">
                  Layers
                </div>
                <div className="flex flex-col gap-2">
                  <Toggle
                    checked={showKillMarkers}
                    onChange={onShowKillMarkersChange}
                    label="Kill Markers"
                  />
                  <Toggle
                    checked={showHeatmap}
                    onChange={onShowHeatmapChange}
                    label="Risk Heatmap"
                  />
                </div>
              </div>

              {/* Legend */}
              {showHeatmap && (
                <div className="pt-2 border-t border-border">
                  <RiskHeatmapLegend />
                </div>
              )}

              {/* Activity indicators */}
              {showKillMarkers && (
                <div className="pt-2 border-t border-border">
                  <div className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2">
                    Kill Activity
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <div className="flex items-center gap-2">
                      <motion.div
                        className="w-3 h-3 rounded-full"
                        style={{
                          backgroundColor: RISK_COLORS.red,
                          boxShadow: `0 0 6px ${RISK_COLORS.red}`,
                        }}
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                      />
                      <span className="text-sm text-text">Ship kills</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <motion.div
                        className="w-3 h-3 rounded-full"
                        style={{
                          backgroundColor: RISK_COLORS.orange,
                          boxShadow: `0 0 6px ${RISK_COLORS.orange}`,
                        }}
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 1, repeat: Infinity, delay: 0.5 }}
                      />
                      <span className="text-sm text-text">Pod kills</span>
                    </div>
                    <div className="text-xs text-text-secondary mt-1">
                      Marker size indicates kill value
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Compact intel status for map overlay
 */
export function IntelStatusBadge({
  totalKills,
  totalPods,
  isConnected,
  onClick,
}: {
  totalKills: number;
  totalPods: number;
  isConnected: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 px-3 py-2 rounded-lg',
        'bg-surface-elevated/90 backdrop-blur-sm border border-border',
        'hover:border-border-hover transition-colors shadow-lg'
      )}
    >
      <div className="flex items-center gap-1.5">
        <Flame className="w-4 h-4 text-risk-orange" />
        <span className="text-sm font-medium text-text">
          {totalKills + totalPods}
        </span>
      </div>
      <div
        className={cn(
          'w-2 h-2 rounded-full',
          isConnected ? 'bg-risk-green' : 'bg-risk-red'
        )}
        style={{
          boxShadow: isConnected
            ? `0 0 4px ${RISK_COLORS.green}`
            : `0 0 4px ${RISK_COLORS.red}`,
        }}
      />
    </button>
  );
}

export default IntelControls;
