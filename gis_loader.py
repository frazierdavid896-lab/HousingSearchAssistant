from __future__ import annotations

from pathlib import Path

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

LITTLE_ROCK_PARKS_URL = (
    "https://maps.littlerock.gov/server/rest/services/"
    "Parks_Data/MapServer/2/query"
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

    response = requests.get(
        url,
        params=parameters,
        timeout=90,
    )
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


def find_name_column(
    frame: gpd.GeoDataFrame,
    preferred_names: tuple[str, ...],
) -> str | None:
    columns = {
        str(column).lower(): column
        for column in frame.columns
    }

    for candidate in preferred_names:
        if candidate in columns:
            return columns[candidate]

    return None


def normalize_facility_layer(
    frame: gpd.GeoDataFrame,
    facility_type: str,
    preferred_names: tuple[str, ...],
) -> gpd.GeoDataFrame:
    frame = frame.copy()

    name_column = find_name_column(
        frame,
        preferred_names,
    )

    if name_column is None:
        frame["Facility Name"] = facility_type
    else:
        frame["Facility Name"] = (
            frame[name_column]
            .fillna(facility_type)
            .astype(str)
        )

    frame["Facility Type"] = facility_type

    normalized = frame[
        [
            "Facility Name",
            "Facility Type",
            "geometry",
        ]
    ].copy()

    return normalized[
        normalized.geometry.notna()
        & ~normalized.geometry.is_empty
    ].copy()


def load_schools() -> gpd.GeoDataFrame:
    school_names = (
        "name",
        "school_name",
        "sch_name",
        "facility",
        "site_name",
        "campus_name",
        "description",
    )

    public = normalize_facility_layer(
        load_arcgis_layer(PUBLIC_SCHOOLS_URL),
        "Public K-12 School",
        school_names,
    )

    private = normalize_facility_layer(
        load_arcgis_layer(PRIVATE_SCHOOLS_URL),
        "Private K-12 School",
        school_names,
    )

    combined = pd.concat(
        [public, private],
        ignore_index=True,
    )

    return gpd.GeoDataFrame(
        combined,
        geometry="geometry",
        crs="EPSG:4326",
    )


def load_parks() -> gpd.GeoDataFrame:
    park_names = (
        "name",
        "park_name",
        "park",
        "facility",
        "site_name",
        "description",
    )

    parks = normalize_facility_layer(
        load_arcgis_layer(LITTLE_ROCK_PARKS_URL),
        "Public Park",
        park_names,
    )

    return gpd.GeoDataFrame(
        parks,
        geometry="geometry",
        crs="EPSG:4326",
    )


def _read_csv_with_encoding_fallback(path_or_buffer) -> pd.DataFrame:
    """
    Read a CSV exported from Excel or another Windows application.

    Tries UTF-8 first, then common Windows encodings.
    """
    encodings = (
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1",
    )

    last_error = None

    for encoding in encodings:
        try:
            if hasattr(path_or_buffer, "seek"):
                path_or_buffer.seek(0)

            return pd.read_csv(
                path_or_buffer,
                encoding=encoding,
            )

        except UnicodeDecodeError as error:
            last_error = error

    raise ValueError(
        "The daycare CSV could not be decoded. "
        "Save it as CSV UTF-8 in Excel and upload it again."
    ) from last_error


def load_daycares_csv(path_or_buffer) -> gpd.GeoDataFrame:
    """
    Load a verified provider list.

    Required columns:
      name, latitude, longitude

    Optional columns:
      license_status, facility_type, address, city, state, zip, source_date
    """
    frame = _read_csv_with_encoding_fallback(
        path_or_buffer
    )

    required = {"name", "latitude", "longitude"}
    missing = required - set(frame.columns)

    if missing:
        raise ValueError(
            "Daycare CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )

    frame = frame.copy()

    if "license_status" in frame.columns:
        allowed = {
            "active",
            "licensed",
            "registered",
            "open",
        }

        frame = frame[
            frame["license_status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(allowed)
        ].copy()

    frame["latitude"] = pd.to_numeric(
        frame["latitude"],
        errors="coerce",
    )
    frame["longitude"] = pd.to_numeric(
        frame["longitude"],
        errors="coerce",
    )

    frame = frame.dropna(
        subset=["latitude", "longitude"]
    ).copy()

    facility_type = (
        frame["facility_type"]
        .fillna("Licensed Daycare")
        .astype(str)
        if "facility_type" in frame.columns
        else pd.Series(
            ["Licensed Daycare"] * len(frame),
            index=frame.index,
        )
    )

    daycares = gpd.GeoDataFrame(
        {
            "Facility Name": frame["name"].astype(str),
            "Facility Type": facility_type,
        },
        geometry=gpd.points_from_xy(
            frame["longitude"],
            frame["latitude"],
        ),
        crs="EPSG:4326",
    )

    return daycares[
        daycares.geometry.notna()
        & ~daycares.geometry.is_empty
    ].copy()


def load_facilities(
    daycare_source=None,
) -> gpd.GeoDataFrame:
    layers = [
        load_schools(),
        load_parks(),
    ]

    if daycare_source is not None:
        layers.append(
            load_daycares_csv(daycare_source)
        )

    combined = pd.concat(
        layers,
        ignore_index=True,
    )

    return gpd.GeoDataFrame(
        combined,
        geometry="geometry",
        crs="EPSG:4326",
    )
