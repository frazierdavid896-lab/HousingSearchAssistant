import re

import folium
import pandas as pd
import streamlit as st
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Housing Search Assistant",
    page_icon="🏠",
    layout="wide",
)

st.title("Housing Search Assistant")
st.subheader("Automatic 2,000-Foot Property Screening")


def remove_unit_designator(address: str) -> str:
    patterns = [
        r"\s+#\s*[A-Za-z0-9-]+",
        r"\s+(apt|apartment|unit|suite|ste)\s*[#:]?\s*[A-Za-z0-9-]+",
    ]

    cleaned = address

    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    return cleaned.strip().rstrip(",")


def locate_properties(
    address_text: str,
) -> tuple[pd.DataFrame, folium.Map]:
    geolocator = Nominatim(
        user_agent="housing-search-assistant"
    )

    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1,
    )

    rows = []

    for raw_address in address_text.splitlines():
        address = raw_address.strip()

        if not address:
            continue

        query = (
            address
            if "Little Rock" in address
            else f"{address}, Little Rock, AR"
        )

        geocoded_from = query

        try:
            location = geocode(
                query,
                country_codes="us",
            )

            if location is None:
                base_address = remove_unit_designator(address)

                if base_address != address:
                    retry_query = (
                        base_address
                        if "Little Rock" in base_address
                        else f"{base_address}, Little Rock, AR"
                    )

                    location = geocode(
                        retry_query,
                        country_codes="us",
                    )

                    geocoded_from = retry_query

            if location:
                rows.append(
                    {
                        "Address": address,
                        "Geocoded From": geocoded_from,
                        "Latitude": location.latitude,
                        "Longitude": location.longitude,
                        "Status": "Located",
                    }
                )
            else:
                rows.append(
                    {
                        "Address": address,
                        "Geocoded From": geocoded_from,
                        "Latitude": None,
                        "Longitude": None,
                        "Status": "Not Found",
                    }
                )

        except Exception as error:
            rows.append(
                {
                    "Address": address,
                    "Geocoded From": geocoded_from,
                    "Latitude": None,
                    "Longitude": None,
                    "Status": f"Error: {error}",
                }
            )

    results = pd.DataFrame(rows)

    map_object = folium.Map(
        location=[34.7465, -92.2896],
        zoom_start=11,
        control_scale=True,
    )

    for row in results.itertuples():
        if (
            pd.notna(row.Latitude)
            and pd.notna(row.Longitude)
        ):
            folium.Marker(
                [row.Latitude, row.Longitude],
                popup=row.Address,
                tooltip=row.Address,
            ).add_to(map_object)

    return results, map_object


if "results" not in st.session_state:
    st.session_state.results = None

if "property_map" not in st.session_state:
    st.session_state.property_map = None


with st.form("address_form"):
    addresses = st.text_area(
        "Paste one address per line:",
        height=200,
    )

    submitted = st.form_submit_button(
        "Locate Properties"
    )


if submitted:
    if not addresses.strip():
        st.warning(
            "Please enter one or more addresses."
        )
    else:
        with st.spinner("Locating properties..."):
            results, property_map = locate_properties(
                addresses
            )

        st.session_state.results = results
        st.session_state.property_map = property_map


if st.session_state.results is not None:
    st.success(
        f"{len(st.session_state.results)} "
        "addresses processed."
    )

    st.dataframe(
        st.session_state.results,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Map")

    st_folium(
        st.session_state.property_map,
        width=None,
        height=650,
        key="property_map_widget",
    )