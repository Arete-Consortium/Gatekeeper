import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement, type ReactNode } from 'react';
import { SystemSearch } from './SystemSearch';

// Mock the API module
vi.mock('@/lib/api', () => ({
  GatekeeperAPI: {
    getSystems: vi.fn().mockResolvedValue([
      { name: 'Jita', system_id: 30000142, region_id: 10000002, constellation_id: 20000020, security_status: 0.95, x: 0, y: 0 },
      { name: 'Amarr', system_id: 30002187, region_id: 10000043, constellation_id: 20000322, security_status: 1.0, x: 1, y: 1 },
      { name: 'Dodixie', system_id: 30002659, region_id: 10000032, constellation_id: 20000390, security_status: 0.87, x: 2, y: 2 },
      { name: 'Rens', system_id: 30002510, region_id: 10000030, constellation_id: 20000369, security_status: 0.9, x: 3, y: 3 },
      { name: 'Tama', system_id: 30003783, region_id: 10000016, constellation_id: 20000554, security_status: 0.3, x: 4, y: 4 },
      { name: 'Amamake', system_id: 30002537, region_id: 10000042, constellation_id: 20000372, security_status: 0.4, x: 5, y: 5 },
    ]),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('SystemSearch', () => {
  it('renders with label and placeholder', () => {
    render(
      <SystemSearch
        label="Origin System"
        value=""
        onChange={vi.fn()}
        placeholder="Search systems..."
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Origin System')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search systems...')).toBeInTheDocument();
  });

  it('renders with default placeholder when none provided', () => {
    render(
      <SystemSearch value="" onChange={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByPlaceholderText('Enter system name...')).toBeInTheDocument();
  });

  it('shows the input field', () => {
    render(
      <SystemSearch value="" onChange={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText('Enter system name...');
    expect(input).toBeInTheDocument();
    expect(input.tagName).toBe('INPUT');
  });

  it('displays the provided value', () => {
    render(
      <SystemSearch value="Jita" onChange={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByDisplayValue('Jita');
    expect(input).toBeInTheDocument();
  });

  it('shows dropdown when typing 2+ characters', async () => {
    const user = userEvent.setup();
    render(
      <SystemSearch value="" onChange={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText('Enter system name...');

    // Type only 1 character - no dropdown
    await user.type(input, 'J');
    expect(screen.queryByText('Jita')).not.toBeInTheDocument();

    // Clear and type 2 characters
    await user.clear(input);
    await user.type(input, 'Ji');

    // Wait for the dropdown to appear with filtered results
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Jita/i })).toBeInTheDocument();
    });
  });

  it('calls onChange when a system is selected from dropdown', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(
      <SystemSearch value="" onChange={handleChange} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText('Enter system name...');
    await user.type(input, 'Ji');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Jita/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Jita/i }));

    expect(handleChange).toHaveBeenCalledWith('Jita');
  });

  it('closes dropdown on escape key', async () => {
    const user = userEvent.setup();

    render(
      <SystemSearch value="" onChange={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText('Enter system name...');
    await user.type(input, 'Ji');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Jita/i })).toBeInTheDocument();
    });

    await user.keyboard('{Escape}');

    // Dropdown should close
    expect(screen.queryByRole('button', { name: /Jita/i })).not.toBeInTheDocument();
  });

  it('does not show dropdown for no matching results', async () => {
    const user = userEvent.setup();

    render(
      <SystemSearch value="" onChange={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText('Enter system name...');
    await user.type(input, 'Zzz');

    // No dropdown items should appear
    await waitFor(() => {
      const buttons = screen.queryAllByRole('button');
      expect(buttons).toHaveLength(0);
    });
  });

  it('displays error message when error prop is set', () => {
    render(
      <SystemSearch
        value=""
        onChange={vi.fn()}
        error="System is required"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('System is required')).toBeInTheDocument();
  });

  it('calls onChange on Enter key when no dropdown item is highlighted', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(
      <SystemSearch value="" onChange={handleChange} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText('Enter system name...');
    await user.type(input, 'X');
    await user.keyboard('{Enter}');

    expect(handleChange).toHaveBeenCalledWith('X');
  });

  it('supports keyboard navigation with ArrowDown and Enter', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(
      <SystemSearch value="" onChange={handleChange} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText('Enter system name...');
    await user.type(input, 'Am');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Amarr/i })).toBeInTheDocument();
    });

    await user.keyboard('{ArrowDown}');
    await user.keyboard('{Enter}');

    expect(handleChange).toHaveBeenCalledWith('Amarr');
  });
});
