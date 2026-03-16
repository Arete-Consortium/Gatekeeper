import { test, expect } from '@playwright/test';

test.describe('PWA', () => {
  test('manifest.json is accessible and has correct fields', async ({ request }) => {
    const response = await request.get('/manifest.json');
    expect(response.status()).toBe(200);

    const manifest = await response.json();
    expect(manifest.name).toBe('Gatekeeper');
    expect(manifest.short_name).toBe('Gatekeeper');
    expect(manifest.display).toBe('standalone');
    expect(manifest.start_url).toBe('/map');
    expect(manifest.theme_color).toBe('#0e7490');
    expect(manifest.background_color).toBe('#000000');
    expect(manifest.icons).toBeDefined();
    expect(manifest.icons.length).toBeGreaterThanOrEqual(2);
  });

  test('icon-192.png returns 200', async ({ request }) => {
    const response = await request.get('/icon-192.png');
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('image/png');
  });

  test('icon-512.png returns 200', async ({ request }) => {
    const response = await request.get('/icon-512.png');
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('image/png');
  });

  test('service worker script is accessible', async ({ request }) => {
    const response = await request.get('/sw.js');
    expect(response.status()).toBe(200);
    const contentType = response.headers()['content-type'];
    expect(contentType).toMatch(/javascript/);
  });

  test('HTML includes manifest link', async ({ page }) => {
    await page.goto('/');
    const manifestLink = page.locator('link[rel="manifest"]');
    await expect(manifestLink).toHaveAttribute('href', '/manifest.json');
  });

  test('HTML includes theme-color meta', async ({ page }) => {
    await page.goto('/');
    const themeColor = page.locator('meta[name="theme-color"]');
    await expect(themeColor).toHaveAttribute('content', '#0e7490');
  });
});
