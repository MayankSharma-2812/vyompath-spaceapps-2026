# VYOMPATH — Phase 2: Primary DTM Raster Metadata & Geodesy Report

**Milestone Event:** NASA Space Apps Challenge 2026 &mdash; Build Day (Session E1)  
**Date:** November 14, 2026 (Simulated Build Day)  
**Lead Author:** Shyam Sharma (Data & GIS Lead, Team NAKSHATRA X)  
**Reviewer:** Mayank Sharma (@MayankSharma-2812, API & Cloud Lead)  
**Verification Target:** Primary Metric Digital Terrain Model (`jezero_aoi_v2.tif`)  
**Final Status:** **`VERIFIED`**  

---

## 1. Executive Summary

As part of Phase 2 build-day verification, the primary digital terrain model extracted from the verified offline bundle v1.6 was audited using `rasterio` (GDAL 3.x bindings).

The primary DTM file [`jezero_aoi_v2.tif`](file:///E:/DATASETS/_audit_phase2_v16/jezero_aoi_v2.tif) ($125,847,250\text{ bytes}$) was verified for dimensional accuracy, projection definition, affine geotransform, pixel posting, elevation bounds, and valid-data coverage. **All empirical measurements match approved system specifications with zero defects.**

---

## 2. Raster Properties & Geodetic Metadata

| Parameter | Specification / Expected Value | Measured Value | Unit / Format | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Driver** | `GTiff` | `GTiff` | GeoTIFF Driver | **MATCH** |
| **File Size** | 125,847,250 bytes | 125,847,250 bytes | Exact Bytes | **MATCH** |
| **Raster Width** | 9,014 pixels | 9,014 pixels | Columns | **MATCH** |
| **Raster Height** | 10,896 pixels | 10,896 pixels | Rows | **MATCH** |
| **Band Count** | 1 | 1 | Single Band | **MATCH** |
| **Data Type** | `Float32` | `float32` | 32-bit Floating Point | **MATCH** |
| **NoData Sentinel** | `-3.4028226550889045e+38` | `-3.4028226550889045e+38` | IEEE 754 Float32 Min | **MATCH** |
| **Coordinate Reference System** | Equirectangular (PDS Mars) | Equirectangular (PDS Mars) | WKT String | **MATCH** |
| **Reference Spheroid** | $R = 3,394,839.8133163\text{ m}$ | $R = 3,394,839.8133163\text{ m}$ | Local Radius Sphere | **MATCH** |
| **Standard Parallel ($\text{lat\_ts}$)** | $15.00^\circ\text{N}$ | $15.00^\circ\text{N}$ | True Scale Latitude | **MATCH** |
| **Central Meridian ($\text{lon\_0}$)** | $77.53^\circ\text{E}$ | $77.53^\circ\text{E}$ | Origin Longitude | **MATCH** |
| **Pixel Posting ($dx$)** | $1.0096633269\text{ m/pixel}$ | $1.0096633269\text{ m/pixel}$ | Easting Increment | **MATCH** |
| **Pixel Posting ($dy$)** | $1.0096633269\text{ m/pixel}$ | $1.0096633269\text{ m/pixel}$ | Northing Increment | **MATCH** |
| **Origin Easting ($X_{\text{origin}}$)** | $-5,200.7757967131\text{ m}$ | $-5,200.7757967131365\text{ m}$ | Projected Upper-Left X | **MATCH** |
| **Origin Northing ($Y_{\text{origin}}$)** | $1,096,000.6476153\text{ m}$ | $1,096,000.6476152753\text{ m}$ | Projected Upper-Left Y | **MATCH** |

---

## 3. Projected Spatial Extents (Bounding Box)

The affine geotransform maps raster pixel coordinates $(C, R)$ to projected coordinates $(X, Y)$ via:
$$X = X_{\text{origin}} + C \cdot dx$$
$$Y = Y_{\text{origin}} - R \cdot dy$$

### Exact Bounding Box Coordinates:
- **Left (West):** $-5,200.7757967131365\text{ m}$
- **Bottom (South):** $1,084,999.3560056877\text{ m}$
- **Right (East):** $3,900.3294317029577\text{ m}$
- **Top (North):** $1,096,000.6476152753\text{ m}$

### Span Dimensions:
- **Total East-West Span:** $9,101.1052\text{ m}$ (~$9.10\text{ km}$)
- **Total North-South Span:** $11,001.2916\text{ m}$ (~$11.00\text{ km}$)

---

## 4. Pixel Elevation Statistics & Valid Coverage

A complete raster read across all $98,216,544\text{ pixels}$ ($9,014 \times 10,896$) evaluated the active HiRISE valid-data mask:

| Metric | Measured Value | Percentage of Raster Area |
| :--- | :---: | :---: |
| **Total Raster Cells** | $98,216,544$ | $100.00\%$ |
| **Valid Metric Elevation Cells** | $62,037,379$ | **$63.16\%$** |
| **NoData Masked Cells** | $36,179,165$ | **$36.84\%$** |
| **Minimum Elevation** | $-2688.7627\text{ m}$ | &mdash; |
| **Maximum Elevation** | $-2510.1851\text{ m}$ | &mdash; |
| **Mean Elevation** | $-2624.5034\text{ m}$ | &mdash; |
| **Standard Deviation** | $30.6403\text{ m}$ | &mdash; |
| **Dynamic Elevation Range** | $178.5776\text{ m}$ | &mdash; |

### Interpretation of Coverage:
The $63.16\%$ valid-data coverage perfectly aligns with the oblique diagonal HiRISE stereo track of observation pair `ESP_037397_1985` and `ESP_037463_1985`. The peripheral $36.84\%$ NoData cells are standard non-rendered margins outside the sensor swath.

---

## 5. Absolute Path and Manifest Audit Findings

A full text scan of metadata files extracted from the bundle identified the following embedded absolute path references:

1. **`manifest.json` (Line 18):**
   `"file": "E:\\DATASETS\\_phase2\\jezero_aoi_v2.tif"`
2. **`validation/*.json` (14 Route Fixtures):**
   `"dem_path": "E:\\DATASETS\\_phase2\\jezero_aoi_v2.tif"`
3. **`validation/unit_test_anchors.json`:**
   References `E:\DATASETS\gdal_env\...` and `E:\DATASETS\_phase2\...` in recorded terminal command strings.

### Impact and Portability Analysis:
- **Runtime Services:** Zero backend services parse these strings to locate the raster. In production, backend services load rasters from configured relative data paths or `$VYOMPATH_DATA_DIR`.
- **Validation Fixtures:** Automated tests in `test_fixture_reproducibility.py` fall back to `os.environ.get("VYOMPATH_DEM_PATH")` and cleanly skip if the raster is not found.
- **Portability Resolution:** During build deployment, Mayank Sharma will set `$VYOMPATH_DATA_DIR` pointing to the staged bundle root (`./data/`).

---

## 6. Discrepancy & Severity Evaluation

- **Dimensional Mismatches:** 0
- **Data Type Mismatches:** 0
- **Projection Mismatches:** 0
- **Raster Readability Failures:** 0
- **Severity Assessment:** **NONE.** The primary metric DTM is 100% verified and ready for backend pathfinding service integration.

---

## 7. Final Verification Status

**`STATUS: VERIFIED`**

The primary DTM `jezero_aoi_v2.tif` is authentic, uncorrupted, and mathematically conformant with NASA/USGS PDS standards.
