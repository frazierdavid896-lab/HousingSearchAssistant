from __future__ import annotations

BUFFER_FEET = 2_000.0
FEET_PER_METER = 3.280839895013123
WORKING_CRS = "EPSG:26915"
WGS84 = "EPSG:4326"
MAP_CENTER = (34.7465, -92.2896)
MAP_ZOOM = 11
REQUEST_TIMEOUT = 90
USER_AGENT = "HousingSearchAssistant/1.0 (Little Rock, Arkansas)"

PUBLIC_SCHOOLS_URL = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Structure/FeatureServer/39/query"
PRIVATE_SCHOOLS_URL = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Structure/FeatureServer/37/query"
LITTLE_ROCK_PARKS_URL = "https://maps.littlerock.gov/server/rest/services/Parks_Data/MapServer/2/query"
LITTLE_ROCK_PARCELS_URL = "https://maps.littlerock.gov/server/rest/services/City_of_Little_Rock_Basemap/MapServer/5/query"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
