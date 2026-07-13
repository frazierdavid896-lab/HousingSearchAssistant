from __future__ import annotations

import geopandas as gpd
import pandas as pd
from config import BUFFER_FEET, FEET_PER_METER, WORKING_CRS
from models import Decision

def screen_properties(properties: gpd.GeoDataFrame, facilities: gpd.GeoDataFrame, daycare_loaded: bool) -> tuple[pd.DataFrame,pd.DataFrame]:
    if properties.empty: return pd.DataFrame(),pd.DataFrame()
    pp=properties.to_crs(WORKING_CRS)
    ff=facilities.to_crs(WORKING_CRS) if not facilities.empty else facilities
    summary=[]; evidence=[]
    for idx,p in pp.iterrows():
        nearby=pd.DataFrame()
        if not ff.empty:
            d=ff.geometry.distance(p.geometry)*FEET_PER_METER
            nearby=ff.loc[d<=BUFFER_FEET].copy(); nearby["Distance (ft)"]=(d.loc[nearby.index]).round().astype(int)
            nearby=nearby.sort_values(["Distance (ft)","Facility Type","Facility Name"])
        original=properties.loc[idx]
        point_fallback=original["Property Geometry Status"]!="PARCEL"
        if not nearby.empty:
            decision=Decision.FAIL
            reason="; ".join(f"{r['Facility Name']} — {r['Facility Type']} ({int(r['Distance (ft)']):,} ft)" for _,r in nearby.iterrows())
        elif point_fallback or not daycare_loaded:
            decision=Decision.REVIEW
            issues=[]
            if point_fallback: issues.append("parcel polygon unavailable; point geometry used")
            if not daycare_loaded: issues.append("verified daycare data not loaded")
            reason="No loaded restricted facility within 2,000 feet, but " + " and ".join(issues) + "."
        else:
            decision=Decision.PASS; reason="No loaded restricted facility geometry was found within 2,000 feet of the parcel boundary."
        for _,r in nearby.iterrows():
            evidence.append({"Address":original["Address"],"Decision":decision,"Facility":r["Facility Name"],"Facility Type":r["Facility Type"],"Distance (ft)":int(r["Distance (ft)"]),"Facility Geometry":r["Geometry Type"],"Source":r["Source"],"Confidence":r["Confidence"]})
        summary.append({"Address":original["Address"],"Decision":decision,"Reason":reason,"Property Geometry":original["Property Geometry Status"],"Property Source":original["Property Geometry Source"],"Latitude":float(original["Latitude"]),"Longitude":float(original["Longitude"])})
    return pd.DataFrame(summary),pd.DataFrame(evidence)
