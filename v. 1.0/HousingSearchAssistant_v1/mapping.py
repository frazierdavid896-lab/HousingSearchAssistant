from __future__ import annotations

import folium
import geopandas as gpd
import pandas as pd
from config import BUFFER_FEET, FEET_PER_METER, MAP_CENTER, MAP_ZOOM, WORKING_CRS

def create_map(properties:gpd.GeoDataFrame, facilities:gpd.GeoDataFrame, summary:pd.DataFrame, evidence:pd.DataFrame)->folium.Map:
    m=folium.Map(location=MAP_CENTER,zoom_start=MAP_ZOOM,control_scale=True)
    colors={"PASS":"green","FAIL":"red","REVIEW":"orange"}
    decisions=dict(zip(summary.Address,summary.Decision)) if not summary.empty else {}
    reasons=dict(zip(summary.Address,summary.Reason)) if not summary.empty else {}
    for _,row in properties.iterrows():
        addr=row["Address"]; color=colors.get(str(decisions.get(addr,"REVIEW")),"orange")
        folium.GeoJson(row.geometry.__geo_interface__,style_function=lambda _,c=color:{"color":c,"weight":3,"fillOpacity":.12},tooltip=f"{decisions.get(addr,'REVIEW')}: {addr}").add_to(m)
        c=row.geometry.centroid
        folium.Marker([c.y,c.x],popup=f"<b>{addr}</b><br>{decisions.get(addr)}<br>{reasons.get(addr,'')}",icon=folium.Icon(color=color,icon="home",prefix="fa")).add_to(m)
    if not evidence.empty and not facilities.empty:
        pairs=set(zip(evidence.Facility,evidence["Facility Type"]))
        rel=facilities[facilities.apply(lambda r:(r["Facility Name"],r["Facility Type"]) in pairs,axis=1)].copy()
        for _,r in rel.iterrows():
            folium.GeoJson(r.geometry.__geo_interface__,tooltip=f"{r['Facility Name']} — {r['Facility Type']}",style_function=lambda _:{"weight":2,"fillOpacity":.18}).add_to(m)
            buf=gpd.GeoSeries([r.geometry],crs=facilities.crs).to_crs(WORKING_CRS).buffer(BUFFER_FEET/FEET_PER_METER).to_crs("EPSG:4326").iloc[0]
            folium.GeoJson(buf.__geo_interface__,style_function=lambda _:{"weight":1,"fillOpacity":.06}).add_to(m)
    return m
