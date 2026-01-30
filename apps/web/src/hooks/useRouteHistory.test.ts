import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement, ReactNode } from 'react';
import { useRouteHistory } from './useRouteHistory';
import { GatekeeperAPI } from '@/lib/api';

// Mock the API module
vi.mock('@/lib/api', () => ({
  GatekeeperAPI: {
    getRouteHistory: vi.fn(),
  },
}));

const mockGetRouteHistory = GatekeeperAPI.getRouteHistory as Mock;

describe('useRouteHistory', () => {
  let queryClient: QueryClient;

  const createWrapper = () => {
    return function Wrapper({ children }: { children: ReactNode }) {
      return createElement(QueryClientProvider, { client: queryClient }, children);
    };
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  describe('successful queries', () => {
    it('fetches route history with default limit', async () => {
      const mockData = {
        items: [
          { from_system: 'Jita', to_system: 'Amarr', profile: 'safer', jumps: 15, timestamp: '2024-01-15T12:00:00Z' },
        ],
        pagination: { total: 1, limit: 10, offset: 0 },
      };
      mockGetRouteHistory.mockResolvedValueOnce(mockData);

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockGetRouteHistory).toHaveBeenCalledWith(10);
      expect(result.current.data).toEqual(mockData);
    });

    it('fetches route history with custom limit', async () => {
      const mockData = {
        items: [],
        pagination: { total: 0, limit: 20, offset: 0 },
      };
      mockGetRouteHistory.mockResolvedValueOnce(mockData);

      const { result } = renderHook(() => useRouteHistory(20), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockGetRouteHistory).toHaveBeenCalledWith(20);
    });

    it('returns multiple route history entries', async () => {
      const mockData = {
        items: [
          { from_system: 'Jita', to_system: 'Amarr', profile: 'safer', jumps: 15, timestamp: '2024-01-15T12:00:00Z' },
          { from_system: 'Dodixie', to_system: 'Rens', profile: 'shortest', jumps: 8, timestamp: '2024-01-15T11:00:00Z' },
          { from_system: 'Hek', to_system: 'Jita', profile: 'paranoid', jumps: 22, timestamp: '2024-01-15T10:00:00Z' },
        ],
        pagination: { total: 3, limit: 10, offset: 0 },
      };
      mockGetRouteHistory.mockResolvedValueOnce(mockData);

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.items).toHaveLength(3);
      expect(result.current.data?.pagination.total).toBe(3);
    });

    it('returns empty items array when no history exists', async () => {
      const mockData = {
        items: [],
        pagination: { total: 0, limit: 10, offset: 0 },
      };
      mockGetRouteHistory.mockResolvedValueOnce(mockData);

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.items).toEqual([]);
    });
  });

  describe('loading state', () => {
    it('starts in loading state', () => {
      mockGetRouteHistory.mockImplementation(() => new Promise(() => {})); // Never resolves

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
    });

    it('transitions from loading to success', async () => {
      const mockData = {
        items: [],
        pagination: { total: 0, limit: 10, offset: 0 },
      };
      mockGetRouteHistory.mockResolvedValueOnce(mockData);

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('error handling', () => {
    it('handles API errors', async () => {
      mockGetRouteHistory.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });

    it('sets error message correctly', async () => {
      mockGetRouteHistory.mockRejectedValueOnce(new Error('API Error: 500 Internal Server Error'));

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error?.message).toBe('API Error: 500 Internal Server Error');
    });
  });

  describe('query key', () => {
    it('uses correct query key with default limit', async () => {
      mockGetRouteHistory.mockResolvedValueOnce({ items: [], pagination: { total: 0, limit: 10, offset: 0 } });

      renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(mockGetRouteHistory).toHaveBeenCalled());

      const queryState = queryClient.getQueryState(['routeHistory', 10]);
      expect(queryState).toBeDefined();
    });

    it('uses correct query key with custom limit', async () => {
      mockGetRouteHistory.mockResolvedValueOnce({ items: [], pagination: { total: 0, limit: 5, offset: 0 } });

      renderHook(() => useRouteHistory(5), { wrapper: createWrapper() });

      await waitFor(() => expect(mockGetRouteHistory).toHaveBeenCalled());

      const queryState = queryClient.getQueryState(['routeHistory', 5]);
      expect(queryState).toBeDefined();
    });

    it('caches queries separately by limit', async () => {
      mockGetRouteHistory.mockResolvedValue({ items: [], pagination: { total: 0, limit: 10, offset: 0 } });

      renderHook(() => useRouteHistory(10), { wrapper: createWrapper() });
      renderHook(() => useRouteHistory(20), { wrapper: createWrapper() });

      await waitFor(() => expect(mockGetRouteHistory).toHaveBeenCalledTimes(2));

      expect(queryClient.getQueryState(['routeHistory', 10])).toBeDefined();
      expect(queryClient.getQueryState(['routeHistory', 20])).toBeDefined();
    });
  });

  describe('stale time configuration', () => {
    it('has 30 second stale time', async () => {
      mockGetRouteHistory.mockResolvedValueOnce({ items: [], pagination: { total: 0, limit: 10, offset: 0 } });

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Data should not be stale immediately
      expect(result.current.isStale).toBe(false);
    });
  });

  describe('refetch behavior', () => {
    it('supports manual refetch', async () => {
      mockGetRouteHistory.mockResolvedValue({ items: [], pagination: { total: 0, limit: 10, offset: 0 } });

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockGetRouteHistory).toHaveBeenCalledTimes(1);

      await result.current.refetch();

      expect(mockGetRouteHistory).toHaveBeenCalledTimes(2);
    });
  });

  describe('return type', () => {
    it('returns RouteHistoryResponse type data', async () => {
      const mockData = {
        items: [
          { from_system: 'Jita', to_system: 'Amarr', profile: 'safer', jumps: 15, timestamp: '2024-01-15T12:00:00Z' },
        ],
        pagination: { total: 1, limit: 10, offset: 0 },
      };
      mockGetRouteHistory.mockResolvedValueOnce(mockData);

      const { result } = renderHook(() => useRouteHistory(), { wrapper: createWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify structure matches RouteHistoryResponse
      expect(result.current.data).toHaveProperty('items');
      expect(result.current.data).toHaveProperty('pagination');
      expect(result.current.data?.items[0]).toHaveProperty('from_system');
      expect(result.current.data?.items[0]).toHaveProperty('to_system');
      expect(result.current.data?.items[0]).toHaveProperty('profile');
      expect(result.current.data?.items[0]).toHaveProperty('jumps');
      expect(result.current.data?.items[0]).toHaveProperty('timestamp');
    });
  });
});
