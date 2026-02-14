import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement, type ReactNode } from 'react';
import { useRoute } from './useRoute';
import { GatekeeperAPI } from '@/lib/api';
import type { Mock } from 'vitest';

// Mock the API module
vi.mock('@/lib/api', () => ({
  GatekeeperAPI: {
    getRoute: vi.fn(),
  },
}));

const mockGetRoute = GatekeeperAPI.getRoute as Mock;

describe('useRoute', () => {
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

  const mockRouteResponse = {
    path: [
      { system_name: 'Jita', security_status: 0.95, risk_score: 10, distance: 0, cumulative_cost: 0 },
      { system_name: 'Perimeter', security_status: 0.87, risk_score: 15, distance: 1, cumulative_cost: 15 },
      { system_name: 'Amarr', security_status: 1.0, risk_score: 5, distance: 1, cumulative_cost: 20 },
    ],
    total_jumps: 3,
    total_distance: 2,
    total_cost: 20,
    max_risk: 15,
    avg_risk: 10,
    profile: 'safer',
    bridges_used: 0,
    thera_used: 0,
  };

  it('starts in loading state when from and to are provided', () => {
    mockGetRoute.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr' }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('calls API with correct default params', async () => {
    mockGetRoute.mockResolvedValueOnce(mockRouteResponse);

    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetRoute).toHaveBeenCalledWith('Jita', 'Amarr', 'safer', { bridges: false, thera: false });
  });

  it('calls API with custom profile', async () => {
    mockGetRoute.mockResolvedValueOnce({ ...mockRouteResponse, profile: 'shortest' });

    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr', profile: 'shortest' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetRoute).toHaveBeenCalledWith('Jita', 'Amarr', 'shortest', { bridges: false, thera: false });
  });

  it('calls API with bridges and thera enabled', async () => {
    mockGetRoute.mockResolvedValueOnce(mockRouteResponse);

    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr', bridges: true, thera: true }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockGetRoute).toHaveBeenCalledWith('Jita', 'Amarr', 'safer', { bridges: true, thera: true });
  });

  it('returns route data on success', async () => {
    mockGetRoute.mockResolvedValueOnce(mockRouteResponse);

    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockRouteResponse);
    expect(result.current.data?.total_jumps).toBe(3);
    expect(result.current.data?.path).toHaveLength(3);
  });

  it('handles API errors', async () => {
    mockGetRoute.mockRejectedValueOnce(new Error('API Error: 500 Internal Server Error'));

    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toBe('API Error: 500 Internal Server Error');
  });

  it('does not fetch when enabled is false', () => {
    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr', enabled: false }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.fetchStatus).toBe('idle');
    expect(mockGetRoute).not.toHaveBeenCalled();
  });

  it('does not fetch when from is empty', () => {
    const { result } = renderHook(
      () => useRoute({ from: '', to: 'Amarr' }),
      { wrapper: createWrapper() }
    );

    expect(result.current.fetchStatus).toBe('idle');
    expect(mockGetRoute).not.toHaveBeenCalled();
  });

  it('does not fetch when to is empty', () => {
    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: '' }),
      { wrapper: createWrapper() }
    );

    expect(result.current.fetchStatus).toBe('idle');
    expect(mockGetRoute).not.toHaveBeenCalled();
  });

  it('transitions from loading to success', async () => {
    mockGetRoute.mockResolvedValueOnce(mockRouteResponse);

    const { result } = renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr' }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeDefined();
  });

  it('uses correct query key including all parameters', async () => {
    mockGetRoute.mockResolvedValueOnce(mockRouteResponse);

    renderHook(
      () => useRoute({ from: 'Jita', to: 'Amarr', profile: 'paranoid', bridges: true, thera: false }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(mockGetRoute).toHaveBeenCalled());

    const queryState = queryClient.getQueryState(['route', 'Jita', 'Amarr', 'paranoid', true, false]);
    expect(queryState).toBeDefined();
  });
});
