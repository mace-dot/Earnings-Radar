"""Persistent inbox and leased delivery outbox. Notifications are opt-in."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import json
import os
import time
from earnings_radar.db import get_conn,utc_now
from earnings_radar.providers.base import HTTP,ProviderError

SEVERITY={'low':0,'medium':1,'high':2,'urgent':3}

def enabled(settings):
    return settings.telegram_enabled and settings.telegram_verified and bool(os.getenv('TELEGRAM_BOT_TOKEN')) and bool(os.getenv('TELEGRAM_CHAT_ID'))

def quiet(settings,now):
    hour=now.astimezone(ZoneInfo('America/New_York')).hour
    start,end=settings.quiet_start,settings.quiet_end
    return (hour>=start or hour<end) if start>end else start<=hour<end

def upsert_alert(conn,evidence,analysis_id,analysis,settings):
    existing=conn.execute('SELECT * FROM alerts WHERE story_key=?',(evidence['story_key'],)).fetchone()
    severity='medium'
    if evidence['provider']=='fed_press' and any(w in evidence['title'].lower() for w in ('fomc','monetary policy')):severity='high'
    now=utc_now()
    payload={'what_changed':evidence['title'],'primary_evidence':{'id':evidence['id'],'url':evidence['url'],'provenance':evidence['provenance']},'affected_companies':analysis.affected_tickers,'why_it_matters':analysis.economic_mechanism,'observed_reaction':analysis.observed_reaction,'action':analysis.suggested_action,'quote_age':'unavailable','feed_type':'no verified executable quote','invalidation':analysis.invalidation_conditions,'missing_information':analysis.missing_information,'policy_status':analysis.policy_status,'backfill':bool(evidence['backfill'])}
    if existing and existing['evidence_id']==evidence['id']:return existing['id']
    if existing:
        prev=conn.execute('SELECT provider,provider_event_id,revision FROM evidence WHERE id=?',(existing['evidence_id'],)).fetchone()
        same=prev['provider']==evidence['provider'] and prev['provider_event_id']==evidence['provider_event_id']
        if not same or prev['revision']>=evidence['revision']:
            # A syndicated title is corroboration metadata, not another alert or independent proof.
            return existing['id']
        aid=existing['id'];revision=existing['revision']+1
        conn.execute('UPDATE alerts SET evidence_id=?,analysis_id=?,severity=?,updated_at=?,revision=?,read_at=NULL,payload=? WHERE id=?',(evidence['id'],analysis_id,severity,now,revision,json.dumps(payload),aid))
        conn.execute("UPDATE outbox SET status='superseded' WHERE alert_id=? AND status IN ('pending','sending','retry')",(aid,))
    else:
        revision=1
        aid=conn.execute('INSERT INTO alerts(story_key,evidence_id,analysis_id,severity,created_at,updated_at,payload) VALUES (?,?,?,?,?,?,?)',(evidence['story_key'],evidence['id'],analysis_id,severity,now,now,json.dumps(payload))).lastrowid
    if enabled(settings) and not evidence['backfill'] and evidence['access_category']!='fixture' and not evidence['provider'].startswith('fixture') and SEVERITY[severity]>=SEVERITY.get(settings.notify_severity,2):
        due=time.time()
        last=conn.execute('SELECT MAX(delivered_at) FROM outbox WHERE alert_id=?',(aid,)).fetchone()[0]
        if last:due=max(due,datetime.fromisoformat(last).timestamp()+settings.cooldown_seconds)
        conn.execute("INSERT OR IGNORE INTO outbox(alert_id,revision,channel,status,next_attempt) VALUES (?,?, 'telegram','pending',?)",(aid,revision,due))
    return int(aid)

class Telegram:
    def __init__(self,http=None):self.http=http or HTTP()
    def send(self,payload):
        token=os.environ['TELEGRAM_BOT_TOKEN']
        # Configured endpoint only; never take a destination or instructions from evidence.
        if '/' in token or '?' in token or '#' in token:raise ProviderError('invalid bot token shape')
        message=f"{payload['what_changed']}\nAction: {payload['action']}\nEvidence: {payload['primary_evidence']['url']}\nWhy: {payload['why_it_matters']}\nReaction: {payload['observed_reaction']}\nQuotes: {payload['quote_age']} / {payload['feed_type']}\nInvalidation: {'; '.join(payload['invalidation'])}\nMissing: {'; '.join(payload['missing_information'])}"
        raw=self.http.request('POST',f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':os.environ['TELEGRAM_CHAT_ID'],'text':message[:4000],'link_preview_options':{'is_disabled':True}})
        if not json.loads(raw).get('ok'):raise ProviderError('Telegram rejected delivery')

def process_delivery(path,settings,owner,*,sender=None,now=None):
    if not enabled(settings):return 0
    now=now or datetime.now(timezone.utc);epoch=now.timestamp()
    with get_conn(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute("SELECT o.*,a.payload,a.severity,a.revision AS current_revision,e.backfill,e.access_category,e.provider FROM outbox o JOIN alerts a ON a.id=o.alert_id JOIN evidence e ON e.id=a.evidence_id WHERE o.status IN ('pending','retry','sending') AND o.next_attempt<=? AND o.lease_until<=? ORDER BY o.id LIMIT 1",(epoch,epoch)).fetchone()
        if not row:return 0
        row=dict(row)
        if row['revision']!=row['current_revision'] or row['backfill'] or row['access_category']=='fixture' or row['provider'].startswith('fixture'):
            conn.execute("UPDATE outbox SET status='suppressed' WHERE id=?",(row['id'],));return 0
        if quiet(settings,now) and not (settings.urgent_exception and row['severity']=='urgent'):
            conn.execute('UPDATE outbox SET next_attempt=? WHERE id=?',(epoch+300,row['id']));return 0
        conn.execute("UPDATE outbox SET lease_owner=?,lease_until=?,status='sending',attempts=attempts+1 WHERE id=?",(owner,epoch+60,row['id']))
    error=None
    try:(sender or Telegram()).send(json.loads(row['payload']))
    except Exception as exc:error=type(exc).__name__
    with get_conn(path) as conn:
        attempts=row['attempts']+1
        status='failed' if error and attempts>=5 else ('retry' if error else 'delivered')
        conn.execute('UPDATE outbox SET status=?,last_error=?,next_attempt=?,delivered_at=?,lease_owner=NULL,lease_until=0 WHERE id=? AND lease_owner=?',(status,error,epoch+min(3600,30*2**attempts),None if error else now.isoformat(),row['id'],owner))
    return 1
