# 🪐 Digital Terrain Model (DTM) Specification & Pipeline Guide

This directory contains the numerical elevation datasets for VyomPath.
All elevations represent meters relative to the Mars MOLA areoid vertical datum.

---

## 1. Candidate DTM Products

### Primary Candidate: Syrtis Major Shield (`DTEED_089986_1980_081600_1980_A01`)
* **Mission & Instrument:** Mars Reconnaissance Orbiter (MRO) / HiRISE
* **Stereo Pair IDs:** `ESP_089986_1980` & `ESP_081600_1980`
* **Geographic Center:** $17.62^\circ\text{N},\; 78.50^\circ\text{E}$ (Planetocentric)
* **Footprint Bounds:**
  * West: $78.32^\circ\text{E}$, East: $78.68^\circ\text{E}$
  * South: $17.41^\circ\text{N}$, North: $17.83^\circ\text{N}$
* **Pixel Posting (Resolution):** $2.01\text{ meters/pixel}$
* **Raw Size:** $\sim 87\text{ MB}$ (PDS3 IMG / GeoTIFF)
* **NoData Value:** `-32768.0` (indicates areas outside stereo parallax correlation)
* **Data Type:** 32-bit floating point (`Float32`)
* **Source URL:** [HiRISE DTM ESP_089986_1980](https://hirise.lpl.arizona.edu/dtm/ESP_089986_1980)

### Alternate Candidate: Jezero Crater Delta (`DTEEC_023524_1985_023379_1985_U01`)
* **Mission & Instrument:** MRO / HiRISE
* **Stereo Pair IDs:** `ESP_023524_1985` & `ESP_023379_1985`
* **Geographic Center:** $18.38^\circ\text{N},\; 77.53^\circ\text{E}$
* **Pixel Posting:** $1.00\text{ meters/pixel}$
* **Raw Size:** $\sim 700\text{ MB}$ (recommend clipping to region of interest)
* **Source URL:** [HiRISE DTM ESP_023524_1985](https://hirise.lpl.arizona.edu/dtm/ESP_023524_1985)

---

## 2. Coordinate System Standards

* **Horizontal Datum:** Mars 2000 Sphere ($R = 3,396,190.0\text{ m}$)
* **Projection:** Equirectangular (`+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +R=3396190 +units=m +no_defs`)
* **Latitude Convention:** Planetocentric $[-90.0, +90.0]^\circ$
* **Longitude Convention:** East-positive $[-180.0, +180.0)^\circ$
* **Vertical Datum:** Mars MOLA Areoid elevation (meters)

---

## 3. PDS to GeoTIFF Conversion (GDAL)

If working from raw PDS `.IMG` files downloaded from the PDS Geosciences Node or Univ. of Arizona:

```bash
# 1. Translate PDS IMG to uncompressed GeoTIFF
gdal_translate -of GTiff input_dtm.IMG intermediate.tif

# 2. Convert to Cloud-Optimized GeoTIFF with LZW compression
gdal_translate intermediate.tif syrtis_major_dtm.tif -co COMPRESS=LZW -co TILED=YES

# 3. Inspect metadata
gdalinfo syrtis_major_dtm.tif
```

---

## 4. Automated Acquisition & Verification Script

Run `python acquire_dtm.py` in this directory to inspect the local DTM or generate a sample test raster for immediate development.
