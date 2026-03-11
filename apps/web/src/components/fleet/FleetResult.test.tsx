import { render, screen } from '@testing-library/react';
import { FleetResult } from './FleetResult';
import type { FleetAnalysisResponse } from '@/lib/types';

// Mock lucide-react icons to simple elements
vi.mock('lucide-react', () => ({
  Shield: (props: Record<string, unknown>) => <span data-testid="shield-icon" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="alert-triangle-icon" {...props} />,
  Lightbulb: (props: Record<string, unknown>) => <span data-testid="lightbulb-icon" {...props} />,
  Users: (props: Record<string, unknown>) => <span data-testid="users-icon" {...props} />,
  Swords: (props: Record<string, unknown>) => <span data-testid="swords-icon" {...props} />,
  Crosshair: (props: Record<string, unknown>) => <span data-testid="crosshair-icon" {...props} />,
  Eye: (props: Record<string, unknown>) => <span data-testid="eye-icon" {...props} />,
  Anchor: (props: Record<string, unknown>) => <span data-testid="anchor-icon" {...props} />,
}));

function createAnalysis(
  overrides: Partial<FleetAnalysisResponse> = {}
): FleetAnalysisResponse {
  return {
    total_pilots: 6,
    total_ships: 6,
    threat_level: 'moderate',
    composition: { dps: 3, logistics: 2, tackle: 1 },
    ship_list: [
      { name: 'Muninn', count: 3, role: 'dps' },
      { name: 'Scimitar', count: 2, role: 'logistics' },
      { name: 'Sabre', count: 1, role: 'tackle' },
    ],
    has_logistics: true,
    has_capitals: false,
    has_tackle: true,
    estimated_dps_category: 'medium',
    advice: ['Light logistics (2 logi). Focus fire may break reps.'],
    ...overrides,
  };
}

describe('FleetResult', () => {
  it('renders threat level badge', () => {
    render(<FleetResult analysis={createAnalysis()} />);
    expect(screen.getByText('Moderate')).toBeInTheDocument();
  });

  it('renders pilot count', () => {
    render(<FleetResult analysis={createAnalysis()} />);
    expect(screen.getByText('6 pilots')).toBeInTheDocument();
  });

  it('renders ship count', () => {
    render(<FleetResult analysis={createAnalysis()} />);
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('renders composition role labels', () => {
    render(<FleetResult analysis={createAnalysis()} />);
    // Role labels appear in both composition breakdown and ship list
    expect(screen.getAllByText('DPS').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Logistics').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Tackle').length).toBeGreaterThanOrEqual(1);
  });

  it('renders ship names in list', () => {
    render(<FleetResult analysis={createAnalysis()} />);
    expect(screen.getByText('Muninn')).toBeInTheDocument();
    expect(screen.getByText('Scimitar')).toBeInTheDocument();
    expect(screen.getByText('Sabre')).toBeInTheDocument();
  });

  it('renders ship counts in list', () => {
    render(<FleetResult analysis={createAnalysis()} />);
    expect(screen.getByText('x3')).toBeInTheDocument();
    expect(screen.getByText('x2')).toBeInTheDocument();
    expect(screen.getByText('x1')).toBeInTheDocument();
  });

  it('renders tactical advice', () => {
    render(<FleetResult analysis={createAnalysis()} />);
    expect(
      screen.getByText(/Focus fire may break reps/)
    ).toBeInTheDocument();
  });

  it('shows Logi badge when has_logistics is true', () => {
    render(<FleetResult analysis={createAnalysis({ has_logistics: true })} />);
    expect(screen.getByText('Logi')).toBeInTheDocument();
  });

  it('shows No Logi badge when has_logistics is false', () => {
    render(<FleetResult analysis={createAnalysis({ has_logistics: false })} />);
    expect(screen.getByText('No Logi')).toBeInTheDocument();
  });

  it('shows Capitals badge when has_capitals is true', () => {
    render(<FleetResult analysis={createAnalysis({ has_capitals: true })} />);
    expect(screen.getByText('Capitals')).toBeInTheDocument();
  });

  it('shows No Caps badge when has_capitals is false', () => {
    render(<FleetResult analysis={createAnalysis({ has_capitals: false })} />);
    expect(screen.getByText('No Caps')).toBeInTheDocument();
  });

  it('renders DPS category badge', () => {
    render(
      <FleetResult analysis={createAnalysis({ estimated_dps_category: 'high' })} />
    );
    expect(screen.getByText('High DPS')).toBeInTheDocument();
  });

  it('renders critical threat level', () => {
    render(<FleetResult analysis={createAnalysis({ threat_level: 'critical' })} />);
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('renders overwhelming threat level', () => {
    render(
      <FleetResult analysis={createAnalysis({ threat_level: 'overwhelming' })} />
    );
    expect(screen.getByText('Overwhelming')).toBeInTheDocument();
  });

  it('renders minimal threat level', () => {
    render(<FleetResult analysis={createAnalysis({ threat_level: 'minimal' })} />);
    expect(screen.getByText('Minimal')).toBeInTheDocument();
  });

  it('handles empty ship list gracefully', () => {
    render(
      <FleetResult
        analysis={createAnalysis({ ship_list: [], composition: {} })}
      />
    );
    // Should not render ship list card header
    expect(screen.queryByText('Ship List')).not.toBeInTheDocument();
  });

  it('handles empty advice gracefully', () => {
    render(<FleetResult analysis={createAnalysis({ advice: [] })} />);
    expect(screen.queryByText('Tactical Advice')).not.toBeInTheDocument();
  });
});
