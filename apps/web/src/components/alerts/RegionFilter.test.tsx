import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RegionFilter, EVE_REGIONS } from './RegionFilter';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ChevronDown: (props: Record<string, unknown>) => <span data-testid="chevron-icon" {...props} />,
}));

describe('RegionFilter', () => {
  const defaultProps = {
    value: '',
    onChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the label', () => {
    render(<RegionFilter {...defaultProps} />);

    expect(screen.getByLabelText('Region (optional)')).toBeInTheDocument();
  });

  it('renders the placeholder text', () => {
    render(<RegionFilter {...defaultProps} />);

    expect(screen.getByPlaceholderText('Type to filter regions...')).toBeInTheDocument();
  });

  it('has combobox role on the input', () => {
    render(<RegionFilter {...defaultProps} />);

    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('shows dropdown with all regions on focus', async () => {
    const user = userEvent.setup();
    render(<RegionFilter {...defaultProps} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    const listbox = screen.getByRole('listbox');
    const options = within(listbox).getAllByRole('option');
    expect(options.length).toBe(EVE_REGIONS.length);
  });

  it('filters regions as user types', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();

    // Render with controlled value "Delv" to simulate typing
    const { rerender } = render(<RegionFilter value="" onChange={onChange} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    // Simulate typing "Delv"
    rerender(<RegionFilter value="Delv" onChange={onChange} />);

    const listbox = screen.getByRole('listbox');
    const options = within(listbox).getAllByRole('option');
    expect(options.length).toBe(1);
    expect(options[0]).toHaveTextContent('Delve');
  });

  it('calls onChange when user types', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<RegionFilter value="" onChange={onChange} />);

    const input = screen.getByRole('combobox');
    await user.type(input, 'D');

    expect(onChange).toHaveBeenCalledWith('D');
  });

  it('calls onChange with region name when clicking an option', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<RegionFilter value="" onChange={onChange} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    const option = screen.getByRole('option', { name: 'Delve' });
    await user.click(option);

    expect(onChange).toHaveBeenCalledWith('Delve');
  });

  it('shows "No matching regions" when no results match', async () => {
    const user = userEvent.setup();
    render(<RegionFilter value="xyznonexistent" onChange={vi.fn()} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    expect(screen.getByText('No matching regions')).toBeInTheDocument();
  });

  it('does not show "No matching regions" when value is empty', async () => {
    const user = userEvent.setup();
    render(<RegionFilter value="" onChange={vi.fn()} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    expect(screen.queryByText('No matching regions')).not.toBeInTheDocument();
  });

  it('closes dropdown on Escape key', async () => {
    const user = userEvent.setup();
    render(<RegionFilter value="" onChange={vi.fn()} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    expect(screen.getByRole('listbox')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('selects highlighted option with Enter key', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<RegionFilter value="" onChange={onChange} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    // ArrowDown to highlight first item, then Enter
    await user.keyboard('{ArrowDown}');
    await user.keyboard('{Enter}');

    // First region alphabetically in the list is Derelik (id: 10000001)
    expect(onChange).toHaveBeenCalledWith('Derelik');
  });

  it('navigates options with ArrowDown and ArrowUp', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<RegionFilter value="" onChange={onChange} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    // Navigate down twice
    await user.keyboard('{ArrowDown}');
    await user.keyboard('{ArrowDown}');

    // Navigate back up
    await user.keyboard('{ArrowUp}');

    // Select with Enter - should be first item (index 0)
    await user.keyboard('{Enter}');

    expect(onChange).toHaveBeenCalledWith('Derelik');
  });

  it('sets aria-expanded correctly', async () => {
    const user = userEvent.setup();
    render(<RegionFilter value="" onChange={vi.fn()} />);

    const input = screen.getByRole('combobox');
    expect(input).toHaveAttribute('aria-expanded', 'false');

    await user.click(input);
    expect(input).toHaveAttribute('aria-expanded', 'true');
  });

  it('filters case-insensitively', async () => {
    const user = userEvent.setup();
    render(<RegionFilter value="the forge" onChange={vi.fn()} />);

    const input = screen.getByRole('combobox');
    await user.click(input);

    const listbox = screen.getByRole('listbox');
    const options = within(listbox).getAllByRole('option');
    expect(options.length).toBe(1);
    expect(options[0]).toHaveTextContent('The Forge');
  });

  it('contains expected EVE regions in the static list', () => {
    const regionNames = EVE_REGIONS.map((r) => r.name);
    expect(regionNames).toContain('The Forge');
    expect(regionNames).toContain('Domain');
    expect(regionNames).toContain('Delve');
    expect(regionNames).toContain('Pochven');
    expect(regionNames).toContain('Jita' === 'system' ? 'The Forge' : 'The Forge'); // Jita is in The Forge
  });

  it('has unique region IDs', () => {
    const ids = EVE_REGIONS.map((r) => r.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });
});
