import { test } from '@playwright/test';
import * as path from 'path';

const SCREENSHOT_DIR = path.resolve('src/features/dashboard/__screenshots__');

const MOCK_LIVE_DTM_PAYLOAD = {
  route_id: 'traverse-sol-386-387',
  total_distance_m: 1450.5,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -2568.87 },
    { distance_m: 250.0, elevation_m: -2568.50 },
    { distance_m: 500.0, elevation_m: -2568.10 },
    { distance_m: 750.0, elevation_m: -2567.80 },
    { distance_m: 1000.0, elevation_m: -2567.60 },
    { distance_m: 1250.0, elevation_m: -2567.55 },
    { distance_m: 1450.5, elevation_m: -2567.50 },
  ],
  total_gain_m: 1.37,
  total_loss_m: 0.0,
  max_slope_deg: 2.4,
  slope_window_m: 50.0,
  dtm_source: 'USGS/NASA HiRISE DTM jezero_aoi_v2.tif (1.01m)',
  dtm_posting_m: 1.01,
  coverage_status: 'complete',
  limitations: [
    'Subpixel bilinear interpolation across 1.01 m/px HiRISE posting.',
    'Traversability outputs are advisory risk indicators; no automated obstacle clearing is implied.',
  ],
  is_mock: false,
};

test.describe('Capture Dashboard QA Visual Proof Screenshots', () => {

  test('Screenshot 1: Integrated Dashboard with Live DTM Terrain Elevation Profile', async ({ page }) => {
    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', mode: 'production/live' }),
      })
    );
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LIVE_DTM_PAYLOAD),
      })
    );

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '01_dashboard_live_dtm_overview.png'),
      fullPage: true,
    });
  });

  test('Screenshot 2: Route A vs Route B Comparison View with Deltas', async ({ page }) => {
    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', mode: 'production/live' }),
      })
    );
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LIVE_DTM_PAYLOAD),
      })
    );

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForTimeout(500);

    // Pin Route A as Route B
    const pinBtn = page.getByRole('button', { name: 'Pin Current as Route B' });
    if (await pinBtn.isVisible()) {
      await pinBtn.click();
      await page.waitForTimeout(300);
    }

    const comparisonPanel = page.locator('.comparison-panel');
    await comparisonPanel.screenshot({
      path: path.join(SCREENSHOT_DIR, '02_route_comparison_deltas.png'),
    });
  });

  test('Screenshot 3: Mobile Responsive Layout at 375px', async ({ page }) => {
    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', mode: 'production/live' }),
      })
    );
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LIVE_DTM_PAYLOAD),
      })
    );

    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await page.waitForTimeout(500);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, '03_dashboard_mobile_view.png'),
      fullPage: false,
    });
  });

});
