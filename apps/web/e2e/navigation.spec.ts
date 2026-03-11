import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should load the landing page (map)', async ({ page }) => {
    await page.goto('/');

    // Landing page re-exports the map page
    const mapContainer = page.locator('[role="application"]');
    await expect(mapContainer).toBeVisible();
  });

  test('should navigate to Route page from navbar', async ({ page }) => {
    await page.goto('/fitting');

    // Click the Route link in navbar
    await page.locator('nav').getByRole('link', { name: /^Route$/i }).first().click();

    // Verify we're on the route page
    await expect(page).toHaveURL('/route');
    await expect(page.getByRole('heading', { name: 'Route Planner', level: 1 })).toBeVisible();
  });

  test('should navigate to Appraisal page from navbar', async ({ page }) => {
    await page.goto('/route');

    // Click the Appraisal link in navbar
    await page.locator('nav').getByRole('link', { name: /^Appraisal$/i }).first().click();

    // Verify we're on the appraisal page
    await expect(page).toHaveURL('/appraisal');
  });

  test('should navigate to Alerts page from navbar', async ({ page }) => {
    await page.goto('/route');

    // Click the Alerts link in navbar
    await page.locator('nav').getByRole('link', { name: /^Alerts$/i }).first().click();

    // Verify we're on the alerts page
    await expect(page).toHaveURL('/alerts');
    await expect(page.getByRole('heading', { name: 'Kill Alerts', level: 1 })).toBeVisible();
  });

  test('should navigate to Intel page from navbar', async ({ page }) => {
    await page.goto('/route');

    // Click the Intel link in navbar
    await page.locator('nav').getByRole('link', { name: /^Intel$/i }).first().click();

    // Verify we're on the intel page
    await expect(page).toHaveURL('/intel');
    await expect(page.getByRole('heading', { name: 'Intel', level: 1 })).toBeVisible();
  });

  test('should load Settings page directly', async ({ page }) => {
    // Settings is only accessible via user dropdown (requires auth) or mobile menu
    // Test that the page loads when navigated to directly
    await page.goto('/settings');
    await expect(page).toHaveURL('/settings');
  });

  test('should navigate back to home via logo', async ({ page }) => {
    // Start on route page
    await page.goto('/route');
    await expect(page).toHaveURL('/route');

    // Click the logo/home link
    await page.getByRole('link', { name: 'EVE Gatekeeper' }).first().click();

    // Verify we're back on home (which is the map)
    await expect(page).toHaveURL('/');
  });

  test('should show active state for current page in navbar', async ({ page }) => {
    await page.goto('/intel');

    // The Intel link should have the active class styling (hidden on mobile)
    const intelLink = page.locator('nav').getByRole('link', { name: /^Intel$/i });
    await expect(intelLink).toHaveClass(/text-primary/);
  });

  test('should navigate to Map page', async ({ page }) => {
    await page.goto('/map');

    // Map page has a container with role="application"
    await expect(page.locator('[role="application"]')).toBeVisible();
  });

  test('should navigate to Pricing page', async ({ page }) => {
    await page.goto('/pricing');

    // Pricing page heading
    await expect(page.getByRole('heading', { name: 'Navigate New Eden Safely', level: 1 })).toBeVisible();

    // Should show Free and Pro tiers
    await expect(page.getByRole('heading', { name: 'Free' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Pro' })).toBeVisible();
  });
});
