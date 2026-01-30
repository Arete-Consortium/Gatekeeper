'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import type { MapKill } from './types';

/**
 * zKillboard WebSocket killmail format
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

interface UseKillStreamOptions {
  /** WebSocket URL for kill feed (defaults to zkillboard) */
  wsUrl?: string;
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
  /** Enable mock data for development (can also use NEXT_PUBLIC_USE_MOCK_KILLS env var) */
  useMock?: boolean;
  /** Minimum ISK value to track (filters out cheap kills) */
  minValue?: number;
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
 * Parse incoming zkillboard killmail to MapKill format
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

// Default zkillboard WebSocket URL
const ZKILLBOARD_WS_URL = 'wss://zkillboard.com/websocket/';

/**
 * Hook for streaming live kill data via WebSocket
 *
 * Connects to zKillboard's WebSocket API to receive real-time killmail data.
 * Supports both real and mock data modes for development.
 *
 * Usage:
 * ```tsx
 * // Real zkillboard data
 * const { kills, isConnected, error } = useKillStream();
 *
 * // Mock data for development
 * const { kills, isConnected } = useKillStream({ useMock: true });
 *
 * // Or set NEXT_PUBLIC_USE_MOCK_KILLS=true in .env.local
 * ```
 *
 * @see https://github.com/zKillboard/zKillboard/wiki/Websocket
 */
export function useKillStream(options: UseKillStreamOptions = {}): UseKillStreamReturn {
  // Check environment variable for mock mode
  const envUseMock = typeof window !== 'undefined' &&
    process.env.NEXT_PUBLIC_USE_MOCK_KILLS === 'true';

  const {
    wsUrl = ZKILLBOARD_WS_URL,
    maxAge = 60 * 60 * 1000, // 1 hour
    maxKills = 500,
    autoReconnect = true,
    reconnectDelay = 5000,
    maxReconnectAttempts = 10,
    systemFilter = [],
    useMock = envUseMock,
    minValue = 0,
  } = options;

  const [kills, setKills] = useState<MapKill[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mockIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const systemFilterRef = useRef(systemFilter);
  const minValueRef = useRef(minValue);
  const reconnectAttemptsRef = useRef(0);

  // Update refs when options change
  useEffect(() => {
    systemFilterRef.current = systemFilter;
  }, [systemFilter]);

  useEffect(() => {
    minValueRef.current = minValue;
  }, [minValue]);

  /**
   * Add a new kill to the list, maintaining max size and age
   */
  const addKill = useCallback((kill: MapKill) => {
    // Apply system filter if configured
    if (systemFilterRef.current.length > 0 && !systemFilterRef.current.includes(kill.systemId)) {
      return;
    }

    // Apply minimum value filter
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
   * Connect to WebSocket
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

    try {
      // Don't create a new connection if one is already open or connecting
      if (wsRef.current?.readyState === WebSocket.OPEN ||
          wsRef.current?.readyState === WebSocket.CONNECTING) {
        return;
      }

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        setReconnectAttempts(0);

        // Subscribe to kill stream
        // @see https://github.com/zKillboard/zKillboard/wiki/Websocket
        try {
          ws.send(JSON.stringify({
            action: 'sub',
            channel: 'killstream',
          }));
        } catch (sendErr) {
          console.error('[useKillStream] Failed to send subscription:', sendErr);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // zKillboard sends killmails directly (not wrapped in a type/payload structure)
          // Validate the message structure before processing
          if (isValidKillmail(data)) {
            const kill = parseZKillboardKillmail(data);
            addKill(kill);
          }
          // Silently ignore other message types (heartbeats, etc.)
        } catch (parseErr) {
          // Log parse errors in development for debugging
          if (process.env.NODE_ENV === 'development') {
            console.warn('[useKillStream] Failed to parse message:', parseErr);
          }
        }
      };

      ws.onerror = (event) => {
        // WebSocket errors are often just "connection failed" without details
        // The close event will follow with more info
        console.error('[useKillStream] WebSocket error:', event);
        setError('WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // Log close reason for debugging
        if (process.env.NODE_ENV === 'development') {
          console.log('[useKillStream] WebSocket closed:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean,
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

        // Auto-reconnect if enabled and we haven't exceeded max attempts
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
          }
        }
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
      setIsConnected(false);
    }
  }, [wsUrl, autoReconnect, reconnectDelay, maxReconnectAttempts, addKill, useMock]);

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
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  /**
   * Reconnect to WebSocket (resets reconnect attempt counter)
   */
  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    setReconnectAttempts(0);
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
   * Connect on mount, disconnect on unmount
   */
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return {
    kills,
    isConnected,
    error,
    reconnectAttempts,
    isMock: useMock,
    reconnect,
    disconnect,
    clearKills,
  };
}

export default useKillStream;
