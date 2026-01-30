import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should load the dashboard page', async ({ page }) => {
    await page.goto('/');

    // Check main heading
    await expect(page.getByRole('heading', { name: 'EVE Gatekeeper', level: 1 })).toBeVisible();

    // Check page tagline
    await expect(page.getByText('Intel & Route Planning')).toBeVisible();

    // Check that Plan Route button is visible
    await expect(page.getByRole('link', { name: /Plan Route/i })).toBeVisible();
  });

  test('should navigate to Route page from navbar', async ({ page }) => {
    await page.goto('/');

    // Click the Route link in navbar
    await page.getByRole('link', { name: /^Route$/i }).click();

    // Verify we're on the route page
    await expect(page).toHaveURL('/route');
    await expect(page.getByRole('heading', { name: 'Route Planner', level: 1 })).toBeVisible();
  });

  test('should navigate to Fitting page from navbar', async ({ page }) => {
    await page.goto('/');

    // Click the Fitting link in navbar
    await page.getByRole('link', { name: /^Fitting$/i }).click();

    // Verify we're on the fitting page
    await expect(page).toHaveURL('/fitting');
    await expect(page.getByRole('heading', { name: 'Fitting Analyzer', level: 1 })).toBeVisible();
  });

  test('should navigate to Alerts page from navbar', async ({ page }) => {
    await page.goto('/');

    // Click the Alerts link in navbar
    await page.getByRole('link', { name: /^Alerts$/i }).click();

    // Verify we're on the alerts page
    await expect(page).toHaveURL('/alerts');
    await expect(page.getByRole('heading', { name: 'Kill Alerts', level: 1 })).toBeVisible();
  });

  test('should navigate to Intel page from navbar', async ({ page }) => {
    await page.goto('/');

    // Click the Intel link in navbar
    await page.getByRole('link', { name: /^Intel$/i }).click();

    // Verify we're on the intel page
    await expect(page).toHaveURL('/intel');
    await expect(page.getByRole('heading', { name: 'Intel', level: 1 })).toBeVisible();
  });

  test('should navigate to Settings page from navbar', async ({ page }) => {
    await page.goto('/');

    // Click the Settings link in navbar
    await page.getByRole('link', { name: /^Settings$/i }).click();

    // Verify we're on the settings page
    await expect(page).toHaveURL('/settings');
  });

  test('should navigate back to dashboard via logo', async ({ page }) => {
    // Start on route page
    await page.goto('/route');
    await expect(page).toHaveURL('/route');

    // Click the logo/home link
    await page.getByRole('link', { name: 'EVE Gatekeeper' }).click();

    // Verify we're back on dashboard
    await expect(page).toHaveURL('/');
  });

  test('should show active state for current page in navbar', async ({ page }) => {
    await page.goto('/intel');

    // The Intel link should have the active class styling
    const intelLink = page.getByRole('link', { name: /^Intel$/i });
    await expect(intelLink).toHaveClass(/text-primary/);
  });

  test('should navigate from dashboard tools section', async ({ page }) => {
    await page.goto('/');

    // Click Fitting Analyzer in tools section
    await page.getByRole('link', { name: /Fitting Analyzer/i }).click();
    await expect(page).toHaveURL('/fitting');
  });
});
