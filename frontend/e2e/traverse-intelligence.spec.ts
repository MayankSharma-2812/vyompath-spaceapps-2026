import { test, expect } from '@playwright/test';

/**
 * =============================================================================
 * Mission-Aware Traverse Intelligence E2E Test Suite
 * Team NAKSHATRA X | NASA Space Apps Challenge 2026
 *
 * Verifies:
 *   1. Traverse intelligence section renders with objective selectors.
 *   2. Objective switching dynamically alters scoring priorities & weights.
 *   3. Single route assessment displays when only Route A is loaded.
 *   4. Pinning Route B triggers comparative intelligence and recommendation.
 *   5. Measured analytical evidence and trade-off explanations are displayed.
 *   6. Disclaimers and non-flight-certified constraints are present.
 * =============================================================================
 */

const MOCK_ROUTE_A = {
  route_id: 'traverse-sol386',
  total_distance_m: 1250.0,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -2560.0 },
    { distance_m: 100.0, elevation_m: -2558.5 },
    { distance_m: 200.0, elevation_m: -2557.0 },
  ],
  total_gain_m: 3.0,
  total_loss_m: 0.0,
  max_slope_deg: 2.8,
  slope_window_m: 50.0,
  dtm_source: 'USGS/NASA HiRISE DTM jezero_aoi_v2.tif',
  dtm_posting_m: 1.0,
  coverage_status: 'complete',
  limitations: ['Verified stereo HiRISE elevation model.'],
  is_mock: false,
};

const MOCK_ROUTE_B_DELTA = {
  route_id: 'route-b-jezeroDelta',
  total_distance_m: 3400.0,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -2500.0 },
    { distance_m: 100.0, elevation_m: -2460.0 },
    { distance_m: 200.0, elevation_m: -2420.0 },
  ],
  total_gain_m: 80.0,
  total_loss_m: 0.0,
  max_slope_deg: 22.4,
  slope_window_m: 50.0,
  dtm_source: 'USGS/NASA HiRISE DTM jezero_aoi_v2.tif',
  dtm_posting_m: 1.0,
  coverage_status: 'complete',
  limitations: ['Steep scarp ingress corridor.'],
  is_mock: false,
};

test.describe('Mission-Aware Traverse Intelligence', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept backend health & route analyze
    await page.route('**/api/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          service: 'vyompath-api',
          mode: 'production/live',
          analysis_mode: 'real_dtm',
          is_mock: false,
        }),
      });
    });

    await page.route('**/api/routes/analyze', async (route) => {
      const postData = route.request().postDataJSON();
      if (postData?.route_id?.includes('route-b')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_ROUTE_B_DELTA),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_ROUTE_A),
        });
      }
    });

    await page.goto('/');
    await page.waitForSelector('#traverse-intelligence-section');
  });

  test('TI-1: renders section heading and three mission objective selectors', async ({ page }) => {
    const section = page.locator('#traverse-intelligence-section');
    await expect(section).toBeVisible();
    await expect(section.locator('h2')).toContainText('Mission-Aware Traverse Intelligence');

    const tabs = section.locator('button[role="tab"]');
    await expect(tabs).toHaveCount(3);
    await expect(tabs.nth(0)).toContainText('Slope-Conscious Traverse');
    await expect(tabs.nth(1)).toContainText('Energy-Efficient Traverse');
    await expect(tabs.nth(2)).toContainText('Data-Confidence-First Traverse');
  });

  test('TI-2: switching mission objectives updates active profile description and weights', async ({ page }) => {
    const section = page.locator('#traverse-intelligence-section');

    // Click Energy-Efficient tab
    await section.locator('button[role="tab"]').nth(1).click();
    await expect(section.locator('button[role="tab"]').nth(1)).toHaveAttribute('aria-selected', 'true');
    await expect(section).toContainText('Energy 60%');

    // Click Data-Confidence-First tab
    await section.locator('button[role="tab"]').nth(2).click();
    await expect(section.locator('button[role="tab"]').nth(2)).toHaveAttribute('aria-selected', 'true');
    await expect(section).toContainText('Data 70%');
  });

  test('TI-3: displays single route assessment when only Route A is available', async ({ page }) => {
    const section = page.locator('#traverse-intelligence-section');
    await expect(section.locator('article[aria-label="Route A metrics"], article').first()).toBeVisible();
    await expect(section).toContainText('Single-route evaluation complete');
  });

  test('TI-4: dual route comparative intelligence recommends Route A over steep Route B on slope objective', async ({ page }) => {
    // Click "Compare with Delta Scarp" to pin Route B
    const compareDeltaBtn = page.locator('button:has-text("Compare with Delta Scarp")').first();
    await compareDeltaBtn.click();

    const section = page.locator('#traverse-intelligence-section');
    // For slope-conscious objective, gentle Route A must win over steep Route B (22.4° max slope)
    await expect(section).toContainText('Route A is recommended for Slope-Conscious Traverse');
    await expect(section).toContainText('lower maximum slope');

    // Both Route A and Route B cards must be rendered
    await expect(section.locator('h4:has-text("Route A")')).toBeVisible();
    await expect(section.locator('h4:has-text("Route B")')).toBeVisible();
  });

  test('TI-5: displays scientific disclaimers and constraints', async ({ page }) => {
    const footer = page.locator('#traverse-intelligence-section footer');
    await expect(footer).toBeVisible();
    await expect(footer).toContainText('DECISION-SUPPORT PROTOTYPE: Not flight-certified rover autonomy');
    await expect(footer).toContainText('Mars gravity');
  });
});
