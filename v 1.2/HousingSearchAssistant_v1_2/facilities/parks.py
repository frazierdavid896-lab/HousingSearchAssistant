from __future__ import annotations

import geopandas as gpd
from config import LITTLE_ROCK_PARKS_URL
from data_sources import arcgis_query, normalized_layer

NAMES=("name","park_name","park","facility","site_name","description")

def load_city_parks() -> gpd.GeoDataFrame:
    return normalized_layer(arcgis_query(LITTLE_ROCK_PARKS_URL), "Public Park", "City of Little Rock Parks GIS", NAMES, "AUTHORITATIVE_POLYGON")
