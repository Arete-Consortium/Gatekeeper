/**
 * Tests for config module
 */
import {
  API_CONFIG,
  ESI_CONFIG,
  THEME,
  ROUTE_PROFILES,
  SHIP_PROFILE_DISPLAY,
  validateConfig,
} from '../config';

describe('API_CONFIG', () => {
  it('should have a GATEKEEPER_URL', () => {
    expect(API_CONFIG.GATEKEEPER_URL).toBeDefined();
    expect(typeof API_CONFIG.GATEKEEPER_URL).toBe('string');
  });

  it('should have ESI_BASE_URL', () => {
    expect(API_CONFIG.ESI_BASE_URL).toBe('https://esi.evetech.net/latest');
  });

  it('should have ZKILLBOARD_URL', () => {
    expect(API_CONFIG.ZKILLBOARD_URL).toBe('https://zkillboard.com/api');
  });

  it('should have a reasonable TIMEOUT', () => {
    expect(API_CONFIG.TIMEOUT).toBeGreaterThan(0);
    expect(API_CONFIG.TIMEOUT).toBeLessThanOrEqual(60000); // Max 60 seconds
  });
});

describe('ESI_CONFIG', () => {
  it('should have OAuth URLs', () => {
    expect(ESI_CONFIG.AUTHORIZE_URL).toContain('login.eveonline.com');
    expect(ESI_CONFIG.TOKEN_URL).toContain('login.eveonline.com');
  });

  it('should have required scopes', () => {
    expect(ESI_CONFIG.SCOPES).toContain('esi-location.read_location.v1');
    expect(ESI_CONFIG.SCOPES).toContain('esi-ui.write_waypoint.v1');
  });

  it('should have a callback URL', () => {
    expect(ESI_CONFIG.CALLBACK_URL).toBeDefined();
  });
});

describe('THEME', () => {
  describe('colors', () => {
    it('should have primary color', () => {
      expect(THEME.colors.primary).toMatch(/^#[0-9a-fA-F]{6}$/);
    });

    it('should have background color', () => {
      expect(THEME.colors.background).toMatch(/^#[0-9a-fA-F]{6}$/);
    });

    it('should have security status colors', () => {
      expect(THEME.colors.highSec).toBeDefined();
      expect(THEME.colors.lowSec).toBeDefined();
      expect(THEME.colors.nullSec).toBeDefined();
      expect(THEME.colors.wormhole).toBeDefined();
    });

    it('should have risk colors', () => {
      expect(THEME.colors.riskGreen).toBeDefined();
      expect(THEME.colors.riskYellow).toBeDefined();
      expect(THEME.colors.riskOrange).toBeDefined();
      expect(THEME.colors.riskRed).toBeDefined();
    });
  });

  describe('spacing', () => {
    it('should have increasing spacing values', () => {
      expect(THEME.spacing.xs).toBeLessThan(THEME.spacing.sm);
      expect(THEME.spacing.sm).toBeLessThan(THEME.spacing.md);
      expect(THEME.spacing.md).toBeLessThan(THEME.spacing.lg);
      expect(THEME.spacing.lg).toBeLessThan(THEME.spacing.xl);
    });
  });

  describe('borderRadius', () => {
    it('should have increasing border radius values', () => {
      expect(THEME.borderRadius.sm).toBeLessThan(THEME.borderRadius.md);
      expect(THEME.borderRadius.md).toBeLessThan(THEME.borderRadius.lg);
      expect(THEME.borderRadius.lg).toBeLessThan(THEME.borderRadius.xl);
    });
  });
});

describe('ROUTE_PROFILES', () => {
  it('should have shortest profile', () => {
    expect(ROUTE_PROFILES.shortest).toBeDefined();
    expect(ROUTE_PROFILES.shortest.label).toBe('Shortest');
    expect(ROUTE_PROFILES.shortest.description).toBeDefined();
    expect(ROUTE_PROFILES.shortest.color).toBeDefined();
  });

  it('should have safer profile', () => {
    expect(ROUTE_PROFILES.safer).toBeDefined();
    expect(ROUTE_PROFILES.safer.label).toBe('Safer');
  });

  it('should have paranoid profile', () => {
    expect(ROUTE_PROFILES.paranoid).toBeDefined();
    expect(ROUTE_PROFILES.paranoid.label).toBe('Paranoid');
  });
});

describe('SHIP_PROFILE_DISPLAY', () => {
  const expectedProfiles = [
    'default',
    'hauler',
    'frigate',
    'cruiser',
    'battleship',
    'mining',
    'capital',
    'cloaky',
  ];

  expectedProfiles.forEach((profile) => {
    it(`should have ${profile} profile`, () => {
      expect(SHIP_PROFILE_DISPLAY[profile as keyof typeof SHIP_PROFILE_DISPLAY]).toBeDefined();
      expect(
        SHIP_PROFILE_DISPLAY[profile as keyof typeof SHIP_PROFILE_DISPLAY].label
      ).toBeDefined();
      expect(
        SHIP_PROFILE_DISPLAY[profile as keyof typeof SHIP_PROFILE_DISPLAY].description
      ).toBeDefined();
      expect(
        SHIP_PROFILE_DISPLAY[profile as keyof typeof SHIP_PROFILE_DISPLAY].color
      ).toBeDefined();
    });
  });
});

describe('validateConfig', () => {
  it('should return valid when config is correct', () => {
    const result = validateConfig();
    // Since GATEKEEPER_URL has a default fallback, it should be valid
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should return errors array', () => {
    const result = validateConfig();
    expect(Array.isArray(result.errors)).toBe(true);
  });
});
