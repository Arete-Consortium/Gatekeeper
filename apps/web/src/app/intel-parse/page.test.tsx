import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import IntelParsePage from './page';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  MessageSquareText: (props: Record<string, unknown>) => <span data-testid="icon-message" {...props} />,
  MapPin: (props: Record<string, unknown>) => <span data-testid="icon-map-pin" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="icon-loader" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="icon-alert" {...props} />,
  CheckCircle: (props: Record<string, unknown>) => <span data-testid="icon-check" {...props} />,
  HelpCircle: (props: Record<string, unknown>) => <span data-testid="icon-help" {...props} />,
}));

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/intel-parse',
}));

// Mock API
const mockParseIntel = vi.fn();
vi.mock('@/lib/api', () => ({
  GatekeeperAPI: {
    parseIntel: (...args: unknown[]) => mockParseIntel(...args),
  },
}));

// Mock UI components
vi.mock('@/components/ui', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="card" className={className}>{children}</div>
  ),
  Button: ({
    children,
    onClick,
    disabled,
    loading,
    className,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    loading?: boolean;
    className?: string;
  }) => (
    <button onClick={onClick} disabled={disabled || loading} className={className} data-testid="button">
      {children}
    </button>
  ),
  ErrorMessage: ({ title, message }: { title: string; message: string }) => (
    <div data-testid="error-message">
      {title}: {message}
    </div>
  ),
  getUserFriendlyError: (err: Error) => err.message,
}));

describe('IntelParsePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page with header and textarea', () => {
    render(<IntelParsePage />);

    expect(screen.getByText('Intel Parser')).toBeInTheDocument();
    expect(screen.getByTestId('intel-textarea')).toBeInTheDocument();
  });

  it('shows empty state when no results', () => {
    render(<IntelParsePage />);

    expect(
      screen.getByText('Paste intel channel or local chat to identify systems and their status')
    ).toBeInTheDocument();
  });

  it('disables parse button when textarea is empty', () => {
    render(<IntelParsePage />);

    const buttons = screen.getAllByTestId('button');
    const parseButton = buttons.find((b) => b.textContent?.includes('Parse'));
    expect(parseButton).toBeDisabled();
  });

  it('enables parse button when textarea has content', () => {
    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'Jita clear' } });

    const buttons = screen.getAllByTestId('button');
    const parseButton = buttons.find((b) => b.textContent?.includes('Parse'));
    expect(parseButton).not.toBeDisabled();
  });

  it('calls parseIntel API on parse button click', async () => {
    mockParseIntel.mockResolvedValue({ systems: [], unknown_lines: [] });

    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'Jita clear' } });

    const buttons = screen.getAllByTestId('button');
    const parseButton = buttons.find((b) => b.textContent?.includes('Parse'));
    fireEvent.click(parseButton!);

    await waitFor(() => {
      expect(mockParseIntel).toHaveBeenCalledWith('Jita clear');
    });
  });

  it('displays parsed systems in results', async () => {
    mockParseIntel.mockResolvedValue({
      systems: [
        {
          system_name: 'Jita',
          system_id: 30000142,
          status: 'clear',
          hostile_count: 0,
          mentioned_at: 'Jita clear',
        },
        {
          system_name: 'HED-GP',
          system_id: 30001161,
          status: 'hostile',
          hostile_count: 3,
          mentioned_at: 'HED-GP +3',
        },
      ],
      unknown_lines: [],
    });

    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'Jita clear\nHED-GP +3' } });

    const buttons = screen.getAllByTestId('button');
    const parseButton = buttons.find((b) => b.textContent?.includes('Parse'));
    fireEvent.click(parseButton!);

    await waitFor(() => {
      expect(screen.getAllByText('Jita').length).toBeGreaterThan(0);
      expect(screen.getAllByText('HED-GP').length).toBeGreaterThan(0);
    });
  });

  it('shows summary stats after parsing', async () => {
    mockParseIntel.mockResolvedValue({
      systems: [
        { system_name: 'Jita', system_id: 1, status: 'clear', hostile_count: 0, mentioned_at: '' },
        { system_name: 'Tama', system_id: 2, status: 'hostile', hostile_count: 2, mentioned_at: '' },
      ],
      unknown_lines: ['random text'],
    });

    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'test' } });

    const buttons = screen.getAllByTestId('button');
    fireEvent.click(buttons.find((b) => b.textContent?.includes('Parse'))!);

    await waitFor(() => {
      // Stats cards render — check for "Systems" label
      expect(screen.getByText('Systems')).toBeInTheDocument();
    });
  });

  it('displays unknown lines section', async () => {
    mockParseIntel.mockResolvedValue({
      systems: [],
      unknown_lines: ['gibberish line 1', 'gibberish line 2'],
    });

    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'test' } });

    const buttons = screen.getAllByTestId('button');
    fireEvent.click(buttons.find((b) => b.textContent?.includes('Parse'))!);

    await waitFor(() => {
      expect(screen.getByText('gibberish line 1')).toBeInTheDocument();
      expect(screen.getByText('gibberish line 2')).toBeInTheDocument();
    });
  });

  it('shows error message on API failure', async () => {
    mockParseIntel.mockRejectedValue(new Error('Network error'));

    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'test' } });

    const buttons = screen.getAllByTestId('button');
    fireEvent.click(buttons.find((b) => b.textContent?.includes('Parse'))!);

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('navigates to map with highlight param on button click', async () => {
    mockParseIntel.mockResolvedValue({
      systems: [
        { system_name: 'Jita', system_id: 1, status: 'clear', hostile_count: 0, mentioned_at: '' },
        { system_name: 'Tama', system_id: 2, status: 'hostile', hostile_count: 1, mentioned_at: '' },
      ],
      unknown_lines: [],
    });

    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'test' } });

    const buttons = screen.getAllByTestId('button');
    fireEvent.click(buttons.find((b) => b.textContent?.includes('Parse'))!);

    await waitFor(() => {
      expect(screen.getAllByText('Jita').length).toBeGreaterThan(0);
    });

    // Find and click the "Highlight on Map" button
    const allButtons = screen.getAllByTestId('button');
    const highlightButton = allButtons.find((b) => b.textContent?.includes('Highlight on Map'));
    expect(highlightButton).toBeTruthy();
    fireEvent.click(highlightButton!);

    expect(mockPush).toHaveBeenCalledWith('/map?highlight=Jita%2CTama');
  });

  it('shows line count in footer text', () => {
    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'line1\nline2\nline3' } });

    expect(screen.getByText('3 lines')).toBeInTheDocument();
  });

  it('supports Ctrl+Enter to parse', async () => {
    mockParseIntel.mockResolvedValue({ systems: [], unknown_lines: [] });

    render(<IntelParsePage />);

    const textarea = screen.getByTestId('intel-textarea');
    fireEvent.change(textarea, { target: { value: 'Jita clear' } });
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

    await waitFor(() => {
      expect(mockParseIntel).toHaveBeenCalledWith('Jita clear');
    });
  });
});
