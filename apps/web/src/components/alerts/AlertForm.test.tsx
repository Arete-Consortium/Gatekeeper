import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AlertForm } from './AlertForm';

// Mock RegionFilter component with dropdown behavior matching test expectations
vi.mock('./RegionFilter', () => {
  const { useState } = require('react');
  const regions = [{ name: 'The Forge', id: 10000002 }];
  return {
    RegionFilter: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => {
      const [showDropdown, setShowDropdown] = useState(false);
      const filtered = regions.filter((r: { name: string }) =>
        r.name.toLowerCase().includes(value.toLowerCase())
      );
      return (
        <div>
          <label htmlFor="region-filter">Region (optional)</label>
          <input
            id="region-filter"
            aria-label="Region (optional)"
            value={value}
            placeholder="Type to filter regions..."
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              onChange(e.target.value);
              setShowDropdown(true);
            }}
            onFocus={() => setShowDropdown(true)}
          />
          {showDropdown && value && filtered.length > 0 && (
            <ul role="listbox">
              {filtered.map((r: { name: string }) => (
                <li
                  key={r.name}
                  role="option"
                  aria-selected={false}
                  onClick={() => {
                    onChange(r.name);
                    setShowDropdown(false);
                  }}
                >
                  {r.name}
                </li>
              ))}
            </ul>
          )}
        </div>
      );
    },
    EVE_REGIONS: regions,
  };
});

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Plus: (props: Record<string, unknown>) => <span data-testid="plus-icon" {...props} />,
  Send: (props: Record<string, unknown>) => <span data-testid="send-icon" {...props} />,
  X: (props: Record<string, unknown>) => <span data-testid="x-icon" {...props} />,
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

  // ==================== Region Filter ====================

  it('renders the region filter input', () => {
    render(<AlertForm {...defaultProps} />);

    expect(screen.getByLabelText('Region (optional)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Type to filter regions...')).toBeInTheDocument();
  });

  it('includes region_name and regions in submission when a region is selected', async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<AlertForm {...defaultProps} onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText('Webhook URL'), 'https://discord.com/api/webhooks/123');

    const regionInput = screen.getByLabelText('Region (optional)');
    await user.type(regionInput, 'The Forge');

    // Click the matching option from the dropdown
    const option = screen.getByRole('option', { name: 'The Forge' });
    await user.click(option);

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    await user.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        region_name: 'The Forge',
        regions: [10000002],
      })
    );
  });

  it('submits undefined region_name when no region is entered', async () => {
    const handleSubmit = vi.fn();
    const user = userEvent.setup();

    render(<AlertForm {...defaultProps} onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText('Webhook URL'), 'https://discord.com/api/webhooks/123');

    const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
    await user.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        region_name: undefined,
        regions: undefined,
      })
    );
  });

  // ==================== Ship Types ====================

  describe('ship type filter', () => {
    it('renders the ship types label', () => {
      render(<AlertForm {...defaultProps} />);

      expect(screen.getByText('Ship Types (optional)')).toBeInTheDocument();
    });

    it('renders the ship type search input', () => {
      render(<AlertForm {...defaultProps} />);

      expect(screen.getByLabelText('Ship type search')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Type to search ship types...')).toBeInTheDocument();
    });

    it('shows dropdown with filtered results when typing', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'Fri');

      const listbox = screen.getByRole('listbox');
      const options = within(listbox).getAllByRole('option');
      expect(options).toHaveLength(1);
      expect(options[0]).toHaveTextContent('Frigate');
    });

    it('shows all types when focusing with empty query', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.click(searchInput);

      const listbox = screen.getByRole('listbox');
      const options = within(listbox).getAllByRole('option');
      expect(options.length).toBe(16);
    });

    it('adds a ship type tag when clicking a dropdown option', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'Cruiser');

      // Click the Cruiser option
      const option = screen.getByRole('option', { name: 'Cruiser' });
      await user.click(option);

      // Should show tag
      expect(screen.getByText('Cruiser')).toBeInTheDocument();
      // Should have remove button
      expect(screen.getByRole('button', { name: 'Remove Cruiser' })).toBeInTheDocument();
    });

    it('adds ship type via Enter key', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'Titan');
      await user.keyboard('{Enter}');

      expect(screen.getByText('Titan')).toBeInTheDocument();
    });

    it('removes ship type tag when clicking remove button', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'Titan');
      await user.keyboard('{Enter}');

      expect(screen.getByText('Titan')).toBeInTheDocument();

      const removeButton = screen.getByRole('button', { name: 'Remove Titan' });
      await user.click(removeButton);

      // Titan tag should be gone, but Titan should still be available in dropdown
      expect(screen.queryByRole('button', { name: 'Remove Titan' })).not.toBeInTheDocument();
    });

    it('removes last ship type tag with Backspace on empty input', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');

      // Add two types using specific-enough queries
      await user.type(searchInput, 'Titan');
      await user.keyboard('{Enter}');
      await user.type(searchInput, 'Shuttle');
      await user.keyboard('{Enter}');

      expect(screen.getByText('Titan')).toBeInTheDocument();
      expect(screen.getByText('Shuttle')).toBeInTheDocument();

      // Focus the input, then Backspace removes last added (Shuttle)
      await user.click(searchInput);
      await user.keyboard('{Backspace}');

      expect(screen.getByText('Titan')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Remove Shuttle' })).not.toBeInTheDocument();
    });

    it('does not show already-selected types in dropdown', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'Titan');
      await user.keyboard('{Enter}');

      // Re-focus and type Titan again
      await user.type(searchInput, 'Titan');

      // Should not show Titan in dropdown since it's already selected
      expect(screen.queryByRole('option', { name: 'Titan' })).not.toBeInTheDocument();
    });

    it('filters case-insensitively', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'battle');

      const listbox = screen.getByRole('listbox');
      const options = within(listbox).getAllByRole('option');
      expect(options).toHaveLength(2);
      expect(options[0]).toHaveTextContent('Battlecruiser');
      expect(options[1]).toHaveTextContent('Battleship');
    });

    it('hides placeholder when ship types are selected', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'Titan');
      await user.keyboard('{Enter}');

      // When ship types are selected, placeholder becomes empty string
      expect(searchInput).toHaveAttribute('placeholder', '');
    });

    it('includes ship_types in form submission data', async () => {
      const handleSubmit = vi.fn();
      const user = userEvent.setup();

      render(<AlertForm {...defaultProps} onSubmit={handleSubmit} />);

      await user.type(screen.getByLabelText('Webhook URL'), 'https://discord.com/api/webhooks/123');

      // Add ship types
      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'Cruiser');
      await user.keyboard('{Enter}');
      await user.type(searchInput, 'Battleship');
      await user.keyboard('{Enter}');

      const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
      await user.click(submitButton);

      expect(handleSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          ship_types: ['Cruiser', 'Battleship'],
        })
      );
    });

    it('submits undefined ship_types when none selected', async () => {
      const handleSubmit = vi.fn();
      const user = userEvent.setup();

      render(<AlertForm {...defaultProps} onSubmit={handleSubmit} />);

      await user.type(screen.getByLabelText('Webhook URL'), 'https://discord.com/api/webhooks/123');

      const submitButton = screen.getByRole('button', { name: /Create Subscription/i });
      await user.click(submitButton);

      expect(handleSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          ship_types: undefined,
        })
      );
    });

    it('closes dropdown on Escape key', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.click(searchInput);

      expect(screen.getByRole('listbox')).toBeInTheDocument();

      await user.keyboard('{Escape}');

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('does not show dropdown when no matches', async () => {
      const user = userEvent.setup();
      render(<AlertForm {...defaultProps} />);

      const searchInput = screen.getByLabelText('Ship type search');
      await user.type(searchInput, 'xyznonexistent');

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });
  });
});
