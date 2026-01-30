'use client';

import { memo, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { KillFeedProps, MapKill, MapSystem, MapViewport } from './types';
import { formatIsk } from '@/lib/utils';

/**
 * Colors for kill markers
 */
const KILL_COLORS = {
  ship: '#ff453a', // Red for ships
  pod: '#ff9f0a',  // Orange for pods
  glow: 'rgba(255, 69, 58, 0.6)',
  podGlow: 'rgba(255, 159, 10, 0.6)',
} as const;

/**
 * Calculate marker size based on kill value
 */
function getMarkerSize(value: number): number {
  // Log scale for value, clamped between 6 and 24 pixels
  const logValue = Math.log10(value + 1);
  const size = Math.max(6, Math.min(24, logValue * 2.5));
  return size;
}

/**
 * Calculate opacity based on age
 */
function getOpacity(timestamp: number, maxAge: number): number {
  const age = Date.now() - timestamp;
  const ageRatio = age / maxAge;
  // Fade from 1 to 0.3 over lifetime
  return Math.max(0.3, 1 - ageRatio * 0.7);
}

/**
 * Transform world coordinates to screen coordinates
 */
function worldToScreen(
  worldX: number,
  worldY: number,
  viewport: MapViewport
): { x: number; y: number } {
  const x = (worldX - viewport.x) * viewport.zoom + viewport.width / 2;
  const y = (worldY - viewport.y) * viewport.zoom + viewport.height / 2;
  return { x, y };
}

/**
 * Check if a point is visible in the viewport
 */
function isVisible(
  screenX: number,
  screenY: number,
  viewport: MapViewport,
  margin: number = 50
): boolean {
  return (
    screenX >= -margin &&
    screenX <= viewport.width + margin &&
    screenY >= -margin &&
    screenY <= viewport.height + margin
  );
}

interface KillMarkerProps {
  kill: MapKill;
  system: MapSystem;
  viewport: MapViewport;
  maxAge: number;
}

/**
 * Individual kill marker with pulse animation
 * Memoized to prevent unnecessary re-renders when viewport changes don't affect visibility
 */
const KillMarker = memo(function KillMarker({ kill, system, viewport, maxAge }: KillMarkerProps) {
  const screenPos = worldToScreen(system.x, system.y, viewport);

  // Skip if not visible
  if (!isVisible(screenPos.x, screenPos.y, viewport)) {
    return null;
  }

  const size = getMarkerSize(kill.value);
  const opacity = getOpacity(kill.timestamp, maxAge);
  const color = kill.isPod ? KILL_COLORS.pod : KILL_COLORS.ship;
  const glowColor = kill.isPod ? KILL_COLORS.podGlow : KILL_COLORS.glow;

  // Age in minutes for tooltip
  const ageMinutes = Math.floor((Date.now() - kill.timestamp) / 60000);
  const ageText = ageMinutes < 1 ? 'Just now' : `${ageMinutes}m ago`;

  return (
    <motion.div
      key={kill.killId}
      className="absolute pointer-events-auto cursor-pointer group"
      style={{
        left: screenPos.x,
        top: screenPos.y,
        transform: 'translate(-50%, -50%)',
      }}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity }}
      exit={{ scale: 0, opacity: 0 }}
      transition={{
        type: 'spring',
        stiffness: 500,
        damping: 25,
        mass: 0.5,
      }}
    >
      {/* Outer pulse ring */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: size * 3,
          height: size * 3,
          left: -(size * 3) / 2 + size / 2,
          top: -(size * 3) / 2 + size / 2,
          background: `radial-gradient(circle, ${glowColor} 0%, transparent 70%)`,
        }}
        initial={{ scale: 0.5, opacity: 0.8 }}
        animate={{
          scale: [0.5, 1.5],
          opacity: [0.8, 0],
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeOut',
        }}
      />

      {/* Secondary pulse ring (delayed) */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: size * 2.5,
          height: size * 2.5,
          left: -(size * 2.5) / 2 + size / 2,
          top: -(size * 2.5) / 2 + size / 2,
          background: `radial-gradient(circle, ${glowColor} 0%, transparent 60%)`,
        }}
        initial={{ scale: 0.5, opacity: 0.6 }}
        animate={{
          scale: [0.5, 1.3],
          opacity: [0.6, 0],
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeOut',
          delay: 0.3,
        }}
      />

      {/* Core marker */}
      <motion.div
        className="relative rounded-full"
        style={{
          width: size,
          height: size,
          backgroundColor: color,
          boxShadow: `0 0 ${size}px ${color}, 0 0 ${size * 2}px ${glowColor}`,
        }}
        animate={{
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 0.5,
          repeat: Infinity,
          repeatDelay: 1,
        }}
      />

      {/* Tooltip on hover */}
      <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
        <div className="bg-surface-elevated border border-border rounded-lg px-3 py-2 shadow-lg whitespace-nowrap text-sm">
          <div className="font-medium text-text">
            {kill.isPod ? 'Pod Kill' : kill.shipType}
          </div>
          <div className="text-text-secondary">
            {formatIsk(kill.value)} | {ageText}
          </div>
          <div className="text-text-secondary text-xs">
            {system.name}
          </div>
        </div>
      </div>
    </motion.div>
  );
});

/**
 * Kill markers overlay for the map
 *
 * Renders animated markers at system locations where kills occurred.
 * Markers pulse red for ships, orange for pods.
 * Size based on kill value, opacity fades over time.
 *
 * Usage:
 * ```tsx
 * <KillMarkers
 *   kills={kills}
 *   systems={systemsMap}
 *   viewport={viewport}
 *   maxAge={3600000} // 1 hour
 * />
 * ```
 */
export function KillMarkers({
  kills,
  systems,
  viewport,
  maxAge = 60 * 60 * 1000, // 1 hour default
}: KillFeedProps) {
  // Filter kills that have valid systems and are within maxAge
  const visibleKills = useMemo(() => {
    const now = Date.now();
    return kills.filter((kill) => {
      const system = systems.get(kill.systemId);
      if (!system) return false;
      if (now - kill.timestamp > maxAge) return false;
      return true;
    });
  }, [kills, systems, maxAge]);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      <AnimatePresence mode="popLayout">
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
            />
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export default KillMarkers;
