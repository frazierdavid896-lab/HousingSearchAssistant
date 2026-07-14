from __future__ import annotations

import folium
import geopandas as gpd
import pandas as pd

from config import (
    BUFFER_FEET,
    FEET_PER_METER,
    MAP_CENTER,
    MAP_ZOOM,
    WORKING_CRS,
)


def _facility_style(category: str) -> dict:
    colors = {
        "SCHOOL": "#b22222",
        "PARK": "#228b22",
        "DAYCARE": "#d97706",
    }

    color = colors.get(category, "#6b7280")

    return {
        "color": color,
        "weight": 3,
        "fillColor": color,
        "fillOpacity": 0.20,
    }


def create_map(
    properties: gpd.GeoDataFrame,
    facilities: gpd.GeoDataFrame,
    summary: pd.DataFrame,
    evidence: pd.DataFrame,
) -> folium.Map:
    map_object = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        control_scale=True,
    )

    decision_colors = {
        "PASS": "green",
        "FAIL": "red",
        "REVIEW": "orange",
    }

    decisions = (
        dict(zip(summary.Address, summary.Decision))
        if not summary.empty
        else {}
    )

    reasons = (
        dict(zip(summary.Address, summary.Reason))
        if not summary.empty
        else {}
    )

    for _, row in properties.iterrows():
        address = row["Address"]
        decision = str(
            decisions.get(address, "REVIEW")
        )
        color = decision_colors.get(
            decision,
            "orange",
        )

        folium.GeoJson(
            row.geometry.__geo_interface__,
            style_function=lambda _feature, c=color: {
                "color": c,
                "weight": 4,
                "fillOpacity": 0.15,
            },
            tooltip=f"{decision}: {address}",
        ).add_to(map_object)

        centroid = row.geometry.centroid

        folium.Marker(
            [centroid.y, centroid.x],
            popup=(
                f"<b>{address}</b><br>"
                f"{decision}<br>"
                f"{reasons.get(address, '')}"
            ),
            icon=folium.Icon(
                color=color,
                icon="home",
                prefix="fa",
            ),
        ).add_to(map_object)

    if (
        not evidence.empty
        and not facilities.empty
    ):
        pairs = set(
            zip(
                evidence.Facility,
                evidence["Facility Type"],
            )
        )

        relevant = facilities[
            facilities.apply(
                lambda row: (
                    row["Facility Name"],
                    row["Facility Type"],
                )
                in pairs,
                axis=1,
            )
        ].copy()

        for _, row in relevant.iterrows():
            category = row.get(
                "Facility Category",
                "OTHER",
            )

            folium.GeoJson(
                row.geometry.__geo_interface__,
                tooltip=(
                    f"{row['Facility Name']} — "
                    f"{row['Facility Type']} — "
                    f"{row['Source']}"
                ),
                style_function=lambda _feature, c=category: (
                    _facility_style(c)
                ),
            ).add_to(map_object)

            buffer_geometry = (
                gpd.GeoSeries(
                    [row.geometry],
                    crs=facilities.crs,
                )
                .to_crs(WORKING_CRS)
                .buffer(
                    BUFFER_FEET
                    / FEET_PER_METER
                )
                .to_crs("EPSG:4326")
                .iloc[0]
            )

            folium.GeoJson(
                buffer_geometry.__geo_interface__,
                style_function=lambda _feature, c=category: {
                    **_facility_style(c),
                    "weight": 1,
                    "fillOpacity": 0.06,
                },
            ).add_to(map_object)

    if not properties.empty:
        minx, miny, maxx, maxy = (
            properties.total_bounds
        )

        map_object.fit_bounds(
            [
                [float(miny), float(minx)],
                [float(maxy), float(maxx)],
            ],
            padding=(40, 40),
        )

    return map_object
