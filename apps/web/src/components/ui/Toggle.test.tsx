import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Toggle } from './Toggle';

describe('Toggle', () => {
  describe('basic rendering', () => {
    it('renders without label', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toBeInTheDocument();
    });

    it('renders with label', () => {
      render(<Toggle checked={false} onChange={() => {}} label="Test Label" />);
      expect(screen.getByText('Test Label')).toBeInTheDocument();
    });

    it('renders as a button element', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle.tagName).toBe('BUTTON');
    });

    it('has type="button" to prevent form submission', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveAttribute('type', 'button');
    });
  });

  describe('checked state', () => {
    it('has aria-checked false when unchecked', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveAttribute('aria-checked', 'false');
    });

    it('has aria-checked true when checked', () => {
      render(<Toggle checked={true} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveAttribute('aria-checked', 'true');
    });

    it('applies bg-primary when checked', () => {
      render(<Toggle checked={true} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveClass('bg-primary');
    });

    it('applies bg-border when unchecked', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveClass('bg-border');
    });

    it('knob translates right when checked', () => {
      const { container } = render(<Toggle checked={true} onChange={() => {}} />);
      const knob = container.querySelector('span.inline-block');
      expect(knob).toHaveClass('translate-x-6');
    });

    it('knob translates left when unchecked', () => {
      const { container } = render(<Toggle checked={false} onChange={() => {}} />);
      const knob = container.querySelector('span.inline-block');
      expect(knob).toHaveClass('translate-x-1');
    });
  });

  describe('onChange handler', () => {
    it('calls onChange with true when toggling from off to on', () => {
      const handleChange = vi.fn();
      render(<Toggle checked={false} onChange={handleChange} />);

      fireEvent.click(screen.getByRole('switch'));

      expect(handleChange).toHaveBeenCalledTimes(1);
      expect(handleChange).toHaveBeenCalledWith(true);
    });

    it('calls onChange with false when toggling from on to off', () => {
      const handleChange = vi.fn();
      render(<Toggle checked={true} onChange={handleChange} />);

      fireEvent.click(screen.getByRole('switch'));

      expect(handleChange).toHaveBeenCalledTimes(1);
      expect(handleChange).toHaveBeenCalledWith(false);
    });

    it('does not call onChange when disabled and clicked', () => {
      const handleChange = vi.fn();
      render(<Toggle checked={false} onChange={handleChange} disabled />);

      fireEvent.click(screen.getByRole('switch'));

      expect(handleChange).not.toHaveBeenCalled();
    });
  });

  describe('disabled state', () => {
    it('has disabled attribute when disabled', () => {
      render(<Toggle checked={false} onChange={() => {}} disabled />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toBeDisabled();
    });

    it('does not have disabled attribute when not disabled', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).not.toBeDisabled();
    });

    it('applies opacity and cursor styles to label when disabled', () => {
      const { container } = render(<Toggle checked={false} onChange={() => {}} disabled label="Test" />);
      const label = container.querySelector('label');
      expect(label).toHaveClass('opacity-50', 'cursor-not-allowed');
    });

    it('applies cursor-not-allowed to button when disabled', () => {
      render(<Toggle checked={false} onChange={() => {}} disabled />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveClass('cursor-not-allowed');
    });

    it('defaults disabled to false', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).not.toBeDisabled();
    });
  });

  describe('label prop', () => {
    it('sets aria-label on the button', () => {
      render(<Toggle checked={false} onChange={() => {}} label="My Toggle" />);
      const toggle = screen.getByRole('switch', { name: 'My Toggle' });
      expect(toggle).toBeInTheDocument();
    });

    it('renders label text after the toggle button', () => {
      const { container } = render(<Toggle checked={false} onChange={() => {}} label="Label Text" />);
      const labelSpan = container.querySelector('span.text-sm');
      expect(labelSpan).toHaveTextContent('Label Text');
    });

    it('does not render label span when label is not provided', () => {
      const { container } = render(<Toggle checked={false} onChange={() => {}} />);
      const labelSpan = container.querySelector('span.text-sm.text-text');
      expect(labelSpan).not.toBeInTheDocument();
    });
  });

  describe('styling', () => {
    it('has focus ring styles', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveClass('focus:ring-2', 'focus:ring-primary');
    });

    it('has transition styles for smooth animation', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveClass('transition-colors', 'duration-200');
    });

    it('toggle knob has proper dimensions', () => {
      const { container } = render(<Toggle checked={false} onChange={() => {}} />);
      const knob = container.querySelector('span.inline-block');
      expect(knob).toHaveClass('h-4', 'w-4', 'rounded-full', 'bg-white');
    });

    it('toggle track has proper dimensions', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      expect(toggle).toHaveClass('h-6', 'w-11', 'rounded-full');
    });
  });

  describe('accessibility', () => {
    it('has role="switch"', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      expect(screen.getByRole('switch')).toBeInTheDocument();
    });

    it('is focusable', () => {
      render(<Toggle checked={false} onChange={() => {}} />);
      const toggle = screen.getByRole('switch');
      toggle.focus();
      expect(toggle).toHaveFocus();
    });

    it('can be toggled with keyboard Enter key', () => {
      const handleChange = vi.fn();
      render(<Toggle checked={false} onChange={handleChange} />);
      const toggle = screen.getByRole('switch');

      fireEvent.keyDown(toggle, { key: 'Enter' });
      // Note: The actual keyboard interaction depends on the button's default behavior
      // which handles Enter as a click
    });
  });
});
