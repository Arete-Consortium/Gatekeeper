import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SecurityBadge } from './SecurityBadge';

describe('SecurityBadge', () => {
  describe('security value display', () => {
    it('displays security value with one decimal place', () => {
      render(<SecurityBadge security={0.95} />);
      // 0.95 rounds to 0.9 with toFixed(1)
      expect(screen.getByText('0.9')).toBeInTheDocument();
    });

    it('displays security value rounded correctly', () => {
      render(<SecurityBadge security={0.54} />);
      expect(screen.getByText('0.5')).toBeInTheDocument();
    });

    it('displays negative security values', () => {
      render(<SecurityBadge security={-0.5} />);
      expect(screen.getByText('-0.5')).toBeInTheDocument();
    });

    it('displays zero security correctly', () => {
      render(<SecurityBadge security={0} />);
      expect(screen.getByText('0.0')).toBeInTheDocument();
    });

    it('handles null security by defaulting to 0', () => {
      // @ts-expect-error - Testing null handling
      render(<SecurityBadge security={null} />);
      expect(screen.getByText('0.0')).toBeInTheDocument();
    });

    it('handles undefined security by defaulting to 0', () => {
      // @ts-expect-error - Testing undefined handling
      render(<SecurityBadge security={undefined} />);
      expect(screen.getByText('0.0')).toBeInTheDocument();
    });
  });

  describe('showValue prop', () => {
    it('shows numeric value when showValue is true', () => {
      render(<SecurityBadge security={0.8} showValue={true} />);
      expect(screen.getByText('0.8')).toBeInTheDocument();
    });

    it('shows H for high-sec when showValue is false', () => {
      render(<SecurityBadge security={0.8} showValue={false} />);
      expect(screen.getByText('H')).toBeInTheDocument();
    });

    it('shows L for low-sec when showValue is false', () => {
      render(<SecurityBadge security={0.3} showValue={false} />);
      expect(screen.getByText('L')).toBeInTheDocument();
    });

    it('shows N for null-sec when showValue is false', () => {
      render(<SecurityBadge security={-0.5} showValue={false} />);
      expect(screen.getByText('N')).toBeInTheDocument();
    });

    it('shows N for zero sec when showValue is false', () => {
      render(<SecurityBadge security={0} showValue={false} />);
      expect(screen.getByText('N')).toBeInTheDocument();
    });

    it('treats 0.5 as high-sec boundary when showValue is false', () => {
      render(<SecurityBadge security={0.5} showValue={false} />);
      expect(screen.getByText('H')).toBeInTheDocument();
    });
  });

  describe('security color styles', () => {
    it('applies high-sec color for security >= 0.5', () => {
      const { container } = render(<SecurityBadge security={0.8} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-high-sec');
      expect(badge).toHaveClass('bg-high-sec/20');
    });

    it('applies high-sec color at boundary (0.5)', () => {
      const { container } = render(<SecurityBadge security={0.5} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-high-sec');
    });

    it('applies low-sec color for security > 0 and < 0.5', () => {
      const { container } = render(<SecurityBadge security={0.3} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-low-sec');
      expect(badge).toHaveClass('bg-low-sec/20');
    });

    it('applies null-sec color for security <= 0', () => {
      const { container } = render(<SecurityBadge security={-0.5} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-null-sec');
      expect(badge).toHaveClass('bg-null-sec/20');
    });

    it('applies null-sec color for zero security', () => {
      const { container } = render(<SecurityBadge security={0} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-null-sec');
    });
  });

  describe('size variants', () => {
    it('applies sm size correctly', () => {
      const { container } = render(<SecurityBadge security={0.8} size="sm" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('px-1.5', 'py-0.5', 'text-xs');
    });

    it('applies md size by default', () => {
      const { container } = render(<SecurityBadge security={0.8} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('px-2', 'py-0.5', 'text-sm');
    });

    it('applies lg size correctly', () => {
      const { container } = render(<SecurityBadge security={0.8} size="lg" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('px-2.5', 'py-1', 'text-base');
    });
  });

  describe('base styles', () => {
    it('renders as a span element', () => {
      const { container } = render(<SecurityBadge security={0.8} />);
      const badge = container.firstChild;
      expect(badge?.nodeName).toBe('SPAN');
    });

    it('has base inline-flex and font styles', () => {
      const { container } = render(<SecurityBadge security={0.8} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('inline-flex', 'items-center', 'font-mono', 'font-semibold', 'rounded', 'border');
    });
  });

  describe('edge cases', () => {
    it('handles very low security values', () => {
      render(<SecurityBadge security={-1.0} />);
      expect(screen.getByText('-1.0')).toBeInTheDocument();
    });

    it('handles very high security values', () => {
      render(<SecurityBadge security={1.0} />);
      expect(screen.getByText('1.0')).toBeInTheDocument();
    });

    it('handles security value of exactly 0.4999', () => {
      const { container } = render(<SecurityBadge security={0.4999} />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-low-sec');
    });
  });
});
