import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AlertForm } from './AlertForm';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Plus: (props: Record<string, unknown>) => <span data-testid="plus-icon" {...props} />,
  Send: (props: Record<string, unknown>) => <span data-testid="send-icon" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader-icon" {...props} />,
  ChevronDown: (props: Record<string, unknown>) => <span data-testid="chevron-icon" {...props} />,
}));

describe('AlertForm', () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    onTest: vi.fn(),
    isSubmitting: false,
    isTesting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the form title', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByText('Create Alert Subscription')).toBeInTheDocument();
  });

  it('renders the webhook URL input', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByLabelText('Webhook URL')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('https://discord.com/api/webhooks/...')).toBeInTheDocument();
  });

  it('renders the name input', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByLabelText('Name (optional)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('My kill alerts...')).toBeInTheDocument();
  });

  it('renders the webhook type selector with Discord and Slack options', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByLabelText('Webhook Type')).toBeInTheDocument();
    const select = screen.getByLabelText('Webhook Type');
    expect(select).toHaveValue('discord');

    // Check options
    const options = select.querySelectorAll('option');
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent('Discord');
    expect(options[1]).toHaveTextContent('Slack');
  });

  it('renders the systems input', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByLabelText('Systems (comma-separated, optional)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Jita, Amarr, Dodixie...')).toBeInTheDocument();
  });

  it('renders the minimum value input', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByLabelText('Minimum Value (millions ISK, optional)')).toBeInTheDocument();
  });

  it('renders the include pods toggle', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByText('Include pod kills')).toBeInTheDocument();
    const toggle = screen.getByRole('switch', { name: 'Include pod kills' });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
  });

  it('has create subscription button disabled when webhook URL is empty', () => {
    render(<AlertForm {...defaultProps} />);

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    expect(submitButton).toBeDisabled();
  });

  it('enables create subscription button when webhook URL is entered', async () => {
    const user = userEvent.setup();
    render(<AlertForm {...defaultProps} />);

    const webhookInput = screen.getByLabelText('Webhook URL');
    await user.type(webhookInput, 'https://discord.com/api/webhooks/123');

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('calls onSubmit with correct data when form is submitted', async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<AlertForm {...defaultProps} onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText('Name (optional)'), 'Test Alert');
    await user.type(screen.getByLabelText('Webhook URL'), 'https://discord.com/api/webhooks/123');
    await user.type(screen.getByLabelText('Systems (comma-separated, optional)'), 'Jita, Amarr');

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    await user.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        webhook_url: 'https://discord.com/api/webhooks/123',
        webhook_type: 'discord',
        name: 'Test Alert',
        systems: ['Jita', 'Amarr'],
        include_pods: true,
      })
    );
  });

  it('calls onTest when test button is clicked', async () => {
    const handleTest = vi.fn();
    const user = userEvent.setup();

    render(<AlertForm {...defaultProps} onTest={handleTest} />);

    const testButton = screen.getByRole('button', { name: /Send Test/i });
    await user.click(testButton);

    expect(handleTest).toHaveBeenCalledTimes(1);
  });

  it('disables submit button when isSubmitting is true', () => {
    render(<AlertForm {...defaultProps} isSubmitting={true} />);

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    expect(submitButton).toBeDisabled();
  });

  it('disables test button when isTesting is true', () => {
    render(<AlertForm {...defaultProps} isTesting={true} />);

    const testButton = screen.getByRole('button', { name: /Send Test/i });
    expect(testButton).toBeDisabled();
  });

  it('allows changing webhook type to slack', async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<AlertForm {...defaultProps} onSubmit={handleSubmit} />);

    const select = screen.getByLabelText('Webhook Type');
    await user.selectOptions(select, 'slack');
    expect(select).toHaveValue('slack');

    await user.type(screen.getByLabelText('Webhook URL'), 'https://hooks.slack.com/services/123');

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    await user.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        webhook_type: 'slack',
      })
    );
  });

  it('handles empty systems field correctly in submission', async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<AlertForm {...defaultProps} onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText('Webhook URL'), 'https://discord.com/api/webhooks/123');

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    await user.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        systems: [],
      })
    );
  });
});
