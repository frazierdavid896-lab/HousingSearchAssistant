from __future__ import annotations

import geopandas as gpd
import pandas as pd

from config import WGS84
from .schools import load_state_school_points
from .parks import load_city_parks
from .osm import load_osm_polygons


def _add_category(
    layer: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    layer = layer.copy()

    if "Facility Category" in layer.columns:
        return layer

    facility_type = layer["Facility Type"].astype(str)

    layer["Facility Category"] = "OTHER"
    layer.loc[
        facility_type.str.contains(
            "school|education",
            case=False,
            regex=True,
        ),
        "Facility Category",
    ] = "SCHOOL"
    layer.loc[
        facility_type.str.contains(
            "park",
            case=False,
            regex=True,
        ),
        "Facility Category",
    ] = "PARK"
    layer.loc[
        facility_type.str.contains(
            "daycare|childcare|kindergarten",
            case=False,
            regex=True,
        ),
        "Facility Category",
    ] = "DAYCARE"

    return layer


def _geometry_rank(value: str) -> int:
    return 2 if value in {"Polygon", "MultiPolygon"} else 1


def _deduplicate(
    facilities: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    if facilities.empty:
        return facilities

    facilities = facilities.copy()
    facilities["_name_key"] = (
        facilities["Facility Name"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "", regex=True)
    )
    facilities["_geometry_rank"] = (
        facilities["Geometry Type"]
        .fillna("")
        .map(_geometry_rank)
    )

    facilities = facilities.sort_values(
        [
            "Facility Category",
            "_name_key",
            "_geometry_rank",
        ],
        ascending=[True, True, False],
    )

    facilities = facilities.drop_duplicates(
        subset=[
            "Facility Category",
            "_name_key",
            "Source",
            "Geometry Type",
        ],
        keep="first",
    )

    return facilities.drop(
        columns=["_name_key", "_geometry_rank"]
    )


def load_all_facilities(
    bounds: tuple[float, float, float, float],
    daycare_layer: gpd.GeoDataFrame | None = None,
) -> tuple[
    gpd.GeoDataFrame,
    list[str],
    dict[str, bool],
]:
    layers: list[gpd.GeoDataFrame] = []
    warnings: list[str] = []
    coverage = {
        "official_schools": False,
        "city_parks": False,
        "osm_polygons": False,
        "verified_daycares": False,
    }

    try:
        schools = _add_category(
            load_state_school_points()
        )
        layers.append(schools)
        coverage["official_schools"] = (
            not schools.empty
        )
    except Exception as error:
        warnings.append(
            f"Arkansas schools unavailable: {error}"
        )

    try:
        parks = _add_category(
            load_city_parks()
        )
        layers.append(parks)
        coverage["city_parks"] = not parks.empty
    except Exception as error:
        warnings.append(
            f"Little Rock parks unavailable: {error}"
        )

    try:
        osm = _add_category(
            load_osm_polygons(bounds)
        )
        layers.append(osm)
        coverage["osm_polygons"] = not osm.empty
    except Exception as error:
        warnings.append(
            f"OpenStreetMap polygons unavailable: {error}"
        )

    if (
        daycare_layer is not None
        and not daycare_layer.empty
    ):
        daycare_layer = _add_category(
            daycare_layer
        )
        layers.append(daycare_layer)
        coverage["verified_daycares"] = True

    nonempty = [
        layer
        for layer in layers
        if layer is not None and not layer.empty
    ]

    if not nonempty:
        empty = gpd.GeoDataFrame(
            columns=[
                "Facility Name",
                "Facility Type",
                "Facility Category",
                "Source",
                "Confidence",
                "Geometry Type",
                "geometry",
            ],
            geometry="geometry",
            crs=WGS84,
        )

        return empty, warnings, coverage

    facilities = gpd.GeoDataFrame(
        pd.concat(
            nonempty,
            ignore_index=True,
            sort=False,
        ),
        geometry="geometry",
        crs=WGS84,
    )

    facilities = _deduplicate(facilities)

    return facilities, warnings, coverage
