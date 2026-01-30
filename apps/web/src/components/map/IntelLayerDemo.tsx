'use client';

import { useState, useMemo } from 'react';
import { KillMarkers } from './KillMarkers';
import { RiskHeatmap } from './RiskHeatmap';
import { IntelControls, IntelStatusBadge } from './IntelControls';
import { useKillStream } from './useKillStream';
import { useIntelData } from './useIntelData';
import type { MapSystem, MapViewport, MapKill, SystemRisk } from './types';

/**
 * Demo component showing Intel Layer integration
 *
 * This component demonstrates how to use:
 * - useKillStream for live kill data
 * - useIntelData for risk analysis
 * - KillMarkers for visualizing kills on the map
 * - RiskHeatmap for system risk visualization
 * - IntelControls for user controls
 */
export function IntelLayerDemo() {
  // Layer visibility state
  const [showKillMarkers, setShowKillMarkers] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true);

  // Kill stream - uses NEXT_PUBLIC_USE_MOCK_KILLS env var or can override with useMock
  const {
    kills,
    isConnected,
    isMock,
    reconnectAttempts,
    error: streamError,
    reconnect,
  } = useKillStream({
    maxAge: 60 * 60 * 1000, // 1 hour
    maxKills: 100,
    maxReconnectAttempts: 5,
  });

  // Intel data (combines API data with live kills)
  const {
    risks,
    hotSystems,
    totalKills,
    totalPods,
    isLoading,
    error: dataError,
    timeRange,
    setTimeRange,
    refresh,
  } = useIntelData({
    timeRange: '24h',
    kills,
  });

  // Mock viewport for demo
  const viewport: MapViewport = useMemo(() => ({
    x: 0,
    y: 0,
    zoom: 1,
    width: 800,
    height: 600,
  }), []);

  // Mock systems map for demo (would come from map data in real usage)
  const systems: Map<number, MapSystem> = useMemo(() => {
    const map = new Map<number, MapSystem>();

    // Generate some mock systems
    const mockSystems: MapSystem[] = [
      { systemId: 30000142, name: 'Jita', x: 0, y: 0, security: 0.95, regionId: 10000002, constellationId: 20000020 },
      { systemId: 30002187, name: 'Amarr', x: 200, y: 100, security: 1.0, regionId: 10000043, constellationId: 20000322 },
      { systemId: 30002659, name: 'Dodixie', x: -150, y: 50, security: 0.87, regionId: 10000032, constellationId: 20000387 },
      { systemId: 30002510, name: 'Rens', x: 100, y: -100, security: 0.9, regionId: 10000030, constellationId: 20000366 },
      { systemId: 30002053, name: 'Hek', x: 50, y: -150, security: 0.54, regionId: 10000042, constellationId: 20000304 },
      { systemId: 30002718, name: 'HED-GP', x: 300, y: -200, security: -0.58, regionId: 10000014, constellationId: 20000397 },
      { systemId: 30003793, name: 'EC-P8R', x: -200, y: -100, security: -0.42, regionId: 10000010, constellationId: 20000554 },
    ];

    for (const sys of mockSystems) {
      map.set(sys.systemId, sys);
    }

    return map;
  }, []);

  return (
    <div className="relative w-full h-screen bg-background">
      {/* Map area (placeholder) */}
      <div className="absolute inset-0 bg-surface flex items-center justify-center">
        <div className="text-text-secondary text-lg">
          Map Canvas Would Render Here
        </div>

        {/* Intel overlays */}
        {showHeatmap && (
          <RiskHeatmap
            risks={risks}
            systems={systems}
            viewport={viewport}
            opacity={0.7}
          />
        )}

        {showKillMarkers && (
          <KillMarkers
            kills={kills}
            systems={systems}
            viewport={viewport}
            maxAge={60 * 60 * 1000}
          />
        )}
      </div>

      {/* Intel controls panel */}
      <div className="absolute top-4 right-4 w-80">
        <IntelControls
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
          showKillMarkers={showKillMarkers}
          onShowKillMarkersChange={setShowKillMarkers}
          showHeatmap={showHeatmap}
          onShowHeatmapChange={setShowHeatmap}
          totalKills={totalKills}
          totalPods={totalPods}
          isConnected={isConnected}
          isLoading={isLoading}
          onRefresh={refresh}
        />
      </div>

      {/* Compact status badge (alternative) */}
      <div className="absolute bottom-4 right-4">
        <IntelStatusBadge
          totalKills={totalKills}
          totalPods={totalPods}
          isConnected={isConnected}
        />
      </div>

      {/* Debug panel */}
      <div className="absolute bottom-4 left-4 bg-surface-elevated/90 border border-border rounded-lg p-4 text-sm max-w-sm">
        <h3 className="font-medium text-text mb-2">Debug Info</h3>
        <div className="space-y-1 text-text-secondary">
          <div>Kills in memory: {kills.length}</div>
          <div>Risk entries: {risks.length}</div>
          <div>Hot systems: {hotSystems.length}</div>
          <div>Stream mode: {isMock ? 'Mock' : 'Live'}</div>
          <div>Stream connected: {isConnected ? 'Yes' : 'No'}</div>
          {reconnectAttempts > 0 && <div>Reconnect attempts: {reconnectAttempts}</div>}
          {streamError && <div className="text-risk-red">Stream error: {streamError}</div>}
          {dataError && <div className="text-risk-red">Data error: {dataError}</div>}
        </div>
      </div>
    </div>
  );
}

export default IntelLayerDemo;
