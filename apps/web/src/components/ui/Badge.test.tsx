import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from './Badge';

describe('Badge', () => {
  it('renders children correctly', () => {
    render(<Badge>Test Badge</Badge>);
    expect(screen.getByText('Test Badge')).toBeInTheDocument();
  });

  it('applies default variant styles', () => {
    render(<Badge>Default</Badge>);
    const badge = screen.getByText('Default');
    expect(badge).toHaveClass('bg-card', 'text-text-secondary');
  });

  it('applies success variant correctly', () => {
    render(<Badge variant="success">Success</Badge>);
    const badge = screen.getByText('Success');
    expect(badge).toHaveClass('text-risk-green');
  });

  it('applies warning variant correctly', () => {
    render(<Badge variant="warning">Warning</Badge>);
    const badge = screen.getByText('Warning');
    expect(badge).toHaveClass('text-risk-yellow');
  });

  it('applies danger variant correctly', () => {
    render(<Badge variant="danger">Danger</Badge>);
    const badge = screen.getByText('Danger');
    expect(badge).toHaveClass('text-risk-red');
  });

  it('applies info variant correctly', () => {
    render(<Badge variant="info">Info</Badge>);
    const badge = screen.getByText('Info');
    expect(badge).toHaveClass('text-primary');
  });

  it('applies sm size correctly', () => {
    render(<Badge size="sm">Small</Badge>);
    const badge = screen.getByText('Small');
    expect(badge).toHaveClass('px-2', 'py-0.5', 'text-xs');
  });

  it('applies md size by default', () => {
    render(<Badge>Medium</Badge>);
    const badge = screen.getByText('Medium');
    expect(badge).toHaveClass('px-2.5', 'py-1', 'text-sm');
  });

  it('applies custom className', () => {
    render(<Badge className="custom-class">Custom</Badge>);
    const badge = screen.getByText('Custom');
    expect(badge).toHaveClass('custom-class');
  });

  it('renders as a span element', () => {
    render(<Badge>Span</Badge>);
    const badge = screen.getByText('Span');
    expect(badge.tagName).toBe('SPAN');
  });

  it('has base styles for all variants', () => {
    render(<Badge>Base</Badge>);
    const badge = screen.getByText('Base');
    expect(badge).toHaveClass('inline-flex', 'items-center', 'font-medium', 'rounded-md', 'border');
  });

  it('passes through additional props', () => {
    render(<Badge data-testid="badge-test" title="Badge tooltip">Props</Badge>);
    const badge = screen.getByTestId('badge-test');
    expect(badge).toHaveAttribute('title', 'Badge tooltip');
  });

  it('combines variant and size correctly', () => {
    render(<Badge variant="danger" size="sm">Small Danger</Badge>);
    const badge = screen.getByText('Small Danger');
    expect(badge).toHaveClass('text-risk-red', 'px-2', 'text-xs');
  });
});
