from __future__ import annotations

import geopandas as gpd
import requests
from shapely.geometry import Polygon, LineString, Point
from config import OVERPASS_URLS, REQUEST_TIMEOUT, USER_AGENT, WGS84

def _query(bounds: tuple[float,float,float,float]) -> dict:
    south, west, north, east = bounds
    q=f"""[out:json][timeout:60];(
      way["amenity"="school"]({south},{west},{north},{east});
      relation["amenity"="school"]({south},{west},{north},{east});
      way["leisure"="park"]({south},{west},{north},{east});
      relation["leisure"="park"]({south},{west},{north},{east});
    );out geom;"""
    last=None
    for url in OVERPASS_URLS:
        try:
            r=requests.post(url,data=q.encode(),timeout=REQUEST_TIMEOUT,headers={"User-Agent":USER_AGENT,"Content-Type":"text/plain"})
            r.raise_for_status(); return r.json()
        except Exception as e: last=e
    raise RuntimeError(f"All Overpass endpoints failed: {last}")

def load_osm_polygons(bounds: tuple[float,float,float,float]) -> gpd.GeoDataFrame:
    rows=[]
    for e in _query(bounds).get("elements",[]):
        tags=e.get("tags",{}); geom=e.get("geometry",[])
        coords=[(p["lon"],p["lat"]) for p in geom if "lon" in p and "lat" in p]
        if len(coords)<3: continue
        shape=Polygon(coords) if coords[0]==coords[-1] else LineString(coords)
        if shape.geom_type != "Polygon": continue
        amenity=tags.get("amenity"); leisure=tags.get("leisure")
        ftype="School Campus (OSM)" if amenity=="school" else "Public Park (OSM)"
        rows.append({"Facility Name":tags.get("name",ftype),"Facility Type":ftype,"Source":"OpenStreetMap","Confidence":"SUPPLEMENTAL_POLYGON","Geometry Type":"Polygon","geometry":shape})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=WGS84)
