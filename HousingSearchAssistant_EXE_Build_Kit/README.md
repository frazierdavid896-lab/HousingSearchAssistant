# Housing Search Assistant v0.4

Version 0.4 adds daycare screening.

## Daycare data

The official Arkansas provider search is authoritative, but it does not expose a simple public GIS download. Export or copy verified Little Rock providers into `daycares_template.csv`.

Required columns:

- `name`
- `latitude`
- `longitude`

Optional columns:

- `license_status`
- `facility_type`
- `address`
- `city`
- `state`
- `zip`
- `source_date`

Accepted active statuses are:

- active
- licensed
- registered
- open

Upload the completed CSV in the app sidebar before screening.

## Install

Copy all files into:

`C:\Users\frazi\Documents\HousingSearchAssistant`

Allow Windows to replace the existing files.

## Run

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

A PASS without daycare data is provisional.
