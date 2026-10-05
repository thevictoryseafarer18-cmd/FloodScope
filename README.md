# FloodScope — Track B flood-damage screening prototype

**A transparent, multimodal map dashboard for screening flood extent, potential asset exposure and settlement access from satellite change plus pre-event OSM.** It is an educational prototype, not an operational early-warning or emergency-dispatch system.

> **Important data status:** the supplied `Space Track.pdf` is a challenge brief, not a raw-data package. This repository includes a visibly labelled **synthetic fixture** to exercise the dashboard. It does **not** contain real August 2026 Trishuli Sentinel observations, a verified event AOI, field damage observations, or EMSR927 validation scores. Do not describe the preview numbers as case-study results.

## What it does

1. **Where might water have expanded?** Compares aligned Sentinel-1 VV/VH in dB. A transparent threshold marks new, dark post-event water candidates; large non-water backscatter changes appear in a separate surface-change watch layer. Optional Sentinel-2 L2A Green/NIR/SCL imagery adds a cloud-masked NDWI water candidate. SAR/optical overlap is recorded as corroboration.
2. **What may be exposed?** Intersects the candidate layers with dated, pre-event OSM buildings, highway ways and bridge tags. Overlap means *potential exposure*, not confirmed damage.
3. **Who may be cut off?** Splits OSM roads into graph edges, removes edges that intersect the water-candidate mask, snaps mapped village/hamlet and town/hospital points to the road graph, and checks connectivity. The output is *potentially isolated* only when no mapped town/hospital remains reachable. The route graph is a screening proxy, not a safe-route product.
4. **Evidence-bounded copilot:** fixed English/Nepali templates and a small intent router answer only from the analysis result object. No generative model is called; unsupported questions abstain. Thus every metric in a brief comes from the map result or input metadata. **No training dataset is used** for this selected AI component.

## User guide and challenge analysis

See [`USER_GUIDE.md`](USER_GUIDE.md) for step-by-step setup, online/offline workflows, reading metrics, downloads, copilot examples, and troubleshooting. [`CHALLENGE_ANALYSIS.md`](CHALLENGE_ANALYSIS.md) maps each PDF requirement to an implementation choice and lists the data still needed for a real case study.

## Run the dashboard

Python 3.10+ is recommended.

```bash
cd floodscope
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

The first screen opens in **SYNTHETIC PREVIEW** mode. It is generated deterministically by `floodscope/demo.py`; the invented river, buildings, villages, water stripe and map values are not observations of Nepal. A matching one-page preview brief is saved at `reports/synthetic_preview_brief.md`. Use the **Run an analysis** tab for actual input data.

### Option A — raw-to-map acquisition through Copernicus Data Space

The end-to-end online path uses the CDSE Sentinel Hub Catalog and Process APIs plus the ohsome API. Create a CDSE OAuth client and either enter its credentials in the dashboard or add them to a local `.env` file:

```dotenv
CDSE_CLIENT_ID=your-oauth-client-id
CDSE_CLIENT_SECRET=your-oauth-client-secret
```

Then:

1. Enter a WGS84 bbox (`west,south,east,north`) and flood date. The Trishuli starter bbox is only a placeholder—replace it with the actual AOI selected for the study.
2. Confirm an OSM snapshot strictly before the flood. The challenge brief identifies **2026-07-27** as the available pre-event snapshot for the **2026-08-26** case.
3. The catalogue selector searches the pre/post windows, requires matching Sentinel-1 relative orbit and direction, excludes ambiguous event-day scenes, and prefers a 12-day pair separation. It then requests both scenes onto the same UTM grid with terrain correction and exports VV, VH and data mask.
4. If requested, the app looks for lower-cloud Sentinel-2 scenes before/after the event and masks cloud/shadow classes with SCL. It continues as SAR-led if a clear optical pair is unavailable; the reason is shown.
5. OSM geometries are retrieved at the selected **pre-event time** through ohsome. A padded OSM query includes nearby road/service context; exposure counts are restricted to features intersecting the imagery footprint.
6. The dashboard reports the selected product IDs, acquisition dates, relative orbit, resolution and OSM snapshot so reviewers can audit inputs.

If CDSE does not return a qualifying pair, the app stops rather than comparing different tracks. Check the event date, bbox, data access and catalogue coverage. A large AOI can be split into smaller runs.

### Option B — upload prepared data

Upload co-registered GeoTIFFs and a GeoJSON FeatureCollection in WGS84:

- Sentinel-1 stack order: **band 1 VV, band 2 VH, optional band 3 dataMask**. Choose `linear`, `db`, or `auto` in the UI. CDSE Process API returns linear power.
- Optional Sentinel-2 stack order: **band 1 Green/B03, band 2 NIR/B08, band 3 SCL, optional band 4 dataMask**.
- Pre/post rasters must share the same shape, affine transform and **projected** CRS; optional S2 must already be aligned to the S1 grid. FloodScope refuses unaligned upload pairs instead of silently warping them.
- OSM GeoJSON must be an extract from a date before the event. Do not upload current/post-event OSM for detection.

Command-line processing is available once data are prepared:

```bash
python scripts/run_analysis.py \\
  --before before_s1.tif --after after_s1.tif --osm osm_pre_event.geojson \\
  --event-date 2026-08-26 --snapshot-date 2026-07-27 --scale linear --out results/
```

Add `--before-s2 s2_pre.tif --after-s2 s2_post.tif` to supply an aligned optical pair. The output folder contains JSON, GeoJSON, water/change mask GeoTIFFs and an English Markdown situation brief.

## Project map

```text
app.py                           Streamlit dashboard and upload/online workflows
floodscope/core.py               SAR/optional optical masks, asset overlay, road graph
floodscope/sources.py            CDSE catalog/process + dated ohsome acquisition
floodscope/report.py             bilingual, map-facts-only copilot and brief
floodscope/demo.py               synthetic dashboard fixture (not Nepal data)
floodscope/io.py                 GeoTIFF/GeoJSON readers and exports
scripts/run_analysis.py          command-line processing for prepared inputs
scripts/compare_reference.py     isolated offline validation only
reports/emsr927_comparison_template.csv
tests/test_core.py               smoke/guardrail tests
```

## Data rules and validation separation

- **Detection inputs:** Sentinel-1, optional Sentinel-2, Copernicus DEM (through Sentinel Hub S1 terrain correction), and OSM at a timestamp before the event. Use the date field and retain product IDs/metadata.
- **Reference-only data:** Copernicus EMSR927, UNOSAT and other published damage maps are **not fetched or consumed by the live detector**. `scripts/compare_reference.py` is an offline scoring utility that accepts a reviewer-provided reference polygon only after a system mask has been saved. Do not pass reference features to `analyze()` or tune thresholds on the held-out judge AOI.
- The supplied brief requests a comparison with EMSR927. A valid score cannot be supplied here because no raw satellite scene, verified event footprint or reference layer was included. Populate `reports/emsr927_comparison_template.csv` only after a reproducible run and independent reference review. Record the reference legend, AOI, CRS, scale and rasterization rule; IoU is not a structural-damage score.
- Train/test geography should be separated if a learned segmentation model is added later. The current copilot choice uses no satellite training set and makes no model-generalization claim.

### Offline-only reference comparison (reviewer-provided file)

```bash
python scripts/compare_reference.py \\
  --mask results/water_candidate_mask.tif \\
  --reference reviewer_reference_only.geojson \\
  --out results/reference_score.json
```

The script reports pixel IoU, precision, recall and F1 after rasterizing the reference onto the system grid. It must be run as **validation only**, not as an inference step. The result depends on map legend, georegistration and all-touched rasterization choices.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover event-date separation, same-track pairing, a synthetic detection fixture and the pre-event snapshot guard.

## Required attribution and citations

Include these attributions in every submission/report (the app-generated situation report includes them):

> Contains modified Copernicus Sentinel data 2026.
>
> Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
>
> © OpenStreetMap contributors.

OSM data are subject to the Open Database License (ODbL); a modified OSM database, if redistributed, must remain under ODbL. This repository does not redistribute an OSM extract.

**Dataset citations:** no Kuro Siwo or Sen1Floods11 samples are used by this implementation. If adding Kuro Siwo, credit/cite **Bountos et al. (2024), Kuro Siwo** and follow the dataset repository/paper licence terms. If adding Sen1Floods11, cite **Bonafilia et al. (2020), Sen1Floods11, CVPR Workshops** and review the original repository's licensing conditions before use. Neither is part of the current model or demo.

Reference-map attribution, when a validation layer is actually used:

> European Union, Copernicus Emergency Management Service data.

Official references and services:

- Copernicus Data Space APIs: <https://dataspace.copernicus.eu/analyse/apis>
- CDSE STAC catalogue: <https://documentation.dataspace.copernicus.eu/APIs/STAC.html>
- CDSE Sentinel-1 GRD processing: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html>
- CDSE Sentinel Hub Processing API: <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process.html>
- ohsome API: <https://api.ohsome.org/> (OSM historical snapshots)
- Kuro Siwo: <https://github.com/Orion-AI-Lab/KuroSiwo>
- Sen1Floods11: <https://github.com/cloudtostreet/Sen1Floods11>
- Copernicus EMS mapping: <https://mapping.emergency.copernicus.eu>

## Limitations / responsibility

This prototype cannot warn of a sudden glacier collapse between satellite passes; identify people, casualties or missing persons; confirm a building's structural integrity; distinguish every flood/debris/landslide/soil-moisture change; certify road or bridge passability; or guarantee the nearest safe hospital. Radar geometry and Himalayan relief, clouds, image timing, thresholds, raster resolution and OSM completeness can all lead to misses and false alarms. It requires human review and field confirmation. Do not include images of victims in demonstrations; none are included in this project.
