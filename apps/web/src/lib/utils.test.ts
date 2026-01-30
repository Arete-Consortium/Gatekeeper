import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  cn,
  formatRelativeTime,
  formatIsk,
  getSecurityClass,
  getSecurityLabel,
  getRiskColorClass,
  getRiskBgClass,
  debounce,
  ROUTE_PROFILES,
} from './utils';

describe('cn (classname merge)', () => {
  it('merges multiple class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('base', false && 'excluded', 'included')).toBe('base included');
  });

  it('handles undefined and null', () => {
    expect(cn('base', undefined, null, 'end')).toBe('base end');
  });

  it('handles empty input', () => {
    expect(cn()).toBe('');
  });
});

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "Just now" for recent timestamps', () => {
    const timestamp = new Date('2024-01-15T11:59:45Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('Just now');
  });

  it('returns minutes ago for timestamps under an hour', () => {
    const timestamp = new Date('2024-01-15T11:30:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('30m ago');
  });

  it('returns hours ago for timestamps under a day', () => {
    const timestamp = new Date('2024-01-15T08:00:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('4h ago');
  });

  it('returns days ago for timestamps under a week', () => {
    const timestamp = new Date('2024-01-13T12:00:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('2d ago');
  });

  it('returns formatted date for timestamps over a week', () => {
    const timestamp = new Date('2024-01-01T12:00:00Z').toISOString();
    // Returns locale date string
    expect(formatRelativeTime(timestamp)).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/);
  });
});

describe('formatIsk', () => {
  it('formats billions correctly', () => {
    expect(formatIsk(1_500_000_000)).toBe('1.50B ISK');
    expect(formatIsk(10_000_000_000)).toBe('10.00B ISK');
  });

  it('formats millions correctly', () => {
    expect(formatIsk(1_500_000)).toBe('1.50M ISK');
    expect(formatIsk(500_000_000)).toBe('500.00M ISK');
  });

  it('formats thousands correctly', () => {
    expect(formatIsk(1_500)).toBe('1.50K ISK');
    expect(formatIsk(999_000)).toBe('999.00K ISK');
  });

  it('formats small values without abbreviation', () => {
    expect(formatIsk(500)).toBe('500 ISK');
    expect(formatIsk(0)).toBe('0 ISK');
  });
});

describe('getSecurityClass', () => {
  it('returns high-sec class for security >= 0.5', () => {
    expect(getSecurityClass(1.0)).toBe('text-high-sec');
    expect(getSecurityClass(0.5)).toBe('text-high-sec');
  });

  it('returns low-sec class for security between 0 and 0.5', () => {
    expect(getSecurityClass(0.4)).toBe('text-low-sec');
    expect(getSecurityClass(0.1)).toBe('text-low-sec');
  });

  it('returns null-sec class for security <= 0', () => {
    expect(getSecurityClass(0)).toBe('text-null-sec');
    expect(getSecurityClass(-0.5)).toBe('text-null-sec');
  });
});

describe('getSecurityLabel', () => {
  it('returns formatted labels for security categories', () => {
    expect(getSecurityLabel('high_sec')).toBe('High Sec');
    expect(getSecurityLabel('low_sec')).toBe('Low Sec');
    expect(getSecurityLabel('null_sec')).toBe('Null Sec');
  });

  it('returns the input for unknown categories', () => {
    expect(getSecurityLabel('wormhole')).toBe('wormhole');
  });
});

describe('getRiskColorClass', () => {
  it('returns correct class for each risk color', () => {
    expect(getRiskColorClass('green')).toBe('text-risk-green');
    expect(getRiskColorClass('yellow')).toBe('text-risk-yellow');
    expect(getRiskColorClass('orange')).toBe('text-risk-orange');
    expect(getRiskColorClass('red')).toBe('text-risk-red');
  });
});

describe('getRiskBgClass', () => {
  it('returns correct background class for each risk color', () => {
    expect(getRiskBgClass('green')).toBe('bg-risk-green');
    expect(getRiskBgClass('yellow')).toBe('bg-risk-yellow');
    expect(getRiskBgClass('orange')).toBe('bg-risk-orange');
    expect(getRiskBgClass('red')).toBe('bg-risk-red');
  });
});

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('delays function execution', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('only executes once for rapid calls', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    debounced();
    debounced();

    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('passes arguments to the debounced function', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced('arg1', 'arg2');
    vi.advanceTimersByTime(100);

    expect(fn).toHaveBeenCalledWith('arg1', 'arg2');
  });

  it('resets timer on subsequent calls', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    vi.advanceTimersByTime(50);
    debounced();
    vi.advanceTimersByTime(50);

    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(50);
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe('ROUTE_PROFILES', () => {
  it('has correct structure for each profile', () => {
    expect(ROUTE_PROFILES.shortest).toMatchObject({
      label: 'Shortest',
      description: expect.any(String),
      color: expect.any(String),
      borderColor: expect.any(String),
    });

    expect(ROUTE_PROFILES.safer).toMatchObject({
      label: 'Safer',
      description: expect.any(String),
      color: expect.any(String),
      borderColor: expect.any(String),
    });

    expect(ROUTE_PROFILES.paranoid).toMatchObject({
      label: 'Paranoid',
      description: expect.any(String),
      color: expect.any(String),
      borderColor: expect.any(String),
    });
  });
});
