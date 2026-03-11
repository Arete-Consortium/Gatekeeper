import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouteResult } from './RouteResult';
import type { RouteResponse } from '@/lib/types';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

// Mock lucide-react icons to simple elements
vi.mock('lucide-react', () => ({
  Gauge: (props: Record<string, unknown>) => <span data-testid="gauge-icon" {...props} />,
  Route: (props: Record<string, unknown>) => <span data-testid="route-icon" {...props} />,
  Zap: (props: Record<string, unknown>) => <span data-testid="zap-icon" {...props} />,
  ShieldCheck: (props: Record<string, unknown>) => <span data-testid="shield-check-icon" {...props} />,
  Shield: (props: Record<string, unknown>) => <span data-testid="shield-icon" {...props} />,
  ShieldAlert: (props: Record<string, unknown>) => <span data-testid="shield-alert-icon" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="alert-triangle-icon" {...props} />,
  MapPin: (props: Record<string, unknown>) => <span data-testid="map-pin-icon" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader2-icon" {...props} />,
  Navigation: (props: Record<string, unknown>) => <span data-testid="navigation-icon" {...props} />,
  Flame: (props: Record<string, unknown>) => <span data-testid="flame-icon" {...props} />,
}));

function createRoute(overrides: Partial<RouteResponse> = {}): RouteResponse {
  return {
    path: [
      { system_name: 'Jita', security_status: 0.95, risk_score: 10, distance: 0, cumulative_cost: 0 },
      { system_name: 'Perimeter', security_status: 0.87, risk_score: 15, distance: 1, cumulative_cost: 15 },
      { system_name: 'Urlen', security_status: 0.78, risk_score: 8, distance: 1, cumulative_cost: 23 },
    ],
    total_jumps: 3,
    total_distance: 2,
    total_cost: 23,
    max_risk: 15,
    avg_risk: 11,
    profile: 'safer',
    bridges_used: 0,
    thera_used: 0,
    ...overrides,
  };
}

describe('RouteResult', () => {
  it('renders route summary with total jumps', () => {
    const route = createRoute({ total_jumps: 7 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Route Summary')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('Jumps')).toBeInTheDocument();
  });

  it('renders max risk and avg risk values', () => {
    const route = createRoute({ max_risk: 42, avg_risk: 18 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Max Risk')).toBeInTheDocument();
    expect(screen.getByText('Avg Risk')).toBeInTheDocument();
    // RiskBadge shows score with toFixed(1)
    expect(screen.getByText('42.0')).toBeInTheDocument();
    expect(screen.getByText('18.0')).toBeInTheDocument();
  });

  it('shows green risk color for risk < 25', () => {
    const route = createRoute({ max_risk: 10, avg_risk: 5 });
    const { container } = renderWithQueryClient(<RouteResult route={route} />);

    // RiskBadge with green color should have text-risk-green class
    const riskBadges = container.querySelectorAll('.text-risk-green');
    expect(riskBadges.length).toBeGreaterThan(0);
  });

  it('shows yellow risk color for risk >= 25 and < 50', () => {
    const route = createRoute({ max_risk: 35, avg_risk: 30 });
    const { container } = renderWithQueryClient(<RouteResult route={route} />);

    const riskBadges = container.querySelectorAll('.text-risk-yellow');
    expect(riskBadges.length).toBeGreaterThan(0);
  });

  it('shows orange risk color for risk >= 50 and < 75', () => {
    const route = createRoute({ max_risk: 60, avg_risk: 55 });
    const { container } = renderWithQueryClient(<RouteResult route={route} />);

    const riskBadges = container.querySelectorAll('.text-risk-orange');
    expect(riskBadges.length).toBeGreaterThan(0);
  });

  it('shows red risk color for risk >= 75', () => {
    const route = createRoute({ max_risk: 90, avg_risk: 80 });
    const { container } = renderWithQueryClient(<RouteResult route={route} />);

    const riskBadges = container.querySelectorAll('.text-risk-red');
    expect(riskBadges.length).toBeGreaterThan(0);
  });

  it('renders each hop in the route', () => {
    const route = createRoute();
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Jita')).toBeInTheDocument();
    expect(screen.getByText('Perimeter')).toBeInTheDocument();
    expect(screen.getByText('Urlen')).toBeInTheDocument();
  });

  it('renders the route path heading', () => {
    const route = createRoute();
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Route Path')).toBeInTheDocument();
  });

  it('handles empty route path', () => {
    const route = createRoute({ path: [], total_jumps: 0 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Route Summary')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('shows bridge indicator when bridges are used', () => {
    const route = createRoute({ bridges_used: 2 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('2 bridges')).toBeInTheDocument();
  });

  it('shows singular bridge text for single bridge', () => {
    const route = createRoute({ bridges_used: 1 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('1 bridge')).toBeInTheDocument();
  });

  it('shows Thera indicator when thera is used', () => {
    const route = createRoute({ thera_used: 1 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Thera')).toBeInTheDocument();
  });

  it('shows None when no special routes are used', () => {
    const route = createRoute({ bridges_used: 0, thera_used: 0 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('None')).toBeInTheDocument();
  });

  it('shows both bridge and thera indicators', () => {
    const route = createRoute({ bridges_used: 1, thera_used: 1 });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('1 bridge')).toBeInTheDocument();
    expect(screen.getByText('Thera')).toBeInTheDocument();
  });

  it('renders profile badge based on route profile', () => {
    const route = createRoute({ profile: 'safer' });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Safer')).toBeInTheDocument();
  });

  it('renders shortest profile badge', () => {
    const route = createRoute({ profile: 'shortest' });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Shortest')).toBeInTheDocument();
  });

  it('renders paranoid profile badge', () => {
    const route = createRoute({ profile: 'paranoid' });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Paranoid')).toBeInTheDocument();
  });
});

describe('RouteHopRow', () => {
  it('renders hop with system name and index', () => {
    const route = createRoute();
    renderWithQueryClient(<RouteResult route={route} />);

    // Index 0 should be rendered for the first hop
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('Jita')).toBeInTheDocument();
  });

  it('renders multiple hops with sequential indices', () => {
    const route = createRoute();
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders risk badges for each hop', () => {
    const route = createRoute({
      path: [
        { system_name: 'Safe', security_status: 0.95, risk_score: 10, distance: 0, cumulative_cost: 0 },
        { system_name: 'Risky', security_status: -0.5, risk_score: 80, distance: 1, cumulative_cost: 80 },
      ],
      total_jumps: 2,
    });
    renderWithQueryClient(<RouteResult route={route} />);

    expect(screen.getByText('Safe')).toBeInTheDocument();
    expect(screen.getByText('Risky')).toBeInTheDocument();
    // Risk scores displayed as toFixed(1)
    expect(screen.getByText('10.0')).toBeInTheDocument();
    expect(screen.getByText('80.0')).toBeInTheDocument();
  });
});
