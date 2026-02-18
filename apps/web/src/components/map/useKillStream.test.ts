import { renderHook, act, waitFor } from '@testing-library/react';
import { useKillStream } from './useKillStream';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async open
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 0);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  // Helper to simulate incoming message
  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  // Helper to simulate close
  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code, reason, wasClean: code === 1000 } as CloseEvent);
  }

  // Helper to simulate error
  simulateError() {
    this.onerror?.(new Event('error'));
  }
}

// Store references to created WebSocket instances
let wsInstances: MockWebSocket[] = [];

vi.stubGlobal('WebSocket', class extends MockWebSocket {
  constructor(url: string) {
    super(url);
    wsInstances.push(this);
  }
});

// Also set the static properties on the global
const MockWS = (globalThis as unknown as Record<string, Record<string, unknown>>).WebSocket;
MockWS.CONNECTING = 0;
MockWS.OPEN = 1;
MockWS.CLOSING = 2;
MockWS.CLOSED = 3;

describe('useKillStream', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    wsInstances = [];
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  function createValidKillmail(overrides: Record<string, unknown> = {}) {
    return {
      killmail_id: 12345,
      killmail_time: '2024-01-15T12:00:00Z',
      solar_system_id: 30000142,
      victim: {
        ship_type_id: 621,
        character_id: 1,
        corporation_id: 1,
        damage_taken: 5000,
      },
      attackers: [],
      zkb: {
        hash: 'abc123',
        fittedValue: 10000000,
        droppedValue: 5000000,
        destroyedValue: 5000000,
        totalValue: 25000000,
        points: 10,
        npc: false,
        solo: false,
        awox: false,
      },
      ...overrides,
    };
  }

  it('initializes with empty state', () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    expect(result.current.kills).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.reconnectAttempts).toBe(0);
    expect(result.current.isMock).toBe(false);
  });

  it('establishes WebSocket connection on mount', async () => {
    renderHook(() => useKillStream({ autoReconnect: false }));

    // Advance timers to trigger the onopen callback
    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(wsInstances).toHaveLength(1);
    expect(wsInstances[0].url).toBe('wss://zkillboard.com/websocket/');
  });

  it('connects to custom WebSocket URL', async () => {
    renderHook(() =>
      useKillStream({
        wsUrl: 'wss://custom.example.com/ws',
        autoReconnect: false,
      })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(wsInstances[0].url).toBe('wss://custom.example.com/ws');
  });

  it('sends subscription message on connect', async () => {
    renderHook(() => useKillStream({ autoReconnect: false }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const ws = wsInstances[0];
    expect(ws.send).toHaveBeenCalledWith(
      JSON.stringify({ action: 'sub', channel: 'killstream' })
    );
  });

  it('sets isConnected to true after connection opens', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(result.current.isConnected).toBe(true);
  });

  it('handles incoming kill events', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const killmail = createValidKillmail();

    act(() => {
      wsInstances[0].simulateMessage(killmail);
    });

    expect(result.current.kills).toHaveLength(1);
    expect(result.current.kills[0].killId).toBe(12345);
    expect(result.current.kills[0].systemId).toBe(30000142);
    expect(result.current.kills[0].value).toBe(25000000);
  });

  it('identifies pod kills correctly', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const podKillmail = createValidKillmail({
      killmail_id: 99999,
      victim: { ship_type_id: 670, character_id: 1, corporation_id: 1, damage_taken: 100 },
    });

    act(() => {
      wsInstances[0].simulateMessage(podKillmail);
    });

    expect(result.current.kills[0].isPod).toBe(true);
    expect(result.current.kills[0].shipType).toBe('Capsule');
  });

  it('deduplicates kills with same killmail_id', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const killmail = createValidKillmail();

    act(() => {
      wsInstances[0].simulateMessage(killmail);
      wsInstances[0].simulateMessage(killmail);
    });

    expect(result.current.kills).toHaveLength(1);
  });

  it('sets error on WebSocket close with non-normal code', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    act(() => {
      wsInstances[0].simulateClose(1006, 'Connection lost abnormally');
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBe('Connection lost abnormally');
  });

  it('sets error on WebSocket error event', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    act(() => {
      wsInstances[0].simulateError();
    });

    expect(result.current.error).toBe('WebSocket connection error');
    expect(result.current.isConnected).toBe(false);
  });

  it('provides disconnect function', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(result.current.isConnected).toBe(true);

    act(() => {
      result.current.disconnect();
    });

    expect(result.current.isConnected).toBe(false);
  });

  it('provides clearKills function', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    act(() => {
      wsInstances[0].simulateMessage(createValidKillmail({ killmail_id: 1 }));
      wsInstances[0].simulateMessage(createValidKillmail({ killmail_id: 2 }));
    });

    expect(result.current.kills).toHaveLength(2);

    act(() => {
      result.current.clearKills();
    });

    expect(result.current.kills).toHaveLength(0);
  });

  it('runs in mock mode when useMock is true', async () => {
    const { result } = renderHook(() =>
      useKillStream({ useMock: true })
    );

    expect(result.current.isMock).toBe(true);

    // In mock mode, it should set isConnected without actually creating a WS
    // and generate initial kills
    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.kills.length).toBeGreaterThan(0);
  });

  it('ignores invalid messages', async () => {
    const { result } = renderHook(() =>
      useKillStream({ autoReconnect: false })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    act(() => {
      wsInstances[0].simulateMessage({ type: 'heartbeat' });
      wsInstances[0].simulateMessage({ invalid: 'data' });
    });

    expect(result.current.kills).toHaveLength(0);
  });
});
