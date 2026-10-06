"""Idempotent revisioned evidence storage; retained content is metadata only."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit
from earnings_radar.validation import utc_timestamp, ticker
from earnings_radar.db import utc_now

def canonical_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password:
        raise ValueError('evidence requires an HTTPS source URL')
    return urlunsplit(('https',p.netloc.lower(),p.path.rstrip('/'),'', ''))

def ingest(conn,event,*,now=None,initial=False,replay=False):
    now=now or datetime.now(timezone.utc)
    published=utc_timestamp(event.published_at,now=now)
    url=canonical_url(event.url)
    symbols=tuple(ticker(t) for t in event.tickers)
    payload=dict(title=event.title,url=url,published_at=published,tickers=symbols,metadata=event.metadata,provenance=event.provenance,claim_type=event.claim_type)
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    # Exact normalized headlines suppress syndicated copies; source URL groups corrections.
    normalized=' '.join(event.title.lower().split())
    story_key=hashlib.sha256(normalized.encode()).hexdigest()
    if event.provider=='sec_document':
        parent=conn.execute('SELECT * FROM evidence WHERE id=?',(event.metadata.get('parent_evidence_id'),)).fetchone()
        if not parent or parent['provider']!='sec' or parent['provider_event_id']!=event.event_id or parent['url']!=url:
            raise ValueError('document parent does not resolve to primary evidence')
        story_key=parent['story_key']
    previous=conn.execute('SELECT * FROM evidence WHERE provider=? AND provider_event_id=? ORDER BY revision DESC LIMIT 1',(event.provider,event.event_id)).fetchone()
    if previous:
        story_key=previous['story_key']
        first_seen=previous['first_seen_at']
    else:
        first_seen=now.isoformat()
    existing=conn.execute('SELECT id FROM evidence WHERE provider=? AND provider_event_id=? AND content_hash=?',(event.provider,event.event_id,digest)).fetchone()
    if existing: return existing['id'],False
    age=(now-datetime.fromisoformat(published)).total_seconds()
    backfill=int(initial or replay or age>7200)
    # Source text isn't fetched; preserve title and references, not licensed article bodies.
    eid=conn.execute('''INSERT INTO evidence(provider,provider_event_id,revision,url,title,published_at,first_seen_at,retrieved_at,content_hash,story_key,tickers,provenance,access_category,claim_type,author,institution,metadata,backfill) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(event.provider,event.event_id,1 if not previous else previous['revision']+1,url,event.title[:2000],published,first_seen,now.isoformat(),digest,story_key,json.dumps(symbols),event.provenance,event.access_category,event.claim_type,event.author,event.institution,json.dumps(event.metadata),backfill)).lastrowid
    return int(eid),True
