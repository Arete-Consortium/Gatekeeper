import { test, expect } from '@playwright/test';

test.describe('Map Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/map');
  });

  test('should load map page with application container', async ({ page }) => {
    // Map renders inside a role="application" container
    const mapContainer = page.locator('[role="application"]');
    await expect(mapContainer).toBeVisible();
    await expect(mapContainer).toHaveAttribute('aria-label', 'Interactive universe map');
  });

  test('should display map heading on desktop', async ({ page }) => {
    // The "New Eden Map" heading is visible on desktop
    await expect(page.getByRole('heading', { name: 'New Eden Map', level: 1 })).toBeVisible();
  });

  test('should show Beta badge', async ({ page }) => {
    await expect(page.getByText('Beta')).toBeVisible();
  });

  test('should have system search input', async ({ page }) => {
    // SystemSearch component renders an input
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible();
  });

  test('should have zoom controls', async ({ page }) => {
    await expect(page.getByLabel('Zoom in')).toBeVisible();
    await expect(page.getByLabel('Zoom out')).toBeVisible();
  });

  test('should have fullscreen toggle', async ({ page }) => {
    await expect(page.getByLabel('Toggle fullscreen mode')).toBeVisible();
  });

  test('should have route planner toggle button', async ({ page }) => {
    const routeButton = page.getByLabel(/route planner/i);
    await expect(routeButton).toBeVisible();
  });

  test('should display layer toggles in sidebar', async ({ page }) => {
    // Layers section should be visible on desktop (collapsible, open by default)
    await expect(page.getByText('Gate connections')).toBeVisible();
    await expect(page.getByText('System labels')).toBeVisible();
    await expect(page.getByText('Region labels')).toBeVisible();
    await expect(page.getByText('Route overlay')).toBeVisible();
    await expect(page.getByText('Landmarks')).toBeVisible();
  });

  test('should display pro-gated layer toggles', async ({ page }) => {
    await expect(page.getByText('Kill markers')).toBeVisible();
    await expect(page.getByText('Risk heatmap')).toBeVisible();
    await expect(page.getByText('Skyhooks')).toBeVisible();
    await expect(page.getByText('Thera connections')).toBeVisible();
  });

  test('should have color mode section', async ({ page }) => {
    // Color Mode is collapsed by default — expand it
    await page.getByText('Color Mode').click();

    await expect(page.getByRole('button', { name: 'Security' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Risk' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Star' })).toBeVisible();
  });

  test('should have legend section', async ({ page }) => {
    // Legend is collapsed by default — expand it
    await page.getByText('Legend').click();

    await expect(page.getByText('High Sec (0.5 - 1.0)')).toBeVisible();
    await expect(page.getByText('Low Sec (0.1 - 0.4)')).toBeVisible();
    await expect(page.getByText('Null Sec (0.0 and below)')).toBeVisible();
  });

  test('should have intel feed controls', async ({ page }) => {
    // Intel feed section inside Layers card
    await expect(page.getByText('Intel Feed')).toBeVisible();
  });

  test('should have copy link button', async ({ page }) => {
    await expect(page.getByLabel('Copy map link to clipboard')).toBeVisible();
  });

  test('should open route planner panel when toggle clicked', async ({ page }) => {
    const routeButton = page.getByLabel(/Open route planner/i);
    await routeButton.click();

    // Route controls panel should appear (it renders inside the map container)
    // The button label changes to "Close route planner" when open
    await expect(page.getByLabel(/Close route planner/i)).toBeVisible();
  });
});
