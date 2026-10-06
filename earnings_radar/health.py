"""Unknown and degraded sources stay visible; no fabricated low-risk status."""
import json
from datetime import datetime, timezone
from earnings_radar.db import fetch_all

def snapshot(conn,*,now=None):
    now=now or datetime.now(timezone.utc)
    workers=fetch_all(conn,'SELECT * FROM worker_health ORDER BY heartbeat DESC')
    alive=any(w['status']=='running' and (now-datetime.fromisoformat(w['heartbeat'])).total_seconds()<90 for w in workers)
    jobs=fetch_all(conn,'SELECT name,status,last_success,last_error,failures,next_run FROM jobs ORDER BY name')
    for j in jobs:
        if j['last_success'] and (now-datetime.fromisoformat(j['last_success'])).total_seconds()>900:
            j['status']='stale'
    coverage=fetch_all(conn,'SELECT provider,MAX(retrieved_at) AS last_retrieval,COUNT(*) AS revisions FROM evidence GROUP BY provider')
    last=conn.execute('SELECT published_at,first_seen_at,retrieved_at FROM evidence ORDER BY id DESC LIMIT 1').fetchone()
    delays=None
    if last:
        delays={'publication_to_arrival_seconds':(datetime.fromisoformat(last['first_seen_at'])-datetime.fromisoformat(last['published_at'])).total_seconds(),'arrival_to_retrieval_seconds':(datetime.fromisoformat(last['retrieved_at'])-datetime.fromisoformat(last['first_seen_at'])).total_seconds()}
    spend=conn.execute('SELECT reserved_usd FROM model_spend WHERE day=?',(now.date().isoformat(),)).fetchone()
    pending=conn.execute("SELECT COUNT(*) FROM evidence e WHERE NOT EXISTS (SELECT 1 FROM analyses a WHERE a.evidence_id=e.id)").fetchone()[0]
    return {'worker':'running' if alive else 'stopped_or_unknown','jobs':jobs,'coverage':coverage,'delays':delays,'analysis_backlog':pending,'model_reserved_usd_today':spend[0] if spend else 0,'market_coverage':'unknown until quotes collected','systemic_risk':'unknown: multi-dimensional indicators not configured'}
