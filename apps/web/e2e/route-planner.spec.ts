import { test, expect } from '@playwright/test';

test.describe('Route Planner', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/route');
  });

  test('should display the route planner form', async ({ page }) => {
    // Check page heading
    await expect(page.getByRole('heading', { name: 'Route Planner', level: 1 })).toBeVisible();

    // Check page description
    await expect(page.getByText('Plan multi-stop routes with waypoints')).toBeVisible();

    // Check form elements via placeholder
    await expect(page.getByPlaceholder('Origin...')).toBeVisible();
    await expect(page.getByPlaceholder('Destination...')).toBeVisible();

    // Check Calculate Route button exists
    const calculateButton = page.getByRole('button', { name: /Calculate Route/i });
    await expect(calculateButton).toBeVisible();
  });

  test('should have system search inputs', async ({ page }) => {
    const originInput = page.getByPlaceholder('Origin...');
    await expect(originInput).toBeVisible();

    const destInput = page.getByPlaceholder('Destination...');
    await expect(destInput).toBeVisible();
  });

  test('should display empty state when no route calculated', async ({ page }) => {
    await expect(
      page.getByText('Enter origin and destination systems to calculate a route')
    ).toBeVisible();
  });

  test('should have route profile dropdown', async ({ page }) => {
    const profileSelect = page.locator('select').first();
    await expect(profileSelect).toBeVisible();

    // Default profile is Safer, should also have Shortest and Paranoid
    await expect(profileSelect).toContainText('Safer');
    await expect(profileSelect).toContainText('Shortest');
    await expect(profileSelect).toContainText('Paranoid');
  });

  test('should have jump bridges toggle', async ({ page }) => {
    await expect(page.getByText('Jump Bridges')).toBeVisible();
  });

  test('should have Thera toggle', async ({ page }) => {
    await expect(page.getByText('Thera')).toBeVisible();
  });

  test('should have Jump Drive toggle', async ({ page }) => {
    await expect(page.getByText('Jump Drive')).toBeVisible();
  });

  test('should have Add Waypoint option', async ({ page }) => {
    await expect(page.getByText('Add Waypoint')).toBeVisible();
  });

  test('should have avoid systems section', async ({ page }) => {
    await expect(page.getByText('AVOID SYSTEMS')).toBeVisible();
    await expect(page.getByPlaceholder('System...')).toBeVisible();
  });

  test('should initialize from URL parameters', async ({ page }) => {
    await page.goto('/route?from=Jita&to=Amarr&profile=shortest');

    const originInput = page.getByPlaceholder('Origin...');
    const destInput = page.getByPlaceholder('Destination...');

    await expect(originInput).toHaveValue('Jita');
    await expect(destInput).toHaveValue('Amarr');
  });

  test('should navigate to route planner from navbar', async ({ page }) => {
    await page.goto('/fitting');

    await page.locator('nav').getByRole('link', { name: /^Route$/i }).first().click();

    await expect(page).toHaveURL('/route');
    await expect(page.getByRole('heading', { name: 'Route Planner', level: 1 })).toBeVisible();
  });
});
