from shapely.geometry import Point, Polygon
import geopandas as gpd

from screening import screen_properties


def test_boundary_distance_zero_inside():
    parcel = Polygon(
        [(0, 0), (1, 0), (1, 1), (0, 1)]
    )
    facility = Point(0.5, 0.5)
    assert parcel.distance(facility) == 0


def test_boundary_distance_positive_outside():
    parcel = Polygon(
        [(0, 0), (1, 0), (1, 1), (0, 1)]
    )
    facility = Point(2, 2)
    assert parcel.distance(facility) > 0


def test_school_polygon_causes_fail():
    parcel = Polygon(
        [
            (500000, 3840000),
            (500020, 3840000),
            (500020, 3840020),
            (500000, 3840020),
        ]
    )

    school = Polygon(
        [
            (500200, 3840000),
            (500300, 3840000),
            (500300, 3840100),
            (500200, 3840100),
        ]
    )

    properties = gpd.GeoDataFrame(
        [
            {
                "Address": "Regression Property",
                "Property Geometry Status": "PARCEL",
                "Property Geometry Source": "Test parcel",
                "Latitude": 34.7,
                "Longitude": -92.3,
                "geometry": parcel,
            }
        ],
        geometry="geometry",
        crs="EPSG:26915",
    )

    facilities = gpd.GeoDataFrame(
        [
            {
                "Facility Name": "Terry Elementary School",
                "Facility Type": "School Campus (OSM)",
                "Facility Category": "SCHOOL",
                "Source": "OpenStreetMap",
                "Confidence": "SUPPLEMENTAL_POLYGON",
                "Geometry Type": "Polygon",
                "geometry": school,
            }
        ],
        geometry="geometry",
        crs="EPSG:26915",
    )

    coverage = {
        "official_schools": True,
        "city_parks": True,
        "osm_polygons": True,
        "verified_daycares": True,
    }

    summary, evidence = screen_properties(
        properties,
        facilities,
        coverage,
    )

    assert str(summary.iloc[0]["Decision"]) == "FAIL"
    assert evidence.iloc[0]["Facility"] == (
        "Terry Elementary School"
    )
