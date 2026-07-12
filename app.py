from __future__ import annotations

import re
from dataclasses import dataclass

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

from gis_loader import load_schools

BUFFER_FEET = 2000
FEET_PER_METER = 3.280839895013123
WORKING_CRS = "EPSG:26915"
MAP_CENTER = [34.7465, -92.2896]


@dataclass(frozen=True)
class GeocodeResult:
    address: str
    geocoded_from: str
    latitude: float | None
    longitude: float | None
    status: str


st.set_page_config(page_title="Housing Search Assistant", page_icon="🏠", layout="wide")
st.title("Housing Search Assistant")
st.subheader("Automatic 2,000-Foot Property Screening")
st.caption("Version 0.2: public and private K–12 school screening.")


def remove_unit_designator(address: str) -> str:
    patterns = [
        r"\s+#\s*[A-Za-z0-9-]+",
        r"\s+(?:apt|apartment|unit|suite|ste)\s*[#:]?\s*[A-Za-z0-9-]+",
    ]
    cleaned = address
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    return cleaned.strip().rstrip(",")


def build_query(address: str) -> str:
    return address if "little rock" in address.lower() else f"{address}, Little Rock, AR"


def geocode_one(address: str, geocode) -> GeocodeResult:
    query = build_query(address)
    geocoded_from = query
    try:
        location = geocode(query, country_codes="us")
        if location is None:
            base_address = remove_unit_designator(address)
            if base_address != address:
                retry_query = build_query(base_address)
                location = geocode(retry_query, country_codes="us")
                geocoded_from = retry_query
        if location is None:
            return GeocodeResult(address, geocoded_from, None, None, "Not Found")
        return GeocodeResult(
            address,
            geocoded_from,
            float(location.latitude),
            float(location.longitude),
            "Located",
        )
    except Exception as error:
        return GeocodeResult(address, geocoded_from, None, None, f"Error: {error}")


def locate_properties(address_text: str) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    geolocator = Nominatim(user_agent="housing-search-assistant-v0.2")
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1.1,
        swallow_exceptions=False,
    )

    items = [
        geocode_one(line.strip(), geocode)
        for line in address_text.splitlines()
        if line.strip()
    ]

    location_table = pd.DataFrame(
        [
            {
                "Address": item.address,
                "Geocoded From": item.geocoded_from,
                "Latitude": item.latitude,
                "Longitude": item.longitude,
                "Location Status": item.status,
            }
            for item in items
        ]
    )

    if location_table.empty:
        empty = gpd.GeoDataFrame(
            columns=[
                "Address",
                "Geocoded From",
                "Latitude",
                "Longitude",
                "Location Status",
                "geometry",
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )
        return empty, location_table

    located = location_table.dropna(subset=["Latitude", "Longitude"]).copy()
    properties = gpd.GeoDataFrame(
        located,
        geometry=gpd.points_from_xy(located["Longitude"], located["Latitude"]),
        crs="EPSG:4326",
    )
    return properties, location_table


@st.cache_data(ttl=86400, show_spinner=False)
def get_schools() -> gpd.GeoDataFrame:
    return load_schools()


def screen_against_schools(
    properties: gpd.GeoDataFrame,
    schools: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if properties.empty:
        return pd.DataFrame(), pd.DataFrame()

    properties_projected = properties.to_crs(WORKING_CRS)
    schools_projected = schools.to_crs(WORKING_CRS)

    summary_rows = []
    evidence_rows = []

    for property_index, property_row in properties_projected.iterrows():
        distances_ft = (
            schools_projected.geometry.distance(property_row.geometry)
            * FEET_PER_METER
        )
        nearby = schools_projected.loc[distances_ft <= BUFFER_FEET].copy()
        nearby["Distance (ft)"] = (
            distances_ft.loc[nearby.index].round().astype(int)
        )
        nearby = nearby.sort_values("Distance (ft)")
        original = properties.loc[property_index]

        if nearby.empty:
            status = "PASS"
            reason = (
                "No loaded public or private K–12 school "
                "was found within 2,000 feet."
            )
        else:
            status = "FAIL"
            reason = "; ".join(
                f"{row['School Name']} ({int(row['Distance (ft)']):,} ft)"
                for _, row in nearby.iterrows()
            )
            for _, row in nearby.iterrows():
                evidence_rows.append(
                    {
                        "Address": original["Address"],
                        "Facility": row["School Name"],
                        "Facility Type": row["Facility Type"],
                        "Distance (ft)": int(row["Distance (ft)"]),
                    }
                )

        summary_rows.append(
            {
                "Address": original["Address"],
                "Geocoded From": original["Geocoded From"],
                "Latitude": float(original.geometry.y),
                "Longitude": float(original.geometry.x),
                "School Screening": status,
                "Reason": reason,
            }
        )

    return pd.DataFrame(summary_rows), pd.DataFrame(evidence_rows)


def create_map(
    summary: pd.DataFrame,
    schools: gpd.GeoDataFrame,
    evidence: pd.DataFrame,
) -> folium.Map:
    map_object = folium.Map(location=MAP_CENTER, zoom_start=11, control_scale=True)
    if summary.empty:
        return map_object

    relevant_names = set(evidence["Facility"]) if not evidence.empty else set()
    relevant_schools = schools[schools["School Name"].isin(relevant_names)].copy()

    for _, school in relevant_schools.iterrows():
        geometry = school.geometry if school.geometry.geom_type == "Point" else school.geometry.centroid
        folium.Circle(
            location=[geometry.y, geometry.x],
            radius=BUFFER_FEET / FEET_PER_METER,
            tooltip=school["School Name"],
            popup=(
                f"<b>{school['School Name']}</b><br>"
                f"{school['Facility Type']}<br>"
                "2,000-foot screening radius"
            ),
            fill=True,
            fill_opacity=0.12,
            weight=2,
        ).add_to(map_object)
        folium.CircleMarker(
            location=[geometry.y, geometry.x],
            radius=5,
            tooltip=school["School Name"],
            popup=school["School Name"],
            fill=True,
        ).add_to(map_object)

    for _, row in summary.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            tooltip=f"{row['School Screening']}: {row['Address']}",
            popup=(
                f"<b>{row['Address']}</b><br>"
                f"<b>{row['School Screening']}</b><br>"
                f"{row['Reason']}"
            ),
        ).add_to(map_object)

    return map_object


for key in ("summary", "evidence", "property_map", "location_results"):
    if key not in st.session_state:
        st.session_state[key] = None


with st.form("address_form"):
    addresses = st.text_area(
        "Paste one property address per line:",
        height=200,
        placeholder=(
            "2616 S Harrison St, Little Rock, AR 72204\n"
            "12 Wellford Dr, Little Rock, AR 72209\n"
            "43 S Meadowcliff Dr, Little Rock, AR 72209\n"
            "3215 Ludwig St #B, Little Rock, AR 72204"
        ),
    )
    submitted = st.form_submit_button("Screen Properties")


if submitted:
    if not addresses.strip():
        st.warning("Please enter one or more addresses.")
    else:
        try:
            with st.spinner("Locating properties and loading school data..."):
                properties, location_results = locate_properties(addresses)
                schools = get_schools()
                summary, evidence = screen_against_schools(properties, schools)
                property_map = create_map(summary, schools, evidence)

            st.session_state.summary = summary
            st.session_state.evidence = evidence
            st.session_state.property_map = property_map
            st.session_state.location_results = location_results
        except Exception as error:
            st.error("The screening process could not be completed.")
            st.exception(error)


if st.session_state.summary is not None:
    summary = st.session_state.summary
    evidence = st.session_state.evidence
    location_results = st.session_state.location_results

    st.success(f"{len(summary)} located properties screened.")
    st.subheader("Screening Results")
    st.dataframe(
        summary[["Address", "School Screening", "Reason"]],
        use_container_width=True,
        hide_index=True,
    )

    unresolved = location_results[
        location_results["Location Status"] != "Located"
    ]
    if not unresolved.empty:
        st.warning("Some addresses could not be located.")
        st.dataframe(unresolved, use_container_width=True, hide_index=True)

    st.subheader("School Evidence")
    if evidence is None or evidence.empty:
        st.info("No schools were found within 2,000 feet of the located properties.")
    else:
        st.dataframe(evidence, use_container_width=True, hide_index=True)

    st.subheader("Map")
    st_folium(
        st.session_state.property_map,
        width=None,
        height=700,
        key="school_screening_map_widget",
    )
