import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Input } from './Input';
import { createRef } from 'react';

describe('Input', () => {
  describe('basic rendering', () => {
    it('renders an input element', () => {
      render(<Input />);
      expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('renders without label by default', () => {
      const { container } = render(<Input />);
      const label = container.querySelector('label');
      expect(label).not.toBeInTheDocument();
    });

    it('has base styling classes', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('w-full', 'px-4', 'py-2', 'bg-card', 'border', 'border-border', 'rounded-lg');
    });

    it('has text and placeholder styling', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('text-text', 'placeholder:text-text-secondary');
    });
  });

  describe('label prop', () => {
    it('renders label when provided', () => {
      render(<Input label="Username" />);
      expect(screen.getByText('Username')).toBeInTheDocument();
    });

    it('label is associated with input via htmlFor', () => {
      render(<Input label="Email" />);
      const label = screen.getByText('Email');
      const input = screen.getByRole('textbox');
      expect(label).toHaveAttribute('for', input.id);
    });

    it('label has proper styling', () => {
      render(<Input label="Password" />);
      const label = screen.getByText('Password');
      expect(label).toHaveClass('block', 'text-sm', 'font-medium', 'text-text-secondary', 'mb-1.5');
    });

    it('uses provided id for label association', () => {
      render(<Input label="Custom" id="custom-id" />);
      const label = screen.getByText('Custom');
      expect(label).toHaveAttribute('for', 'custom-id');
    });

    it('generates unique id when not provided', () => {
      const { rerender } = render(<Input label="First" />);
      const firstInput = screen.getByRole('textbox');
      const firstId = firstInput.id;

      rerender(<Input label="Second" key="second" />);
      const secondInput = screen.getByRole('textbox');

      expect(firstId).toBeTruthy();
      expect(secondInput.id).toBeTruthy();
    });
  });

  describe('error prop', () => {
    it('displays error message when provided', () => {
      render(<Input error="This field is required" />);
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    it('error message has role="alert"', () => {
      render(<Input error="Invalid input" />);
      expect(screen.getByRole('alert')).toHaveTextContent('Invalid input');
    });

    it('error message has proper styling', () => {
      render(<Input error="Error text" />);
      const error = screen.getByRole('alert');
      expect(error).toHaveClass('mt-1', 'text-sm', 'text-risk-red');
    });

    it('input has error border styling when error is present', () => {
      render(<Input error="Error" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('border-risk-red', 'focus:ring-risk-red');
    });

    it('does not display error message when not provided', () => {
      render(<Input />);
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('input does not have error styling when no error', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).not.toHaveClass('border-risk-red');
    });
  });

  describe('aria attributes', () => {
    it('sets aria-invalid="true" when error is present', () => {
      render(<Input error="Error message" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('does not set aria-invalid when no error', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).not.toHaveAttribute('aria-invalid');
    });

    it('sets aria-describedby pointing to error message', () => {
      render(<Input error="Error message" id="my-input" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'my-input-error');
    });

    it('error message has id matching aria-describedby', () => {
      render(<Input error="Error message" id="my-input" />);
      const error = screen.getByRole('alert');
      expect(error).toHaveAttribute('id', 'my-input-error');
    });

    it('does not set aria-describedby when no error', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).not.toHaveAttribute('aria-describedby');
    });
  });

  describe('ref forwarding', () => {
    it('forwards ref to the input element', () => {
      const ref = createRef<HTMLInputElement>();
      render(<Input ref={ref} />);
      expect(ref.current).toBeInstanceOf(HTMLInputElement);
    });

    it('ref can be used to focus the input', () => {
      const ref = createRef<HTMLInputElement>();
      render(<Input ref={ref} />);
      ref.current?.focus();
      expect(screen.getByRole('textbox')).toHaveFocus();
    });
  });

  describe('className prop', () => {
    it('applies custom className', () => {
      render(<Input className="custom-class" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('custom-class');
    });

    it('merges custom className with base styles', () => {
      render(<Input className="my-custom-class" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('w-full', 'my-custom-class');
    });
  });

  describe('input attributes', () => {
    it('passes through placeholder attribute', () => {
      render(<Input placeholder="Enter text..." />);
      const input = screen.getByPlaceholderText('Enter text...');
      expect(input).toBeInTheDocument();
    });

    it('passes through type attribute', () => {
      render(<Input type="email" data-testid="email-input" />);
      const input = screen.getByTestId('email-input');
      expect(input).toHaveAttribute('type', 'email');
    });

    it('passes through disabled attribute', () => {
      render(<Input disabled />);
      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
    });

    it('passes through required attribute', () => {
      render(<Input required />);
      const input = screen.getByRole('textbox');
      expect(input).toBeRequired();
    });

    it('passes through value and onChange', () => {
      const handleChange = vi.fn();
      render(<Input value="test" onChange={handleChange} />);
      const input = screen.getByRole('textbox');

      expect(input).toHaveValue('test');

      fireEvent.change(input, { target: { value: 'new value' } });
      expect(handleChange).toHaveBeenCalled();
    });

    it('passes through data-testid', () => {
      render(<Input data-testid="my-input" />);
      expect(screen.getByTestId('my-input')).toBeInTheDocument();
    });
  });

  describe('focus styling', () => {
    it('has focus ring styles', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('focus:outline-none', 'focus:ring-2', 'focus:ring-primary', 'focus:border-primary');
    });

    it('has transition styles', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('transition-all', 'duration-200');
    });
  });

  describe('displayName', () => {
    it('has displayName set for debugging', () => {
      expect(Input.displayName).toBe('Input');
    });
  });
});
