from __future__ import annotations

import geopandas as gpd
import requests
from config import REQUEST_TIMEOUT, USER_AGENT, WGS84

def arcgis_query(url: str, **overrides) -> gpd.GeoDataFrame:
    params = {
        "where": "1=1", "outFields": "*", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson", "resultRecordCount": 5000,
    }
    params.update(overrides)
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    payload = response.json()
    if "features" not in payload:
        raise RuntimeError(f"Unexpected ArcGIS response: {payload}")
    return gpd.GeoDataFrame.from_features(payload["features"], crs=WGS84)

def normalized_layer(frame: gpd.GeoDataFrame, facility_type: str, source: str, preferred_names: tuple[str,...], confidence: str) -> gpd.GeoDataFrame:
    frame = frame.copy()
    by_lower = {str(c).lower(): c for c in frame.columns}
    name_col = next((by_lower[n] for n in preferred_names if n in by_lower), None)
    frame["Facility Name"] = facility_type if name_col is None else frame[name_col].fillna(facility_type).astype(str)
    frame["Facility Type"] = facility_type
    frame["Source"] = source
    frame["Confidence"] = confidence
    frame["Geometry Type"] = frame.geometry.geom_type
    out = frame[["Facility Name","Facility Type","Source","Confidence","Geometry Type","geometry"]].copy()
    return out[out.geometry.notna() & ~out.geometry.is_empty].copy()
