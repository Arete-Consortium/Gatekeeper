import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskBadge } from './RiskBadge';

describe('RiskBadge', () => {
  describe('risk colors', () => {
    it('renders green risk with Safe label', () => {
      render(<RiskBadge riskColor="green" />);
      expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('renders yellow risk with Caution label', () => {
      render(<RiskBadge riskColor="yellow" />);
      expect(screen.getByText('Caution')).toBeInTheDocument();
    });

    it('renders orange risk with Danger label', () => {
      render(<RiskBadge riskColor="orange" />);
      expect(screen.getByText('Danger')).toBeInTheDocument();
    });

    it('renders red risk with Critical label', () => {
      render(<RiskBadge riskColor="red" />);
      expect(screen.getByText('Critical')).toBeInTheDocument();
    });
  });

  describe('color styles', () => {
    it('applies green color styles', () => {
      const { container } = render(<RiskBadge riskColor="green" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-risk-green');
    });

    it('applies yellow color styles', () => {
      const { container } = render(<RiskBadge riskColor="yellow" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-risk-yellow');
    });

    it('applies orange color styles', () => {
      const { container } = render(<RiskBadge riskColor="orange" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-risk-orange');
    });

    it('applies red color styles', () => {
      const { container } = render(<RiskBadge riskColor="red" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('text-risk-red');
    });
  });

  describe('risk score display', () => {
    it('displays risk score when provided', () => {
      render(<RiskBadge riskColor="yellow" riskScore={7.5} />);
      expect(screen.getByText('7.5')).toBeInTheDocument();
    });

    it('displays label when risk score is not provided', () => {
      render(<RiskBadge riskColor="green" />);
      expect(screen.getByText('Safe')).toBeInTheDocument();
      expect(screen.queryByText(/\d+\.\d+/)).not.toBeInTheDocument();
    });

    it('formats risk score to one decimal place', () => {
      render(<RiskBadge riskColor="red" riskScore={9.123} />);
      expect(screen.getByText('9.1')).toBeInTheDocument();
    });

    it('handles zero risk score', () => {
      render(<RiskBadge riskColor="green" riskScore={0} />);
      expect(screen.getByText('0.0')).toBeInTheDocument();
    });
  });

  describe('icon display', () => {
    it('shows icon by default', () => {
      const { container } = render(<RiskBadge riskColor="green" />);
      const svg = container.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });

    it('hides icon when showIcon is false', () => {
      const { container } = render(<RiskBadge riskColor="green" showIcon={false} />);
      const svg = container.querySelector('svg');
      expect(svg).not.toBeInTheDocument();
    });
  });

  describe('size variants', () => {
    it('applies sm size correctly', () => {
      const { container } = render(<RiskBadge riskColor="green" size="sm" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('px-1.5', 'py-0.5', 'text-xs');
    });

    it('applies md size by default', () => {
      const { container } = render(<RiskBadge riskColor="green" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('px-2', 'py-0.5', 'text-sm');
    });

    it('applies lg size correctly', () => {
      const { container } = render(<RiskBadge riskColor="green" size="lg" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('px-2.5', 'py-1', 'text-base');
    });

    it('applies correct icon size for sm', () => {
      const { container } = render(<RiskBadge riskColor="green" size="sm" />);
      const svg = container.querySelector('svg');
      expect(svg).toHaveClass('h-3', 'w-3');
    });

    it('applies correct icon size for lg', () => {
      const { container } = render(<RiskBadge riskColor="green" size="lg" />);
      const svg = container.querySelector('svg');
      expect(svg).toHaveClass('h-4', 'w-4');
    });
  });

  describe('base styles', () => {
    it('has base inline-flex styles', () => {
      const { container } = render(<RiskBadge riskColor="green" />);
      const badge = container.firstChild;
      expect(badge).toHaveClass('inline-flex', 'items-center', 'font-medium', 'rounded', 'border');
    });
  });
});
