from __future__ import annotations

from collections import defaultdict

import geopandas as gpd
import requests
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

from config import OVERPASS_URLS, REQUEST_TIMEOUT, USER_AGENT, WGS84


def _query(bounds: tuple[float, float, float, float]) -> dict:
    south, west, north, east = bounds

    query = f"""
    [out:json][timeout:90];
    (
      nwr["amenity"="school"]({south},{west},{north},{east});
      nwr["amenity"="kindergarten"]({south},{west},{north},{east});
      nwr["amenity"="childcare"]({south},{west},{north},{east});
      nwr["social_facility"="day_care"]({south},{west},{north},{east});
      nwr["landuse"="education"]({south},{west},{north},{east});
      nwr["building"="school"]({south},{west},{north},{east});
    );
    out body geom center;
    """

    last_error: Exception | None = None

    for url in OVERPASS_URLS:
        try:
            response = requests.post(
                url,
                data=query.encode("utf-8"),
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "text/plain",
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as error:
            last_error = error

    raise RuntimeError(
        f"All Overpass endpoints failed: {last_error}"
    )


def _closed_polygon(coords: list[tuple[float, float]]):
    if len(coords) < 4:
        return None

    if coords[0] != coords[-1]:
        coords = [*coords, coords[0]]

    polygon = Polygon(coords)

    if polygon.is_empty or not polygon.is_valid:
        return None

    return polygon


def _geometry_from_way(element: dict):
    geometry = element.get("geometry", [])
    coords = [
        (point["lon"], point["lat"])
        for point in geometry
        if "lon" in point and "lat" in point
    ]

    polygon = _closed_polygon(coords)

    if polygon is not None:
        return polygon

    center = element.get("center")

    if center:
        return Point(
            float(center["lon"]),
            float(center["lat"]),
        )

    return None


def _geometry_from_relation(element: dict):
    outer_lines: list[LineString] = []

    for member in element.get("members", []):
        if member.get("role") not in {"outer", ""}:
            continue

        geometry = member.get("geometry", [])
        coords = [
            (point["lon"], point["lat"])
            for point in geometry
            if "lon" in point and "lat" in point
        ]

        if len(coords) >= 2:
            outer_lines.append(LineString(coords))

    if outer_lines:
        merged = unary_union(outer_lines)
        polygons = list(polygonize(merged))

        if polygons:
            return unary_union(polygons)

    center = element.get("center")

    if center:
        return Point(
            float(center["lon"]),
            float(center["lat"]),
        )

    return None


def _geometry_from_element(element: dict):
    element_type = element.get("type")

    if element_type == "node":
        if "lat" in element and "lon" in element:
            return Point(
                float(element["lon"]),
                float(element["lat"]),
            )
        return None

    if element_type == "way":
        return _geometry_from_way(element)

    if element_type == "relation":
        return _geometry_from_relation(element)

    return None


def _classify(tags: dict[str, str]) -> tuple[str, str] | None:
    amenity = tags.get("amenity", "")
    social_facility = tags.get("social_facility", "")
    building = tags.get("building", "")
    landuse = tags.get("landuse", "")

    if amenity == "school":
        return "School Campus (OSM)", "SCHOOL"

    if amenity in {"kindergarten", "childcare"}:
        return "Daycare (OSM)", "DAYCARE"

    if social_facility == "day_care":
        return "Daycare (OSM)", "DAYCARE"

    if building == "school":
        return "School Building (OSM)", "SCHOOL"

    if landuse == "education":
        return "Education Campus (OSM)", "SCHOOL"

    return None


def load_osm_polygons(
    bounds: tuple[float, float, float, float],
) -> gpd.GeoDataFrame:
    rows: list[dict] = []

    for element in _query(bounds).get("elements", []):
        tags = element.get("tags", {})
        classification = _classify(tags)

        if classification is None:
            continue

        facility_type, category = classification
        geometry = _geometry_from_element(element)

        if geometry is None or geometry.is_empty:
            continue

        geometry_type = geometry.geom_type
        confidence = (
            "SUPPLEMENTAL_POLYGON"
            if geometry_type in {"Polygon", "MultiPolygon"}
            else "SUPPLEMENTAL_POINT"
        )

        rows.append(
            {
                "Facility Name": (
                    tags.get("name")
                    or tags.get("official_name")
                    or tags.get("operator")
                    or facility_type
                ),
                "Facility Type": facility_type,
                "Facility Category": category,
                "Source": "OpenStreetMap",
                "Confidence": confidence,
                "Geometry Type": geometry_type,
                "OSM Element Type": element.get("type", ""),
                "OSM Element ID": element.get("id"),
                "geometry": geometry,
            }
        )

    return gpd.GeoDataFrame(
        rows,
        geometry="geometry",
        crs=WGS84,
    )
