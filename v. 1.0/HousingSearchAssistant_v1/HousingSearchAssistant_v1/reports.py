from __future__ import annotations

from io import BytesIO
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak

def build_pdf(summary:pd.DataFrame,evidence:pd.DataFrame)->bytes:
    out=BytesIO(); doc=SimpleDocTemplate(out,pagesize=letter,rightMargin=.55*inch,leftMargin=.55*inch,topMargin=.55*inch,bottomMargin=.55*inch)
    styles=getSampleStyleSheet(); story=[Paragraph("Housing Search Assistant — Screening Report",styles["Title"]),Spacer(1,12)]
    for _,row in summary.iterrows():
        story += [Paragraph(str(row["Address"]),styles["Heading2"]),Paragraph(f"Decision: <b>{row['Decision']}</b>",styles["BodyText"]),Paragraph(str(row["Reason"]),styles["BodyText"]),Paragraph(f"Property geometry: {row['Property Geometry']} — {row['Property Source']}",styles["BodyText"]),Spacer(1,10)]
        ev=evidence[evidence.Address==row.Address] if not evidence.empty else evidence
        if not ev.empty:
            data=[["Facility","Type","Distance","Source"]]+[[r.Facility,r["Facility Type"],f"{int(r['Distance (ft)']):,} ft",r.Source] for _,r in ev.iterrows()]
            t=Table(data,colWidths=[2.0*inch,1.45*inch,.8*inch,2.1*inch],repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("GRID",(0,0),(-1,-1),.25,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),8)])); story.append(t)
        story.append(PageBreak())
    doc.build(story); return out.getvalue()
