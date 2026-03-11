import { render, screen, fireEvent } from '@testing-library/react';
import { MarketTicker } from './MarketTicker';
import type { MarketTickerItem } from '@/lib/types';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  ArrowUpDown: (props: Record<string, unknown>) => <span data-testid="arrow-updown-icon" {...props} />,
  ArrowUp: (props: Record<string, unknown>) => <span data-testid="arrow-up-icon" {...props} />,
  ArrowDown: (props: Record<string, unknown>) => <span data-testid="arrow-down-icon" {...props} />,
}));

function createItem(overrides: Partial<MarketTickerItem> = {}): MarketTickerItem {
  return {
    type_id: 34,
    type_name: 'Tritanium',
    region_id: 10000002,
    region_name: 'The Forge',
    average_price: 5.5,
    highest: 6.0,
    lowest: 5.0,
    volume: 1000000,
    date: '2026-03-10',
    price_change_pct: 2.5,
    ...overrides,
  };
}

describe('MarketTicker', () => {
  it('renders item name', () => {
    render(<MarketTicker items={[createItem()]} />);
    expect(screen.getAllByText('Tritanium').length).toBeGreaterThanOrEqual(1);
  });

  it('renders region name', () => {
    render(<MarketTicker items={[createItem()]} />);
    expect(screen.getAllByText('The Forge').length).toBeGreaterThanOrEqual(1);
  });

  it('renders price change with positive sign', () => {
    render(<MarketTicker items={[createItem({ price_change_pct: 5.25 })]} />);
    expect(screen.getAllByText('+5.25%').length).toBeGreaterThanOrEqual(1);
  });

  it('renders negative price change', () => {
    render(<MarketTicker items={[createItem({ price_change_pct: -3.1 })]} />);
    expect(screen.getAllByText('-3.10%').length).toBeGreaterThanOrEqual(1);
  });

  it('renders zero price change', () => {
    render(<MarketTicker items={[createItem({ price_change_pct: 0 })]} />);
    expect(screen.getAllByText('0.00%').length).toBeGreaterThanOrEqual(1);
  });

  it('shows empty state when no items', () => {
    render(<MarketTicker items={[]} />);
    expect(screen.getByText(/No market data available/)).toBeInTheDocument();
  });

  it('renders multiple items', () => {
    const items = [
      createItem({ type_id: 34, type_name: 'Tritanium' }),
      createItem({ type_id: 35, type_name: 'Pyerite', region_id: 10000043, region_name: 'Domain' }),
    ];
    render(<MarketTicker items={items} />);
    expect(screen.getAllByText('Tritanium').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Pyerite').length).toBeGreaterThanOrEqual(1);
  });

  it('filters items by search', () => {
    const items = [
      createItem({ type_id: 34, type_name: 'Tritanium' }),
      createItem({ type_id: 35, type_name: 'Pyerite' }),
    ];
    render(<MarketTicker items={items} />);

    const input = screen.getByPlaceholderText('Filter items or regions...');
    fireEvent.change(input, { target: { value: 'Pyerite' } });

    // Pyerite should still be visible, Tritanium should be filtered out in desktop row
    expect(screen.getAllByText('Pyerite').length).toBeGreaterThanOrEqual(1);
  });

  it('filters items by region name', () => {
    const items = [
      createItem({ type_id: 34, region_name: 'The Forge' }),
      createItem({ type_id: 35, type_name: 'Pyerite', region_id: 10000043, region_name: 'Domain' }),
    ];
    render(<MarketTicker items={items} />);

    const input = screen.getByPlaceholderText('Filter items or regions...');
    fireEvent.change(input, { target: { value: 'Domain' } });

    expect(screen.getAllByText('Domain').length).toBeGreaterThanOrEqual(1);
  });

  it('shows no match message when filter has no results', () => {
    render(<MarketTicker items={[createItem()]} />);

    const input = screen.getByPlaceholderText('Filter items or regions...');
    fireEvent.change(input, { target: { value: 'nonexistent' } });

    expect(screen.getByText('No items match your filter.')).toBeInTheDocument();
  });

  it('renders sort headers', () => {
    render(<MarketTicker items={[createItem()]} />);
    expect(screen.getByText('Item')).toBeInTheDocument();
    expect(screen.getByText('Avg Price')).toBeInTheDocument();
    expect(screen.getByText('Change')).toBeInTheDocument();
    expect(screen.getByText('Vol')).toBeInTheDocument();
  });

  it('toggles sort direction on header click', () => {
    const items = [
      createItem({ type_id: 34, type_name: 'Tritanium', average_price: 5.5 }),
      createItem({ type_id: 35, type_name: 'Pyerite', average_price: 10.0 }),
    ];
    render(<MarketTicker items={items} />);

    // Click price header to sort descending
    fireEvent.click(screen.getByText('Avg Price'));
    // Click again to toggle direction
    fireEvent.click(screen.getByText('Avg Price'));

    // Component should not crash
    expect(screen.getAllByText('Tritanium').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Pyerite').length).toBeGreaterThanOrEqual(1);
  });

  it('formats ISK values', () => {
    render(
      <MarketTicker
        items={[createItem({ average_price: 3500000 })]}
      />
    );
    expect(screen.getAllByText('3.50M ISK').length).toBeGreaterThanOrEqual(1);
  });

  it('formats large volume', () => {
    render(
      <MarketTicker
        items={[createItem({ volume: 2500000 })]}
      />
    );
    expect(screen.getAllByText('2.5M').length).toBeGreaterThanOrEqual(1);
  });

  it('has accessible table role', () => {
    render(<MarketTicker items={[createItem()]} />);
    expect(screen.getByRole('table', { name: 'Market ticker prices' })).toBeInTheDocument();
  });

  it('has accessible filter input', () => {
    render(<MarketTicker items={[createItem()]} />);
    expect(screen.getByLabelText('Filter market ticker')).toBeInTheDocument();
  });

  it('applies green class for positive change', () => {
    render(<MarketTicker items={[createItem({ price_change_pct: 5.0 })]} />);
    const elements = screen.getAllByText('+5.00%');
    // At least one element should have the green class
    const hasGreenClass = elements.some((el) =>
      el.className.includes('text-risk-green')
    );
    expect(hasGreenClass).toBe(true);
  });

  it('applies red class for negative change', () => {
    render(<MarketTicker items={[createItem({ price_change_pct: -3.0 })]} />);
    const elements = screen.getAllByText('-3.00%');
    const hasRedClass = elements.some((el) =>
      el.className.includes('text-risk-red')
    );
    expect(hasRedClass).toBe(true);
  });
});
