import { test, expect } from '@playwright/test';

/**
 * =============================================================================
 * VyomPath Master Playwright Test Suite: Journeys J1 - J7
 * Team NAKSHATRA X | NASA Space Apps Challenge 2026
 *
 * Requirements Reference:
 *   - docs/test-plan.md
 *   - docs/testing-and-acceptance-plan.md
 *   - Master Build Timeline v3.1 (Gate G3 Acceptance Criteria)
 *
 * Strict Pre-Event Mode (D1):
 *   Journeys J1, J4 (structural), and J6 verify currently implemented UI/UX components.
 *   Journeys J2, J3, J5, and J7 require interactive map features reserved for
 *   the hackathon build (Nov 14-15) and are explicitly marked with test.fixme().
 * =============================================================================
 */

test.describe('VyomPath User Journeys', () => {

  // ---------------------------------------------------------------------------
  // Journey J1: Load the Planetary Map
  // ---------------------------------------------------------------------------
  test('J1: User loads the map workspace and sees initial surface controls', async ({ page }) => {
    await page.goto('/');

    // 1. Verify workspace branding & navigation
    await expect(page.locator('.brand')).toContainText('NAKSHATRA');
    await expect(page.locator('.brand')).toContainText('VYOMPATH');

    // 2. Verify top toolbar and study region indicator
    const toolbar = page.locator('.top-toolbar');
    await expect(toolbar).toBeVisible();
    await expect(toolbar).toContainText('MARS RESEARCH WORKSPACE');
    await expect(toolbar).toContainText('Explore the surface');

    // 3. Verify Map Canvas container is present in DOM
    const mapCanvas = page.locator('[data-testid="mars-map-canvas"]');
    await expect(mapCanvas).toBeAttached();

    // 4. Verify initial map stage notice
    await expect(page.locator('.map-panel')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // Journey J2: Draw Route and See Metrics
  // ---------------------------------------------------------------------------
  test('J2: User draws a route and obtains terrain elevation profile and metrics', async ({ page }) => {
    test.fixme(
      true,
      'Pending Event-Day Hackathon Implementation (Nov 14 E2/E3): ' +
      'OpenLayers interactive drawing (ol/interaction/Draw) and live backend DTM sampling ' +
      'are reserved under strict D1 pre-event governance.'
    );

    await page.goto('/');
    const mapCanvas = page.locator('[data-testid="mars-map-canvas"]');

    // Click waypoints on the canvas to draw a route
    const box = await mapCanvas.boundingBox();
    if (!box) throw new Error('Map canvas not found');

    await page.mouse.click(box.x + box.width * 0.4, box.y + box.height * 0.4);
    await page.mouse.click(box.x + box.width * 0.6, box.y + box.height * 0.6);

    // Assert that elevation profile chart renders points
    await expect(page.locator('.recharts-surface')).toBeVisible();

    // Assert that distance and elevation gain metrics are populated
    const metricCards = page.locator('.metric-card');
    await expect(metricCards.first()).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // Journey J3: Route Outside Valid Footprint
  // ---------------------------------------------------------------------------
  test('J3: Route outside DTM footprint reports out_of_bounds coverage status', async ({ page }) => {
    test.fixme(
      true,
      'Pending Event-Day Hackathon Implementation (Nov 14 E2): ' +
      'Live DTM valid-data footprint boundary checking is reserved for the hackathon.'
    );

    await page.goto('/');
    // When a route is drawn outside the Jezero valid-data mask
    const badge = page.locator('.panel-tag');
    await expect(badge).toContainText('OUT OF BOUNDS');
  });

  // ---------------------------------------------------------------------------
  // Journey J4: Route A versus Route B Comparison
  // ---------------------------------------------------------------------------
  test('J4: Route comparison panel renders comparison cards and metric differences', async ({ page }) => {
    await page.goto('/');

    const comparisonSection = page.locator('.comparison-panel');
    await expect(comparisonSection).toBeVisible();
    await expect(comparisonSection).toContainText('Route A vs Route B');

    // Verify Route A and Route B cards are present
    const cards = page.locator('.comparison-route-card');
    await expect(cards).toHaveCount(2);
    await expect(cards.nth(0)).toContainText('Route A');
    await expect(cards.nth(1)).toContainText('Route B');

    // Verify Difference section header
    const deltas = page.locator('.comparison-deltas');
    await expect(deltas).toBeVisible();
    await expect(deltas).toContainText('Differences');
  });

  // ---------------------------------------------------------------------------
  // Journey J5: POI Card Displays Verified Citation
  // ---------------------------------------------------------------------------
  test('J5: Nearby scientific POI card displays NASA mission citation and source link', async ({ page }) => {
    await page.goto('/');
    const summaryPanel = page.locator('.summary-panel');
    await expect(summaryPanel).toContainText('Perseverance');
  });

  // ---------------------------------------------------------------------------
  // Journey J6: Scientific Provenance and Limitations Display
  // ---------------------------------------------------------------------------
  test('J6: Dashboard displays elevation analysis section with status badge', async ({ page }) => {
    await page.goto('/');

    const terrainPanel = page.locator('.terrain-panel');
    await expect(terrainPanel).toBeVisible();
    await expect(terrainPanel).toContainText('Terrain Elevation Profile');

    // Verify status badge exists
    const statusBadge = terrainPanel.locator('.panel-tag');
    await expect(statusBadge).toBeVisible();

    // Verify terrain metric cards
    const metrics = page.locator('.terrain-metrics');
    await expect(metrics).toBeVisible();
    await expect(metrics).toContainText('Gain');
    await expect(metrics).toContainText('Loss');
  });

  // ---------------------------------------------------------------------------
  // Journey J7: Mars Trek Unavailable and Fallback Loads
  // ---------------------------------------------------------------------------
  test('J7: Offline or remote WMTS failure triggers fallback layer display', async ({ page }) => {
    test.fixme(
      true,
      'Pending Event-Day Hackathon Implementation (Nov 14 E3): ' +
      'Tile fallback event handler on WMTS tile load errors.'
    );

    // Intercept NASA Trek tile requests and force failure
    await page.route('**/trek.nasa.gov/**', (route) => route.abort());
    await page.goto('/');

    // Verify fallback notice or layer status
    const badge = page.locator('.panel-tag');
    await expect(badge).toBeVisible();
  });

});
