# VYOMPATH — Phase 2: Regional Tile Integrity & Inventory Report

**Milestone Event:** NASA Space Apps Challenge 2026 &mdash; Build Day (Session E1)  
**Date:** November 14, 2026 (Simulated Build Day)  
**Lead Author:** Shyam Sharma (Data & GIS Lead, Team NAKSHATRA X)  
**Reviewers:** Mayank Sharma (API & Cloud Lead), Arya Tiwari (Map & OpenLayers Lead)  
**Verification Target:** Regional Tile Grid Packages (v1.6 Data Bundle)  
**Final Status:** **`VERIFIED`**  

---

## 1. Executive Summary

As part of Phase 2 verification, the complete regional tile inventory extracted from [`vyompath-demo-bundle-v1.6.zip`](file:///E:/DATASETS/_phase18/vyompath-demo-bundle-v1.6.zip) into an isolated directory was independently audited, validated, and decoded.

Every single one of the **2,380 regional PNG image tiles** was loaded and decoded through image processing libraries. **Zero corrupted images, zero zero-byte files, and zero duplicate paths were found.** All tile dimensions are uniformly $256 \times 256\text{ pixels}$. Basemap layers are 4-channel `RGBA` and hillshade layers are 2-channel `LA`, both featuring transparent NoData margins outside the active HiRISE swaths.

---

## 2. Extraction & Audit Commands Executed

The extraction and verification procedures were conducted non-destructively:

1. **Extraction Target Directory:** `E:\DATASETS\_audit_phase2_v16` (isolated directory outside project repository; verified non-existent prior to execution).
2. **Decompression Execution:** Full archive extracted using Python `zipfile` module.
3. **PNG Decoding Execution:**
   - Every file was opened and decoded via Pillow:
     ```python
     with Image.open(tile_path) as im:
         im.verify() # Validates PNG chunk integrity and signature
     with Image.open(tile_path) as im:
         im.load()   # Fully decompresses image raster bytes
     ```
4. **TileJSON Structural Validation:** Parsed and validated via Python `json` parser against Slippy Map XYZ standards.

---

## 3. Regional Tile Inventory by Zoom Level

The actual tile counts across regions, layers, and zoom levels match the authorized Phase 18 / Gate G2 specifications with 100% precision:

### 3.1 Detailed Tile Count Matrix

| Region | Layer | Zoom Level | Shipped Tiles | Bounding Box Grid | Omitted Exterior Cells ("Holes") | Color Mode | Image Dimensions | Zero-Byte Files | Corrupted Files |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Jezero** | Basemap | `z12` | 18 | 20 | 2 | `RGBA` | $256 \times 256$ | 0 | 0 |
| **Jezero** | Basemap | `z13` | 50 | 54 | 4 | `RGBA` | $256 \times 256$ | 0 | 0 |
| **Jezero** | Basemap | `z14` | 184 | 216 | 32 | `RGBA` | $256 \times 256$ | 0 | 0 |
| **Jezero** | Basemap | `z15` | 678 | 805 | 127 | `RGBA` | $256 \times 256$ | 0 | 0 |
| **Jezero Basemap Subtotal** | &mdash; | `z12–z15` | **930** | **1,095** | **165** | `RGBA` | $256 \times 256$ | **0** | **0** |
| **Jezero** | Hillshade | `z12` | 18 | 20 | 2 | `LA` | $256 \times 256$ | 0 | 0 |
| **Jezero** | Hillshade | `z13` | 50 | 54 | 4 | `LA` | $256 \times 256$ | 0 | 0 |
| **Jezero** | Hillshade | `z14` | 184 | 216 | 32 | `LA` | $256 \times 256$ | 0 | 0 |
| **Jezero** | Hillshade | `z15` | 678 | 805 | 127 | `LA` | $256 \times 256$ | 0 | 0 |
| **Jezero Hillshade Subtotal** | &mdash; | `z12–z15` | **930** | **1,095** | **165** | `LA` | $256 \times 256$ | **0** | **0** |
| **Syrtis** | Basemap | `z12` | 17 | 18 | 1 | `RGBA` | $256 \times 256$ | 0 | 0 |
| **Syrtis** | Basemap | `z13` | 55 | 72 | 17 | `RGBA` | $256 \times 256$ | 0 | 0 |
| **Syrtis** | Basemap | `z14` | 188 | 242 | 54 | `RGBA` | $256 \times 256$ | 0 | 0 |
| **Syrtis Basemap Subtotal** | &mdash; | `z12–z14` | **260** | **332** | **72** | `RGBA` | $256 \times 256$ | **0** | **0** |
| **Syrtis** | Hillshade | `z12` | 17 | 18 | 1 | `LA` | $256 \times 256$ | 0 | 0 |
| **Syrtis** | Hillshade | `z13` | 55 | 72 | 17 | `LA` | $256 \times 256$ | 0 | 0 |
| **Syrtis** | Hillshade | `z14` | 188 | 242 | 54 | `LA` | $256 \times 256$ | 0 | 0 |
| **Syrtis Hillshade Subtotal** | &mdash; | `z12–z14` | **260** | **332** | **72** | `LA` | $256 \times 256$ | **0** | **0** |
| **TOTAL REGIONAL TILES** | &mdash; | &mdash; | **2,380** | **2,854** | **474** | &mdash; | $256 \times 256$ | **0** | **0** |

---

## 4. Tile Coordinate Extents and Spatial Envelopes

The XYZ coordinate boundaries of the shipped tiles were verified:

### Jezero Crater AOI (`tiles/jezero-aoi-v2-1/`)
- **`z12`:** $X \in [5858 \dots 5861]$ (4 columns), $Y \in [1627 \dots 1631]$ (5 rows) &rarr; 18 tiles
- **`z13`:** $X \in [11717 \dots 11722]$ (6 columns), $Y \in [3254 \dots 3262]$ (9 rows) &rarr; 50 tiles
- **`z14`:** $X \in [23434 \dots 23445]$ (12 columns), $Y \in [6508 \dots 6525]$ (18 rows) &rarr; 184 tiles
- **`z15`:** $X \in [46868 \dots 46890]$ (23 columns), $Y \in [13016 \dots 13050]$ (35 rows) &rarr; 678 tiles

### Syrtis Major Sample (`tiles/syrtis-1/`)
- **`z12`:** $X \in [5881 \dots 5883]$ (3 columns), $Y \in [1644 \dots 1649]$ (6 rows) &rarr; 17 tiles
- **`z13`:** $X \in [11762 \dots 11767]$ (6 columns), $Y \in [3288 \dots 3299]$ (12 rows) &rarr; 55 tiles
- **`z14`:** $X \in [23524 \dots 23534]$ (11 columns), $Y \in [6577 \dots 6598]$ (22 rows) &rarr; 188 tiles

### Explanation of Missing XYZ Coordinates ("Tile Holes")
The HiRISE stereo ground track forms an oblique diagonal swath across Mars. Cells located within the rectangular bounding box that fall completely outside the valid data polygon were intentionally masked out at generation time (`shipped = bbox_count - hole_count`). This represents intended engineering design rather than missing data.

---

## 5. Tile Directory Structure & URL Specifications for Arya Tiwari

### 5.1 On-Disk Directory Structure
```text
tiles/
├── jezero-aoi-v2-1/
│   ├── tiles.json
│   ├── basemap/
│   │   ├── 12/{x}/{y}.png
│   │   ├── 13/{x}/{y}.png
│   │   ├── 14/{x}/{y}.png
│   │   └── 15/{x}/{y}.png
│   └── hillshade/
│       ├── 12/{x}/{y}.png
│       ├── 13/{x}/{y}.png
│       ├── 14/{x}/{y}.png
│       └── 15/{x}/{y}.png
└── syrtis-1/
    ├── tiles.json
    ├── basemap/
    │   ├── 12/{x}/{y}.png
    │   ├── 13/{x}/{y}.png
    │   └── 14/{x}/{y}.png
    └── hillshade/
        ├── 12/{x}/{y}.png
        ├── 13/{x}/{y}.png
        └── 14/{x}/{y}.png
```

### 5.2 Exact URL Templates for OpenLayers / MapCanvas
Arya's MapCanvas configuration must configure the layer sources using standard Slippy XYZ URL templates:

1. **Jezero Basemap Layer:**  
   `tiles/jezero-aoi-v2-1/basemap/{z}/{x}/{y}.png`  
   *Supported Zoom Range:* `minZoom: 12`, `maxZoom: 15`
2. **Jezero Hillshade Layer:**  
   `tiles/jezero-aoi-v2-1/hillshade/{z}/{x}/{y}.png`  
   *Supported Zoom Range:* `minZoom: 12`, `maxZoom: 15`
3. **Syrtis Major Basemap Layer:**  
   `tiles/syrtis-1/basemap/{z}/{x}/{y}.png`  
   *Supported Zoom Range:* `minZoom: 12`, `maxZoom: 14`
4. **Syrtis Major Hillshade Layer:**  
   `tiles/syrtis-1/hillshade/{z}/{x}/{y}.png`  
   *Supported Zoom Range:* `minZoom: 12`, `maxZoom: 14`

**Tile Scheme:** Standard Slippy Map XYZ (Top-Left origin, $X$ increases East, $Y$ increases South). OpenLayers `ol.source.XYZ` handles this natively without `{-y}` inversion.

---

## 6. TileJSON Metadata Validation

Both TileJSON metadata files were audited:
- `tiles/jezero-aoi-v2-1/tiles.json` ($13,980\text{ bytes}$)
- `tiles/syrtis-1/tiles.json` ($8,639\text{ bytes}$)

### Findings:
1. **JSON Syntax:** 100% valid JSON syntax.
2. **Layer Specifications:** Correctly documents 4 channels for `basemap` (RGBA) and 2 channels for `hillshade` (LA) with `transparent_nodata: true`.
3. **Tile Counts & Holes:** Exactly mirrors the shipped files and hole counts on disk.
4. **CRS Definition:** Mars 2000 Equirectangular (`MARS:2000`, `+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +R=3396190 +units=m +no_defs`).
5. **Tile Size:** Explicitly specifies `256 x 256` pixels.

---

## 7. Discrepancy & Anomaly Evaluation

- **Corrupted Tiles:** 0
- **Missing Declared Tiles:** 0
- **Zero-Byte Tiles:** 0
- **Unexpected Zoom Levels:** 0 (Zoom level 16 is completely excluded as mandated by Gate G2 Decision D6).
- **Severity Assessment:** **NONE.** All regional tile packages are complete and verified.

---

## 8. Final Verification Status

**`STATUS: VERIFIED`**

All 2,380 regional PNG tiles across Jezero and Syrtis are completely intact, readable, correctly structured, and ready for deployment to the OpenLayers frontend.
