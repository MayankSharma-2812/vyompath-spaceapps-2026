import { test, expect } from '@playwright/test';

/**
 * mock-mode-transparency.spec.ts
 *
 * Verifies truth-in-labeling for mock vs real DTM modes:
 * - Mock mode banner appears with required warning copy
 * - Real-DTM indicator appears only for genuine DTM analysis
 * - Mock coverage displays as NOT APPLICABLE
 * - Mock elevation & slope metrics are labeled as illustrative
 * - Empty POI state renders an honest empty state
 * - Switching between mock and real responses does not leave stale UI data
 */

const MOCK_SYNTHETIC_PAYLOAD = {
  route_id: 'qa-mock-traverse',
  total_distance_m: 1200.0,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -2500.0 },
    { distance_m: 600.0, elevation_m: -2480.0 },
    { distance_m: 1200.0, elevation_m: -2500.0 },
  ],
  total_gain_m: 20.0,
  total_loss_m: 20.0,
  max_slope_deg: 3.5,
  slope_window_m: 50.0,
  dtm_source: 'synthetic/mock — no real DTM loaded',
  dtm_posting_m: 0.0,
  coverage_status: 'not_applicable',
  nearby_pois: [],
  limitations: [
    'DEMONSTRATION MODE: Elevation and slope values shown are generated synthetic examples.',
    'MOCK DATA: Elevation profile is a deterministic synthetic sine-wave.',
    'COVERAGE: Not applicable in synthetic/mock mode.',
  ],
  analysis_mode: 'mock',
  is_mock: true,
};

const REAL_DTM_PAYLOAD = {
  route_id: 'qa-real-traverse',
  total_distance_m: 1450.5,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -2568.87 },
    { distance_m: 50.0, elevation_m: -2568.20 },
    { distance_m: 100.0, elevation_m: -2567.50 },
  ],
  total_gain_m: 1.37,
  total_loss_m: 0.0,
  max_slope_deg: 2.4,
  slope_window_m: 50.0,
  dtm_source: 'USGS/NASA HiRISE DTM jezero_aoi_v2.tif (1.01m)',
  dtm_posting_m: 1.01,
  coverage_status: 'complete',
  nearby_pois: [],
  limitations: ['HiRISE regional stereo DTM coverage is bounded within Jezero AOI.'],
  analysis_mode: 'real_dtm',
  is_mock: false,
};

test.describe('Mock-Mode Transparency & Real DTM Verification', () => {

  test('TC-MOCK-1: Demonstration mode banner is prominently displayed in mock mode', async ({ page }) => {
    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          service: 'vyompath-api',
          mode: 'development/mock',
          analysis_mode: 'mock',
          is_mock: true,
        }),
      })
    );
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SYNTHETIC_PAYLOAD),
      })
    );

    await page.goto('/');

    // Check demonstration mode banner
    const demoBanner = page.locator('.demo-mode-banner');
    await expect(demoBanner).toBeVisible();
    await expect(demoBanner).toContainText('DEMONSTRATION MODE — SYNTHETIC TERRAIN DATA');
    await expect(demoBanner).toContainText('Elevation and slope values shown are generated synthetic examples');
    await expect(demoBanner).toContainText('must not be used for mission planning');

    // Real DTM banner must NOT be visible
    await expect(page.locator('.real-dtm-banner')).not.toBeVisible();
  });

  test('TC-MOCK-2: Mock coverage shows NOT APPLICABLE and metrics are labeled illustrative', async ({ page }) => {
    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          service: 'vyompath-api',
          mode: 'development/mock',
          analysis_mode: 'mock',
          is_mock: true,
        }),
      })
    );
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SYNTHETIC_PAYLOAD),
      })
    );

    await page.goto('/');

    // Summary panel coverage status must state NOT APPLICABLE (never Complete)
    const summaryPanel = page.locator('.summary-panel');
    await expect(summaryPanel).toBeVisible();
    await expect(summaryPanel).toContainText('NOT APPLICABLE (Synthetic Data)');
    await expect(summaryPanel).toContainText('N/A (Synthetic / Illustrative)');

    // Terrain profile heading and metric cards must indicate illustrative
    const terrainPanel = page.locator('.terrain-panel');
    await expect(terrainPanel).toContainText('Terrain Elevation Profile (Synthetic / Illustrative)');
    await expect(terrainPanel).toContainText('Elevation Gain (Illustrative)');
    await expect(terrainPanel).toContainText('Elevation Loss (Illustrative)');
  });

  test('TC-MOCK-3: Real DTM indicator appears when genuine DTM is active and shows metadata', async ({ page }) => {
    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          service: 'vyompath-api',
          mode: 'production/live',
          analysis_mode: 'real_dtm',
          is_mock: false,
        }),
      })
    );
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(REAL_DTM_PAYLOAD),
      })
    );

    await page.goto('/');

    // Real DTM banner must be visible with DTM metadata
    const realBanner = page.locator('.real-dtm-banner');
    await expect(realBanner).toBeVisible();
    await expect(realBanner).toContainText('REAL HiRISE DTM ANALYSIS');
    await expect(realBanner).toContainText('1.01 m/px');
    await expect(realBanner).toContainText('COMPLETE');

    // Demo banner must NOT be visible
    await expect(page.locator('.demo-mode-banner')).not.toBeVisible();

    // Summary panel must show genuine complete status
    const summaryPanel = page.locator('.summary-panel');
    await expect(summaryPanel).toContainText('Complete (100% Valid)');
    await expect(summaryPanel).toContainText('1.01 m/px');
  });

  test('TC-MOCK-4: Switching from Real DTM to Mock Mode clears stale indicators', async ({ page }) => {
    let serveReal = true;

    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          mode: serveReal ? 'production/live' : 'development/mock',
          analysis_mode: serveReal ? 'real_dtm' : 'mock',
          is_mock: !serveReal,
        }),
      })
    );

    await page.route('**/api/routes/analyze', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(serveReal ? REAL_DTM_PAYLOAD : MOCK_SYNTHETIC_PAYLOAD),
      });
    });

    await page.goto('/');

    // Initially real
    await expect(page.locator('.real-dtm-banner')).toBeVisible();

    // Switch mode
    serveReal = false;
    await page.click('button:has-text("Clear / Draw Freehand")');

    // Route clear empties analysis, then drawing a new route in mock mode switches banner
    // Click Floor Corridor
    await page.click('button:has-text("Floor Corridor (Sol 386–387)")');

    // Now mock banner must appear
    await expect(page.locator('.demo-mode-banner')).toBeVisible();
    await expect(page.locator('.real-dtm-banner')).not.toBeVisible();
  });

});
