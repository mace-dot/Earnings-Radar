"""Point-in-time engineering replay, isolated from live delivery and performance claims."""
from datetime import datetime,timezone
import json
from earnings_radar.analysis import factual_analysis
from earnings_radar.db import utc_now

def run(conn,as_of):
    if as_of.tzinfo is None:raise ValueError('replay requires timezone-aware as-of timestamp')
    as_of=as_of.astimezone(timezone.utc)
    # Only revisions known on the decision date; never use a current revised value retroactively.
    rows=conn.execute('''SELECT e.* FROM evidence e WHERE e.first_seen_at<=? AND e.retrieved_at<=? AND e.published_at<=? AND NOT EXISTS (SELECT 1 FROM evidence newer WHERE newer.provider=e.provider AND newer.provider_event_id=e.provider_event_id AND newer.revision>e.revision AND newer.retrieved_at<=?) ORDER BY e.id''',(as_of.isoformat(),)*4).fetchall()
    analyses=[factual_analysis(dict(r)).model_dump() for r in rows]
    report={'as_of':as_of.isoformat(),'evidence_count':len(rows),'analyses':analyses,'notifications':0,'engineering_replay_only':True,'limitations':['No profitability claim','No historical licensed quote dataset','Watchlist selection may have survivor bias','No future quotes or revisions used']}
    conn.execute('INSERT INTO replay_runs(created_at,as_of,payload) VALUES (?,?,?)',(utc_now(),as_of.isoformat(),json.dumps(report)))
    return report
