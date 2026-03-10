'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import type { MapKill } from './types';
import { GatekeeperAPI } from '@/lib/api';

/**
 * zKillboard WebSocket killmail format (used for direct fallback)
 * @see https://github.com/zKillboard/zKillboard/wiki/Websocket
 */
interface ZKillboardKillmail {
  killmail_id: number;
  killmail_time: string;
  solar_system_id: number;
  victim: {
    alliance_id?: number;
    character_id?: number;
    corporation_id?: number;
    damage_taken?: number;
    ship_type_id: number;
  };
  attackers?: Array<{
    alliance_id?: number;
    character_id?: number;
    corporation_id?: number;
    damage_done?: number;
    final_blow?: boolean;
    ship_type_id?: number;
    weapon_type_id?: number;
  }>;
  zkb: {
    locationID?: number;
    hash: string;
    fittedValue: number;
    droppedValue: number;
    destroyedValue: number;
    totalValue: number;
    points: number;
    npc: boolean;
    solo: boolean;
    awox: boolean;
    labels?: string[];
    href?: string;
  };
}

/**
 * Backend WebSocket kill event data format
 * Sent from /ws/killfeed as { type: "kill", data: {...} }
 */
interface BackendKillData {
  kill_id: number;
  solar_system_id: number;
  solar_system_name?: string;
  region_id?: number;
  kill_time: string;
  ship_type_id: number;
  ship_type_name?: string;
  is_pod: boolean;
  total_value: number;
  risk_score?: number;
}

interface UseKillStreamOptions {
  /** Max age of kills to keep in milliseconds (default: 1 hour) */
  maxAge?: number;
  /** Max number of kills to keep in buffer */
  maxKills?: number;
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Max reconnect attempts before giving up (0 = infinite) */
  maxReconnectAttempts?: number;
  /** Filter by system IDs (empty = all systems) */
  systemFilter?: number[];
  /** Filter by region IDs (empty = all regions) */
  regionFilter?: number[];
  /** Enable mock data for development (can also use NEXT_PUBLIC_USE_MOCK_KILLS env var) */
  useMock?: boolean;
  /** Minimum ISK value to track (filters out cheap kills) */
  minValue?: number;
  /** Include pod kills (default: true) */
  includePods?: boolean;
}

interface UseKillStreamReturn {
  /** Recent kills */
  kills: MapKill[];
  /** WebSocket connection status */
  isConnected: boolean;
  /** Any connection error */
  error: string | null;
  /** Number of reconnect attempts */
  reconnectAttempts: number;
  /** Whether using mock data */
  isMock: boolean;
  /** Whether using direct zKillboard fallback */
  isFallback: boolean;
  /** Manually reconnect */
  reconnect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
  /** Clear all kills */
  clearKills: () => void;
}

// Pod type IDs in EVE Online
const POD_TYPE_IDS = [670, 33328]; // Capsule, Genolution CA-4

// Ship type ID to name mapping (common ships for display)
// In production, this would come from ESI or a static data export
const SHIP_TYPE_NAMES: Record<number, string> = {
  670: 'Capsule',
  33328: 'Capsule - Genolution CA-4',
  // Frigates
  587: 'Rifter',
  603: 'Punisher',
  599: 'Incursus',
  606: 'Tristan',
  // Cruisers
  621: 'Caracal',
  627: 'Thorax',
  24690: 'Hurricane',
  // Battleships
  638: 'Raven',
  641: 'Megathron',
  // Capitals
  23757: 'Archon',
  23911: 'Nyx',
  671: 'Erebus',
};

/**
 * Get ship name from type ID
 * Falls back to "Unknown Ship (ID)" if not in our lookup table
 */
function getShipTypeName(typeId: number): string {
  return SHIP_TYPE_NAMES[typeId] || `Ship #${typeId}`;
}

/**
 * Parse backend kill event data to MapKill format
 */
function parseBackendKill(data: BackendKillData): MapKill {
  return {
    killId: data.kill_id,
    systemId: data.solar_system_id,
    timestamp: new Date(data.kill_time).getTime(),
    shipType: data.ship_type_name || getShipTypeName(data.ship_type_id),
    value: data.total_value,
    isPod: data.is_pod,
  };
}

/**
 * Parse incoming zkillboard killmail to MapKill format (fallback)
 */
function parseZKillboardKillmail(killmail: ZKillboardKillmail): MapKill {
  const isPod = POD_TYPE_IDS.includes(killmail.victim.ship_type_id);

  return {
    killId: killmail.killmail_id,
    systemId: killmail.solar_system_id,
    timestamp: new Date(killmail.killmail_time).getTime(),
    shipType: getShipTypeName(killmail.victim.ship_type_id),
    value: killmail.zkb.totalValue,
    isPod,
  };
}

/**
 * Validate that a message is a valid zkillboard killmail
 */
function isValidKillmail(data: unknown): data is ZKillboardKillmail {
  if (!data || typeof data !== 'object') return false;
  const obj = data as Record<string, unknown>;
  return (
    typeof obj.killmail_id === 'number' &&
    typeof obj.solar_system_id === 'number' &&
    typeof obj.killmail_time === 'string' &&
    typeof obj.victim === 'object' &&
    obj.victim !== null &&
    typeof (obj.victim as Record<string, unknown>).ship_type_id === 'number' &&
    typeof obj.zkb === 'object' &&
    obj.zkb !== null &&
    typeof (obj.zkb as Record<string, unknown>).totalValue === 'number'
  );
}

/**
 * Validate that a message is a valid backend kill event
 */
function isValidBackendKill(data: unknown): data is BackendKillData {
  if (!data || typeof data !== 'object') return false;
  const obj = data as Record<string, unknown>;
  return (
    typeof obj.kill_id === 'number' &&
    typeof obj.solar_system_id === 'number' &&
    typeof obj.kill_time === 'string' &&
    typeof obj.ship_type_id === 'number' &&
    typeof obj.is_pod === 'boolean' &&
    typeof obj.total_value === 'number'
  );
}

/**
 * Generate mock kill data for development
 */
function generateMockKill(systemIds: number[]): MapKill {
  const isPod = Math.random() < 0.15; // 15% chance of pod
  const randomSystem = systemIds.length > 0
    ? systemIds[Math.floor(Math.random() * systemIds.length)]
    : 30000142 + Math.floor(Math.random() * 1000); // Default to random Jita-area systems

  const ships = [
    'Rifter', 'Caracal', 'Thorax', 'Drake', 'Hurricane',
    'Raven', 'Megathron', 'Abaddon', 'Maelstrom',
    'Nyx', 'Aeon', 'Erebus', 'Avatar',
  ];

  const values = [
    5_000_000, 25_000_000, 50_000_000, 100_000_000,
    500_000_000, 1_000_000_000, 5_000_000_000, 50_000_000_000,
  ];

  return {
    killId: Date.now() + Math.floor(Math.random() * 10000),
    systemId: randomSystem,
    timestamp: Date.now(),
    shipType: isPod ? 'Capsule' : ships[Math.floor(Math.random() * ships.length)],
    value: isPod ? 50_000_000 : values[Math.floor(Math.random() * values.length)],
    isPod,
  };
}

// Default zkillboard WebSocket URL (fallback)
const ZKILLBOARD_WS_URL = 'wss://zkillboard.com/websocket/';

/**
 * Convert an HTTP(S) base URL to a WebSocket URL for the backend killfeed.
 */
function getBackendWsUrl(): string {
  const baseUrl = GatekeeperAPI.getBaseUrl();
  const wsUrl = baseUrl
    .replace(/^https:\/\//, 'wss://')
    .replace(/^http:\/\//, 'ws://');
  // Strip trailing slash, append /api/v1/ws/killfeed
  return `${wsUrl.replace(/\/$/, '')}/api/v1/ws/killfeed`;
}

/**
 * Hook for streaming live kill data via WebSocket
 *
 * Connects to the backend's /ws/killfeed endpoint for filtered, enriched kill data.
 * Falls back to direct zKillboard WebSocket if the backend is unavailable.
 * Supports mock data mode for development.
 *
 * Usage:
 * ```tsx
 * // Backend kill feed (default)
 * const { kills, isConnected, error } = useKillStream();
 *
 * // Mock data for development
 * const { kills, isConnected } = useKillStream({ useMock: true });
 *
 * // Or set NEXT_PUBLIC_USE_MOCK_KILLS=true in .env.local
 * ```
 */
export function useKillStream(options: UseKillStreamOptions = {}): UseKillStreamReturn {
  // Check environment variable for mock mode
  const envUseMock = typeof window !== 'undefined' &&
    process.env.NEXT_PUBLIC_USE_MOCK_KILLS === 'true';

  const {
    maxAge = 60 * 60 * 1000, // 1 hour
    maxKills = 500,
    autoReconnect = true,
    reconnectDelay = 5000,
    maxReconnectAttempts = 10,
    systemFilter = [],
    regionFilter = [],
    useMock = envUseMock,
    minValue = 0,
    includePods = true,
  } = options;

  const [kills, setKills] = useState<MapKill[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [isFallback, setIsFallback] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mockIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const systemFilterRef = useRef(systemFilter);
  const regionFilterRef = useRef(regionFilter);
  const minValueRef = useRef(minValue);
  const reconnectAttemptsRef = useRef(0);
  const usingFallbackRef = useRef(false);

  // Update refs when options change
  useEffect(() => {
    systemFilterRef.current = systemFilter;
  }, [systemFilter]);

  useEffect(() => {
    regionFilterRef.current = regionFilter;
  }, [regionFilter]);

  useEffect(() => {
    minValueRef.current = minValue;
  }, [minValue]);

  /**
   * Add a new kill to the list, maintaining max size and age.
   * When using the backend, filtering is server-side; client-side filtering
   * is still applied for the zKillboard fallback path.
   */
  const addKill = useCallback((kill: MapKill) => {
    // Apply client-side system filter (primarily for fallback mode)
    if (systemFilterRef.current.length > 0 && !systemFilterRef.current.includes(kill.systemId)) {
      return;
    }

    // Apply minimum value filter (primarily for fallback mode)
    if (kill.value < minValueRef.current) {
      return;
    }

    setKills((prev) => {
      // Check for duplicate killmail_id
      if (prev.some((k) => k.killId === kill.killId)) {
        return prev;
      }

      const now = Date.now();
      // Filter out old kills and add new one
      const filtered = prev
        .filter((k) => now - k.timestamp < maxAge)
        .slice(0, maxKills - 1);
      return [kill, ...filtered];
    });
  }, [maxAge, maxKills]);

  /**
   * Clean up old kills periodically
   */
  useEffect(() => {
    const cleanup = setInterval(() => {
      const now = Date.now();
      setKills((prev) => prev.filter((k) => now - k.timestamp < maxAge));
    }, 60000); // Clean every minute

    return () => clearInterval(cleanup);
  }, [maxAge]);

  /**
   * Send subscription filters to the backend WebSocket
   */
  const sendSubscription = useCallback((ws: WebSocket) => {
    try {
      const subscribeMsg: Record<string, unknown> = {
        type: 'subscribe',
        systems: systemFilterRef.current.length > 0 ? systemFilterRef.current : [],
        regions: regionFilterRef.current.length > 0 ? regionFilterRef.current : [],
        min_value: minValueRef.current,
        include_pods: includePods,
      };
      ws.send(JSON.stringify(subscribeMsg));
    } catch (sendErr) {
      console.error('[useKillStream] Failed to send subscription:', sendErr);
    }
  }, [includePods]);

  /**
   * Connect to zKillboard WebSocket (fallback)
   */
  const connectToZKillboard = useCallback(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[useKillStream] Falling back to direct zKillboard connection');
    }

    usingFallbackRef.current = true;
    setIsFallback(true);

    try {
      const ws = new WebSocket(ZKILLBOARD_WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        setReconnectAttempts(0);

        // Subscribe to zKillboard kill stream
        try {
          ws.send(JSON.stringify({
            action: 'sub',
            channel: 'killstream',
          }));
        } catch (sendErr) {
          console.error('[useKillStream] Failed to send zKillboard subscription:', sendErr);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (isValidKillmail(data)) {
            const kill = parseZKillboardKillmail(data);
            addKill(kill);
          }
        } catch (parseErr) {
          if (process.env.NODE_ENV === 'development') {
            console.warn('[useKillStream] Failed to parse zKillboard message:', parseErr);
          }
        }
      };

      ws.onerror = () => {
        setError('zKillboard WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;
        handleClose(event);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to zKillboard');
      setIsConnected(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addKill]);

  /**
   * Handle WebSocket close with auto-reconnect logic
   */
  const handleClose = useCallback((event: CloseEvent) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[useKillStream] WebSocket closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
        fallback: usingFallbackRef.current,
      });
    }

    // Set error message based on close code
    if (event.code !== 1000 && event.code !== 1001) {
      const closeReasons: Record<number, string> = {
        1002: 'Protocol error',
        1003: 'Invalid data type',
        1006: 'Connection lost abnormally',
        1007: 'Invalid message data',
        1008: 'Policy violation',
        1009: 'Message too large',
        1010: 'Server didn\'t respond to extension request',
        1011: 'Server error',
        1015: 'TLS handshake failed',
      };
      setError(closeReasons[event.code] || `Connection closed (code: ${event.code})`);
    }

    // Auto-reconnect if enabled
    if (autoReconnect) {
      const shouldReconnect = maxReconnectAttempts === 0 ||
        reconnectAttemptsRef.current < maxReconnectAttempts;

      if (shouldReconnect) {
        reconnectAttemptsRef.current += 1;
        setReconnectAttempts(reconnectAttemptsRef.current);

        // Exponential backoff: base delay * 2^attempts, capped at 60 seconds
        const backoffDelay = Math.min(
          reconnectDelay * Math.pow(2, reconnectAttemptsRef.current - 1),
          60000
        );

        if (process.env.NODE_ENV === 'development') {
          console.log(`[useKillStream] Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttemptsRef.current})`);
        }

        reconnectTimeoutRef.current = setTimeout(connect, backoffDelay);
      } else {
        setError(`Max reconnect attempts (${maxReconnectAttempts}) exceeded. Call reconnect() to try again.`);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoReconnect, reconnectDelay, maxReconnectAttempts]);

  /**
   * Connect to WebSocket — tries backend first, falls back to zKillboard
   */
  const connect = useCallback(() => {
    // If using mock, don't connect to real WebSocket
    if (useMock) {
      setIsConnected(true);
      setError(null);
      reconnectAttemptsRef.current = 0;
      setReconnectAttempts(0);
      return;
    }

    // Check if we've exceeded max reconnect attempts
    if (maxReconnectAttempts > 0 && reconnectAttemptsRef.current >= maxReconnectAttempts) {
      setError(`Max reconnect attempts (${maxReconnectAttempts}) exceeded. Call reconnect() to try again.`);
      return;
    }

    // Don't create a new connection if one is already open or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    // If we already know the backend is down, go straight to fallback
    if (usingFallbackRef.current) {
      connectToZKillboard();
      return;
    }

    // Try backend WebSocket first
    const backendWsUrl = getBackendWsUrl();

    try {
      const ws = new WebSocket(backendWsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        setIsFallback(false);
        usingFallbackRef.current = false;
        reconnectAttemptsRef.current = 0;
        setReconnectAttempts(0);

        // Send subscription filters to backend
        sendSubscription(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'kill' && isValidBackendKill(data.data)) {
            const kill = parseBackendKill(data.data);
            addKill(kill);
          }
          // Other message types (connected, subscribed, pong, error) are
          // informational — log in dev mode, otherwise silently ignore
          else if (process.env.NODE_ENV === 'development' && data.type !== 'kill') {
            console.log('[useKillStream] Backend message:', data.type, data);
          }
        } catch (parseErr) {
          if (process.env.NODE_ENV === 'development') {
            console.warn('[useKillStream] Failed to parse backend message:', parseErr);
          }
        }
      };

      ws.onerror = () => {
        // Backend WS failed — fall back to zKillboard
        // The close handler will fire next; we prevent it from triggering
        // normal reconnect by cleaning up here
        console.warn('[useKillStream] Backend WebSocket failed, falling back to zKillboard');
        wsRef.current = null;

        // Suppress the onclose handler's reconnect for this specific ws
        ws.onclose = null;
        try { ws.close(); } catch { /* already closed */ }

        connectToZKillboard();
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // If the backend closes immediately (e.g., 404 / not running),
        // fall back to zKillboard on the first attempt
        if (reconnectAttemptsRef.current === 0 && event.code !== 1000) {
          connectToZKillboard();
          return;
        }

        handleClose(event);
      };
    } catch (err) {
      // WebSocket constructor can throw on invalid URL
      console.warn('[useKillStream] Backend WS construction failed, falling back to zKillboard:', err);
      connectToZKillboard();
    }
  }, [useMock, maxReconnectAttempts, addKill, sendSubscription, connectToZKillboard, handleClose]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (mockIntervalRef.current) {
      clearInterval(mockIntervalRef.current);
      mockIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.onclose = null; // Prevent reconnect on intentional disconnect
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  /**
   * Reconnect to WebSocket (resets reconnect attempt counter and fallback state)
   */
  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    setReconnectAttempts(0);
    usingFallbackRef.current = false;
    setIsFallback(false);
    disconnect();
    // Small delay to ensure clean disconnect before reconnecting
    setTimeout(connect, 100);
  }, [disconnect, connect]);

  /**
   * Clear all kills
   */
  const clearKills = useCallback(() => {
    setKills([]);
  }, []);

  /**
   * Mock data generator for development
   */
  useEffect(() => {
    if (!useMock) return;

    // Generate initial mock kills
    const initialKills: MapKill[] = [];
    for (let i = 0; i < 10; i++) {
      const kill = generateMockKill(systemFilter);
      // Spread timestamps over the last 30 minutes
      kill.timestamp = Date.now() - Math.random() * 30 * 60 * 1000;
      initialKills.push(kill);
    }
    setKills(initialKills.sort((a, b) => b.timestamp - a.timestamp));

    // Generate new kills every 5-15 seconds
    mockIntervalRef.current = setInterval(() => {
      if (Math.random() < 0.7) { // 70% chance each interval
        const kill = generateMockKill(systemFilter);
        addKill(kill);
      }
    }, 5000 + Math.random() * 10000);

    return () => {
      if (mockIntervalRef.current) {
        clearInterval(mockIntervalRef.current);
      }
    };
  }, [useMock, systemFilter, addKill]);

  /**
   * Re-send subscription filters when they change (backend mode only)
   */
  useEffect(() => {
    if (useMock || usingFallbackRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      sendSubscription(wsRef.current);
    }
  }, [systemFilter, regionFilter, minValue, includePods, useMock, sendSubscription]);

  /**
   * Connect on mount, disconnect on unmount.
   * Use refs to avoid reconnect loops from unstable callback deps.
   */
  const connectRef = useRef(connect);
  const disconnectRef = useRef(disconnect);
  connectRef.current = connect;
  disconnectRef.current = disconnect;

  useEffect(() => {
    connectRef.current();
    return () => disconnectRef.current();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    kills,
    isConnected,
    error,
    reconnectAttempts,
    isMock: useMock,
    isFallback,
    reconnect,
    disconnect,
    clearKills,
  };
}

export default useKillStream;
