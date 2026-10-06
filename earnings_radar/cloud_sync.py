"""Publish validated public research to Supabase, without private SQLite tables."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from earnings_radar.db import get_conn
from earnings_radar.analysis_schema import validate_analysis
from web.api._store import Store


def record(row):
    payload = json.loads(row['payload'])
    analysis = validate_analysis(payload, row).model_dump()
    # SQLite numeric IDs are local to each run. Replace references with stable cloud IDs.
    identity = hashlib.sha256(json.dumps([row['provider'], row['provider_event_id'], row['content_hash']]).encode()).hexdigest()
    analysis['event_id'] = identity
    for fact in analysis['confirmed_facts']:
        fact['evidence_id'] = identity
    return {'id': identity, 'provider': row['provider'], 'provider_event_id': row['provider_event_id'],
            'content_hash': row['content_hash'], 'title': row['title'], 'url': row['url'],
            'institution': row['institution'] or '', 'published_at': row['published_at'],
            'retrieved_at': row['retrieved_at'], 'tickers': json.loads(row['tickers']), 'analysis': analysis}


def publish(path, store=None):
    store = store or Store()
    with get_conn(path) as conn:
        rows = conn.execute('''SELECT e.*, a.payload FROM evidence e JOIN analyses a ON a.id =
            (SELECT MAX(a2.id) FROM analyses a2 WHERE a2.evidence_id=e.id)
            ORDER BY e.published_at DESC LIMIT 500''').fetchall()
        jobs = [dict(r) for r in conn.execute('SELECT name,last_success,last_error,status FROM jobs')]
        sources = [dict(r) for r in conn.execute('SELECT * FROM source_registry')]
    records = [record(dict(r)) for r in rows]
    for start in range(0, len(records), 25):
        store.request('radar_events', rows=records[start:start+25])
    store.request('radar_status', rows=[{'id': 'collector', 'updated_at': datetime.now(timezone.utc).isoformat(),
                                       'payload': {'jobs': jobs, 'sources': sources, 'cadence': 'hourly_scheduled'}}])
    return len(records)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--db', required=True); args = p.parse_args()
    print(f'Published {publish(args.db)} validated research revisions')

if __name__ == '__main__':
    main()
