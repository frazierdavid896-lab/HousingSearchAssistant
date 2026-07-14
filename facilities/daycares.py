from __future__ import annotations

from io import BytesIO
from typing import Callable

import geopandas as gpd
import pandas as pd
from bs4 import BeautifulSoup
from config import WGS84

STATE_COLUMNS = (
    "Facility Number",
    "Facility Name",
    "Facility Type",
    "Better Beginnings",
    "Address",
    "County",
    "Director",
    "Owner",
    "Phone",
    "Email Address",
    "Website Address",
    "Total Allowed Capacity",
    "Voucher Participant",
    "CACFP Facility",
    "ABC Facility",
)


def parse_arkansas_facility_export(content: bytes) -> pd.DataFrame:
    """Parse Arkansas DHS Facility Data.xls (HTML disguised as .xls)."""
    decoded = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            decoded = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded is None:
        raise ValueError(
            "The Arkansas facility export could not be decoded."
        )

    soup = BeautifulSoup(decoded, "html.parser")
    rows: list[list[str]] = []

    for tr in soup.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in tr.find_all(["th", "td"])
        ]
        if cells:
            rows.append(cells)

    if not rows:
        raise ValueError(
            "The Arkansas facility export contains no table rows."
        )

    headers = rows[0]
    missing = [
        column
        for column in STATE_COLUMNS
        if column not in headers
    ]

    if missing:
        # Some exports place every table cell in a flat sequence.
        all_cells = [
            cell.get_text(" ", strip=True)
            for cell in soup.find_all(["th", "td"])
        ]

        if all_cells[:len(STATE_COLUMNS)] == list(STATE_COLUMNS):
            headers = list(STATE_COLUMNS)
            width = len(headers)
            data_cells = all_cells[width:]
            rows = [
                data_cells[index:index + width]
                for index in range(0, len(data_cells), width)
                if len(data_cells[index:index + width]) == width
            ]
        else:
            raise ValueError(
                "Unrecognized Arkansas facility export. Missing: "
                + ", ".join(missing)
            )
    else:
        width = len(headers)
        rows = [
            (row + [""] * width)[:width]
            for row in rows[1:]
        ]

    frame = pd.DataFrame(rows, columns=headers)
    frame = frame.dropna(how="all").copy()

    for column in (
        "Facility Number",
        "Facility Name",
        "Address",
        "County",
    ):
        frame[column] = (
            frame[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    frame = frame[
        (frame["Facility Number"] != "")
        & (frame["Facility Name"] != "")
        & (frame["Address"] != "")
    ]

    return frame.reset_index(drop=True)


def geocode_arkansas_facilities(
    frame: pd.DataFrame,
    geocode: Callable[[str], tuple[float | None, float | None, str]],
    county: str = "Pulaski",
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Geocode state-format facility rows and return located and unresolved records."""
    work = frame.copy()
    if county:
        work = work[work["County"].str.casefold() == county.casefold()].copy()

    records: list[dict] = []
    unresolved: list[dict] = []
    for row in work.to_dict("records"):
        lat, lon, status = geocode(row["Address"])
        common = {
            "Facility Number": row["Facility Number"],
            "Facility Name": row["Facility Name"],
            "Facility Type": row["Facility Type"] or "Licensed Child Care Facility",
            "Address": row["Address"],
            "County": row["County"],
            "Director": row.get("Director", ""),
            "Owner": row.get("Owner", ""),
            "Phone": row.get("Phone", ""),
            "Capacity": row.get("Total Allowed Capacity", ""),
            "Geocode Status": status,
        }
        if lat is None or lon is None:
            unresolved.append(common)
        else:
            common["latitude"] = lat
            common["longitude"] = lon
            records.append(common)

    if records:
        located = pd.DataFrame(records)
        gdf = gpd.GeoDataFrame(
            {
                "Facility Name": located["Facility Name"],
                "Facility Type": located["Facility Type"],
                "Source": "Arkansas DHS Facility Data export",
                "Confidence": "AUTHORITATIVE_GEOCODED_POINT",
                "Geometry Type": "Point",
                "Facility Number": located["Facility Number"],
                "Facility Address": located["Address"],
                "County": located["County"],
                "Phone": located["Phone"],
                "Capacity": located["Capacity"],
            },
            geometry=gpd.points_from_xy(located["longitude"], located["latitude"]),
            crs=WGS84,
        )
    else:
        gdf = gpd.GeoDataFrame(
            columns=[
                "Facility Name", "Facility Type", "Source", "Confidence",
                "Geometry Type", "Facility Number", "Facility Address",
                "County", "Phone", "Capacity", "geometry",
            ],
            geometry="geometry",
            crs=WGS84,
        )

    return gdf, pd.DataFrame(unresolved)
