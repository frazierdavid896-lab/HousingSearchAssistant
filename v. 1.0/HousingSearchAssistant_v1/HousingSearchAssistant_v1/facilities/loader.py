from __future__ import annotations

import geopandas as gpd
import pandas as pd
from config import WGS84
from .schools import load_state_school_points
from .parks import load_city_parks
from .osm import load_osm_polygons


def load_all_facilities(
    bounds: tuple[float, float, float, float],
    daycare_layer: gpd.GeoDataFrame | None = None,
) -> tuple[gpd.GeoDataFrame, list[str]]:
    layers = []
    warnings = []

    for name, loader in (
        ("Arkansas schools", load_state_school_points),
        ("Little Rock parks", load_city_parks),
    ):
        try:
            layers.append(loader())
        except Exception as error:
            warnings.append(f"{name} unavailable: {error}")

    try:
        layers.append(load_osm_polygons(bounds))
    except Exception as error:
        warnings.append(f"OpenStreetMap polygons unavailable: {error}")

    if daycare_layer is not None and not daycare_layer.empty:
        layers.append(daycare_layer)

    nonempty = [layer for layer in layers if layer is not None and not layer.empty]
    if not nonempty:
        return (
            gpd.GeoDataFrame(
                columns=[
                    "Facility Name", "Facility Type", "Source", "Confidence",
                    "Geometry Type", "geometry",
                ],
                geometry="geometry",
                crs=WGS84,
            ),
            warnings,
        )

    return (
        gpd.GeoDataFrame(pd.concat(nonempty, ignore_index=True), geometry="geometry", crs=WGS84),
        warnings,
    )
