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

  it('has exactly three profiles', () => {
    const keys = Object.keys(ROUTE_PROFILES);
    expect(keys).toEqual(['shortest', 'safer', 'paranoid']);
  });

  it('has unique labels for each profile', () => {
    const labels = Object.values(ROUTE_PROFILES).map((p) => p.label);
    const uniqueLabels = new Set(labels);
    expect(uniqueLabels.size).toBe(labels.length);
  });

  it('has descriptive text for shortest profile', () => {
    expect(ROUTE_PROFILES.shortest.description).toContain('jumps');
  });

  it('has descriptive text for safer profile', () => {
    expect(ROUTE_PROFILES.safer.description).toContain('risk');
  });

  it('has descriptive text for paranoid profile', () => {
    expect(ROUTE_PROFILES.paranoid.description).toContain('safety');
  });
});

describe('cn - additional edge cases', () => {
  it('handles arrays of class names', () => {
    expect(cn(['foo', 'bar'])).toBe('foo bar');
  });

  it('handles deeply nested conditionals', () => {
    const isActive = true;
    const isDisabled = false;
    expect(cn('base', isActive && 'active', isDisabled && 'disabled')).toBe('base active');
  });

  it('handles number values', () => {
    expect(cn('base', 0)).toBe('base');
  });
});

describe('formatRelativeTime - additional edge cases', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "1m ago" at exactly 1 minute', () => {
    const timestamp = new Date('2024-01-15T11:59:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('1m ago');
  });

  it('returns "59m ago" at exactly 59 minutes', () => {
    const timestamp = new Date('2024-01-15T11:01:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('59m ago');
  });

  it('returns "1h ago" at exactly 1 hour', () => {
    const timestamp = new Date('2024-01-15T11:00:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('1h ago');
  });

  it('returns "23h ago" at exactly 23 hours', () => {
    const timestamp = new Date('2024-01-14T13:00:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('23h ago');
  });

  it('returns "1d ago" at exactly 1 day', () => {
    const timestamp = new Date('2024-01-14T12:00:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('1d ago');
  });

  it('returns "6d ago" at exactly 6 days', () => {
    const timestamp = new Date('2024-01-09T12:00:00Z').toISOString();
    expect(formatRelativeTime(timestamp)).toBe('6d ago');
  });
});

describe('formatIsk - additional edge cases', () => {
  it('formats exact boundary of 1 billion', () => {
    expect(formatIsk(1_000_000_000)).toBe('1.00B ISK');
  });

  it('formats exact boundary of 1 million', () => {
    expect(formatIsk(1_000_000)).toBe('1.00M ISK');
  });

  it('formats exact boundary of 1 thousand', () => {
    expect(formatIsk(1_000)).toBe('1.00K ISK');
  });

  it('formats values just below boundaries', () => {
    expect(formatIsk(999_999_999)).toBe('1000.00M ISK');
    expect(formatIsk(999_999)).toBe('1000.00K ISK');
    expect(formatIsk(999)).toBe('999 ISK');
  });

  it('handles very large values', () => {
    expect(formatIsk(100_000_000_000)).toBe('100.00B ISK');
  });
});

describe('getSecurityClass - additional edge cases', () => {
  it('handles boundary value 0.5 as high-sec', () => {
    expect(getSecurityClass(0.5)).toBe('text-high-sec');
  });

  it('handles boundary value 0.4999 as low-sec', () => {
    expect(getSecurityClass(0.4999)).toBe('text-low-sec');
  });

  it('handles 0.0001 as low-sec', () => {
    expect(getSecurityClass(0.0001)).toBe('text-low-sec');
  });

  it('handles -1.0 as null-sec', () => {
    expect(getSecurityClass(-1.0)).toBe('text-null-sec');
  });
});

describe('getRiskColorClass - default fallback', () => {
  it('returns secondary class for unknown risk color', () => {
    // @ts-expect-error Testing invalid input
    expect(getRiskColorClass('unknown')).toBe('text-text-secondary');
  });
});

describe('getRiskBgClass - default fallback', () => {
  it('returns secondary bg class for unknown risk color', () => {
    // @ts-expect-error Testing invalid input
    expect(getRiskBgClass('unknown')).toBe('bg-text-secondary');
  });
});

describe('debounce - additional edge cases', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('uses the latest arguments when called multiple times', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced('first');
    debounced('second');
    debounced('third');

    vi.advanceTimersByTime(100);

    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('third');
  });

  it('allows separate invocations after delay has passed', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced('first');
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledWith('first');

    debounced('second');
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledWith('second');

    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('handles zero delay', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 0);

    debounced('value');
    vi.advanceTimersByTime(0);

    expect(fn).toHaveBeenCalledWith('value');
  });
});
