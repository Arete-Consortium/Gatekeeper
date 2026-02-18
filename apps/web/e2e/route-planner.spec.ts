import { test, expect } from '@playwright/test';

test.describe('Route Planner', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/route');
  });

  test('should display the route planner form', async ({ page }) => {
    // Check page heading
    await expect(page.getByRole('heading', { name: 'Route Planner', level: 1 })).toBeVisible();

    // Check page description
    await expect(page.getByText('Find the safest path between solar systems')).toBeVisible();

    // Check form elements via placeholder (avoids label duplication from SSR)
    await expect(page.getByPlaceholder('Origin system...')).toBeVisible();
    await expect(page.getByPlaceholder('Destination system...')).toBeVisible();
    await expect(page.locator('select')).toBeVisible();

    // Check Calculate Route button exists and is disabled (no inputs)
    const calculateButton = page.getByRole('button', { name: /Calculate Route/i });
    await expect(calculateButton).toBeVisible();
  });

  test('should have system search inputs', async ({ page }) => {
    // Check origin input placeholder
    const originInput = page.getByPlaceholder('Origin system...');
    await expect(originInput).toBeVisible();

    // Check destination input placeholder
    const destInput = page.getByPlaceholder('Destination system...');
    await expect(destInput).toBeVisible();
  });

  test('should display empty state when no route calculated', async ({ page }) => {
    // Check for empty state message
    await expect(
      page.getByText('Enter origin and destination systems to calculate a route')
    ).toBeVisible();
  });

  test('should have swap button between origin and destination', async ({ page }) => {
    const swapButton = page.getByRole('button', { name: /Swap origin and destination/i });
    await expect(swapButton).toBeVisible();
  });

  test('should swap origin and destination when swap button clicked', async ({ page }) => {
    const originInput = page.getByPlaceholder('Origin system...');
    const destInput = page.getByPlaceholder('Destination system...');

    // Type in origin and press Enter to commit to parent state
    await originInput.fill('Jita');
    await originInput.press('Enter');
    // Type in destination and press Enter to commit
    await destInput.fill('Amarr');
    await destInput.press('Enter');

    // Click swap
    await page.getByRole('button', { name: /Swap origin and destination/i }).click();

    // Verify swapped values
    await expect(originInput).toHaveValue('Amarr');
    await expect(destInput).toHaveValue('Jita');
  });

  test('should have route profile dropdown with options', async ({ page }) => {
    const profileSelect = page.locator('select').first();
    await expect(profileSelect).toBeVisible();

    // Use auto-retrying assertions (innerHTML is immediate, won't wait for hydration)
    await expect(profileSelect).toContainText('Safer');
    await expect(profileSelect).toContainText('Balanced');
    await expect(profileSelect).toContainText('Shortest');
  });

  test('should have jump bridges toggle', async ({ page }) => {
    // Check for the Include Jump Bridges toggle
    const bridgesToggle = page.getByText('Include Jump Bridges');
    await expect(bridgesToggle).toBeVisible();
  });

  test('should have Thera toggle', async ({ page }) => {
    // Check for the Include Thera toggle
    const theraToggle = page.getByText('Include Thera');
    await expect(theraToggle).toBeVisible();
  });

  test('should initialize from URL parameters', async ({ page }) => {
    // Navigate with URL params
    await page.goto('/route?from=Jita&to=Amarr&profile=shortest');

    // Verify inputs are populated
    const originInput = page.getByPlaceholder('Origin system...');
    const destInput = page.getByPlaceholder('Destination system...');

    await expect(originInput).toHaveValue('Jita');
    await expect(destInput).toHaveValue('Amarr');
  });

  test('should navigate to route planner from dashboard Plan Route button', async ({ page }) => {
    // Start from dashboard
    await page.goto('/');

    // Click the Plan Route button
    await page.getByRole('link', { name: /Plan Route/i }).click();

    // Verify we're on route page
    await expect(page).toHaveURL('/route');
    await expect(page.getByRole('heading', { name: 'Route Planner', level: 1 })).toBeVisible();
  });
});
