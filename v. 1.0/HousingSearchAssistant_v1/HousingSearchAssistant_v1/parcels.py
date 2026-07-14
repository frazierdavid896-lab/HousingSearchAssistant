from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point
from config import LITTLE_ROCK_PARCELS_URL, WGS84
from data_sources import arcgis_query

def parcel_for_point(point: Point) -> gpd.GeoDataFrame:
    geometry = f"{point.x},{point.y}"
    try:
        parcels = arcgis_query(
            LITTLE_ROCK_PARCELS_URL,
            geometry=geometry,
            geometryType="esriGeometryPoint",
            inSR="4326",
            spatialRel="esriSpatialRelIntersects",
            resultRecordCount=20,
        )
    except Exception:
        return gpd.GeoDataFrame(columns=["Parcel Source","Parcel Status","geometry"], geometry="geometry", crs=WGS84)
    if parcels.empty:
        return gpd.GeoDataFrame(columns=["Parcel Source","Parcel Status","geometry"], geometry="geometry", crs=WGS84)
    parcels = parcels.copy()
    parcels["Parcel Source"] = "City of Little Rock Tax Parcel Boundary"
    parcels["Parcel Status"] = "Polygon located"
    return parcels

def attach_parcels(points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    output_columns = [
        column for column in points.columns if column != "geometry"
    ] + [
        "Property Geometry Status",
        "Property Geometry Source",
        "geometry",
    ]

    if points.empty:
        return gpd.GeoDataFrame(
            columns=output_columns,
            geometry="geometry",
            crs=WGS84,
        )

    rows=[]
    for _, row in points.iterrows():
        match = parcel_for_point(row.geometry)
        if not match.empty:
            parcel = match.iloc[0]
            geometry = parcel.geometry
            status = "PARCEL"
            source = parcel.get("Parcel Source", "City parcel layer")
        else:
            geometry = row.geometry
            status = "POINT_FALLBACK"
            source = "Geocoded address point"
        record = row.drop(labels=["geometry"]).to_dict()
        record.update({"Property Geometry Status": status, "Property Geometry Source": source, "geometry": geometry})
        rows.append(record)
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=WGS84)
