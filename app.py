from __future__ import annotations

from datetime import date
import json
import os

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from pyproj import CRS, Transformer
from rasterio.transform import Affine
from shapely.geometry import GeometryCollection, LineString, MultiLineString, Point, Polygon, shape
from shapely.ops import transform as geom_transform

from floodscope.core import analyze
from floodscope.demo import make_demo_result
from floodscope.io import mask_geotiff, read_geotiff, read_geojson, result_geojson, result_json
from floodscope.report import ATTRIBUTIONS, answer_question, build_report
from floodscope.sources import fetch_ohsome_snapshot, fetch_satellite_pair

load_dotenv()
st.set_page_config(page_title="FloodScope | Flood damage from space", page_icon="🌊", layout="wide")

st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: #07111b; color: #e7edf2; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px; }
[data-testid="stMetric"] { background: linear-gradient(145deg,#101e2b,#0b1723); border: 1px solid #203345; padding: 14px 16px; border-radius: 14px; }
[data-testid="stMetricLabel"] { color: #9db0c0; }
[data-testid="stMetricValue"] { color: #f5f7f9; }
div.stButton > button { border-radius: 10px; border: 1px solid #e6a23c; background: #d98e23; color: #101820; font-weight: 700; }
div.stButton > button:hover { border-color: #f4bc5a; background: #e8a53a; color: #06111a; }
section[data-testid="stSidebar"] { background: #091521; border-right: 1px solid #203345; }
.floodscope-kicker { color: #efa83e; letter-spacing: .16em; font-size: .75rem; font-weight: 800; }
.floodscope-title { font-size: clamp(2.1rem,4vw,3.55rem); line-height: 1.03; font-weight: 800; letter-spacing: -.04em; margin: .35rem 0 .55rem; color: #f4f7f8; }
.floodscope-sub { color: #a8bac8; max-width: 900px; font-size: 1.02rem; }
.demo-banner { border: 1px solid #c98532; background: rgba(174,100,21,.14); color: #ffd28c; padding: 12px 16px; border-radius: 12px; font-weight: 700; margin: .8rem 0 1rem; }
.live-banner { border: 1px solid #248c79; background: rgba(36,140,121,.12); color: #9ee5d5; padding: 12px 16px; border-radius: 12px; font-weight: 700; margin: .8rem 0 1rem; }
.small-note { color: #8fa5b6; font-size: .88rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Building clearly-labeled synthetic preview…")
def demo_result():
    return make_demo_result()


def _fc(result: dict, key: str) -> list[dict]:
    return ((result.get("layers") or {}).get(key) or {}).get("features", [])


def _add_geometry_lines(fig, features, name, color, width, result, *, filter_exposure=None, showlegend=True, projected=True):
    internal = result["internal"]
    raster_crs = CRS.from_user_input(internal["crs"])
    from_wgs = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
    inv = ~internal["transform"]
    xs, ys, labels = [], [], []
    for feat in features:
        props = feat.get("properties") or {}
        if filter_exposure is not None and props.get("exposure") not in filter_exposure:
            continue
        geom_json = feat.get("geometry")
        if not geom_json:
            continue
        try:
            g = geom_transform(from_wgs.transform, shape(geom_json))
            if not projected:
                g = geom_transform(lambda x, y, z=None: (inv.a*x + inv.b*y + inv.c, inv.d*x + inv.e*y + inv.f), g)
        except Exception:
            continue
        if isinstance(g, LineString):
            line_geoms = [g]
        elif isinstance(g, MultiLineString):
            line_geoms = list(g.geoms)
        elif isinstance(g, GeometryCollection):
            line_geoms = [part for part in g.geoms if isinstance(part, LineString)]
        else:
            line_geoms = []
        for line in line_geoms:
            coords = list(line.coords)
            xs.extend([p[0] for p in coords] + [None])
            ys.extend([p[1] for p in coords] + [None])
            labels.extend([str(props.get("name") or name)] * len(coords) + [None])
    if xs:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, text=labels, mode="lines", line={"color": color, "width": width},
            name=name, legendgroup=name, showlegend=showlegend,
            hovertemplate="%{text}<extra></extra>",
        ))


def _add_point_features(fig, features, name, color, result, marker_symbol="circle", size=8, text_labels=False, filter_exposure=None, projected=True):
    internal = result["internal"]
    raster_crs = CRS.from_user_input(internal["crs"])
    from_wgs = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
    inv = ~internal["transform"]
    xs, ys, labels, custom = [], [], [], []
    for feat in features:
        props = feat.get("properties") or {}
        if filter_exposure is not None and props.get("exposure") not in filter_exposure:
            continue
        if not feat.get("geometry"):
            continue
        try:
            g = geom_transform(from_wgs.transform, shape(feat["geometry"]))
            p = g if isinstance(g, Point) else g.representative_point()
            if projected:
                px, py = p.x, p.y
            else:
                px = inv.a*p.x + inv.b*p.y + inv.c
                py = inv.d*p.x + inv.e*p.y + inv.f
        except Exception:
            continue
        xs.append(px); ys.append(py)
        labels.append(str(props.get("name") or name))
        custom.append([str(props.get("exposure", "")), str(props.get("network_status", ""))])
    if xs:
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text" if text_labels else "markers",
            text=labels if text_labels else None, textposition="top center",
            marker={"color": color, "size": size, "symbol": marker_symbol, "line": {"color": "#07111b", "width": 1}},
            name=name, customdata=custom, hovertemplate="%{text}<br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
        ))


def make_scene(result: dict, shown: list[str]):
    internal = result["internal"]
    water = internal["water_mask"]
    change = internal["change_mask"]
    after_db = internal["after_vv_db"]
    rows, cols = water.shape
    transform = internal["transform"]
    north_up = abs(transform.b) < 1e-9 and abs(transform.d) < 1e-9 and transform.a > 0 and transform.e < 0
    if north_up:
        xaxis_values = transform.c + (np.arange(cols) + 0.5) * transform.a
        yaxis_values = transform.f + (np.arange(rows) + 0.5) * transform.e
        x_title = f"Easting (m) · {internal['crs']}"
        y_title = "Northing (m)"
        x_range = [float(xaxis_values[0] - transform.a / 2), float(xaxis_values[-1] + transform.a / 2)]
        y_range = [float(yaxis_values[-1] + transform.e / 2), float(yaxis_values[0] - transform.e / 2)]
    else:
        xaxis_values, yaxis_values = np.arange(cols), np.arange(rows)
        x_title, y_title = "Raster column (pixel)", "Raster row (north at top)"
        x_range, y_range = [0, cols], [rows, 0]
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=after_db, x=xaxis_values, y=yaxis_values, colorscale="Greys", zmin=-28, zmax=-4,
        showscale=False, hovertemplate="Post-event VV: %{z:.1f} dB<extra></extra>", name="Sentinel-1 VV",
    ))
    if "Water candidates" in shown and water.any():
        fig.add_trace(go.Heatmap(
            z=np.where(water, 1.0, np.nan), x=xaxis_values, y=yaxis_values,
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(246,171,67,0.76)"]],
            zmin=0, zmax=1, showscale=False, hoverinfo="skip", name="Water candidate",
        ))
    if "Surface change watch" in shown and change.any():
        fig.add_trace(go.Heatmap(
            z=np.where(change, 1.0, np.nan), x=xaxis_values, y=yaxis_values,
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(219,113,151,0.68)"]],
            zmin=0, zmax=1, showscale=False, hoverinfo="skip", name="Surface change",
        ))
    if "Roads" in shown:
        _add_geometry_lines(fig, _fc(result, "roads"), "OSM roads", "#a9bac8", 1.7, result, projected=north_up)
        _add_geometry_lines(fig, _fc(result, "roads"), "Water-overlap road candidate", "#ff685d", 3.4, result,
                            filter_exposure={"water candidate"}, showlegend=False, projected=north_up)
    if "Assets" in shown:
        _add_point_features(fig, _fc(result, "buildings"), "OSM buildings", "#e1e8ec", result, size=5, projected=north_up)
        _add_point_features(fig, _fc(result, "exposed"), "Potential exposure", "#ff7365", result, size=9,
                            filter_exposure={"water candidate", "surface-change watch"}, projected=north_up)
    if "Settlements & services" in shown:
        _add_point_features(fig, _fc(result, "settlements"), "Settlements", "#64c5b0", result,
                            marker_symbol="diamond", size=10, text_labels=True, projected=north_up)
        _add_point_features(fig, _fc(result, "services"), "Town / hospital", "#f4ecb0", result,
                            marker_symbol="star", size=13, text_labels=True, projected=north_up)
    fig.update_layout(
        template="plotly_dark", height=590, margin={"l": 20, "r": 20, "t": 35, "b": 35},
        paper_bgcolor="#0a1520", plot_bgcolor="#0a1520", font={"color": "#d9e4ec"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        xaxis={"title": x_title, "showgrid": False, "zeroline": False, "range": x_range},
        yaxis={"title": y_title, "showgrid": False, "zeroline": False,
               "scaleanchor": "x", "scaleratio": 1, "range": y_range},
    )
    return fig


def show_metrics(result: dict):
    s = result["summary"]
    cols = st.columns(5)
    cols[0].metric("New-water candidates", f"{s['water_candidate_area_ha']:.2f} ha")
    cols[1].metric("Surface-change watch", f"{s['surface_change_watch_area_ha']:.2f} ha")
    cols[2].metric("Buildings in water mask", str(s["buildings_overlapping_water_candidate"]))
    cols[3].metric("Road features in water mask", str(s["road_features_overlapping_water_candidate"]))
    cols[4].metric("Potentially isolated", str(s["potentially_cut_off_settlements"]))


def show_downloads(result: dict, is_demo: bool):
    from floodscope.report import build_report
    st.markdown("#### Export this map-derived brief")
    lang = st.selectbox("Report language", ["English", "Nepali"], key="report_language")
    report_md = build_report(result, lang, is_demo=is_demo)
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("Situation report · Markdown", report_md.encode("utf-8"), file_name="floodscope_situation_report.md", mime="text/markdown")
    c2.download_button("Analysis · JSON", result_json(result), file_name="floodscope_result.json", mime="application/json")
    c3.download_button("Layers · GeoJSON", result_geojson(result), file_name="floodscope_layers.geojson", mime="application/geo+json")
    c4.download_button("Water mask · GeoTIFF", mask_geotiff(result), file_name="water_candidate_mask.tif", mime="image/tiff")
    with st.expander("Preview the generated one-page situation report"):
        st.markdown(report_md)


if "active_result" not in st.session_state:
    st.session_state.active_result = demo_result()
    st.session_state.is_demo = True

st.markdown('<div class="floodscope-kicker">MULTIMODAL AI HACKATHON · TRACK B</div>', unsafe_allow_html=True)
st.markdown('<div class="floodscope-title">Flood damage mapping,<br>from space.</div>', unsafe_allow_html=True)
st.markdown('<div class="floodscope-sub">FloodScope turns co-registered Sentinel-1 change, optional cloud-masked Sentinel-2 evidence and pre-event OpenStreetMap into a transparent rescue-planning screening map.</div>', unsafe_allow_html=True)

active = st.session_state.active_result
is_demo = bool(st.session_state.get("is_demo", False))
if is_demo:
    st.markdown('<div class="demo-banner">SYNTHETIC PREVIEW · invented test pixels and fictional map features — not Trishuli observations, not EMSR927, and not for operational decisions.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="live-banner">ANALYSIS OUTPUT · candidate detections only — verify imagery, OSM snapshot and field conditions before any response decision.</div>', unsafe_allow_html=True)

main_tab, run_tab, method_tab, validation_tab = st.tabs(["Situation dashboard", "Run an analysis", "Method & limitations", "Case-study validation"])

with main_tab:
    show_metrics(active)
    s = active["summary"]
    left, right = st.columns([1.65, 0.85], gap="large")
    with left:
        st.markdown("### Evidence map")
        shown = st.multiselect(
            "Visible layers", ["Water candidates", "Surface change watch", "Roads", "Assets", "Settlements & services"],
            default=["Water candidates", "Surface change watch", "Roads", "Assets", "Settlements & services"],
            key="visible_layers",
        )
        st.plotly_chart(make_scene(active, shown), width="stretch", config={"displaylogo": False})
        if is_demo:
            st.caption("Background: synthetic VV-like test pixels. Gold: invented new-water candidate. Rose: invented surface-change patch. Roads/buildings are fictional test features. This schematic is not a Trishuli observation.")
        else:
            st.caption("Background: post-event Sentinel-1 VV backscatter in dB. Gold: new-water candidate. Rose: large SAR surface-change watch (possible debris or unrelated change). Road/building overlays are pre-event OSM. This map is a screening layer, not an impact confirmation.")
    with right:
        st.markdown("### Rescue questions")
        st.markdown("**Map-facts-only copilot**  ·  deterministic English/Nepali responses; no free-form model can invent a number.")
        question = st.text_input("Ask about water, exposed assets, bridges or cut-off settlements", placeholder="Which settlements may be cut off?", key="copilot_question")
        qlang = st.radio("Answer language", ["English", "Nepali"], horizontal=True, key="copilot_language")
        if st.button("Ask the map", key="ask_map"):
            st.info(answer_question(question, active, qlang))
        st.markdown("### Access screening")
        names = s.get("potentially_cut_off_names", [])
        if names:
            for name in names:
                st.markdown(f"- **{name}** — no remaining route to a mapped town/hospital in the candidate graph")
        elif s.get("settlements_assessed", 0):
            st.success("No settlement in the assessed graph lost all routes to mapped services under the water-overlap proxy.")
        else:
            st.warning("No settlement-to-service route could be assessed from the supplied OSM graph.")
        st.markdown("### Provenance snapshot")
        meta = active.get("metadata", {})
        if meta.get("synthetic_demo"):
            st.write(f"Challenge date label: **{s.get('event_date')}**")
            st.write("Satellite inputs: **synthetic test pixels; no scenes retrieved**")
            st.write("OSM inputs: **fictional features; no dated snapshot retrieved**")
        else:
            st.write(f"Event date: **{s.get('event_date')}**")
            st.write(f"OSM snapshot: **{s.get('osm_snapshot_date')}**")
            pre = meta.get("sentinel1_before", {}) or {}
            post = meta.get("sentinel1_after", {}) or {}
            st.write(f"Sentinel-1 pair: **{str(pre.get('datetime', 'not supplied'))[:10]} → {str(post.get('datetime', 'not supplied'))[:10]}**")
            if meta.get("sentinel1_relative_orbit_matched") is False:
                st.error("Relative-orbit match was not confirmed. Do not interpret this pair pixel by pixel.")
            st.caption(f"Projected grid: {meta.get('crs', 'not supplied')} · approx. {meta.get('pixel_size_m', '—')} m pixels")
    st.divider()
    show_downloads(active, is_demo)

with run_tab:
    st.markdown("### Choose an input path")
    mode = st.radio("Input path", ["Fetch raw satellite data from Copernicus", "Upload co-registered GeoTIFFs + pre-event OSM GeoJSON"], horizontal=True, key="input_mode")
    st.warning("For the August 2026 case study, the PDF supplies the challenge specification but no raw satellite rasters or OSM extract. The starter bbox below is only a user-editable placeholder; it is not a verified EMSR927 event perimeter.")
    if mode.startswith("Fetch"):
        st.markdown("#### End-to-end CDSE acquisition")
        with st.expander("Copernicus OAuth setup", expanded=not bool(os.getenv("CDSE_CLIENT_ID"))):
            st.write("Create an OAuth client in Copernicus Data Space and enter its client ID/secret here, or set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET in a local .env file. Credentials are used only for this run and are not written to the project.")
        default_id = os.getenv("CDSE_CLIENT_ID", "")
        default_secret = os.getenv("CDSE_CLIENT_SECRET", "")
        idcol, secretcol = st.columns(2)
        client_id = idcol.text_input("CDSE client ID", value=default_id, key="cdse_client_id")
        client_secret = secretcol.text_input("CDSE client secret", value=default_secret, type="password", key="cdse_client_secret")
        st.markdown("**AOI bbox in WGS84** — west, south, east, north. Keep the imagery AOI manageable; use a padded OSM network context to include routes to nearby services.")
        c1, c2, c3, c4 = st.columns(4)
        west = c1.number_input("West longitude", min_value=-180.0, max_value=180.0, value=85.00, step=0.01, format="%.4f")
        south = c2.number_input("South latitude", min_value=-80.0, max_value=84.0, value=27.90, step=0.01, format="%.4f")
        east = c3.number_input("East longitude", min_value=-180.0, max_value=180.0, value=85.30, step=0.01, format="%.4f")
        north = c4.number_input("North latitude", min_value=-80.0, max_value=84.0, value=28.15, step=0.01, format="%.4f")
        d1, d2, d3 = st.columns(3)
        event_day = d1.date_input("Flood date", value=date(2026, 8, 26), key="event_date_online")
        default_snapshot = date(2026, 7, 27) if event_day == date(2026, 8, 26) else date.fromordinal(max(date(1970, 1, 1).toordinal(), event_day.toordinal() - 1))
        snapshot_day = d2.date_input("Pre-event OSM snapshot", value=default_snapshot, key="snapshot_date_online")
        include_s2 = d3.checkbox("Try Sentinel-2 if a clear pair exists", value=True)
        b1, b2 = st.columns([1, 3])
        network_buffer = b1.number_input("OSM route buffer (km)", min_value=0, max_value=50, value=10, step=1)
        cloud_max = b2.slider("Sentinel-2 catalogue cloud ceiling (%)", min_value=0, max_value=80, value=50)
        if st.button("Fetch, map and build the brief", type="primary", key="run_cdse"):
            if snapshot_day >= event_day:
                st.error("The OSM snapshot must pre-date the flood date.")
            elif not (west < east and south < north):
                st.error("Enter a valid bbox: west < east and south < north.")
            else:
                try:
                    with st.spinner("Searching CDSE for a same-relative-orbit Sentinel-1 pair, fetching dated OSM and screening the scene…"):
                        fetched = fetch_satellite_pair([west, south, east, north], event_day, client_id, client_secret,
                                                       include_s2=include_s2, cloud_max=cloud_max)
                        osm = fetch_ohsome_snapshot([west, south, east, north], snapshot_day, network_buffer_km=network_buffer)
                        meta = dict(fetched["metadata"])
                        meta["source"] = "Copernicus Data Space Sentinel Hub Process API + ohsome dated OSM snapshot"
                        meta["osm_source"] = "ohsome API /elements/geometry; requested snapshot before event"
                        meta["osm_feature_count"] = len(osm)
                        result = analyze(fetched["before_s1"], fetched["after_s1"], fetched["transform"], fetched["crs"], osm,
                                         event_date=event_day, snapshot_date=snapshot_day, source_scale="linear",
                                         before_s2=fetched.get("before_s2"), after_s2=fetched.get("after_s2"), metadata=meta)
                    st.session_state.active_result = result
                    st.session_state.is_demo = False
                    st.success("Analysis complete. The live dashboard now shows map-derived candidate indicators.")
                    if not result["metadata"].get("optical_sentinel2_used", False):
                        s2_reason = result["metadata"].get("sentinel2", {}).get("reason", "No clear SCL-valid optical pixels remained.")
                        st.info("Sentinel-2 was unavailable or had no usable cloud-masked coverage; the result is Sentinel-1-led. " + str(s2_reason))
                    st.rerun()
                except Exception as exc:
                    st.error(f"Analysis did not complete: {exc}")
                    st.caption("Check OAuth credentials, AOI size, CDSE catalogue coverage, same-track scene availability and the selected pre-event OSM date. No EMS reference map is used by this pipeline.")
    else:
        st.markdown("#### Upload aligned inputs")
        st.markdown("GeoTIFF bands: Sentinel-1 **1=VV, 2=VH, optional 3=dataMask**; optional Sentinel-2 **1=Green/B03, 2=NIR/B08, 3=SCL, optional 4=dataMask**. Before/after S1 files must have identical shape, transform and projected CRS. Both pairs must be on the same grid if optical data are provided.")
        file1, file2 = st.columns(2)
        before_file = file1.file_uploader("Before-event Sentinel-1 GeoTIFF", type=["tif", "tiff"], key="before_s1_file")
        after_file = file2.file_uploader("After-event Sentinel-1 GeoTIFF", type=["tif", "tiff"], key="after_s1_file")
        file3, file4 = st.columns(2)
        before_s2_file = file3.file_uploader("Optional before-event Sentinel-2 GeoTIFF", type=["tif", "tiff"], key="before_s2_file")
        after_s2_file = file4.file_uploader("Optional after-event Sentinel-2 GeoTIFF", type=["tif", "tiff"], key="after_s2_file")
        osm_file = st.file_uploader("Pre-event OSM GeoJSON (from ohsome or a verified pre-event extract)", type=["geojson", "json"], key="osm_file")
        uc1, uc2, uc3 = st.columns(3)
        upload_event = uc1.date_input("Flood date", value=date(2026, 8, 26), key="event_date_upload")
        upload_default_snapshot = date(2026, 7, 27) if upload_event == date(2026, 8, 26) else date.fromordinal(max(date(1970, 1, 1).toordinal(), upload_event.toordinal() - 1))
        upload_snapshot = uc2.date_input("Pre-event OSM snapshot", value=upload_default_snapshot, key="snapshot_date_upload")
        upload_scale = uc3.selectbox("S1 input units", ["auto", "linear", "db"], index=0)
        if st.button("Analyze uploaded layers", type="primary", key="run_upload"):
            if not before_file or not after_file or not osm_file:
                st.error("Upload before/after Sentinel-1 GeoTIFFs and a pre-event OSM GeoJSON.")
            elif upload_snapshot >= upload_event:
                st.error("The OSM snapshot must pre-date the flood date.")
            elif bool(before_s2_file) != bool(after_s2_file):
                st.error("Upload both Sentinel-2 dates or neither.")
            else:
                try:
                    b1_arr, b1_meta = read_geotiff(before_file)
                    a1_arr, a1_meta = read_geotiff(after_file)
                    if b1_meta["transform"] != a1_meta["transform"] or str(b1_meta["crs"]) != str(a1_meta["crs"]) or b1_arr.shape != a1_arr.shape:
                        raise ValueError("Before and after S1 files are not pixel-aligned. Reproject/resample them to one grid before uploading.")
                    optical_pre = optical_post = None
                    if before_s2_file and after_s2_file:
                        optical_pre, smeta0 = read_geotiff(before_s2_file)
                        optical_post, smeta1 = read_geotiff(after_s2_file)
                        if (smeta0["transform"] != b1_meta["transform"] or smeta1["transform"] != b1_meta["transform"] or
                            str(smeta0["crs"]) != str(b1_meta["crs"]) or str(smeta1["crs"]) != str(b1_meta["crs"]) or
                            optical_pre.shape[1:] != b1_arr.shape[1:] or optical_post.shape[1:] != b1_arr.shape[1:]):
                            raise ValueError("Optional S2 files must be pre-aligned to the S1 grid; this prototype does not silently resample uploaded rasters.")
                    features = read_geojson(osm_file)
                    result = analyze(b1_arr, a1_arr, b1_meta["transform"], b1_meta["crs"], features,
                                     event_date=upload_event, snapshot_date=upload_snapshot, source_scale=upload_scale,
                                     before_s2=optical_pre, after_s2=optical_post,
                                     metadata={"source": "Uploaded GeoTIFFs + GeoJSON (user-provided provenance)",
                                               "osm_source": "User-provided; verify that this is a pre-event snapshot", "osm_feature_count": len(features)})
                    st.session_state.active_result = result
                    st.session_state.is_demo = False
                    st.success("Uploaded layers analyzed. The dashboard now shows candidate outputs from those files.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Upload analysis failed: {exc}")

with method_tab:
    st.markdown("### Transparent screening, not a black-box damage claim")
    st.markdown("""
**Primary flood evidence:** Sentinel-1 VV/VH before–after change in dB, with a small median filter. New-water candidates require low post-event VV plus a negative VV change and supporting VH evidence. Optional Sentinel-2 uses a cloud/SCL-masked NDWI increase; the app records radar-only, optical-only and corroborated areas. High-magnitude radar change not meeting the water rule is shown separately as a **surface-change watch** (possible debris, bank erosion, landslide, agriculture or other change).

**Assets:** OSM buildings, roads and bridge tags are intersected with candidate polygons. A pixel overlap means *potential exposure*, not confirmed damage. Building counts are OSM features, not people or buildings independently verified from imagery.

**Access:** OSM road ways are split into short graph edges. Edges crossing the water-candidate mask are removed in a hypothetical post-event graph. Village/hamlet nodes are snapped to the road graph and tested against mapped towns/cities and hospitals. The output is a *potentially isolated* list, not a certified passability route. The graph is simplified and may omit private roads, bridges, footpaths, closures, ferries, elevation constraints and out-of-area destinations.

**AI component:** an evidence-bounded English/Nepali situation-report copilot. It uses an explicit intent router and fixed templates that read only the map result object; it does not call a generative language model. Unsupported questions receive an abstention instead of invented values. No training dataset is used.

**Raw data:** the online path discovers Sentinel-1 GRD candidates through CDSE, selects before/after scenes on the same relative orbit and direction (preferring a 12-day separation), requests co-registered terrain-corrected exports, optionally seeks clear Sentinel-2 L2A scenes, and retrieves OSM from ohsome at a user-selected date before the event.
""")
    st.markdown("### Limitations the team should say aloud")
    st.markdown("""
- A satellite revisit is not a warning system; a glacier collapse can happen between acquisitions. Clouds block optical scenes and can delay usable evidence.
- Steep Himalayan terrain creates radar shadow, layover and geometric effects; terrain correction cannot remove every artifact. Flood thresholds are screening heuristics and have not been trained/calibrated on a Himalayan validation set here.
- SAR change does not uniquely identify water versus wet soil, debris, landslide or vegetation change. The watch layer is intentionally non-specific.
- OSM may omit villages, private tracks, footbridges, roads and hospitals. A road intersecting a candidate pixel is not proof of failure, while a road outside the AOI may be absent from the graph.
- The system has no population, casualty, missing-person, structural-integrity, safe-route or ground-sensor input. It must not be used as a sole basis for evacuation, rescue dispatch or resource allocation.
- This repository contains a synthetic preview only. No real Trishuli measurements or EMSR927 accuracy scores are claimed until raw Sentinel scenes and an independent reference-map comparison are run.
""")

with validation_tab:
    st.markdown("### August 2026 Trishuli case study — validation status")
    st.info("The supplied PDF describes the challenge and the EMSR927 reference, but it contains no raw Sentinel rasters or OSM extract. The app also does not download or ingest EMSR927. Therefore there is no defensible event map, EMSR927 score or field-verified cut-off list in this starter build.")
    st.markdown("""
**Data-rule separation**

- Detection inputs: Sentinel-1, optional Sentinel-2, pre-event OSM via ohsome, and the Copernicus DEM used for terrain correction.
- Reference-only: EMSR927/UNOSAT or other published impact layers. The live pipeline has no code path that fetches them.
- OSM: choose a snapshot strictly before the event (the supplied brief identifies 27 July 2026 for the Trishuli case). The online form defaults to that date for the given event.

**How to complete comparison:** run an event AOI against the raw pre/post imagery; save the water-candidate mask and OSM overlays; then, in an isolated validation session, use `scripts/compare_reference.py` with a reviewer-provided EMSR927 vector layer to compute overlap metrics. Do not feed the reference layer to `analyze()` or use it to tune thresholds on the scored event. Record method, AOI, CRS/resolution and dates beside any metric.

See `reports/emsr927_comparison_template.csv` and `REPORT.md` for the blank scorecard and current limitations. The provided dashboard values are generated from a synthetic fixture and must never be reported as Trishuli results.
""")

st.divider()
st.markdown("<div class='small-note'>Educational prototype · not an operational warning or emergency-dispatch system. No victim imagery is used.\n<br>" + "<br>".join(ATTRIBUTIONS) + "</div>", unsafe_allow_html=True)
