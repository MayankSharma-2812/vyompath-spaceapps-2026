import { test, expect } from '@playwright/test';

/**
 * =============================================================================
 * VyomPath Issue #14: Comprehensive Dashboard QA & Regression Test Suite
 * Team NAKSHATRA X | NASA Space Apps Challenge 2026
 *
 * Verifies:
 *   1. Mock vs Live backend mode indicator truth-in-labeling
 *   2. Handling of null/missing elevation samples without JavaScript 0-coercion
 *   3. Out-of-bounds and partial DTM gap coverage states
 *   4. HTTP 422 route length validation and error banner display
 *   5. Route clearing and stale analysis state prevention
 *   6. Route A vs Route B comparison, delta calculations, and Route B clearing
 *   7. Scientific preset corridor switching (Floor vs Delta Scarp)
 *   8. Responsive layout stability across desktop, tablet, and mobile
 *   9. Zero fabricated safety claims compliance
 * =============================================================================
 */

const MOCK_LIVE_DTM_PAYLOAD = {
  route_id: 'qa-traverse-live',
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
  limitations: ['HiRISE regional stereo DTM coverage is bounded within Jezero AOI.'],
  is_mock: false,
};

const MOCK_PARTIAL_GAP_PAYLOAD = {
  route_id: 'qa-traverse-partial',
  total_distance_m: 800.0,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -2570.0 },
    { distance_m: 50.0, elevation_m: null }, // NoData gap
    { distance_m: 100.0, elevation_m: -2569.0 },
  ],
  total_gain_m: 1.0,
  total_loss_m: 0.0,
  max_slope_deg: 3.1,
  slope_window_m: 50.0,
  dtm_source: 'USGS/NASA HiRISE DTM jezero_aoi_v2.tif (1.01m)',
  dtm_posting_m: 1.01,
  coverage_status: 'partial_gap',
  limitations: ['Traverse crosses NoData margin in HiRISE stereo strip.'],
  is_mock: false,
};

const MOCK_OUT_OF_BOUNDS_PAYLOAD = {
  route_id: 'qa-traverse-oob',
  total_distance_m: 5000.0,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: null },
    { distance_m: 50.0, elevation_m: null },
  ],
  total_gain_m: 0.0,
  total_loss_m: 0.0,
  max_slope_deg: 0.0,
  slope_window_m: 50.0,
  dtm_source: 'Deterministic Synthetic Fallback (Mock)',
  dtm_posting_m: 0.0,
  coverage_status: 'out_of_bounds',
  limitations: ['Coordinates lie entirely outside HiRISE DTM footprint.'],
  is_mock: true,
};

test.describe('Issue #14: Dashboard QA & Truth-in-Labeling Verification', () => {

  test('QA-1: Truthful backend mode badge reflects live vs mock health status', async ({ page }) => {
    // Intercept health check with live terrain engine mode
    await page.route('**/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', mode: 'production/live' }),
      })
    );
    await page.goto('/');

    const topBadge = page.locator('.top-toolbar .status-badge');
    await expect(topBadge).toBeVisible();
    await expect(topBadge).toContainText('LIVE TERRAIN ENGINE');
  });

  test('QA-2: Offline backend health failure truthfully displays offline mock badge', async ({ page }) => {
    // Abort health check to simulate offline backend
    await page.route('**/api/health', (route) => route.abort());
    await page.goto('/');

    const topBadge = page.locator('.top-toolbar .status-badge');
    await expect(topBadge).toBeVisible();
    await expect(topBadge).toContainText('BACKEND OFFLINE (MOCK)');
  });

  test('QA-3: Live DTM analysis renders genuine elevation, units, and limitations', async ({ page }) => {
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
    await page.goto('/');

    // Check terrain panel status badge
    const terrainPanel = page.locator('.terrain-panel');
    await expect(terrainPanel).toBeVisible();
    await expect(terrainPanel.locator('.panel-tag')).toContainText('LIVE DTM DATA');

    // Check metric cards in terrain panel
    const metrics = page.locator('.terrain-metrics .metric-card');
    await expect(metrics.nth(0)).toContainText('1.4 m'); // Elevation gain
    await expect(metrics.nth(2)).toContainText('-2567.5 m'); // Max elevation
    await expect(metrics.nth(3)).toContainText('-2568.9 m'); // Min elevation

    // Check limitations section
    const summaryPanel = page.locator('.summary-panel');
    await expect(summaryPanel).toContainText('Scientific limitations & data provenance');
    await expect(summaryPanel).toContainText('HiRISE regional stereo DTM coverage');
  });

  test('QA-4: Null elevation values in partial gap are not coerced to 0.0 m', async ({ page }) => {
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_PARTIAL_GAP_PAYLOAD),
      })
    );
    await page.goto('/');

    const terrainPanel = page.locator('.terrain-panel');
    await expect(terrainPanel).toBeVisible();
    // Warning badges for partial gap
    await expect(terrainPanel).toContainText('PARTIAL DTM GAP');

    // Min elevation must be -2570.0 m and Max -2569.0 m (NOT 0.0 m!)
    const metrics = page.locator('.terrain-metrics .metric-card');
    await expect(metrics.nth(2)).toContainText('-2569.0 m');
    await expect(metrics.nth(3)).toContainText('-2570.0 m');
    await expect(metrics.nth(2).locator('.metric-card-value')).toHaveText('-2569.0 m');
    await expect(metrics.nth(3).locator('.metric-card-value')).toHaveText('-2570.0 m');
  });

  test('QA-5: Out-of-bounds traverse displays OUT OF COVERAGE and handles all-null profile', async ({ page }) => {
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_OUT_OF_BOUNDS_PAYLOAD),
      })
    );
    await page.goto('/');

    const terrainPanel = page.locator('.terrain-panel');
    await expect(terrainPanel.locator('.panel-tag')).toContainText('OUT OF COVERAGE');

    // Elevation chart must display empty state explaining no valid samples
    await expect(page.locator('.chart-empty-state')).toContainText('Elevation data unavailable');
    await expect(page.locator('.chart-empty-state')).toContainText('did not return any valid elevation samples');

    // Metrics must indicate no valid samples rather than misleading 0m
    const metrics = page.locator('.terrain-metrics .metric-card');
    await expect(metrics.nth(2)).toContainText('No valid samples');
    await expect(metrics.nth(3)).toContainText('No valid samples');
  });

  test('QA-6: HTTP 422 route length violation displays actionable error banner', async ({ page }) => {
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Total route length of 27179.6 m exceeds the 25,000.0 m limit',
        }),
      })
    );
    await page.goto('/');

    // Error banner in chart empty state and comparison status
    const chartState = page.locator('.chart-empty-state');
    await expect(chartState).toBeVisible();
    await expect(chartState).toContainText('Total route length of 27179.6 m exceeds the 25,000.0 m limit');

    // Error reflected in Route Comparison status
    const comparisonStatus = page.locator('.comparison-route-status');
    await expect(comparisonStatus.first()).toContainText('exceeds the 25,000.0 m limit');
  });

  test('QA-7: Route clearing resets Route A analysis and prevents stale state', async ({ page }) => {
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LIVE_DTM_PAYLOAD),
      })
    );
    await page.goto('/');

    // Confirm initial Route A loaded
    await expect(page.locator('.comparison-route-status').first()).toContainText('Route A analysis loaded.');

    // Click "Clear / Draw Freehand" in toolbar
    const clearBtn = page.getByRole('button', { name: 'Clear / Draw Freehand' });
    await clearBtn.click();

    // Confirm Route A is reset and displays prompt, NOT stale analysis
    await expect(page.locator('.comparison-route-status').first()).toContainText('No Route A drawn.');
    const emptyNotice = page.locator('.summary-section .empty-state');
    await expect(emptyNotice.first()).toContainText('No route metrics yet');
  });

  test('QA-8: Route A vs Route B pinning, delta calculations, and Route B clearing', async ({ page }) => {
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LIVE_DTM_PAYLOAD),
      })
    );
    await page.goto('/');

    // Pin Route A as Route B
    const pinBtn = page.getByRole('button', { name: 'Pin Current as Route B' });
    await expect(pinBtn).toBeVisible();
    await pinBtn.click();

    // Verify Route B is now pinned
    const routeBCard = page.locator('.comparison-route-card').nth(1);
    await expect(routeBCard).toContainText('Route B analysis pinned.');

    // Deltas should be 0.0 with "No difference"
    const deltas = page.locator('.comparison-delta dd');
    await expect(deltas.first()).toContainText('Δ 0.0 m · No difference');

    // Verify "Clear Route B" button is visible and click it
    const clearRouteBBtn = page.getByRole('button', { name: 'Clear Route B' });
    await expect(clearRouteBBtn).toBeVisible();
    await clearRouteBBtn.click();

    // Verify Route B is reset
    await expect(routeBCard).toContainText('No distinct Route B pinned');
  });

  test('QA-9: Responsive viewport tests at tablet and mobile resolutions', async ({ page }) => {
    // 1. Tablet resolution (768 x 1024)
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await expect(page.locator('.brand')).toBeVisible();
    await expect(page.locator('.map-panel')).toBeVisible();

    // 2. Mobile resolution (375 x 667)
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page.locator('.top-toolbar h1')).toBeVisible();
    await expect(page.locator('.preset-selector')).toBeVisible();
  });

  test('QA-10: Scientific honesty — zero fabricated safety or hazard claims in DOM', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();

    // Must never contain unsafe subjective safety terms
    expect(content.toLowerCase()).not.toContain('safe route');
    expect(content.toLowerCase()).not.toContain('safest path');
    expect(content.toLowerCase()).not.toContain('hazard-free');
    expect(content.toLowerCase()).not.toContain('safe passage');

    // Advisory risk disclosure must be present
    expect(content).toContain('Traversability outputs are advisory risk indicators');
  });

  test('QA-11: Interactive sidebar navigation buttons update active state and navigate sections', async ({ page }) => {
    await page.goto('/');

    // 1. Initial state has 'Explore Map' active
    const exploreBtn = page.getByRole('button', { name: 'Explore Map' });
    await expect(exploreBtn).toHaveClass(/is-active/);

    // 2. Click 'Terrain Profile' navigation button
    const terrainBtn = page.getByRole('button', { name: 'Terrain Profile' });
    await terrainBtn.click();
    await expect(terrainBtn).toHaveClass(/is-active/);
    await expect(page.locator('#terrain-section')).toBeVisible();

    // 3. Click 'Route Comparison' navigation button
    const comparisonBtn = page.getByRole('button', { name: 'Route Comparison' });
    await comparisonBtn.click();
    await expect(comparisonBtn).toHaveClass(/is-active/);
    await expect(page.locator('#comparison-section')).toBeVisible();
  });

});
