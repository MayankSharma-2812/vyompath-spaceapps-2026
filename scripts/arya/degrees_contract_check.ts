/**
 * PREP TOOLING, NOT PRODUCT CODE
 * degrees_contract_check.ts — Verification of Frontend/Backend Lon-Lat Degrees Contract
 *
 * Author: Arya (Map & OpenLayers Lead, Team NAKSHATRA X)
 * Role: NASA Space Apps Challenge 2026 - Martian Map / VyomPath
 * Reference: Master Coding Manual v3.1 (Sections 5.1 and 5.5)
 */

export const R = 3396190.0;
export const TOLERANCE_DEG = 1e-9;

export function degreesToMars2000Meters(lon: number, lat: number): [number, number] {
  const x = (lon * Math.PI / 180.0) * R;
  const y = (lat * Math.PI / 180.0) * R;
  return [x, y];
}

export function mars2000MetersToDegrees(x: number, y: number): [number, number] {
  const lon = (x / R) * (180.0 / Math.PI);
  const lat = (y / R) * (180.0 / Math.PI);
  return [lon, lat];
}

export function wrapLonManual51(v: number): number {
  return ((v + 180.0) % 360.0) - 180.0;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  wrapped_lon: number | null;
}

export function validateBackendSchema(lon: number, lat: number): ValidationResult {
  const errors: string[] = [];
  if (lon < -180.0) {
    errors.append ? errors.push(`lon: Input should be greater than or equal to -180 [got ${lon}]`) : errors.push(`lon: Input should be greater than or equal to -180 [got ${lon}]`);
  } else if (lon > 360.0) {
    errors.push(`lon: Input should be less than or equal to 360 [got ${lon}]`);
  }

  if (lat < -90.0) {
    errors.push(`lat: Input should be greater than or equal to -90 [got ${lat}]`);
  } else if (lat > 90.0) {
    errors.push(`lat: Input should be less than or equal to 90 [got ${lat}]`);
  }

  const valid = errors.length === 0;
  const wrapped_lon = valid ? wrapLonManual51(lon) : null;

  return { valid, errors, wrapped_lon };
}

export const TEST_VECTORS = [
  {
    name: "POI Sol 386",
    lon: 77.46313311,
    lat: 18.46079140,
    description: "Perseverance Sol 386 rapid transit waypoint"
  },
  {
    name: "POI Sol 387",
    lon: 77.46157944,
    lat: 18.46447597,
    description: "Perseverance Sol 387 rapid transit staging waypoint"
  },
  {
    name: "Footprint NW Vertex",
    lon: 77.4529065312924,
    lat: 18.509867934244717,
    description: "jezero_dtm.geojson Northwest outline vertex"
  },
  {
    name: "Footprint SW Vertex",
    lon: 77.49937431082921,
    lat: 18.159346791095654,
    description: "jezero_dtm.geojson Southwest outline vertex"
  },
  {
    name: "Footprint SE Vertex",
    lon: 77.59814921501544,
    lat: 18.171121711363813,
    description: "jezero_dtm.geojson Southeast outline vertex"
  },
  {
    name: "Footprint NE Vertex",
    lon: 77.55176964310874,
    lat: 18.521557652484884,
    description: "jezero_dtm.geojson Northeast outline vertex"
  },
  {
    name: "Footprint BBox NW Corner",
    lon: 77.4529065312924,
    lat: 18.521557652484884,
    description: "Jezero DTM bounding box NW corner"
  },
  {
    name: "Footprint BBox SW Corner",
    lon: 77.4529065312924,
    lat: 18.159346791095654,
    description: "Jezero DTM bounding box SW corner"
  },
  {
    name: "Footprint BBox SE Corner",
    lon: 77.59814921501544,
    lat: 18.159346791095654,
    description: "Jezero DTM bounding box SE corner"
  },
  {
    name: "Footprint BBox NE Corner",
    lon: 77.59814921501544,
    lat: 18.521557652484884,
    description: "Jezero DTM bounding box NE corner"
  },
  {
    name: "Origin (Equator & Prime Meridian)",
    lon: 0.0,
    lat: 0.0,
    description: "Planetary coordinate origin"
  },
  {
    name: "Antimeridian East (+180)",
    lon: 180.0,
    lat: 0.0,
    description: "Eastern antimeridian edge (+180)"
  },
  {
    name: "Antimeridian West (-180)",
    lon: -180.0,
    lat: 0.0,
    description: "Western antimeridian edge (-180)"
  },
  {
    name: "North Pole (+90)",
    lon: 0.0,
    lat: 90.0,
    description: "Planetary North Pole"
  },
  {
    name: "South Pole (-90)",
    lon: 0.0,
    lat: -90.0,
    description: "Planetary South Pole"
  },
  {
    name: "0-360 Domain Point (lon 270 equator)",
    lon: 270.0,
    lat: 0.0,
    description: "Positive 0-360 representation of 90 deg West"
  },
  {
    name: "0-360 Domain Point (lon 270 lat 18.44)",
    lon: 270.0,
    lat: 18.44,
    description: "Jezero latitude with 0-360 longitude domain"
  }
];

export function runChecks() {
  const results = [];
  let maxErrLon = 0.0;
  let maxErrLat = 0.0;
  let worstVectorName = "";

  for (const v of TEST_VECTORS) {
    const lonIn = v.lon;
    const latIn = v.lat;

    const [xM, yM] = degreesToMars2000Meters(lonIn, latIn);
    const [lonRt, latRt] = mars2000MetersToDegrees(xM, yM);

    const errLon = Math.abs(lonRt - lonIn);
    const errLat = Math.abs(latRt - latIn);

    if (errLon > maxErrLon || errLat > maxErrLat) {
      maxErrLon = Math.max(maxErrLon, errLon);
      maxErrLat = Math.max(maxErrLat, errLat);
      worstVectorName = v.name;
    }

    const degreesValidation = validateBackendSchema(lonIn, latIn);
    const metresAsDegreesValidation = validateBackendSchema(xM, yM);
    const wrappedLon = wrapLonManual51(lonIn);

    results.push({
      name: v.name,
      description: v.description,
      input_degrees: {
        lon: Number(lonIn.toFixed(8)),
        lat: Number(latIn.toFixed(8))
      },
      mars2000_meters: {
        x: Number(xM.toFixed(3)),
        y: Number(yM.toFixed(3))
      },
      round_trip_degrees: {
        lon: Number(lonRt.toFixed(8)),
        lat: Number(latRt.toFixed(8))
      },
      round_trip_error_deg: {
        lon_err: errLon.toExponential(2),
        lat_err: errLat.toExponential(2),
        passed_1e_9: (errLon < TOLERANCE_DEG && errLat < TOLERANCE_DEG)
      },
      schema_validation_as_degrees: degreesValidation,
      metres_as_degrees_trap: {
        sent_values: { lon: Number(xM.toFixed(3)), lat: Number(yM.toFixed(3)) },
        validation_passed: metresAsDegreesValidation.valid,
        validation_errors: metresAsDegreesValidation.errors,
        http_status_expected: metresAsDegreesValidation.valid ? 200 : 422
      },
      lon_wrap_result: {
        original_lon: lonIn,
        wrapped_lon: Number(wrappedLon.toFixed(8)),
        seam_shift_detected: (lonIn === 180.0 && wrappedLon === -180.0)
      }
    });
  }

  const wrapChecks = {
    lon_270_maps_to: wrapLonManual51(270.0),
    lon_180_maps_to: wrapLonManual51(180.0),
    lon_minus_180_maps_to: wrapLonManual51(-180.0),
    seam_behavior_note: "Lon +180.0 maps to -180.0; both boundary limits fold onto the Western antimeridian [-180, 180)."
  };

  const trapFailures = results.filter(r => !r.metres_as_degrees_trap.validation_passed).length;

  return {
    generated_by: "scripts/arya/degrees_contract_check.ts",
    timestamp_utc: new Date().toISOString(),
    crs: "MARS:2000 (IAU 2000 Mars Sphere, R = 3,396,190.0 m)",
    tolerance_deg: TOLERANCE_DEG,
    round_trip_accuracy: {
      all_passed: (maxErrLon < TOLERANCE_DEG && maxErrLat < TOLERANCE_DEG),
      max_err_lon_deg: maxErrLon.toExponential(2),
      max_err_lat_deg: maxErrLat.toExponential(2),
      worst_vector: worstVectorName
    },
    metres_as_degrees_trap_summary: {
      total_tested: results.length,
      rejected_by_backend_schema: trapFailures,
      passed_only_at_origin: results.length - trapFailures,
      conclusion: "Raw projected metres sent as degrees are immediately rejected by Pydantic with HTTP 422 Unprocessable Entity for all non-origin coordinates."
    },
    longitude_wrap_checks: wrapChecks,
    openlayers_distance_notice: "OpenLayers ol/sphere.getLength() is strictly PROHIBITED because it hardcodes Earth authalic radius (6,371,008.8 m). Frontend displays only authoritative backend-calculated geodesic distances.",
    vectors: results
  };
}

if (process.argv[1] && (process.argv[1].endsWith('degrees_contract_check.ts') || process.argv[1].endsWith('degrees_contract_check.js'))) {
  console.log("=".repeat(75));
  console.log("Arya's Degrees Contract & Schema Trap Check - TypeScript (PREP TOOLING)");
  console.log("=".repeat(75));

  const res = runChecks();
  const acc = res.round_trip_accuracy;
  console.log(`1. Bidirectional Precision Check (< ${res.tolerance_deg} deg):`);
  console.log(`   Max lon error: ${acc.max_err_lon_deg} deg`);
  console.log(`   Max lat error: ${acc.max_err_lat_deg} deg`);
  console.log(`   Worst case vector: ${acc.worst_vector}`);
  console.log(`   Status: ${acc.all_passed ? 'PASSED' : 'FAILED'}`);
  console.log("-".repeat(75));

  console.log("2. Longitude Wrap (Manual Section 5.1):");
  const wc = res.longitude_wrap_checks;
  console.log(`   wrap_lon(270.0)  -> ${wc.lon_270_maps_to.toFixed(1)} deg (expected -90.0 deg)`);
  console.log(`   wrap_lon(180.0)  -> ${wc.lon_180_maps_to.toFixed(1)} deg (expected -180.0 deg)`);
  console.log(`   wrap_lon(-180.0) -> ${wc.lon_minus_180_maps_to.toFixed(1)} deg (expected -180.0 deg)`);
  console.log(`   Seam Note: ${wc.seam_behavior_note}`);
  console.log("-".repeat(75));

  console.log("3. Metres-as-Degrees Schema Trap:");
  const trap = res.metres_as_degrees_trap_summary;
  console.log(`   Tested vectors: ${trap.total_tested}`);
  console.log(`   Rejected (HTTP 422): ${trap.rejected_by_backend_schema}`);
  console.log(`   Passed (Origin (0,0) only): ${trap.passed_only_at_origin}`);
  console.log(`   ${trap.conclusion}`);
  console.log("-".repeat(75));

  console.log("4. Distance Calculation Policy:");
  console.log(`   ${res.openlayers_distance_notice}`);
  console.log("=".repeat(75));

  if (process.argv.includes('--json')) {
    console.log(JSON.stringify(res, null, 2));
  }
}
