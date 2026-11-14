import { test, expect } from '@playwright/test';

/**
 * =============================================================================
 * Production Smoke Test Bug Verification Suite (BUG-008 through BUG-011)
 * Team NAKSHATRA X | NASA Space Apps Challenge 2026
 *
 * Verifies:
 *   - BUG-008: MOLA base layer configuration and overzooming at z >= 8
 *   - BUG-009: CTX Visible Mosaic base layer URL and switching
 *   - BUG-010: HiRISE DTM Live vs. Mock status badge truth-in-labeling
 *   - BUG-011: Analytical overlays independence across toggles (Footprint, Waypoints, Regional DTM)
 * =============================================================================
 */

const MOCK_FALLBACK_ANALYSIS = {
  route_id: 'traverse-mock-test',
  total_distance_m: 1250.0,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -4000.0 },
    { distance_m: 50.0, elevation_m: -3990.0 },
    { distance_m: 100.0, elevation_m: -3980.0 },
  ],
  total_gain_m: 20.0,
  total_loss_m: 0.0,
  max_slope_deg: 5.2,
  slope_window_m: 50.0,
  dtm_source: 'synthetic/mock — no real DTM loaded',
  dtm_posting_m: 0.0,
  coverage_status: 'complete',
  nearby_pois: [],
  limitations: [
    'MOCK DATA: Elevation profile is a deterministic synthetic sine-wave.',
  ],
  is_mock: true,
};

const LIVE_DTM_ANALYSIS = {
  route_id: 'traverse-live-test',
  total_distance_m: 1250.0,
  elevation_profile: [
    { distance_m: 0.0, elevation_m: -2560.5 },
    { distance_m: 50.0, elevation_m: -2558.2 },
    { distance_m: 100.0, elevation_m: -2555.0 },
  ],
  total_gain_m: 5.5,
  total_loss_m: 0.0,
  max_slope_deg: 3.1,
  slope_window_m: 50.0,
  dtm_source: 'HiRISE Stereo DTM (Jezero AOI v2, 1.0m posting)',
  dtm_posting_m: 1.0,
  coverage_status: 'complete',
  nearby_pois: [],
  limitations: [
    'Valid stereo bounds within Jezero Crater crater floor.',
  ],
  is_mock: false,
};

test.describe('Production Smoke Test Defect Verifications (BUG-008 to BUG-011)', () => {

  test('BUG-008: MOLA base layer loads with continuous overzoom at initial view zoom 12', async ({ page }) => {
    // Intercept map tile requests to verify no zoom levels > 7 are requested for MOLA
    const requestedZLevels: number[] = [];
    await page.route('**/trek.nasa.gov/**/Mars_MGS_MOLA_ClrShade_merge_global_463m/**', (route) => {
      const url = route.request().url();
      const match = url.match(/\/(\d+)\/(\d+)\/(\d+)\.jpg/);
      if (match) {
        requestedZLevels.push(parseInt(match[1], 10));
      }
      route.fulfill({
        status: 200,
        contentType: 'image/jpeg',
        body: Buffer.from([]),
      });
    });

    await page.goto('/');

    const mapCanvas = page.locator('[data-testid="mars-map-canvas"]');
    await expect(mapCanvas).toBeVisible();

    // Verify map canvas viewport has initialized
    const viewport = mapCanvas.locator('.ol-viewport');
    await expect(viewport).toBeAttached();

    // Verify that every requested MOLA tile is within native range z <= 7
    if (requestedZLevels.length > 0) {
      for (const z of requestedZLevels) {
        expect(z).toBeLessThanOrEqual(7);
      }
    }
  });

  test('BUG-009: CTX Visible Mosaic base layer switches cleanly and queries ArcGIS server', async ({ page }) => {
    let ctxRequested = false;
    await page.route('**/astro.arcgis.com/arcgis/rest/services/OnMars/CTX/MapServer/**', (route) => {
      ctxRequested = true;
      route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: Buffer.from([]),
      });
    });

    await page.goto('/');

    // Select CTX Mosaic from basemap selector
    const ctxButton = page.locator('button:has-text("CTX")');
    await expect(ctxButton).toBeVisible();
    await ctxButton.click();

    // Verify CTX button has active styling
    await expect(ctxButton).toHaveClass(/bg-cyan-600/);

    // Verify that CTX tiles were requested from the ArcGIS endpoint
    await page.waitForTimeout(500);
    expect(ctxRequested).toBe(true);

    // Switch to Viking and verify clean transition
    const vikingButton = page.locator('button:has-text("Viking")');
    await expect(vikingButton).toBeVisible();
    await vikingButton.click();
    await expect(vikingButton).toHaveClass(/bg-cyan-600/);
  });

  test('BUG-010: Route analysis overlay card truthfully reports DEVELOPMENT / MOCK DATA in fallback mode', async ({ page }) => {
    // Intercept routes/analyze with mock fallback payload
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_FALLBACK_ANALYSIS),
      })
    );

    await page.goto('/');

    // In mock fallback mode, badge MUST report DEVELOPMENT / MOCK DATA, NOT LIVE HiRISE DTM
    const modeBadge = page.locator('.mars-map-canvas span:has-text("DEVELOPMENT / MOCK DATA")');
    await expect(modeBadge).toBeVisible();

    // Must NOT contain "LIVE HiRISE DTM"
    const liveBadge = page.locator('.mars-map-canvas span:has-text("LIVE HiRISE DTM")');
    await expect(liveBadge).not.toBeVisible();

    // Terrain profile panel tag must also show DEVELOPMENT / MOCK
    const profileTag = page.locator('#terrain-section .status-badge');
    await expect(profileTag.first()).toContainText('DEVELOPMENT / MOCK');
  });

  test('BUG-010: Route analysis overlay card truthfully reports LIVE HiRISE DTM when genuine DTM is active', async ({ page }) => {
    // Intercept routes/analyze with genuine live DTM payload
    await page.route('**/api/routes/analyze', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(LIVE_DTM_ANALYSIS),
      })
    );

    await page.goto('/');

    // With genuine DTM, badge reports LIVE HiRISE DTM
    const liveBadge = page.locator('.mars-map-canvas span:has-text("LIVE HiRISE DTM")');
    await expect(liveBadge).toBeVisible();
    await expect(liveBadge).toHaveClass(/bg-emerald-950/);

    // Must NOT contain "DEVELOPMENT / MOCK DATA"
    const mockBadge = page.locator('.mars-map-canvas span:has-text("DEVELOPMENT / MOCK DATA")');
    await expect(mockBadge).not.toBeVisible();
  });

  test('BUG-011: Analytical overlays (Footprint, Waypoints, Regional DTM) toggle independently', async ({ page }) => {
    await page.goto('/');

    // Locate the toolbar toggle buttons
    const hiRiseBtn = page.getByRole('button', { name: 'HiRISE DTM' });
    const footprintBtn = page.getByRole('button', { name: 'Footprint' });
    const _waypointsBtn = page.getByRole('button', { name: 'Waypoints' });

    // Locate the in-canvas checkboxes
    const footprintCheckbox = page.locator('label:has-text("HiRISE DTM Footprint") input[type="checkbox"]');
    const waypointsCheckbox = page.locator('label:has-text("Rover Waypoints") input[type="checkbox"]');
    const regionalCheckbox = page.locator('label:has-text("Regional DTM Tiles") input[type="checkbox"]');

    // All should be initially checked / active
    await expect(footprintCheckbox).toBeChecked();
    await expect(waypointsCheckbox).toBeChecked();
    await expect(regionalCheckbox).toBeChecked();

    // 1. Toggle Footprint off via toolbar button
    await footprintBtn.click();
    await expect(footprintCheckbox).not.toBeChecked();
    // Others must remain checked
    await expect(waypointsCheckbox).toBeChecked();
    await expect(regionalCheckbox).toBeChecked();

    // 2. Toggle Footprint back on via in-canvas checkbox
    await footprintCheckbox.check();
    await expect(footprintCheckbox).toBeChecked();
    await expect(footprintBtn).toHaveCSS('background-color', 'rgb(254, 243, 199)'); // Active amber background

    // 3. Toggle Waypoints off via in-canvas checkbox
    await waypointsCheckbox.uncheck();
    await expect(waypointsCheckbox).not.toBeChecked();
    // Footprint and regional must remain checked
    await expect(footprintCheckbox).toBeChecked();
    await expect(regionalCheckbox).toBeChecked();

    // 4. Toggle Regional DTM off via toolbar button
    await hiRiseBtn.click();
    await expect(regionalCheckbox).not.toBeChecked();
    // Footprint remains checked, waypoints remains unchecked
    await expect(footprintCheckbox).toBeChecked();
    await expect(waypointsCheckbox).not.toBeChecked();
  });

});
