# Housing Search Assistant v1.0

Production-oriented Streamlit GIS screening application for Little Rock, Arkansas.

## Decisions
- **FAIL**: a loaded restricted facility is within 2,000 feet.
- **PASS**: no loaded facility is within 2,000 feet, parcel polygon is available, and verified daycare data is loaded.
- **REVIEW**: parcel or daycare evidence is incomplete.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Daycare CSV
Required columns: `name`, `latitude`, `longitude`.
Optional columns: `license_status`, `facility_type`.

## Important
This is a screening tool, not a legal determination. GIS sources may be incomplete or stale. REVIEW cases require manual verification.
