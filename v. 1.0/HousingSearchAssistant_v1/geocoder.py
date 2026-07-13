from __future__ import annotations

import re
import geopandas as gpd
import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from config import USER_AGENT, WGS84
from models import GeocodeResult

_UNIT_PATTERNS = (
    r"\s+#\s*[A-Za-z0-9-]+",
    r"\s+(?:apt|apartment|unit|suite|ste)\s*[#:]?\s*[A-Za-z0-9-]+",
)

def remove_unit_designator(address: str) -> str:
    cleaned = address
    for pattern in _UNIT_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    return cleaned.strip().rstrip(",")

def build_query(address: str) -> str:
    return address if "little rock" in address.lower() else f"{address}, Little Rock, AR"

def geocode_one(address: str, geocode) -> GeocodeResult:
    attempts = [build_query(address)]
    base = remove_unit_designator(address)
    if base != address:
        attempts.append(build_query(base))
    try:
        for query in attempts:
            location = geocode(query, country_codes="us")
            if location is not None:
                return GeocodeResult(address, query, float(location.latitude), float(location.longitude), "Located")
        return GeocodeResult(address, attempts[-1], None, None, "Not Found")
    except Exception as error:
        return GeocodeResult(address, attempts[-1], None, None, f"Error: {error}")

def locate_properties(address_text: str) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    locator = Nominatim(user_agent=USER_AGENT)
    geocode = RateLimiter(locator.geocode, min_delay_seconds=1.1, swallow_exceptions=False)
    results = [geocode_one(line.strip(), geocode) for line in address_text.splitlines() if line.strip()]
    table = pd.DataFrame([{
        "Address": r.address, "Geocoded From": r.geocoded_from,
        "Latitude": r.latitude, "Longitude": r.longitude,
        "Location Status": r.status, "Geocoder": r.provider,
    } for r in results])
    if table.empty:
        return gpd.GeoDataFrame(columns=["Address","geometry"], geometry="geometry", crs=WGS84), table
    located = table.dropna(subset=["Latitude","Longitude"]).copy()
    gdf = gpd.GeoDataFrame(located, geometry=gpd.points_from_xy(located.Longitude, located.Latitude), crs=WGS84)
    return gdf, table
