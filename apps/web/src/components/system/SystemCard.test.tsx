import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SystemCard } from './SystemCard';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ShieldCheck: (props: Record<string, unknown>) => <span data-testid="shield-check-icon" {...props} />,
  Shield: (props: Record<string, unknown>) => <span data-testid="shield-icon" {...props} />,
  ShieldAlert: (props: Record<string, unknown>) => <span data-testid="shield-alert-icon" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="alert-triangle-icon" {...props} />,
}));

describe('SystemCard', () => {
  it('renders system name', () => {
    render(<SystemCard systemName="Jita" security={0.95} />);

    expect(screen.getByText('Jita')).toBeInTheDocument();
  });

  it('renders security badge for high-sec system', () => {
    const { container } = render(<SystemCard systemName="Jita" security={0.95} />);

    expect(screen.getByText('0.9')).toBeInTheDocument();
    const badge = container.querySelector('.text-high-sec');
    expect(badge).toBeInTheDocument();
  });

  it('renders security badge for low-sec system', () => {
    const { container } = render(<SystemCard systemName="Tama" security={0.3} />);

    expect(screen.getByText('0.3')).toBeInTheDocument();
    const badge = container.querySelector('.text-low-sec');
    expect(badge).toBeInTheDocument();
  });

  it('renders security badge for null-sec system', () => {
    const { container } = render(<SystemCard systemName="HED-GP" security={-0.5} />);

    expect(screen.getByText('-0.5')).toBeInTheDocument();
    const badge = container.querySelector('.text-null-sec');
    expect(badge).toBeInTheDocument();
  });

  it('displays kill count when provided', () => {
    render(<SystemCard systemName="Tama" security={0.3} kills={42} />);

    expect(screen.getByText('42 kills')).toBeInTheDocument();
  });

  it('displays pod count when provided and greater than zero', () => {
    render(<SystemCard systemName="Tama" security={0.3} pods={15} />);

    expect(screen.getByText('15 pods')).toBeInTheDocument();
  });

  it('does not display pod count when zero', () => {
    render(<SystemCard systemName="Tama" security={0.3} pods={0} />);

    expect(screen.queryByText('0 pods')).not.toBeInTheDocument();
  });

  it('does not display kill/pod section when neither is provided', () => {
    render(<SystemCard systemName="Jita" security={0.95} />);

    expect(screen.queryByText(/kills/)).not.toBeInTheDocument();
    expect(screen.queryByText(/pods/)).not.toBeInTheDocument();
  });

  it('displays both kill and pod counts together', () => {
    render(<SystemCard systemName="Tama" security={0.3} kills={100} pods={25} />);

    expect(screen.getByText('100 kills')).toBeInTheDocument();
    expect(screen.getByText('25 pods')).toBeInTheDocument();
  });

  it('shows risk badge when riskColor is provided', () => {
    const { container } = render(
      <SystemCard systemName="Tama" security={0.3} riskColor="red" />
    );

    // RiskBadge renders with the risk-red class
    const riskBadge = container.querySelector('.text-risk-red');
    expect(riskBadge).toBeInTheDocument();
  });

  it('does not show risk badge when riskColor is not provided', () => {
    const { container } = render(
      <SystemCard systemName="Jita" security={0.95} />
    );

    // No risk badge classes should be present (other than security)
    const greenRisk = container.querySelector('.border-l-risk-green');
    const yellowRisk = container.querySelector('.border-l-risk-yellow');
    const orangeRisk = container.querySelector('.border-l-risk-orange');
    const redRisk = container.querySelector('.border-l-risk-red');

    expect(greenRisk).not.toBeInTheDocument();
    expect(yellowRisk).not.toBeInTheDocument();
    expect(orangeRisk).not.toBeInTheDocument();
    expect(redRisk).not.toBeInTheDocument();
  });

  it('applies green border for green risk', () => {
    const { container } = render(
      <SystemCard systemName="System" security={0.5} riskColor="green" />
    );

    const card = container.querySelector('.border-l-risk-green');
    expect(card).toBeInTheDocument();
  });

  it('applies yellow border for yellow risk', () => {
    const { container } = render(
      <SystemCard systemName="System" security={0.3} riskColor="yellow" />
    );

    const card = container.querySelector('.border-l-risk-yellow');
    expect(card).toBeInTheDocument();
  });

  it('applies orange border for orange risk', () => {
    const { container } = render(
      <SystemCard systemName="System" security={0.1} riskColor="orange" />
    );

    const card = container.querySelector('.border-l-risk-orange');
    expect(card).toBeInTheDocument();
  });

  it('applies red border for red risk', () => {
    const { container } = render(
      <SystemCard systemName="System" security={-0.5} riskColor="red" />
    );

    const card = container.querySelector('.border-l-risk-red');
    expect(card).toBeInTheDocument();
  });

  it('handles click when onClick is provided', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(
      <SystemCard systemName="Jita" security={0.95} onClick={handleClick} />
    );

    const systemName = screen.getByText('Jita');
    await user.click(systemName.closest('.bg-card')!);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    const { container } = render(
      <SystemCard systemName="Jita" security={0.95} className="custom-test-class" />
    );

    expect(container.querySelector('.custom-test-class')).toBeInTheDocument();
  });

  it('applies border-l-4 base class', () => {
    const { container } = render(
      <SystemCard systemName="Jita" security={0.95} />
    );

    const card = container.firstChild;
    expect(card).toHaveClass('border-l-4');
  });
});
