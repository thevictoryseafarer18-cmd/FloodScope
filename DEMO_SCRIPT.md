# 3-minute demo video script

**Recording note:** show the prominent **SYNTHETIC PREVIEW** label at the start. Do not title the fixture as a real Trishuli map and do not show victim imagery. If a real CDSE run is available, replace the synthetic walk-through only after auditing the acquisition metadata and retain all cautions below.

| Time | Screen / action | Voiceover |
|---|---|---|
| 0:00–0:20 | Open dashboard; pause on synthetic banner. | “FloodScope is a Track B prototype for turning satellite change into a rescue-planning screening map. This first scene is a synthetic UI test fixture—not a Nepal observation and not an EMSR927 result.” |
| 0:20–0:50 | Show five metrics and switch layers on/off. | “The dashboard separates new-water candidates from a broader surface-change watch. It overlays dated OSM roads, buildings and bridges. An overlap is potential exposure, not confirmed damage.” |
| 0:50–1:20 | Click a village/road; ask copilot “Which settlements may be cut off?” | “The access layer removes road edges that intersect candidate water and checks mapped villages against OSM towns and hospitals. The bilingual copilot uses fixed templates and reads every count from the map result; it abstains when a question is outside its evidence.” |
| 1:20–1:55 | Open Run an analysis → CDSE. Show editable bbox, flood date and snapshot date; do not expose any secret. | “For a real run, the user supplies a CDSE OAuth client, an event area and date, then confirms a pre-event OSM snapshot. FloodScope selects Sentinel-1 scenes on one relative orbit and direction, prefers a twelve-day pair, and can add clear Sentinel-2.” |
| 1:55–2:20 | Show upload route and required band order. | “There is also an offline path for co-registered GeoTIFFs and pre-event OSM GeoJSON. The app rejects misaligned rasters rather than pretending a pixel-wise comparison is valid.” |
| 2:20–2:45 | Open Method & limitations and validation tab. | “Steep terrain, clouds, radar geometry, threshold error and incomplete OSM can all mislead. EMSR927 is validation-only; no reference map enters detection. We have not claimed a real case-study score because raw imagery and a verified reference extract are not part of the supplied files.” |
| 2:45–3:00 | Finish on attribution/footer. | “This is an educational screening prototype, not a warning system or a safe-route authority. Field confirmation remains essential. Contains modified Copernicus Sentinel data 2026; © OpenStreetMap contributors.” |
