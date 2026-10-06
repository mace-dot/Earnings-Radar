"""Deterministic factual notices plus optional bounded model review."""
import json
import os
from datetime import datetime, timezone
from earnings_radar.analysis_schema import validate_analysis
from earnings_radar.evidence import classify
from earnings_radar.db import get_conn,utc_now
from earnings_radar.model import AnthropicModel,reserve

def factual_analysis(evidence):
    category,policy=classify(evidence)
    return validate_analysis({
        'event_id':evidence['id'],'affected_tickers':json.loads(evidence['tickers']),
        'confirmed_facts':[{'evidence_id':evidence['id'],'field':'title','excerpt':evidence['title']}],
        'hypotheses':[], 'economic_mechanism':'Not established from source metadata alone; inspect the linked primary document.',
        'bullish_implications':[],'bearish_implications':[],'counterevidence':[],
        'time_horizon':'Unspecified pending document review','observed_reaction':'Unknown: no synchronized market reaction verified',
        'suggested_action':'investigate','invalidation_conditions':['Source correction or conflicting primary evidence'],
        'missing_information':['Full-document review','Expectations or consensus','Fresh synchronized option and underlying quotes','Contradictory evidence','Documented company exposures'],
        'evidence_confidence':'medium' if evidence['provenance']=='primary' else 'low',
        'category':category,'policy_status':policy,
        'caveat':'A confirmed fact here is what the publisher reported in its title, not verification of every underlying claim. Evidence confidence is not probability of trading success.'
    },evidence)

def process_pending(path,settings,limit=25,model=None):
    with get_conn(path) as conn:
        rows=[dict(r) for r in conn.execute('SELECT e.* FROM evidence e WHERE NOT EXISTS (SELECT 1 FROM analyses a WHERE a.evidence_id=e.id) ORDER BY e.id LIMIT ?',(limit,))]
    for evidence in rows:
        result=factual_analysis(evidence);version='deterministic-v1';model_status='disabled'
        if settings.model_enabled and os.getenv('ANTHROPIC_API_KEY'):
            with get_conn(path) as conn:
                allowed=reserve(conn,settings.model_daily_budget)
            if allowed:
                try:
                    result=(model or AnthropicModel()).analyze(evidence,settings)
                    version=settings.model;model_status='validated'
                except Exception as exc:
                    model_status='failed:'+type(exc).__name__
            else: model_status='budget_exhausted'
        elif settings.model_enabled:model_status='credential_missing'
        with get_conn(path) as conn:
            # Lease-independent idempotency prevents duplicate analyses from concurrent workers.
            cur=conn.execute('INSERT OR IGNORE INTO analyses(evidence_id,model_version,config,created_at,payload) VALUES (?,?,?,?,?)',(evidence['id'],version,json.dumps({'model_status':model_status,'schema':'v1'}),utc_now(),result.model_dump_json()))
            aid=cur.lastrowid if cur.rowcount else conn.execute('SELECT id FROM analyses WHERE evidence_id=? AND model_version=?',(evidence['id'],version)).fetchone()[0]
            from earnings_radar.alerts import upsert_alert
            upsert_alert(conn,evidence,aid,result,settings)
    return len(rows)
