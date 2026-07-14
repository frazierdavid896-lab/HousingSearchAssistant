from __future__ import annotations

import geopandas as gpd
import pandas as pd
from config import PUBLIC_SCHOOLS_URL, PRIVATE_SCHOOLS_URL, WGS84
from data_sources import arcgis_query, normalized_layer

NAMES=("name","school_name","sch_name","facility","site_name","campus_name","description")

def load_state_school_points() -> gpd.GeoDataFrame:
    public = normalized_layer(arcgis_query(PUBLIC_SCHOOLS_URL), "Public K-12 School", "Arkansas GIS Office", NAMES, "AUTHORITATIVE_POINT")
    private = normalized_layer(arcgis_query(PRIVATE_SCHOOLS_URL), "Private K-12 School", "Arkansas GIS Office", NAMES, "AUTHORITATIVE_POINT")
    return gpd.GeoDataFrame(pd.concat([public,private], ignore_index=True), geometry="geometry", crs=WGS84)
