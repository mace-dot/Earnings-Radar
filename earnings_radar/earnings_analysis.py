"""Deterministic SEC fundamental context. No consensus or guidance is invented."""
import json
from datetime import datetime

def summarize(conn,ticker,as_of):
    rows=conn.execute("SELECT * FROM evidence WHERE provider='sec_fundamentals' AND published_at<=? AND retrieved_at<=? ORDER BY retrieved_at DESC,id DESC",(as_of.isoformat(),as_of.isoformat())).fetchall()
    latest={}
    for row in rows:
        if ticker not in json.loads(row['tickers']):continue
        m=json.loads(row['metadata']);key=(m['tag'],m['start'],m['end'])
        if key not in latest:latest[key]=(row,m)
    result=[]
    for tag in sorted({k[0] for k in latest}):
        facts=sorted([v for k,v in latest.items() if k[0]==tag],key=lambda v:v[1]['end'],reverse=True)
        current_row,current=facts[0]
        duration=(datetime.fromisoformat(current['end'])-datetime.fromisoformat(current['start'])).days
        prior=next(((r,m) for r,m in facts[1:] if 300<=(datetime.fromisoformat(current['end'])-datetime.fromisoformat(m['end'])).days<=400 and abs((datetime.fromisoformat(m['end'])-datetime.fromisoformat(m['start'])).days-duration)<10),None)
        change=None
        if prior and prior[1]['value']!=0:change=(current['value']-prior[1]['value'])/abs(prior[1]['value'])*100
        result.append({'metric':tag,'reported_value_usd':current['value'],'period_end':current['end'],'duration_days':duration,'year_over_year_pct':change,'evidence_id':current_row['id'],'comparison_evidence_id':prior[0]['id'] if prior else None,'expectations':'unavailable','guidance':'not extracted from XBRL concept data','limitations':'Historical reported result, not a live price or expected earnings move'})
    return result
