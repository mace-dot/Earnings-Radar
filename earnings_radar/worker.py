"""Browser-independent, single-host collection worker. python -m earnings_radar.worker."""
import argparse
import json
import os
import signal
import threading
import uuid
from datetime import datetime, timezone
from earnings_radar.db import init_db,get_conn,utc_now
from earnings_radar.settings import Settings
from earnings_radar.jobs import seed,claim,finish,verify_lease
from earnings_radar.ingestion import ingest
from earnings_radar.providers.official_feeds import OfficialFeeds,FEEDS
from earnings_radar.providers.sec import SEC,CIKS
from earnings_radar.providers.news import AlpacaNews
from earnings_radar.providers.market_data import AlpacaMarketData
from earnings_radar.providers.base import ProviderError

class Worker:
    def __init__(self,path=None,settings=None):
        from earnings_radar.sources import prepare
        self.path=prepare(path)
        self.settings=settings or Settings()
        self.owner=str(uuid.uuid4())
        self.stop=threading.Event()
        self.feeds=OfficialFeeds()
        self.news=AlpacaNews()
        self.market=AlpacaMarketData()
        self.ciks={**CIKS,**json.loads(os.getenv('RADAR_CIK_MAP','{}'))}
        names=list(FEEDS)+['sec:'+t for t in self.settings.watchlist]+['alpaca_news','alpaca_market']
        with get_conn(self.path) as conn: seed(conn,names)

    def heartbeat(self,status='running'):
        with get_conn(self.path) as conn:
            conn.execute('INSERT INTO worker_health VALUES (?,?,?) ON CONFLICT(owner) DO UPDATE SET heartbeat=excluded.heartbeat,status=excluded.status',(self.owner,utc_now(),status))

    def collect(self,job):
        name=job['name'];checkpoint=job['checkpoint']
        if name in FEEDS: return self.feeds.collect(name),[],utc_now()
        if name.startswith('sec:'):
            t=name.split(':',1)[1]
            if t not in self.ciks: raise ProviderError('CIK mapping missing for '+t)
            return SEC(self.settings.sec_user_agent).collect(t,self.ciks[t]),[],utc_now()
        if name=='alpaca_news':
            events,cp=self.news.collect(self.settings.watchlist,checkpoint)
            return events,[],cp
        if name=='alpaca_market': return [],self.market.collect(self.settings.watchlist),utc_now()
        raise ProviderError('unknown job')

    def tick(self):
        self.heartbeat()
        with get_conn(self.path) as conn: job=claim(conn,self.owner)
        if not job: return False
        try:
            events,observations,checkpoint=self.collect(job)
            with get_conn(self.path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                verify_lease(conn,job['name'],self.owner)
                for event in events: ingest(conn,event,initial=job['last_success'] is None)
                for q in observations:
                    conn.execute('INSERT OR IGNORE INTO market_observations(ticker,provider,observed_at,retrieved_at,feed_type,payload) VALUES (?,?,?,?,?,?)',(q['ticker'],q['provider'],q['timestamp'],utc_now(),q['feed_type'],json.dumps(q)))
                finish(conn,job['name'],self.owner,checkpoint=checkpoint,interval=self.settings.poll_seconds)
        except Exception as exc:
            # Never put provider response bodies, secrets or arbitrary exception URLs in logs.
            error=str(exc) if isinstance(exc,ProviderError) else type(exc).__name__
            with get_conn(self.path) as conn:
                try: finish(conn,job['name'],self.owner,error=error,max_attempts=self.settings.max_attempts)
                except RuntimeError: pass
        self.heartbeat()
        return True

    def process(self):
        from earnings_radar.analysis import process_pending
        from earnings_radar.alerts import process_delivery
        process_pending(self.path,self.settings)
        process_delivery(self.path,self.settings,self.owner)

    def run(self,once=False):
        try:
            while not self.stop.is_set():
                worked=self.tick()
                self.process()
                if once:
                    if not worked: break
                else: self.stop.wait(1 if worked else 10)
        finally: self.heartbeat('stopped')

def main():
    p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');p.add_argument('--db');args=p.parse_args()
    worker=Worker(args.db)
    for sig in (signal.SIGTERM,signal.SIGINT): signal.signal(sig,lambda *_:worker.stop.set())
    worker.run(args.once)

if __name__=='__main__': main()
