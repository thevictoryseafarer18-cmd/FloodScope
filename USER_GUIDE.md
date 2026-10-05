# FloodScope user guide

FloodScope is a **screening prototype** for comparing pre/post flood satellite data and checking possible OSM asset exposure and road connectivity. It is not a warning system, field survey or safe-route authority.

## 1. Start the dashboard

From the project folder:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). The first dashboard view is in **SYNTHETIC PREVIEW** mode. Its radar-like pixels, roads, buildings and settlement names are invented to demonstrate the interface. **Do not use or cite those preview metrics as real Trishuli results.**

## 2. Run an end-to-end Copernicus analysis

Choose **Run an analysis → Fetch raw satellite data from Copernicus**.

### Before clicking Run

1. **Set up CDSE access.** Create a Copernicus Data Space OAuth client. Enter its client ID and secret in the app, or copy `.env.example` to `.env` and set `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`. Never publish real credentials.
2. **Draw/select the AOI bbox** using WGS84 longitude/latitude: west, south, east, north. The prefilled Nepal bbox is only a placeholder; confirm a study area from an approved source. Keep the AOI modest or split it into tiles if the request is too large.
3. **Set the flood date.** The case-study form defaults to `2026-08-26` based on the supplied challenge brief. For other judge-selected events, replace it.
4. **Choose a pre-event OSM snapshot.** It must be strictly earlier than the flood date. For the challenge's Trishuli case, the supplied brief identifies `2026-07-27`; the form uses that date by default for the August 26 event. Do not substitute current/post-event edits.
5. Decide whether to try **Sentinel-2**. Leave enabled if you want optical corroboration; clouds may leave no usable S2 pixels. Sentinel-1 remains the primary cloud-robust input.
6. Set the OSM route buffer. A larger padded context can help include roads to a nearby town/hospital just outside the image AOI. It increases query size.

Click **Fetch, map and build the brief**. The app searches for a Sentinel-1 pre/post pair on the **same relative orbit and direction**, excludes acquisitions dated on the event day to avoid timing ambiguity, and prefers a 12-day pair separation. If it cannot verify a matching pair, it stops rather than compare incompatible tracks. Wait for the map to load; inspect selected product IDs, dates, orbit, pixel size and OSM date in the provenance panel.

### Successful output

The dashboard switches from the synthetic banner to **ANALYSIS OUTPUT**. It shows:

- a grayscale post-event Sentinel-1 VV layer;
- gold **new-water candidates** from pre/post change, optionally including optical candidates;
- rose **surface-change watch** patches that may be debris or another surface change;
- OSM road, building, settlement, town/hospital and bridge overlays;
- map-derived asset-overlap and settlement-connectivity metrics;
- the bilingual map-facts-only copilot and a generated one-page brief.

Treat all results as candidate indicators. A pixel overlap does not prove a building was damaged or a road/bridge failed.

## 3. Run using prepared data instead

Choose **Run an analysis → Upload co-registered GeoTIFFs + pre-event OSM GeoJSON**.

Required files:

- **Before and after Sentinel-1 GeoTIFF:** band 1 = VV, band 2 = VH, optional band 3 = data mask. The pair must have identical dimensions, CRS and affine transform. Use a projected CRS such as UTM.
- **Pre-event OSM GeoJSON:** a `Feature` or `FeatureCollection` in WGS84 with OSM tags in `properties.tags` (or flattened tag properties). Include `building`, `highway`, `bridge`, `place`, and hospital tags where available. Verify the snapshot date yourself.
- Enter an event date and a strictly earlier snapshot date. Select S1 units: `linear` for linear backscatter power, `db` for decibels, or `auto` only when you know the file's value range.

Optional Sentinel-2:

- Upload both before and after files or neither.
- band 1 = Green/B03, band 2 = NIR/B08, band 3 = SCL class, optional band 4 = data mask.
- Both files must already be aligned to the Sentinel-1 grid. This prototype will not silently resample uploaded rasters.

Click **Analyze uploaded layers**. If an input has a different grid, missing CRS or invalid date order, fix it upstream and re-upload.

## 4. Ask the copilot

On **Situation dashboard**, try questions like:

- “How much new water is mapped?”
- “Which settlements may be cut off?”
- “How many bridges overlap the water layer?”
- “कुन बस्ती सडकबाट अलग हुन सक्छ?”

Choose English or Nepali, then click **Ask the map**. This is a bounded intent router with fixed responses, not a general-purpose chatbot. It reads values only from the current map result and abstains on unsupported questions; it does not infer casualties, population, safe routes or structural condition.

## 5. Download the outputs

Use the export controls under the map:

- **Situation report · Markdown:** one-page brief in English or Nepali, with required attributions and limitations.
- **Analysis · JSON:** input metadata, metrics, road-network summary and layers.
- **Layers · GeoJSON:** candidate polygons and OSM overlay features.
- **Water mask · GeoTIFF:** one-band raster where `1` indicates a water candidate and `0` is background.

The command-line path additionally writes a surface-change mask:

```bash
python scripts/run_analysis.py \\
  --before before_s1.tif --after after_s1.tif --osm osm_pre_event.geojson \\
  --event-date 2026-08-26 --snapshot-date 2026-07-27 --scale linear --out results/
```

## 6. Understand the indicators

- **New-water candidate area:** pixels meeting a transparent SAR threshold, plus optional S2 candidates. It is not a surveyed flood boundary.
- **Surface-change watch:** significant VV/VH change not already labeled water. Debris is one possibility; this layer is deliberately not named “debris damage.”
- **Buildings/roads/bridges overlapping water:** OSM features intersecting the candidate area. Counts can miss unmapped features and are not structural assessments.
- **Potentially cut-off settlement:** a mapped village/hamlet that had a route to a mapped town/hospital in the baseline road graph but loses all such routes after water-overlap edges are removed. “Not assessed” means the baseline graph or destination was insufficient.
- **Sentinel-2 corroboration:** cloud/SCL-filtered NDWI change. No optical result can mean clouds/no suitable acquisition, not “no flood.”

## 7. EMSR927 case-study comparison

EMSR927 is **reference-only**. It must not be used to create, tune or feed the detection map. After saving an independent FloodScope mask, a reviewer can score it offline with a supplied reference-only GeoJSON:

```bash
python scripts/compare_reference.py \\
  --mask results/water_candidate_mask.tif \\
  --reference reviewer_reference_only.geojson \\
  --out results/reference_score.json
```

The script calculates pixel IoU, precision, recall and F1 after rasterizing the reference onto the result grid. Keep a record of the reference legend, CRS, resolution, AOI and rasterization rule. These metrics do not score structural damage or rescue usefulness. The starter project contains no EMSR927 layer or real case-study score.

## 8. Safety, data rules and troubleshooting

- Never report the synthetic preview as Nepal/Trishuli evidence.
- Never use EMSR927, UNOSAT, other published damage maps or post-event OSM edits as detection inputs.
- No satellite revisit can warn minutes ahead of a sudden glacier collapse. Clouds, steep terrain/radar shadow, thresholds and incomplete OSM can create misses and false alarms.
- Verify possible cut-offs with current local information. This graph cannot certify a safe route or bridge.
- **No CDSE token:** create/configure an OAuth client; test credentials without sharing them.
- **No same-track pair:** confirm bbox/date, product coverage and orbit metadata; try a valid adjacent date or smaller AOI. Do not use different orbits as a pixel-wise pair.
- **Request too large/ohsome timeout:** shrink or tile the AOI; retain enough padded road context to reach mapped services.
- **Bad/misaligned uploads:** reproject/resample both dates to one projected CRS, identical transform and dimensions; preserve S1 band units/order and S2 SCL class values.

For data credits, limitations and technical details, see `README.md` and `REPORT.md`.
