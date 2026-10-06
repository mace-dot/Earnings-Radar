"""Only dated, explicitly evidenced company relationships enter discovery."""
from datetime import date
import json

def exposures(conn,ticker,as_of):
    rows=conn.execute('''SELECT r.*,e.title,e.published_at FROM relationships r JOIN evidence e ON e.id=r.evidence_id WHERE r.subject=? AND r.valid_from<=? AND (r.valid_until IS NULL OR r.valid_until>=?) AND e.published_at<=?''',(ticker,as_of.date().isoformat(),as_of.date().isoformat(),as_of.isoformat())).fetchall()
    result=[]
    for row in rows:
        result.append({'ticker':row['related'],'relationship':row['kind'],'evidence_id':row['evidence_id'],'dated':row['valid_from'],'stale':(as_of.date()-date.fromisoformat(row['valid_from'])).days>365,'hypothesis':'Exposure is documented; financial impact and whether it is priced remain unknown.'})
    return result
