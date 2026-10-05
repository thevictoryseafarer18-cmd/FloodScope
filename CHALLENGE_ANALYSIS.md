# Challenge brief analysis → system decisions

## What was supplied

`Space Track.pdf` is a **problem statement and rules document**. It describes an August 2026 Trishuli flood case, required satellite/OSM inputs, an optional AI component, evaluation criteria, source attributions and the EMSR927 reference-only rule. It does not include raw Sentinel-1/2 images, a verified event footprint, a historical OSM extract, training tiles or an EMSR927 vector layer. Therefore the system can implement the workflow, but cannot honestly calculate real event hectares, damage counts or reference accuracy from the supplied file alone.

## Requirements translated into implementation

| Brief requirement | FloodScope implementation | Status / caveat |
|---|---|---|
| Input area + flood date | Online bbox/date form and upload mode | Starter bbox is explicitly not a verified event footprint |
| Sentinel-1 before/after | CDSE Catalog/Process adapter; VV/VH; orthorectification and Copernicus DEM terrain correction | Requires the user's CDSE OAuth client; stops if a same-track pair cannot be verified |
| Compare same orbit track | Catalog pairing by relative orbit + direction; event-day acquisition excluded; 12-day gap preferred | Selected item metadata is preserved; an exact 12-day pair is preferred, not fabricated if absent |
| Optional Sentinel-2 | Searches for clear L2A scenes; uses SCL masks and NDWI change on the common grid | Optional; cloud or scene availability may leave no valid pixels |
| Buildings, roads, bridges | Dated ohsome OSM geometries before event; building/highway/bridge tags intersected with candidate layers | Counts indicate map overlap, not physical damage |
| Cut-off settlements | Road graph removes candidate-water-overlap edges and tests access to mapped towns/hospitals | Potential isolation only; not a route-safety assessment |
| AI component | Bilingual fact-grounded situation-report copilot | Deterministic templates; no training dataset or generative model; unsupported requests abstain |
| Bonus upstream path | Not implemented in this version | Copernicus DEM is used for SAR terrain correction only; no valley-routing claim |
| EMSR927 case comparison | Separate offline-only polygon scoring script and blank scorecard | No reference layer is included or consumed by detection; real score remains unrun |
| Dashboard + one-page report | Streamlit dashboard, Markdown output in English/Nepali, JSON/GeoJSON/TIFF exports | Synthetic preview is visibly labelled |
| README + demo | README, this analysis, user guide, ≤6-page report and 3-minute demo script | No recorded video or GitHub remote is created in this workspace |
| Limitations + attribution | Generated reports, README and report include constraints and required source credits | No training data used; future training data must be cited if added |

## Data-governance choices

1. The online pipeline requests OSM at a user-supplied timestamp before the event, rather than using current Overpass results. For the supplied Trishuli date it defaults to 2026-07-27, as the brief identifies that as the pre-event snapshot.
2. Sentinel-1 pairing is constrained to the same relative orbit and direction. Cross-track image comparisons are rejected because viewing geometry differs.
3. EMSR927, UNOSAT and other published damage maps are not input to `analyze()` and are not fetched by the detector. The optional comparison script is a separate reviewer-run validation utility.
4. Asset and settlement names in the preview are invented. The synthetic fixture exercises the pipeline and interface only; no real Nepal imagery or OSM has been embedded.
5. Every asset, road and settlement conclusion is phrased as a *candidate*, *overlap* or *potential isolation*. Human review and current field information are still necessary.

## Hackathon work still required for a real case-study submission

- Obtain CDSE OAuth credentials; validate the chosen Trishuli AOI and same-relative-orbit scene IDs and times.
- Run the raw-to-map path from Sentinel data and a pre-event OSM snapshot; save source metadata and screenshots.
- Independently acquire EMSR927 reference polygons only for validation, document their legend/scale/georegistration, and fill the scorecard without using them to tune detection.
- Review representative false positives/negatives over unseen Himalayan scenes. The current rule thresholds are a baseline, not a validated model.
- Record the 3-minute demo against an audited run, keep the synthetic banner visible only for the synthetic tour, and state all limitations in Q&A.
