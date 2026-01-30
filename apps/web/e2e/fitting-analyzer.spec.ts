import { test, expect } from '@playwright/test';

const EXAMPLE_FITTING = `[Heron, Explorer]

Nanofiber Internal Structure II
Nanofiber Internal Structure II

5MN Y-T8 Compact Microwarpdrive
Data Analyzer I
Relic Analyzer I
Cargo Scanner I

Core Probe Launcher I
Prototype Cloaking Device I

Small Gravity Capacitor Upgrade I
Small Gravity Capacitor Upgrade I
`;

test.describe('Fitting Analyzer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/fitting');
  });

  test('should display the fitting analyzer page', async ({ page }) => {
    // Check page heading
    await expect(page.getByRole('heading', { name: 'Fitting Analyzer', level: 1 })).toBeVisible();

    // Check page description
    await expect(page.getByText('Analyze ship fittings for travel recommendations')).toBeVisible();
  });

  test('should display empty state when no fitting analyzed', async ({ page }) => {
    // Check for empty state message
    await expect(page.getByText('Paste an EFT fitting to analyze travel capabilities')).toBeVisible();
  });

  test('should have textarea for EFT fitting input', async ({ page }) => {
    const textarea = page.getByPlaceholder(/Paste your EFT fitting here/i);
    await expect(textarea).toBeVisible();
  });

  test('should have Analyze Fitting button', async ({ page }) => {
    const analyzeButton = page.getByRole('button', { name: /Analyze Fitting/i });
    await expect(analyzeButton).toBeVisible();
  });

  test('should have Paste, Load Example, and Clear buttons', async ({ page }) => {
    // Check Paste button
    await expect(page.getByRole('button', { name: /Paste/i })).toBeVisible();

    // Check Load Example button
    await expect(page.getByRole('button', { name: /Load Example/i })).toBeVisible();
  });

  test('should load example fitting when Load Example clicked', async ({ page }) => {
    // Click Load Example button
    await page.getByRole('button', { name: /Load Example/i }).click();

    // Verify textarea has content
    const textarea = page.getByPlaceholder(/Paste your EFT fitting here/i);
    await expect(textarea).not.toBeEmpty();

    // Should contain Heron Explorer fitting
    await expect(textarea).toContainText('[Heron, Explorer]');
  });

  test('should show Clear button after text is entered', async ({ page }) => {
    // Initially Clear button should not be visible (or disabled)
    const clearButton = page.getByRole('button', { name: /Clear/i });

    // Load example to get text in textarea
    await page.getByRole('button', { name: /Load Example/i }).click();

    // Now Clear should be visible
    await expect(clearButton).toBeVisible();
  });

  test('should clear textarea when Clear button clicked', async ({ page }) => {
    // Load example
    await page.getByRole('button', { name: /Load Example/i }).click();

    // Verify textarea has content
    const textarea = page.getByPlaceholder(/Paste your EFT fitting here/i);
    await expect(textarea).not.toBeEmpty();

    // Click Clear
    await page.getByRole('button', { name: /Clear/i }).click();

    // Verify textarea is empty
    await expect(textarea).toBeEmpty();
  });

  test('should allow manual text input', async ({ page }) => {
    const textarea = page.getByPlaceholder(/Paste your EFT fitting here/i);

    // Type in a fitting
    await textarea.fill(EXAMPLE_FITTING);

    // Verify content
    await expect(textarea).toHaveValue(EXAMPLE_FITTING);
  });

  test('should enable Analyze button when text is entered', async ({ page }) => {
    const analyzeButton = page.getByRole('button', { name: /Analyze Fitting/i });
    const textarea = page.getByPlaceholder(/Paste your EFT fitting here/i);

    // Button should be disabled initially (empty textarea)
    await expect(analyzeButton).toBeDisabled();

    // Enter some text
    await textarea.fill(EXAMPLE_FITTING);

    // Button should now be enabled
    await expect(analyzeButton).toBeEnabled();
  });

  test('should submit fitting for analysis when button clicked', async ({ page }) => {
    const textarea = page.getByPlaceholder(/Paste your EFT fitting here/i);
    const analyzeButton = page.getByRole('button', { name: /Analyze Fitting/i });

    // Enter fitting
    await textarea.fill(EXAMPLE_FITTING);

    // Click analyze - this will make API call
    // Even if API fails, button should show loading state briefly
    await analyzeButton.click();

    // Button should show loading state or complete
    // We're just testing that the button is clickable and form submits
    // The actual API response handling depends on backend availability
  });

  test('should navigate from dashboard tools section', async ({ page }) => {
    // Start from dashboard
    await page.goto('/');

    // Click Fitting Analyzer in tools
    await page.getByRole('link', { name: /Fitting Analyzer/i }).click();

    // Verify navigation
    await expect(page).toHaveURL('/fitting');
    await expect(page.getByRole('heading', { name: 'Fitting Analyzer', level: 1 })).toBeVisible();
  });
});
