# Housing Search Assistant v1.2

Polygon-first, multi-source Streamlit GIS screening for Little Rock, Arkansas.

## Screening sources

- Arkansas GIS public-school points
- Arkansas GIS private-school points
- City of Little Rock park polygons
- OpenStreetMap school, education-campus, kindergarten, childcare, and daycare geometry
- Arkansas daycare export uploaded by the user
- City parcel polygons for subject properties

## Decisions

- **FAIL**: at least one loaded restricted facility is within 2,000 feet.
- **PASS**: no loaded restricted facility is within 2,000 feet, parcel geometry is available, and all required source categories loaded successfully.
- **REVIEW**: no nearby facility was found, but parcel geometry or one or more source categories are incomplete.

## Regression case

`615 Mimi Ln, Little Rock, AR 72211` should fail because Terry Elementary is nearby. The OSM campus polygon is preferred when available, while Arkansas school points remain a fallback.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important

This is a screening tool, not a legal determination. GIS sources may be incomplete, stale, or approximate.
