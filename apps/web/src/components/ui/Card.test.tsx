import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './Card';

describe('Card', () => {
  describe('basic rendering', () => {
    it('renders children correctly', () => {
      render(<Card>Card content</Card>);
      expect(screen.getByText('Card content')).toBeInTheDocument();
    });

    it('renders as a div element', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card?.nodeName).toBe('DIV');
    });

    it('has base card styles', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('bg-card', 'rounded-lg', 'border', 'border-border', 'p-4');
    });
  });

  describe('hover prop', () => {
    it('does not apply hover styles by default', () => {
      const { container } = render(<Card>Content</Card>);
      const card = container.firstChild;
      expect(card).not.toHaveClass('card-hover', 'cursor-pointer');
    });

    it('applies hover styles when hover is true', () => {
      const { container } = render(<Card hover>Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('card-hover', 'cursor-pointer');
    });

    it('does not apply hover styles when hover is false', () => {
      const { container } = render(<Card hover={false}>Content</Card>);
      const card = container.firstChild;
      expect(card).not.toHaveClass('card-hover');
    });
  });

  describe('className prop', () => {
    it('applies custom className', () => {
      const { container } = render(<Card className="custom-class">Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('custom-class');
    });

    it('merges custom className with base styles', () => {
      const { container } = render(<Card className="my-extra-class">Content</Card>);
      const card = container.firstChild;
      expect(card).toHaveClass('bg-card', 'my-extra-class');
    });
  });

  describe('additional props', () => {
    it('passes through data-testid', () => {
      render(<Card data-testid="test-card">Content</Card>);
      expect(screen.getByTestId('test-card')).toBeInTheDocument();
    });

    it('passes through onClick handler', async () => {
      const handleClick = vi.fn();
      render(<Card onClick={handleClick} data-testid="clickable-card">Content</Card>);
      const card = screen.getByTestId('clickable-card');

      fireEvent.click(card);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('passes through aria attributes', () => {
      render(<Card aria-label="test card">Content</Card>);
      expect(screen.getByLabelText('test card')).toBeInTheDocument();
    });
  });
});

describe('CardHeader', () => {
  it('renders children correctly', () => {
    render(<CardHeader>Header content</CardHeader>);
    expect(screen.getByText('Header content')).toBeInTheDocument();
  });

  it('has base margin-bottom style', () => {
    const { container } = render(<CardHeader>Header</CardHeader>);
    const header = container.firstChild;
    expect(header).toHaveClass('mb-4');
  });

  it('applies custom className', () => {
    const { container } = render(<CardHeader className="custom-header">Header</CardHeader>);
    const header = container.firstChild;
    expect(header).toHaveClass('custom-header', 'mb-4');
  });

  it('passes through additional props', () => {
    render(<CardHeader data-testid="card-header">Header</CardHeader>);
    expect(screen.getByTestId('card-header')).toBeInTheDocument();
  });
});

describe('CardTitle', () => {
  it('renders children correctly', () => {
    render(<CardTitle>Title text</CardTitle>);
    expect(screen.getByText('Title text')).toBeInTheDocument();
  });

  it('renders as h3 element', () => {
    render(<CardTitle>Title</CardTitle>);
    const title = screen.getByRole('heading', { level: 3 });
    expect(title).toBeInTheDocument();
  });

  it('has base font styles', () => {
    const { container } = render(<CardTitle>Title</CardTitle>);
    const title = container.firstChild;
    expect(title).toHaveClass('text-lg', 'font-semibold', 'text-text');
  });

  it('applies custom className', () => {
    const { container } = render(<CardTitle className="custom-title">Title</CardTitle>);
    const title = container.firstChild;
    expect(title).toHaveClass('custom-title');
  });

  it('passes through additional props', () => {
    render(<CardTitle id="my-title">Title</CardTitle>);
    expect(document.getElementById('my-title')).toBeInTheDocument();
  });
});

describe('CardDescription', () => {
  it('renders children correctly', () => {
    render(<CardDescription>Description text</CardDescription>);
    expect(screen.getByText('Description text')).toBeInTheDocument();
  });

  it('renders as p element', () => {
    const { container } = render(<CardDescription>Description</CardDescription>);
    const desc = container.firstChild;
    expect(desc?.nodeName).toBe('P');
  });

  it('has base text styles', () => {
    const { container } = render(<CardDescription>Description</CardDescription>);
    const desc = container.firstChild;
    expect(desc).toHaveClass('text-sm', 'text-text-secondary', 'mt-1');
  });

  it('applies custom className', () => {
    const { container } = render(<CardDescription className="custom-desc">Description</CardDescription>);
    const desc = container.firstChild;
    expect(desc).toHaveClass('custom-desc');
  });
});

describe('CardContent', () => {
  it('renders children correctly', () => {
    render(<CardContent>Content text</CardContent>);
    expect(screen.getByText('Content text')).toBeInTheDocument();
  });

  it('renders as div element', () => {
    const { container } = render(<CardContent>Content</CardContent>);
    const content = container.firstChild;
    expect(content?.nodeName).toBe('DIV');
  });

  it('applies custom className', () => {
    const { container } = render(<CardContent className="custom-content">Content</CardContent>);
    const content = container.firstChild;
    expect(content).toHaveClass('custom-content');
  });

  it('passes through additional props', () => {
    render(<CardContent data-testid="card-content">Content</CardContent>);
    expect(screen.getByTestId('card-content')).toBeInTheDocument();
  });
});

describe('Card composition', () => {
  it('composes all subcomponents correctly', () => {
    render(
      <Card data-testid="composed-card">
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
          <CardDescription>Test Description</CardDescription>
        </CardHeader>
        <CardContent>Test Content</CardContent>
      </Card>
    );

    expect(screen.getByTestId('composed-card')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Test Title' })).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('supports hover card with all subcomponents', () => {
    const { container } = render(
      <Card hover>
        <CardHeader>
          <CardTitle>Hover Card</CardTitle>
        </CardHeader>
        <CardContent>Click me!</CardContent>
      </Card>
    );

    const card = container.firstChild;
    expect(card).toHaveClass('card-hover', 'cursor-pointer');
  });
});
