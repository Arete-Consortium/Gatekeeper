import { describe, it, expect } from 'vitest';
import {
  getSecurityColor,
  getSpectralColor,
  getRiskColor,
  SECURITY_COLORS,
  RISK_COLORS,
  SPECTRAL_COLORS,
} from './types';

describe('getSecurityColor', () => {
  it('returns highSec for 1.0', () => {
    expect(getSecurityColor(1.0)).toBe(SECURITY_COLORS.highSec);
  });

  it('returns highSec for 0.5', () => {
    expect(getSecurityColor(0.5)).toBe(SECURITY_COLORS.highSec);
  });

  it('returns lowSec for 0.4', () => {
    expect(getSecurityColor(0.4)).toBe(SECURITY_COLORS.lowSec);
  });

  it('returns lowSec for 0.1', () => {
    expect(getSecurityColor(0.1)).toBe(SECURITY_COLORS.lowSec);
  });

  it('returns nullSec for 0.0', () => {
    expect(getSecurityColor(0.0)).toBe(SECURITY_COLORS.nullSec);
  });

  it('returns nullSec for negative security', () => {
    expect(getSecurityColor(-0.5)).toBe(SECURITY_COLORS.nullSec);
  });
});

describe('getSpectralColor', () => {
  it('returns correct color for known class', () => {
    expect(getSpectralColor('O')).toBe(SPECTRAL_COLORS.O);
    expect(getSpectralColor('G')).toBe(SPECTRAL_COLORS.G);
    expect(getSpectralColor('M')).toBe(SPECTRAL_COLORS.M);
  });

  it('falls back to G for unknown class', () => {
    expect(getSpectralColor('Z')).toBe(SPECTRAL_COLORS.G);
  });
});

describe('getRiskColor', () => {
  it('returns correct colors', () => {
    expect(getRiskColor('green')).toBe(RISK_COLORS.green);
    expect(getRiskColor('yellow')).toBe(RISK_COLORS.yellow);
    expect(getRiskColor('orange')).toBe(RISK_COLORS.orange);
    expect(getRiskColor('red')).toBe(RISK_COLORS.red);
  });
});
