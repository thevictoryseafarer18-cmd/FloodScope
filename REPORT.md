# FloodScope — technical report (Track B)

**Status:** executable prototype; the dashboard's bundled scene is synthetic. This report does not claim a real EMSR927 comparison or Trishuli damage count.

## 1. Goal and design

FloodScope accepts an event date and AOI, then produces three map-derived screening outputs: new-water candidates, OSM assets with candidate overlap, and settlements whose modeled road connection to mapped towns/hospitals may be severed. The design prioritizes auditability: every layer has a named rule and source date; uncertain surface change is not called debris by default; map exposure is not called confirmed damage; the route graph is not called a safe route.

The dashboard supports two execution paths. The CDSE path searches Sentinel-1 GRD metadata, pairs acquisitions on the same relative orbit and direction (preferring a 12-day interval), exports both onto the same terrain-corrected UTM grid, optionally requests clear Sentinel-2 L2A data, and fetches OSM through ohsome at a pre-event time. The upload/CLI path accepts pre-aligned GeoTIFFs and a dated OSM GeoJSON. Copernicus EMS/UNOSAT maps are intentionally absent from the detection code path.

## 2. Detection and analysis

### Satellite change

Sentinel-1 input bands are VV and VH linear power or dB. Linear values are converted by `10 log10(power)`. A 3×3 median filter reduces isolated speckle. The baseline water rule requires post-event VV ≤ −14.5 dB, VV change ≤ −2.5 dB, and either low post-event VH or a supporting VH decrease. Small connected components are removed. These are prototype thresholds, not a learned Himalayan classifier.

Large absolute VV/VH changes are a separate **surface-change watch**. That layer can reflect debris or bank change, but also slope movement, wet soil, agriculture, vegetation, radar geometry or unrelated change. It is not silently merged into confirmed flood extent.

Optional Sentinel-2 uses the green–NIR NDWI change with Sentinel-2 Scene Classification Layer cloud/shadow masking. SAR-only, optical-only and corroborated area are kept as separate metrics. If usable optical acquisitions are unavailable, the run continues with radar and records the omission.

### OSM damage proxy

Dated OSM building polygons/points, highway ways and bridge-tagged features are projected to the satellite grid and intersected with candidate polygons. Counts mean OSM features overlapping a candidate area. They do not measure structural integrity, repair status or occupancy. Roads are also split at mapped vertices for the network test; candidate-water intersections are removed only in a hypothetical post-event graph.

### Access proxy

Village/hamlet features are snapped to a nearby graph node. Mapped towns/cities and hospitals are candidate destinations. A settlement is flagged potentially isolated only if it had a baseline path to a mapped destination but no destination remains reachable after candidate road edges are removed. The result records unassessed settlements separately. Missing OSM roads, edge-of-AOI services and geometry errors can change this result.

## 3. AI component and report safety

This build selects the **situation-report copilot** track. It is a compact, deterministic bilingual intent router and template set, not a free-form language model. It accepts supported questions about water area, asset overlap, bridges, surface change and access; otherwise it abstains. Counts and areas are read directly from the result object's metrics. The English and Nepali briefs disclose dates, potential-vs-confirmed language, and limitations. No training dataset is used, so no segmentation accuracy or out-of-region generalization is claimed.

## 4. Case study and evaluation status

The supplied challenge PDF gives the August 2026 event description and identifies EMSR927 as a reference-only comparison. It does not supply raw Sentinel-1/Sentinel-2 rasters, a verified AOI, a pre-event OSM extract, or EMSR927 vector data. CDSE access also requires the user's own OAuth client. Consequently, this repository cannot responsibly report flood hectares, damaged buildings, cut-off settlements or reference-map accuracy for the real event at this stage.

For a valid case study, select a verified AOI; retrieve an S1 before/after same-track pair (record scene IDs and dates); request an OSM snapshot before the event (the brief identifies 2026-07-27); retain optional S2 cloud/SCL metadata; run the app; and save the outputs. Only then, in a separate evaluation step, compare the saved water mask against a reviewer-provided EMSR927 layer. Record the reference legend/class, georegistration, pixel size, AOI and rasterization rule. The offline script reports IoU, precision, recall and F1 for the water mask only. Those metrics are not building-damage or life-safety accuracy. Do not use the reference map to tune thresholds on the held-out event.

The included synthetic fixture is useful for UI and code-path checks only. It is explicitly marked on-screen and in the generated report. Unit tests cover pair matching, event-day exclusion, pre-event snapshot validation and non-empty fixture outputs; they are not a substitute for geospatial accuracy evaluation.

## 5. Limitations and responsible use

- Sentinel revisits are separated by days; this is not a glacier-failure warning system and may not capture peak extent.
- Monsoon clouds limit optical confirmation. Sentinel-1 is cloud-robust but affected by layover, shadow, speckle, incidence angle and topographic distortion.
- The threshold model is not trained or validated on unseen Himalayan scenes; wet ground, river widening, landslides and debris can be confused.
- OSM is incomplete and may not represent informal tracks, private bridges, temporary crossings, closed roads or all health facilities. A mapped road overlap neither proves failure nor rules out failure elsewhere.
- Pixel overlap and graph connectivity are screening indicators. No population, occupancy, casualties, missing people, field reports, structural engineering or live road status are ingested.
- This system must not be the sole basis for evacuation, rescue dispatch, aid allocation or declaring routes safe. Human review and field confirmation are required.

## Attributions

Contains modified Copernicus Sentinel data 2026.

Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

© OpenStreetMap contributors.

No Kuro Siwo or Sen1Floods11 data are used by this implementation. If used in a future segmentation model, cite Bountos et al. (2024) for Kuro Siwo or Bonafilia et al. (2020), CVPR Workshops, for Sen1Floods11 and follow the respective dataset terms. EMS reference attribution, if a review layer is used: “European Union, Copernicus Emergency Management Service data”.
