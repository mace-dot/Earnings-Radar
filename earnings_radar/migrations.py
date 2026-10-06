"""Numbered, transactional migrations with SQLite online backups."""
from pathlib import Path
from datetime import datetime, timezone
import sqlite3

MIGRATIONS = {
1: '''
ALTER TABLE earnings_events ADD COLUMN provider TEXT NOT NULL DEFAULT 'csv';
ALTER TABLE earnings_events ADD COLUMN provider_event_id TEXT;
ALTER TABLE earnings_events ADD COLUMN fiscal_period TEXT;
ALTER TABLE earnings_events ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE earnings_events ADD COLUMN superseded_by INTEGER REFERENCES earnings_events(id);
ALTER TABLE earnings_events ADD COLUMN feed_type TEXT NOT NULL DEFAULT 'historical';
ALTER TABLE option_quotes ADD COLUMN feed_type TEXT NOT NULL DEFAULT 'historical';
ALTER TABLE option_quotes ADD COLUMN underlying_timestamp TEXT;
ALTER TABLE option_quotes ADD COLUMN call_timestamp TEXT;
ALTER TABLE option_quotes ADD COLUMN put_timestamp TEXT;
ALTER TABLE option_quotes ADD COLUMN call_contract_id TEXT;
ALTER TABLE option_quotes ADD COLUMN put_contract_id TEXT;
ALTER TABLE option_quotes ADD COLUMN multiplier INTEGER NOT NULL DEFAULT 100;
ALTER TABLE option_quotes ADD COLUMN adjusted INTEGER NOT NULL DEFAULT 0;
CREATE TABLE earnings_revisions(id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE paper_legs(id INTEGER PRIMARY KEY, trade_id INTEGER NOT NULL REFERENCES paper_trades(id), side TEXT NOT NULL CHECK(side IN ('buy','sell')), quantity INTEGER NOT NULL CHECK(quantity>0), strike REAL NOT NULL CHECK(strike>0), expiration TEXT NOT NULL, option_type TEXT NOT NULL CHECK(option_type IN ('call','put')), multiplier INTEGER NOT NULL CHECK(multiplier>0), contract_id TEXT, premium REAL NOT NULL CHECK(premium>=0));
CREATE INDEX idx_event_identity ON earnings_events(provider,provider_event_id);
''',
2: '''
CREATE TABLE evidence(id INTEGER PRIMARY KEY, provider TEXT NOT NULL, provider_event_id TEXT NOT NULL, revision INTEGER NOT NULL, url TEXT NOT NULL, title TEXT NOT NULL, published_at TEXT NOT NULL, first_seen_at TEXT NOT NULL, retrieved_at TEXT NOT NULL, content_hash TEXT NOT NULL, story_key TEXT NOT NULL, tickers TEXT NOT NULL, provenance TEXT NOT NULL, access_category TEXT NOT NULL, claim_type TEXT NOT NULL, author TEXT, institution TEXT, metadata TEXT NOT NULL, backfill INTEGER NOT NULL, UNIQUE(provider,provider_event_id,content_hash));
CREATE INDEX idx_evidence_story ON evidence(story_key);
CREATE TABLE jobs(name TEXT PRIMARY KEY, next_run REAL NOT NULL DEFAULT 0, lease_owner TEXT, lease_until REAL NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0, checkpoint TEXT, last_success TEXT, last_error TEXT, status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE worker_health(owner TEXT PRIMARY KEY, heartbeat TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE analyses(id INTEGER PRIMARY KEY, evidence_id INTEGER NOT NULL REFERENCES evidence(id), model_version TEXT NOT NULL, config TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(evidence_id,model_version));
CREATE TABLE relationships(id INTEGER PRIMARY KEY, subject TEXT NOT NULL, related TEXT NOT NULL, kind TEXT NOT NULL, evidence_id INTEGER NOT NULL REFERENCES evidence(id), valid_from TEXT NOT NULL, valid_until TEXT);
CREATE TABLE model_spend(day TEXT PRIMARY KEY, reserved_usd REAL NOT NULL DEFAULT 0);
''',
3: '''
CREATE TABLE alerts(id INTEGER PRIMARY KEY, story_key TEXT NOT NULL UNIQUE, evidence_id INTEGER NOT NULL REFERENCES evidence(id), analysis_id INTEGER NOT NULL REFERENCES analyses(id), severity TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, read_at TEXT, payload TEXT NOT NULL);
CREATE TABLE outbox(id INTEGER PRIMARY KEY, alert_id INTEGER NOT NULL REFERENCES alerts(id), revision INTEGER NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0, lease_owner TEXT, lease_until REAL NOT NULL DEFAULT 0, last_error TEXT, delivered_at TEXT, UNIQUE(alert_id,revision,channel));
''',
6: '''
CREATE TABLE source_registry(id TEXT PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,documentation_url TEXT NOT NULL,access_status TEXT NOT NULL,capabilities TEXT NOT NULL);
''',
5: '''
CREATE TABLE market_observations(id INTEGER PRIMARY KEY,ticker TEXT NOT NULL,provider TEXT NOT NULL,observed_at TEXT NOT NULL,retrieved_at TEXT NOT NULL,feed_type TEXT NOT NULL,payload TEXT NOT NULL, UNIQUE(ticker,provider,observed_at));
''',
4: '''
CREATE TABLE evaluations(id INTEGER PRIMARY KEY, alert_id INTEGER REFERENCES alerts(id), evidence_id INTEGER REFERENCES evidence(id), quote_id INTEGER REFERENCES option_quotes(id), created_at TEXT NOT NULL, config TEXT NOT NULL, payload TEXT NOT NULL);
ALTER TABLE paper_trades ADD COLUMN evaluation_id INTEGER REFERENCES evaluations(id);
ALTER TABLE paper_trades ADD COLUMN origin TEXT NOT NULL DEFAULT 'legacy_manual';
CREATE TABLE replay_runs(id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, as_of TEXT NOT NULL, payload TEXT NOT NULL);
'''
}

def backup(path, destination=None):
    path = Path(path)
    if destination is None:
        folder = path.parent / 'backups'
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / (path.name + '.' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.bak')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('backup integrity check failed')
    return destination

def migrate(conn, path):
    # A single write lock prevents two processes racing migrations/backups.
    conn.execute('BEGIN IMMEDIATE')
    try:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='schema_version'").fetchone()
        version = conn.execute('SELECT COALESCE(MAX(version),0) FROM schema_version').fetchone()[0] if exists else 0
        if version > max(MIGRATIONS):
            raise RuntimeError('database schema is newer than this application')
        pending = sorted(v for v in MIGRATIONS if v > version)
        if pending:
            # The writer has made no changes yet; a separate reader gets a consistent snapshot.
            backup(path)
            conn.execute('CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
            for v in pending:
                for statement in MIGRATIONS[v].split(';'):
                    if statement.strip():
                        conn.execute(statement)
                conn.execute('INSERT INTO schema_version VALUES (?,?)', (v, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
