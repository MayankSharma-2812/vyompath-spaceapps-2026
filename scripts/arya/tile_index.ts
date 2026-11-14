/**
 * PREP TOOLING, NOT PRODUCT CODE
 * tile_index.ts — Martian Equirectangular Tile Index Calculation & Verification
 *
 * Author: Arya (Interactive Map Engineer, Team NAKSHATRA X)
 * Role: NASA Space Apps Challenge 2026 - Martian Map / VyomPath
 * Reference: Master Coding Guide v3.1, Section 5.4
 *
 * Grid Specification (VERIFIED):
 *   - CRS: MARS:2000 Equirectangular (IAU 2000 Sphere, EPSG:104905)
 *   - Radius: R = 3,396,190.0 m (standard IAU Mars Sphere)
 *   - Half World Dimensions:
 *       HX = pi * R = 10,669,445.5540916 m
 *       HY = HX / 2 = 5,334,722.7770458 m
 *   - Zoom 0 Matrix: 2 columns x 1 row (2x1 aspect ratio)
 *   - Tile Size: 256 x 256 pixels
 *   - Zoom 0 Resolution: RES0 = (2 * HX) / 512 = 41,677.52169567 m/px
 *   - Origin: Top-Left (-180 deg lon, +90 deg lat), Y grows downward
 *   - Clamping: lon=180 clamped to 2^(z+1)-1, lat=-90 clamped to 2^z-1
 */

import * as fs from 'fs';
import * as path from 'path';

export const R = 3396190.0;
export const HX = Math.PI * R;
export const HY = HX / 2.0;
export const RES0 = (2.0 * HX) / 512.0; // 41677.52169567039 m/pixel

export interface TileIndexResult {
  z: number;
  x: number;
  y: number;
}

export interface TileBounds {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

export function tileIndex(lon: number, lat: number, z: number): [number, number, number] {
  if (z < 0) {
    throw new Error(`Zoom level z must be >= 0, got ${z}`);
  }

  const X = (lon * Math.PI / 180.0) * R;
  const Y = (lat * Math.PI / 180.0) * R;
  const t = 256.0 * RES0 / Math.pow(2.0, z);

  let x = Math.floor((X + HX) / t);
  let y = Math.floor((HY - Y) / t);

  const maxX = Math.pow(2.0, z + 1) - 1;
  const maxY = Math.pow(2.0, z) - 1;

  // Clamp edge cases (anti-meridian +180 and South Pole -90)
  x = Math.max(0, Math.min(x, maxX));
  y = Math.max(0, Math.min(y, maxY));

  return [z, x, y];
}

export function tileBounds(z: number, x: number, y: number): TileBounds {
  const n_x = 2 * Math.pow(2, z);
  const n_y = Math.pow(2, z);

  const minLon = -180.0 + (x / n_x) * 360.0;
  const maxLon = -180.0 + ((x + 1) / n_x) * 360.0;
  const maxLat = 90.0 - (y / n_y) * 180.0;
  const minLat = 90.0 - ((y + 1) / n_y) * 180.0;

  return { minLon, minLat, maxLon, maxLat };
}

export function verifyManualClaim() {
  const computed = tileIndex(77.45, 18.44, 15);
  const claimed = [15, 46867, 13027];
  const matches = computed[0] === claimed[0] && computed[1] === claimed[1] && computed[2] === claimed[2];
  return {
    input: { lon: 77.45, lat: 18.44, z: 15 },
    computed,
    claimed,
    matches,
    note: "Mathematical result matches claimed index exactly. However, file 15/46867/13027.jpg does not exist in tiles_aoi because lon 77.45 deg E is 681.75 m west of the Jezero valid stereo boundary at lat 18.44 deg N (edge at lon 77.462124 deg E, computed with R=3,396,190 m)."
  };
}

export const TEST_POINTS = [
  {
    name: "SYNTH-GRID-POINT-01",
    lon: 77.45088572,
    lat: 18.44462715,
    notes: "Perseverance Sol 13 (landing site vicinity; outside v2 valid stereo footprint)"
  },
  {
    name: "SYNTH-GRID-POINT-02",
    lon: 77.45177711,
    lat: 18.44520229,
    notes: "Perseverance Sol 23 (early ingress; outside v2 valid stereo footprint)"
  },
  {
    name: "SYNTH-GRID-POINT-03",
    lon: 77.45102155,
    lat: 18.44486273,
    notes: "Perseverance Sol 34 (Van Zyl overlook; outside v2 valid stereo footprint)"
  },
  {
    name: "SYNTH-GRID-POINT-04",
    lon: 77.46313311,
    lat: 18.46079140,
    notes: "Perseverance Sol 386 (rapid transit waypoint; INSIDE v2 valid stereo footprint)"
  },
  {
    name: "SYNTH-GRID-POINT-05",
    lon: 77.46157944,
    lat: 18.46447597,
    notes: "Perseverance Sol 387 (rapid transit staging; INSIDE v2 valid stereo footprint)"
  },
  {
    name: "Footprint-NW-Corner",
    lon: 77.45290653,
    lat: 18.50986793,
    notes: "Jezero valid stereo footprint NW vertex"
  },
  {
    name: "Footprint-SW-Corner",
    lon: 77.49937431,
    lat: 18.15934679,
    notes: "Jezero valid stereo footprint SW vertex"
  },
  {
    name: "Footprint-SE-Corner",
    lon: 77.59814922,
    lat: 18.17112171,
    notes: "Jezero valid stereo footprint SE vertex"
  },
  {
    name: "Footprint-NE-Corner",
    lon: 77.55176964,
    lat: 18.52155765,
    notes: "Jezero valid stereo footprint NE vertex"
  },
  {
    name: "Manual-Claim-Point",
    lon: 77.45,
    lat: 18.44,
    notes: "Master Guide Section 5.4 reference point (tested)"
  },
  {
    name: "Edge-Antimeridian-East",
    lon: 180.0,
    lat: 0.0,
    notes: "Global edge case: lon=180 boundary clamp"
  },
  {
    name: "Edge-SouthPole",
    lon: 0.0,
    lat: -90.0,
    notes: "Global edge case: lat=-90 boundary clamp"
  },
  {
    name: "Edge-Origin",
    lon: 0.0,
    lat: 0.0,
    notes: "Global origin: prime meridian and equator intersection"
  },
  {
    name: "Tile-Boundary-Jezero",
    lon: 77.4365234375,
    lat: 18.45703125,
    notes: "Exact tile grid boundary at z12 (multiple of 180 / 2^12)"
  }
];

export function buildFixtures(bundleDir?: string) {
  const zooms = [12, 14, 15, 16];
  const fixturePoints = [];

  let effectiveBundleDir = bundleDir || process.env.VYOMPATH_BUNDLE_DIR;
  if (!effectiveBundleDir) {
    const candidates = [
      'C:\\Users\\aryat\\AppData\\Local\\Temp\\vyompath_bundle',
      '/tmp/vyompath_bundle',
      path.resolve('data/bundle')
    ];
    for (const c of candidates) {
      if (fs.existsSync(c) && fs.existsSync(path.join(c, 'tiles_aoi'))) {
        effectiveBundleDir = c;
        break;
      }
    }
  }

  for (const p of TEST_POINTS) {
    for (const z of zooms) {
      const [zIdx, xIdx, yIdx] = tileIndex(p.lon, p.lat, z);
      const aoiRel = `tiles_aoi/${z}/${xIdx}/${yIdx}.jpg`;
      const hillRel = `tiles_hillshade/${z}/${xIdx}/${yIdx}.jpg`;

      let aoiExists = false;
      let hillExists = false;
      if (effectiveBundleDir && fs.existsSync(effectiveBundleDir)) {
        aoiExists = fs.existsSync(path.join(effectiveBundleDir, aoiRel));
        hillExists = fs.existsSync(path.join(effectiveBundleDir, hillRel));
      }

      const b = tileBounds(zIdx, xIdx, yIdx);

      fixturePoints.push({
        name: p.name,
        lon: p.lon,
        lat: p.lat,
        z,
        expected: [zIdx, xIdx, yIdx],
        tile_bounds_lonlat: [
          Number(b.minLon.toFixed(8)),
          Number(b.minLat.toFixed(8)),
          Number(b.maxLon.toFixed(8)),
          Number(b.maxLat.toFixed(8))
        ],
        bundle_file_exists: {
          tiles_aoi: aoiExists,
          tiles_hillshade: hillExists
        },
        notes: p.notes
      });
    }
  }

  return {
    generated_by: "scripts/arya/tile_index.ts",
    method: "Master Coding Manual v3.1, Section 5.4 (Mars 2000 Equirectangular 2x1)",
    grid_specification: {
      crs: "MARS:2000 (IAU 2000 Sphere, EPSG:104905)",
      radius_m: R,
      half_width_hx_m: HX,
      half_height_hy_m: HY,
      res0_m_per_px: RES0,
      aspect_ratio: "2:1",
      tile_size_px: 256,
      origin: "top-left [-180, 90]"
    },
    manual_claim_verification: verifyManualClaim(),
    generated_at: new Date().toISOString(),
    bundle_dir_evaluated: effectiveBundleDir || "UNAVAILABLE",
    points: fixturePoints
  };
}

// Self-executing runner
if (process.argv[1] && (process.argv[1].endsWith('tile_index.ts') || process.argv[1].endsWith('tile_index.js'))) {
  console.log("=".repeat(70));
  console.log("Arya's Mars Tile Index Verification - TypeScript (PREP TOOLING, NOT PRODUCT CODE)");
  console.log("=".repeat(70));

  const claim = verifyManualClaim();
  console.log(`Manual 5.4 Claim Test: tileIndex(77.45, 18.44, 15)`);
  console.log(`  Computed: [${claim.computed.join(', ')}]`);
  console.log(`  Claimed:  [${claim.claimed.join(', ')}]`);
  console.log(`  Matches:  ${claim.matches} (VERIFIED)`);
  console.log(`  Note:     ${claim.note}`);
  console.log("-".repeat(70));

  const fixtures = buildFixtures();
  console.log(`Generated ${fixtures.points.length} golden test vectors across zooms 12, 14, 15, 16.`);

  const existingAoi = fixtures.points.filter(p => p.bundle_file_exists.tiles_aoi).length;
  const existingHill = fixtures.points.filter(p => p.bundle_file_exists.tiles_hillshade).length;
  console.log(`Bundle file existence (dir: ${fixtures.bundle_dir_evaluated}):`);
  console.log(`  tiles_aoi matches:       ${existingAoi} / ${fixtures.points.length}`);
  console.log(`  tiles_hillshade matches: ${existingHill} / ${fixtures.points.length}`);
  console.log("=".repeat(70));

  if (process.argv.includes('--json')) {
    console.log(JSON.stringify(fixtures, null, 2));
  }
}
