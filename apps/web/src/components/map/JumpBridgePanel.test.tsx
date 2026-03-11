import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { JumpBridgePanel } from './JumpBridgePanel';

// Mock lucide-react icons (project convention)
vi.mock('lucide-react', () => ({
  X: () => <span>X</span>,
}));

// Mock API
const mockGetJumpBridges = vi.fn();
const mockAddJumpBridge = vi.fn();
const mockDeleteJumpBridge = vi.fn();
const mockImportJumpBridges = vi.fn();

vi.mock('@/lib/api', () => ({
  GatekeeperAPI: {
    getJumpBridges: (...args: unknown[]) => mockGetJumpBridges(...args),
    addJumpBridge: (...args: unknown[]) => mockAddJumpBridge(...args),
    deleteJumpBridge: (...args: unknown[]) => mockDeleteJumpBridge(...args),
    importJumpBridges: (...args: unknown[]) => mockImportJumpBridges(...args),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('JumpBridgePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetJumpBridges.mockResolvedValue({ bridges: [], total: 0 });
  });

  it('renders with empty state', async () => {
    render(<JumpBridgePanel />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText(/No jump bridges configured/)
      ).toBeInTheDocument();
    });
  });

  it('renders bridge list', async () => {
    mockGetJumpBridges.mockResolvedValue({
      bridges: [
        {
          id: 'jb-test1',
          from_system: '1DQ1-A',
          from_system_id: 30004759,
          to_system: '8QT-H4',
          to_system_id: 30004760,
          owner_alliance: null,
          status: 'online',
          created_at: '2026-03-11T00:00:00Z',
          created_by: null,
          notes: '',
        },
      ],
      total: 1,
    });

    render(<JumpBridgePanel />, { wrapper: createWrapper() });

    // Text is split across child elements, so use a function matcher
    await waitFor(() => {
      const bridgeItems = screen.getAllByText((content, element) => {
        return element?.textContent?.includes('1DQ1-A') ?? false;
      });
      expect(bridgeItems.length).toBeGreaterThan(0);
    });
  });

  it('shows add form when clicking + Add', async () => {
    render(<JumpBridgePanel />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('+ Add')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('+ Add'));

    expect(
      screen.getByPlaceholderText(/From system/)
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/To system/)
    ).toBeInTheDocument();
  });

  it('shows import form when clicking Import', async () => {
    render(<JumpBridgePanel />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Import')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Import'));

    expect(
      screen.getByPlaceholderText(/Paste jump bridges/)
    ).toBeInTheDocument();
  });

  it('displays status indicator colors', async () => {
    mockGetJumpBridges.mockResolvedValue({
      bridges: [
        {
          id: 'jb-online',
          from_system: '1DQ1-A',
          from_system_id: 1,
          to_system: '8QT-H4',
          to_system_id: 2,
          owner_alliance: null,
          status: 'online',
          created_at: '2026-03-11T00:00:00Z',
          created_by: null,
          notes: '',
        },
        {
          id: 'jb-offline',
          from_system: '49-U6U',
          from_system_id: 3,
          to_system: 'PUIG-F',
          to_system_id: 4,
          owner_alliance: null,
          status: 'offline',
          created_at: '2026-03-11T00:00:00Z',
          created_by: null,
          notes: '',
        },
      ],
      total: 2,
    });

    render(<JumpBridgePanel />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTitle('Online')).toBeInTheDocument();
      expect(screen.getByTitle('Offline')).toBeInTheDocument();
    });
  });

  it('displays bridge count in header', async () => {
    mockGetJumpBridges.mockResolvedValue({
      bridges: [
        {
          id: 'jb-1',
          from_system: '1DQ1-A',
          from_system_id: 1,
          to_system: '8QT-H4',
          to_system_id: 2,
          owner_alliance: null,
          status: 'unknown',
          created_at: '2026-03-11T00:00:00Z',
          created_by: null,
          notes: '',
        },
      ],
      total: 1,
    });

    render(<JumpBridgePanel />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('(1)')).toBeInTheDocument();
    });
  });

  it('toggles between add and import forms', async () => {
    render(<JumpBridgePanel />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('+ Add')).toBeInTheDocument();
    });

    // Open add form
    fireEvent.click(screen.getByText('+ Add'));
    expect(screen.getByPlaceholderText(/From system/)).toBeInTheDocument();

    // Switch to import — should close add form
    fireEvent.click(screen.getByText('Import'));
    expect(screen.queryByPlaceholderText(/From system/)).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Paste jump bridges/)).toBeInTheDocument();
  });
});
