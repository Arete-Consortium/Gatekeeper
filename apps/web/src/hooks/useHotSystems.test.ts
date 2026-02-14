import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement, type ReactNode } from 'react';
import { useHotSystems } from './useHotSystems';
import { GatekeeperAPI } from '@/lib/api';
import type { Mock } from 'vitest';

// Mock the API module
vi.mock('@/lib/api', () => ({
  GatekeeperAPI: {
    getHotSystems: vi.fn(),
  },
}));

const mockGetHotSystems = GatekeeperAPI.getHotSystems as Mock;

describe('useHotSystems', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return function Wrapper({ children }: { children: ReactNode }) {
      return createElement(QueryClientProvider, { client: queryClient }, children);
    };
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const mockHotSystems = [
    { system_id: 30003783, system_name: 'Tama', security: 0.3, category: 'low_sec', recent_kills: 150, recent_pods: 30 },
    { system_id: 30002537, system_name: 'Amamake', security: 0.4, category: 'low_sec', recent_kills: 120, recent_pods: 25 },
    { system_id: 30000142, system_name: 'Jita', security: 0.95, category: 'high_sec', recent_kills: 100, recent_pods: 10 },
  ];

  it('returns hot systems data on success', async () => {
    mockGetHotSystems.mockResolvedValueOnce(mockHotSystems);

    const { result } = renderHook(() => useHotSystems(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockHotSystems);
    expect(result.current.data).toHaveLength(3);
    expect(result.current.data?.[0].system_name).toBe('Tama');
  });

  it('fetches with default parameters (24 hours, 10 limit)', async () => {
    mockGetHotSystems.mockResolvedValueOnce(mockHotSystems);

    const { result } = renderHook(() => useHotSystems(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetHotSystems).toHaveBeenCalledWith(24, 10);
  });

  it('accepts custom time range parameter', async () => {
    mockGetHotSystems.mockResolvedValueOnce(mockHotSystems);

    const { result } = renderHook(() => useHotSystems(48), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetHotSystems).toHaveBeenCalledWith(48, 10);
  });

  it('accepts custom limit parameter', async () => {
    mockGetHotSystems.mockResolvedValueOnce(mockHotSystems);

    const { result } = renderHook(() => useHotSystems(24, 20), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetHotSystems).toHaveBeenCalledWith(24, 20);
  });

  it('accepts both custom hours and limit', async () => {
    mockGetHotSystems.mockResolvedValueOnce([]);

    const { result } = renderHook(() => useHotSystems(12, 5), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetHotSystems).toHaveBeenCalledWith(12, 5);
  });

  it('handles API errors', async () => {
    mockGetHotSystems.mockRejectedValueOnce(new Error('API Error: 503 Service Unavailable'));

    const { result } = renderHook(() => useHotSystems(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toBe('API Error: 503 Service Unavailable');
    expect(result.current.data).toBeUndefined();
  });

  it('returns loading state initially', () => {
    mockGetHotSystems.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useHotSystems(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('transitions from loading to success', async () => {
    mockGetHotSystems.mockResolvedValueOnce(mockHotSystems);

    const { result } = renderHook(() => useHotSystems(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeDefined();
  });

  it('uses correct query key including hours and limit', async () => {
    mockGetHotSystems.mockResolvedValueOnce(mockHotSystems);

    renderHook(() => useHotSystems(48, 15), { wrapper: createWrapper() });

    await waitFor(() => expect(mockGetHotSystems).toHaveBeenCalled());

    const queryState = queryClient.getQueryState(['hotSystems', 48, 15]);
    expect(queryState).toBeDefined();
  });

  it('caches queries separately by parameters', async () => {
    mockGetHotSystems.mockResolvedValue(mockHotSystems);

    renderHook(() => useHotSystems(24, 10), { wrapper: createWrapper() });
    renderHook(() => useHotSystems(48, 10), { wrapper: createWrapper() });

    await waitFor(() => expect(mockGetHotSystems).toHaveBeenCalledTimes(2));

    expect(queryClient.getQueryState(['hotSystems', 24, 10])).toBeDefined();
    expect(queryClient.getQueryState(['hotSystems', 48, 10])).toBeDefined();
  });

  it('returns empty array when no hot systems exist', async () => {
    mockGetHotSystems.mockResolvedValueOnce([]);

    const { result } = renderHook(() => useHotSystems(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });
});
