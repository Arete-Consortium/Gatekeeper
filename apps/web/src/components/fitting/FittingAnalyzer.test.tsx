import { render, screen } from '@testing-library/react';
import { FittingResult } from './FittingAnalyzer';
import type { FittingAnalysisResponse } from '@/lib/types';

// Mock lucide-react icons to simple elements
vi.mock('lucide-react', () => ({
  Ship: (props: Record<string, unknown>) => <span data-testid="ship-icon" {...props} />,
  Shield: (props: Record<string, unknown>) => <span data-testid="shield-icon" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="alert-triangle-icon" {...props} />,
  Lightbulb: (props: Record<string, unknown>) => <span data-testid="lightbulb-icon" {...props} />,
  Eye: (props: Record<string, unknown>) => <span data-testid="eye-icon" {...props} />,
  Zap: (props: Record<string, unknown>) => <span data-testid="zap-icon" {...props} />,
  Navigation: (props: Record<string, unknown>) => <span data-testid="navigation-icon" {...props} />,
}));

function createAnalysis(overrides: Partial<FittingAnalysisResponse> = {}): FittingAnalysisResponse {
  return {
    fitting: {
      ship_name: 'Heron',
      ship_category: 'frigate',
      jump_capability: 'none',
      modules: ['Core Probe Launcher I', 'Prototype Cloaking Device I'],
      cargo: [],
      drones: [],
      charges: [],
      is_covert_capable: false,
      is_cloak_capable: true,
      has_warp_stabs: false,
      is_bubble_immune: false,
      has_align_mods: true,
      has_warp_speed_mods: false,
      ...overrides.fitting,
    },
    travel: {
      ship_name: 'Heron',
      category: 'frigate',
      can_use_gates: true,
      can_use_jump_bridges: true,
      can_jump: false,
      can_bridge_others: false,
      can_covert_bridge: false,
      recommended_profile: 'paranoid',
      warnings: [],
      tips: [],
      ...overrides.travel,
    },
  };
}

describe('FittingResult', () => {
  it('renders ship name and category', () => {
    const analysis = createAnalysis();
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Heron')).toBeInTheDocument();
    expect(screen.getByText('frigate')).toBeInTheDocument();
  });

  it('shows recommended profile', () => {
    const analysis = createAnalysis({
      travel: {
        ship_name: 'Heron',
        category: 'frigate',
        can_use_gates: true,
        can_use_jump_bridges: true,
        can_jump: false,
        can_bridge_others: false,
        can_covert_bridge: false,
        recommended_profile: 'paranoid',
        warnings: [],
        tips: [],
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Recommended Profile')).toBeInTheDocument();
    expect(screen.getByText('paranoid')).toBeInTheDocument();
  });

  it('renders travel recommendations title', () => {
    const analysis = createAnalysis();
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Travel Recommendations')).toBeInTheDocument();
  });

  it('shows capability badges when cloak capable', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Heron',
        ship_category: 'frigate',
        jump_capability: 'none',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: false,
        is_cloak_capable: true,
        has_warp_stabs: false,
        is_bubble_immune: false,
        has_align_mods: false,
        has_warp_speed_mods: false,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Cloak Capable')).toBeInTheDocument();
  });

  it('shows covert ops badge when covert capable', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Buzzard',
        ship_category: 'covert_ops',
        jump_capability: 'none',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: true,
        is_cloak_capable: true,
        has_warp_stabs: false,
        is_bubble_immune: false,
        has_align_mods: false,
        has_warp_speed_mods: false,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Covert Ops')).toBeInTheDocument();
  });

  it('shows bubble immune badge when applicable', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Ares',
        ship_category: 'interceptor',
        jump_capability: 'none',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: false,
        is_cloak_capable: false,
        has_warp_stabs: false,
        is_bubble_immune: true,
        has_align_mods: false,
        has_warp_speed_mods: false,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Bubble Immune')).toBeInTheDocument();
  });

  it('shows warp stabs badge when fitted', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Heron',
        ship_category: 'frigate',
        jump_capability: 'none',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: false,
        is_cloak_capable: false,
        has_warp_stabs: true,
        is_bubble_immune: false,
        has_align_mods: false,
        has_warp_speed_mods: false,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Warp Stabs')).toBeInTheDocument();
  });

  it('shows align mods badge', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Heron',
        ship_category: 'frigate',
        jump_capability: 'none',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: false,
        is_cloak_capable: false,
        has_warp_stabs: false,
        is_bubble_immune: false,
        has_align_mods: true,
        has_warp_speed_mods: false,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Align Mods')).toBeInTheDocument();
  });

  it('shows warp speed mods badge', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Heron',
        ship_category: 'frigate',
        jump_capability: 'none',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: false,
        is_cloak_capable: false,
        has_warp_stabs: false,
        is_bubble_immune: false,
        has_align_mods: false,
        has_warp_speed_mods: true,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Warp Speed')).toBeInTheDocument();
  });

  it('displays gate and jump bridge capabilities', () => {
    const analysis = createAnalysis();
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Gates')).toBeInTheDocument();
    expect(screen.getByText('Jump Bridges')).toBeInTheDocument();
    expect(screen.getByText('Jump Drive')).toBeInTheDocument();
  });

  it('shows Yes/No badges for travel capabilities', () => {
    const analysis = createAnalysis({
      travel: {
        ship_name: 'Heron',
        category: 'frigate',
        can_use_gates: true,
        can_use_jump_bridges: true,
        can_jump: false,
        can_bridge_others: false,
        can_covert_bridge: false,
        recommended_profile: 'paranoid',
        warnings: [],
        tips: [],
      },
    });
    render(<FittingResult analysis={analysis} />);

    const yesElements = screen.getAllByText('Yes');
    const noElements = screen.getAllByText('No');
    expect(yesElements.length).toBeGreaterThan(0);
    expect(noElements.length).toBeGreaterThan(0);
  });

  it('displays warnings when present', () => {
    const analysis = createAnalysis({
      travel: {
        ship_name: 'Heron',
        category: 'frigate',
        can_use_gates: true,
        can_use_jump_bridges: true,
        can_jump: false,
        can_bridge_others: false,
        can_covert_bridge: false,
        recommended_profile: 'paranoid',
        warnings: ['Paper thin tank', 'No prop mod fitted'],
        tips: [],
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Warnings')).toBeInTheDocument();
    expect(screen.getByText('Paper thin tank')).toBeInTheDocument();
    expect(screen.getByText('No prop mod fitted')).toBeInTheDocument();
  });

  it('does not display warnings section when no warnings', () => {
    const analysis = createAnalysis({
      travel: {
        ship_name: 'Heron',
        category: 'frigate',
        can_use_gates: true,
        can_use_jump_bridges: true,
        can_jump: false,
        can_bridge_others: false,
        can_covert_bridge: false,
        recommended_profile: 'paranoid',
        warnings: [],
        tips: [],
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.queryByText('Warnings')).not.toBeInTheDocument();
  });

  it('displays tips when present', () => {
    const analysis = createAnalysis({
      travel: {
        ship_name: 'Heron',
        category: 'frigate',
        can_use_gates: true,
        can_use_jump_bridges: true,
        can_jump: false,
        can_bridge_others: false,
        can_covert_bridge: false,
        recommended_profile: 'paranoid',
        warnings: [],
        tips: ['Use cloak + MWD trick', 'Align to celestials before warping'],
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Tips')).toBeInTheDocument();
    expect(screen.getByText('Use cloak + MWD trick')).toBeInTheDocument();
    expect(screen.getByText('Align to celestials before warping')).toBeInTheDocument();
  });

  it('does not display tips section when no tips', () => {
    const analysis = createAnalysis({
      travel: {
        ship_name: 'Heron',
        category: 'frigate',
        can_use_gates: true,
        can_use_jump_bridges: true,
        can_jump: false,
        can_bridge_others: false,
        can_covert_bridge: false,
        recommended_profile: 'paranoid',
        warnings: [],
        tips: [],
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.queryByText('Tips')).not.toBeInTheDocument();
  });

  it('shows jump capability when not none', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Archon',
        ship_category: 'carrier',
        jump_capability: 'jump_drive',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: false,
        is_cloak_capable: false,
        has_warp_stabs: false,
        is_bubble_immune: false,
        has_align_mods: false,
        has_warp_speed_mods: false,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.getByText('Jump Capability')).toBeInTheDocument();
    expect(screen.getByText('jump_drive')).toBeInTheDocument();
  });

  it('hides jump capability section when capability is none', () => {
    const analysis = createAnalysis({
      fitting: {
        ship_name: 'Heron',
        ship_category: 'frigate',
        jump_capability: 'none',
        modules: [],
        cargo: [],
        drones: [],
        charges: [],
        is_covert_capable: false,
        is_cloak_capable: false,
        has_warp_stabs: false,
        is_bubble_immune: false,
        has_align_mods: false,
        has_warp_speed_mods: false,
      },
    });
    render(<FittingResult analysis={analysis} />);

    expect(screen.queryByText('Jump Capability')).not.toBeInTheDocument();
  });
});
