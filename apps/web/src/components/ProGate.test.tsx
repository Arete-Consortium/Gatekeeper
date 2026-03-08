import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProGate } from './ProGate';

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('ProGate', () => {
  it('renders children when user is Pro', () => {
    mockUseAuth.mockReturnValue({ isPro: true, isAuthenticated: true });

    render(
      <ProGate feature="Kill Alerts">
        <div>Pro content</div>
      </ProGate>
    );

    expect(screen.getByText('Pro content')).toBeInTheDocument();
  });

  it('shows upgrade CTA when user is free tier', () => {
    mockUseAuth.mockReturnValue({ isPro: false, isAuthenticated: true });

    render(
      <ProGate feature="Kill Alerts">
        <div>Pro content</div>
      </ProGate>
    );

    expect(screen.queryByText('Pro content')).not.toBeInTheDocument();
    expect(screen.getByText('Kill Alerts requires Pro')).toBeInTheDocument();
    expect(screen.getByText('Upgrade to Pro')).toBeInTheDocument();
  });

  it('shows upgrade CTA when not authenticated', () => {
    mockUseAuth.mockReturnValue({ isPro: false, isAuthenticated: false });

    render(
      <ProGate feature="Advanced Stats">
        <div>Pro content</div>
      </ProGate>
    );

    expect(screen.queryByText('Pro content')).not.toBeInTheDocument();
    expect(screen.getByText('Advanced Stats requires Pro')).toBeInTheDocument();
  });

  it('shows generic text when no feature name provided', () => {
    mockUseAuth.mockReturnValue({ isPro: false, isAuthenticated: true });

    render(
      <ProGate>
        <div>Pro content</div>
      </ProGate>
    );

    expect(screen.getByText('Pro Feature')).toBeInTheDocument();
  });
});
