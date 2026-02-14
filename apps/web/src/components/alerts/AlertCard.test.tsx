import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AlertCard } from './AlertCard';
import type { AlertSubscription } from '@/lib/types';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Trash2: (props: Record<string, unknown>) => <span data-testid="trash-icon" {...props} />,
  Bell: (props: Record<string, unknown>) => <span data-testid="bell-icon" {...props} />,
  BellOff: (props: Record<string, unknown>) => <span data-testid="bell-off-icon" {...props} />,
  MessageSquare: (props: Record<string, unknown>) => <span data-testid="message-icon" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader-icon" {...props} />,
}));

function createSubscription(overrides: Partial<AlertSubscription> = {}): AlertSubscription {
  return {
    id: 'sub-abc123',
    name: 'My Kill Alerts',
    webhook_type: 'discord',
    systems: ['Jita', 'Amarr'],
    regions: [],
    min_value: null,
    include_pods: true,
    ship_types: [],
    enabled: true,
    created_at: '2024-01-15T12:00:00Z',
    ...overrides,
  };
}

describe('AlertCard', () => {
  const defaultProps = {
    onToggle: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-15T12:30:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders subscription name', () => {
    const subscription = createSubscription({ name: 'My Kill Alerts' });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('My Kill Alerts')).toBeInTheDocument();
  });

  it('renders truncated id when name is null', () => {
    const subscription = createSubscription({ name: null, id: 'sub-abcdef12345' });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Alert sub-abcd')).toBeInTheDocument();
  });

  it('shows Discord webhook type badge', () => {
    const subscription = createSubscription({ webhook_type: 'discord' });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Discord')).toBeInTheDocument();
  });

  it('shows Slack webhook type badge', () => {
    const subscription = createSubscription({ webhook_type: 'slack' });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Slack')).toBeInTheDocument();
  });

  it('shows system list', () => {
    const subscription = createSubscription({ systems: ['Jita', 'Amarr', 'Dodixie'] });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Systems: Jita, Amarr, Dodixie')).toBeInTheDocument();
  });

  it('truncates system list when more than 3 systems', () => {
    const subscription = createSubscription({
      systems: ['Jita', 'Amarr', 'Dodixie', 'Rens', 'Hek'],
    });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText(/Systems: Jita, Amarr, Dodixie/)).toBeInTheDocument();
    expect(screen.getByText(/\+2 more/)).toBeInTheDocument();
  });

  it('does not show systems section when systems list is empty', () => {
    const subscription = createSubscription({ systems: [] });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.queryByText(/Systems:/)).not.toBeInTheDocument();
  });

  it('shows regions count when regions are set', () => {
    const subscription = createSubscription({ regions: [10000002, 10000043, 10000032] });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Regions: 3 selected')).toBeInTheDocument();
  });

  it('shows minimum value when set', () => {
    const subscription = createSubscription({ min_value: 100_000_000 });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Min Value: 100M ISK')).toBeInTheDocument();
  });

  it('shows ship types when set', () => {
    const subscription = createSubscription({ ship_types: ['Caracal', 'Drake'] });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Ships: Caracal, Drake')).toBeInTheDocument();
  });

  it('truncates ship types when more than 3', () => {
    const subscription = createSubscription({
      ship_types: ['Caracal', 'Drake', 'Raven', 'Megathron'],
    });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText(/Ships: Caracal, Drake, Raven/)).toBeInTheDocument();
    expect(screen.getByText(/\+1 more/)).toBeInTheDocument();
  });

  it('shows including pod kills text', () => {
    const subscription = createSubscription({ include_pods: true });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText('Including pod kills')).toBeInTheDocument();
  });

  it('does not show pod kills text when include_pods is false', () => {
    const subscription = createSubscription({ include_pods: false });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.queryByText('Including pod kills')).not.toBeInTheDocument();
  });

  it('shows created time', () => {
    const subscription = createSubscription({ created_at: '2024-01-15T12:00:00Z' });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByText(/Created 30m ago/)).toBeInTheDocument();
  });

  it('has a delete button that calls onDelete', async () => {
    vi.useRealTimers(); // need real timers for userEvent
    const handleDelete = vi.fn();
    const user = userEvent.setup();

    const subscription = createSubscription();
    render(<AlertCard subscription={subscription} onToggle={vi.fn()} onDelete={handleDelete} />);

    const deleteButton = screen.getByTestId('trash-icon').closest('button')!;
    await user.click(deleteButton);

    expect(handleDelete).toHaveBeenCalledWith('sub-abc123');
  });

  it('has a toggle switch that calls onToggle', async () => {
    vi.useRealTimers();
    const handleToggle = vi.fn();
    const user = userEvent.setup();

    const subscription = createSubscription({ enabled: true });
    render(<AlertCard subscription={subscription} onToggle={handleToggle} onDelete={vi.fn()} />);

    const toggle = screen.getByRole('switch');
    await user.click(toggle);

    expect(handleToggle).toHaveBeenCalledWith('sub-abc123', false);
  });

  it('shows bell icon when enabled', () => {
    const subscription = createSubscription({ enabled: true });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByTestId('bell-icon')).toBeInTheDocument();
  });

  it('shows bell-off icon when disabled', () => {
    const subscription = createSubscription({ enabled: false });
    render(<AlertCard subscription={subscription} {...defaultProps} />);

    expect(screen.getByTestId('bell-off-icon')).toBeInTheDocument();
  });

  it('applies reduced opacity when disabled', () => {
    const subscription = createSubscription({ enabled: false });
    const { container } = render(<AlertCard subscription={subscription} {...defaultProps} />);

    // The Card wrapper should have opacity-60 class
    const card = container.firstChild;
    expect(card).toHaveClass('opacity-60');
  });

  it('does not apply reduced opacity when enabled', () => {
    const subscription = createSubscription({ enabled: true });
    const { container } = render(<AlertCard subscription={subscription} {...defaultProps} />);

    const card = container.firstChild;
    expect(card).not.toHaveClass('opacity-60');
  });
});
