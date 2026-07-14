from __future__ import annotations

import geopandas as gpd
import pandas as pd

from config import (
    BUFFER_FEET,
    FEET_PER_METER,
    WORKING_CRS,
)
from models import Decision


def _coverage_issues(
    coverage: dict[str, bool],
) -> list[str]:
    labels = {
        "official_schools": (
            "official school source unavailable"
        ),
        "city_parks": (
            "official park source unavailable"
        ),
        "osm_polygons": (
            "supplemental campus polygons unavailable"
        ),
        "verified_daycares": (
            "verified daycare data not loaded"
        ),
    }

    return [
        message
        for key, message in labels.items()
        if not coverage.get(key, False)
    ]


def screen_properties(
    properties: gpd.GeoDataFrame,
    facilities: gpd.GeoDataFrame,
    coverage: dict[str, bool],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if properties.empty:
        return pd.DataFrame(), pd.DataFrame()

    projected_properties = properties.to_crs(
        WORKING_CRS
    )

    projected_facilities = (
        facilities.to_crs(WORKING_CRS)
        if not facilities.empty
        else facilities
    )

    summary_rows: list[dict] = []
    evidence_rows: list[dict] = []

    general_coverage_issues = _coverage_issues(
        coverage
    )

    for index, property_row in (
        projected_properties.iterrows()
    ):
        nearby = pd.DataFrame()

        if not projected_facilities.empty:
            distances = (
                projected_facilities.geometry.distance(
                    property_row.geometry
                )
                * FEET_PER_METER
            )

            nearby = projected_facilities.loc[
                distances <= BUFFER_FEET
            ].copy()

            nearby["Distance (ft)"] = (
                distances.loc[nearby.index]
                .round()
                .astype(int)
            )

            nearby = nearby.sort_values(
                [
                    "Distance (ft)",
                    "Facility Category",
                    "Facility Type",
                    "Facility Name",
                ]
            )

        original = properties.loc[index]
        point_fallback = (
            original["Property Geometry Status"]
            != "PARCEL"
        )

        if not nearby.empty:
            decision = Decision.FAIL
            reason = "; ".join(
                (
                    f"{row['Facility Name']} — "
                    f"{row['Facility Type']} "
                    f"({int(row['Distance (ft)']):,} ft, "
                    f"{row['Source']}, "
                    f"{row['Geometry Type']})"
                )
                for _, row in nearby.iterrows()
            )
        else:
            review_issues = list(
                general_coverage_issues
            )

            if point_fallback:
                review_issues.append(
                    "parcel polygon unavailable; "
                    "point geometry used"
                )

            if review_issues:
                decision = Decision.REVIEW
                reason = (
                    "No loaded restricted facility "
                    "was found within 2,000 feet, but "
                    + "; ".join(review_issues)
                    + "."
                )
            else:
                decision = Decision.PASS
                reason = (
                    "No loaded restricted facility "
                    "geometry was found within "
                    "2,000 feet of the parcel boundary."
                )

        for _, row in nearby.iterrows():
            evidence_rows.append(
                {
                    "Address": original["Address"],
                    "Decision": decision,
                    "Facility": row[
                        "Facility Name"
                    ],
                    "Facility Type": row[
                        "Facility Type"
                    ],
                    "Facility Category": row.get(
                        "Facility Category",
                        "",
                    ),
                    "Distance (ft)": int(
                        row["Distance (ft)"]
                    ),
                    "Facility Geometry": row[
                        "Geometry Type"
                    ],
                    "Source": row["Source"],
                    "Confidence": row[
                        "Confidence"
                    ],
                }
            )

        summary_rows.append(
            {
                "Address": original["Address"],
                "Decision": decision,
                "Reason": reason,
                "Property Geometry": original[
                    "Property Geometry Status"
                ],
                "Property Source": original[
                    "Property Geometry Source"
                ],
                "Latitude": float(
                    original["Latitude"]
                ),
                "Longitude": float(
                    original["Longitude"]
                ),
            }
        )

    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(evidence_rows),
    )
