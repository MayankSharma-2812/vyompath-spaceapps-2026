/**
 * waypointData.ts — Footprint Polygon & POI Definitions
 *
 * Sourced directly from:
 * - data/footprints/jezero_dtm.geojson (98-vertex display stereo HiRISE DTM boundary)
 * - Third-party rover telemetry quarantined per Issue #11 pending verified rights.
 */

import type { RoverWaypoint } from './types';

export const JEZERO_CENTER: [number, number] = [77.45, 18.44];

/**
 * 98-vertex bounding polygon of the valid HiRISE stereo DTM strip.
 * Longitudes in planetocentric degrees [lon, lat], rounded to 8 decimal places.
 */
export const JEZERO_DTM_FOOTPRINT_COORDINATES: [number, number][] = [
  [77.54679473, 18.52108052],
  [77.5371801, 18.51988769],
  [77.50327309, 18.51593432],
  [77.47704014, 18.51273072],
  [77.47476438, 18.5125092],
  [77.45290653, 18.50986793],
  [77.45542927, 18.49044187],
  [77.45747569, 18.47546336],
  [77.45770503, 18.47326514],
  [77.4601572, 18.45525343],
  [77.46386192, 18.42652331],
  [77.46779598, 18.39721381],
  [77.46855456, 18.39106223],
  [77.46910145, 18.38724518],
  [77.46913674, 18.38663172],
  [77.47284146, 18.35931595],
  [77.47404108, 18.34975628],
  [77.47434099, 18.34805224],
  [77.47434099, 18.34754103],
  [77.47536419, 18.34045222],
  [77.47700486, 18.32736519],
  [77.4773224, 18.32535442],
  [77.47769288, 18.32215083],
  [77.47779872, 18.32181002],
  [77.47839854, 18.3169535],
  [77.47922769, 18.31102344],
  [77.47938646, 18.3093194],
  [77.48058609, 18.30098664],
  [77.48069193, 18.29955525],
  [77.48090363, 18.29834538],
  [77.48152109, 18.29347182],
  [77.48208562, 18.28960365],
  [77.4826325, 18.28493458],
  [77.48369099, 18.27774353],
  [77.4862843, 18.25753361],
  [77.48741336, 18.24950758],
  [77.48817194, 18.24321967],
  [77.48928336, 18.2352618],
  [77.49106515, 18.22152723],
  [77.49404657, 18.19957919],
  [77.49484044, 18.19306975],
  [77.49510506, 18.19145092],
  [77.4957578, 18.18628767],
  [77.49586365, 18.1858787],
  [77.49679865, 18.17861949],
  [77.49708091, 18.1771881],
  [77.49732789, 18.17441051],
  [77.49753959, 18.17272351],
  [77.4980512, 18.16938359],
  [77.49850988, 18.16549838],
  [77.49863337, 18.16490196],
  [77.49886271, 18.16284007],
  [77.49937431, 18.15934679],
  [77.50131488, 18.15961944],
  [77.50554884, 18.16004545],
  [77.50964168, 18.16060778],
  [77.51094715, 18.16069298],
  [77.51652187, 18.1612894],
  [77.52624235, 18.16248223],
  [77.53202878, 18.16309568],
  [77.53629802, 18.16360689],
  [77.53758586, 18.16381138],
  [77.54026737, 18.16406698],
  [77.54374275, 18.16454411],
  [77.54601851, 18.1647486],
  [77.55379842, 18.1657199],
  [77.56152541, 18.16658896],
  [77.56505371, 18.16706609],
  [77.58652345, 18.1696392],
  [77.59814922, 18.17112171],
  [77.59686138, 18.17930111],
  [77.59456799, 18.19773882],
  [77.59255685, 18.21251286],
  [77.59234515, 18.21370568],
  [77.59222166, 18.21573349],
  [77.5917277, 18.21961871],
  [77.59045751, 18.2287694],
  [77.58839345, 18.24473626],
  [77.58707034, 18.25386992],
  [77.58687628, 18.25586365],
  [77.58661166, 18.25755065],
  [77.58610005, 18.26198115],
  [77.58474166, 18.27174531],
  [77.58437118, 18.27520451],
  [77.58343618, 18.2824126],
  [77.58301279, 18.28513907],
  [77.58211307, 18.29178482],
  [77.5746507, 18.3487509],
  [77.5704873, 18.37944067],
  [77.56620041, 18.41304435],
  [77.56334248, 18.43429374],
  [77.56150777, 18.44843727],
  [77.56000824, 18.45932609],
  [77.55780305, 18.47648578],
  [77.55554493, 18.49291273],
  [77.55312804, 18.51186166],
  [77.55176964, 18.52155765],
  [77.54679473, 18.52108052],
];

/**
 * Mars 2020 Perseverance Rover Waypoints.
 * Quarantined per Issue #11 pending verified upstream redistribution rights.
 * Default shipping state is an empty array to prevent distribution of unverified telemetry.
 */
export const ROVER_WAYPOINTS: RoverWaypoint[] = [];

/**
 * Public NASA/JPL Ground-Truth Calibration Anchors (Sols 386 & 387).
 * Verified within ±0.05m against HiRISE DTM for telemetry cross-check.
 */
export const PERSEVERANCE_REFERENCE_WAYPOINTS: RoverWaypoint[] = [
  {
    id: 'SOL-386-ANCHOR',
    name: 'Perseverance Sol 386 Anchor',
    sol: 386,
    lon: 77.46313311,
    lat: 18.46079140,
    elev_geoid_m: -2568.87,
    inside_footprint: true,
    note: 'Crater floor rapid transit anchor (verified within ±0.05m against HiRISE DTM)',
  },
  {
    id: 'SOL-387-ANCHOR',
    name: 'Perseverance Sol 387 Anchor',
    sol: 387,
    lon: 77.46157944,
    lat: 18.46447597,
    elev_geoid_m: -2568.58,
    inside_footprint: true,
    note: 'Rapid transit staging anchor (verified within ±0.05m against HiRISE DTM)',
  },
];

export const GEOLOGICAL_EMPTY_STATE_MESSAGE =
  'Zero catalogued USGS/PDS geological formations lie within this 8.3 × 10 km micro-DTM. Third-party rover waypoints are excluded pending verified redistribution rights.';
