from __future__ import annotations

import geopandas as gpd
import pandas as pd
import requests

PUBLIC_SCHOOLS_URL = (
    "https://gis.arkansas.gov/arcgis/rest/services/"
    "FEATURESERVICES/Structure/FeatureServer/39/query"
)
PRIVATE_SCHOOLS_URL = (
    "https://gis.arkansas.gov/arcgis/rest/services/"
    "FEATURESERVICES/Structure/FeatureServer/37/query"
)


def load_arcgis_layer(url: str) -> gpd.GeoDataFrame:
    parameters = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": 5000,
    }
    response = requests.get(url, params=parameters, timeout=90)
    response.raise_for_status()
    payload = response.json()
    if "features" not in payload:
        raise RuntimeError(
            "The GIS service returned an unexpected response: "
            f"{payload}"
        )
    return gpd.GeoDataFrame.from_features(
        payload["features"],
        crs="EPSG:4326",
    )


def find_name_column(frame: gpd.GeoDataFrame) -> str | None:
    preferred = (
        "name",
        "school_name",
        "sch_name",
        "facility",
        "site_name",
        "campus_name",
        "description",
    )
    columns = {str(column).lower(): column for column in frame.columns}
    for candidate in preferred:
        if candidate in columns:
            return columns[candidate]
    return None


def normalize_school_layer(
    frame: gpd.GeoDataFrame,
    school_type: str,
) -> gpd.GeoDataFrame:
    frame = frame.copy()
    name_column = find_name_column(frame)

    if name_column is None:
        frame["School Name"] = school_type
    else:
        frame["School Name"] = (
            frame[name_column].fillna(school_type).astype(str)
        )

    frame["Facility Type"] = school_type
    normalized = frame[
        ["School Name", "Facility Type", "geometry"]
    ].copy()

    return normalized[
        normalized.geometry.notna()
        & ~normalized.geometry.is_empty
    ].copy()


def load_schools() -> gpd.GeoDataFrame:
    public = normalize_school_layer(
        load_arcgis_layer(PUBLIC_SCHOOLS_URL),
        "Public K-12 School",
    )
    private = normalize_school_layer(
        load_arcgis_layer(PRIVATE_SCHOOLS_URL),
        "Private K-12 School",
    )
    combined = pd.concat([public, private], ignore_index=True)
    return gpd.GeoDataFrame(
        combined,
        geometry="geometry",
        crs="EPSG:4326",
    )
