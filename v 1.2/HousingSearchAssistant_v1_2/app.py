from __future__ import annotations

import hashlib

import streamlit as st
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium

from facilities import load_all_facilities
from facilities.daycares import parse_arkansas_facility_export, geocode_arkansas_facilities
from geocoder import locate_properties
from parcels import attach_parcels
from screening import screen_properties
from mapping import create_map
from reports import build_pdf

st.set_page_config(page_title="Housing Search Assistant", page_icon="🏠", layout="wide")
st.title("Housing Search Assistant")
st.caption("Version 1.2 — polygon-first, multi-source parcel-to-facility screening")


def _geocode_daycare_address(address: str) -> tuple[float | None, float | None, str]:
    location = _daycare_geocoder(address, country_codes="us")
    if location is None:
        return None, None, "Not Found"
    return float(location.latitude), float(location.longitude), "Located"


_daycare_locator = Nominatim(user_agent="housing-search-assistant-daycare-v1.1")
_daycare_geocoder = RateLimiter(
    _daycare_locator.geocode,
    min_delay_seconds=1.05,
    swallow_exceptions=True,
)


@st.cache_data(ttl=604800, show_spinner=False)
def load_state_daycares(file_bytes: bytes, county: str):
    frame = parse_arkansas_facility_export(file_bytes)
    return geocode_arkansas_facilities(frame, _geocode_daycare_address, county=county)


with st.sidebar:
    st.header("Arkansas daycare data")
    daycare_upload = st.file_uploader(
        "Upload Arkansas DHS Facility Data.xls",
        type=["xls", "html", "htm"],
        help="Upload the state provider export directly. No rearranging or template conversion is required.",
    )
    daycare_county = st.text_input("County filter", value="Pulaski")
    st.info("The first upload may take several minutes while facility addresses are geocoded. Results are cached.")

with st.form("screen"):
    addresses = st.text_area("One property address per line", height=190)
    submitted = st.form_submit_button("Screen properties", type="primary")

if submitted:
    if not addresses.strip():
        st.warning("Enter at least one address.")
    else:
        try:
            daycare_layer = None
            daycare_unresolved = None
            daycare_loaded = False

            with st.spinner("Loading Arkansas daycare facilities..."):
                if daycare_upload is not None:
                    daycare_bytes = daycare_upload.getvalue()
                    daycare_layer, daycare_unresolved = load_state_daycares(daycare_bytes, daycare_county.strip())
                    daycare_loaded = not daycare_layer.empty

            with st.spinner("Locating parcels and loading GIS layers..."):
                points, locations = locate_properties(addresses)
                properties = attach_parcels(points)
                if properties.empty:
                    raise RuntimeError("No addresses could be located.")

                minx, miny, maxx, maxy = properties.total_bounds
                pad = .04
                bounds = (miny - pad, minx - pad, maxy + pad, maxx + pad)
                facilities, warnings, coverage = load_all_facilities(
                    bounds,
                    daycare_layer=daycare_layer,
                )
                summary, evidence = screen_properties(
                    properties,
                    facilities,
                    coverage,
                )
                fmap = create_map(properties, facilities, summary, evidence)
                pdf = build_pdf(summary, evidence)

            st.session_state.update(
                dict(
                    summary=summary,
                    evidence=evidence,
                    locations=locations,
                    properties=properties,
                    facilities=facilities,
                    fmap=fmap,
                    pdf=pdf,
                    warnings=warnings,
                    daycare_count=len(daycare_layer) if daycare_layer is not None else 0,
                    daycare_unresolved=daycare_unresolved,
                    coverage=coverage,
                )
            )
        except Exception as error:
            st.error("Screening failed.")
            st.exception(error)

if "summary" in st.session_state:
    for warning in st.session_state.warnings:
        st.warning(warning)

    if st.session_state.daycare_count:
        st.success(f"Loaded {st.session_state.daycare_count:,} Arkansas daycare facilities for screening.")
    else:
        st.warning("No daycare facilities were successfully loaded. PASS results are disabled.")

    unresolved_daycares = st.session_state.daycare_unresolved
    if unresolved_daycares is not None and not unresolved_daycares.empty:
        with st.expander(f"Daycare addresses not located: {len(unresolved_daycares):,}"):
            st.dataframe(unresolved_daycares, use_container_width=True, hide_index=True)

    with st.expander("Source coverage", expanded=False):
        coverage = st.session_state.get("coverage", {})
        st.write(
            {
                "Official Arkansas schools": coverage.get("official_schools", False),
                "City of Little Rock parks": coverage.get("city_parks", False),
                "OSM school/daycare polygons": coverage.get("osm_polygons", False),
                "Verified daycare export": coverage.get("verified_daycares", False),
            }
        )

    st.subheader("Results")
    st.dataframe(st.session_state.summary, use_container_width=True, hide_index=True)

    unresolved = st.session_state.locations[
        st.session_state.locations["Location Status"] != "Located"
    ]
    if not unresolved.empty:
        st.warning("Some property addresses could not be located.")
        st.dataframe(unresolved, use_container_width=True, hide_index=True)

    st.subheader("Evidence")
    if st.session_state.evidence.empty:
        st.info("No nearby loaded facilities.")
    else:
        st.dataframe(st.session_state.evidence, use_container_width=True, hide_index=True)

    column1, column2 = st.columns(2)
    column1.download_button(
        "Download CSV",
        st.session_state.summary.to_csv(index=False).encode(),
        "housing_screening_results.csv",
        "text/csv",
    )
    column2.download_button(
        "Download PDF report",
        st.session_state.pdf,
        "housing_screening_report.pdf",
        "application/pdf",
    )

    st.subheader("Map")
    st_folium(st.session_state.fmap, width=None, height=720, returned_objects=[])
