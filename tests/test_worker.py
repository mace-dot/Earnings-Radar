from datetime import datetime,timezone,timedelta
import json
import pytest
from earnings_radar.db import init_db,get_conn
from earnings_radar.jobs import seed,claim,finish
from earnings_radar.ingestion import ingest
from earnings_radar.providers.base import Event,HTTP,ProviderError
from earnings_radar.providers.official_feeds import parse_rss
from earnings_radar.providers.sec import SEC
from earnings_radar.worker import Worker
from earnings_radar.settings import Settings
from earnings_radar.health import snapshot

NOW=datetime(2026,10,6,18,tzinfo=timezone.utc)
def event(**kw):
    values=dict(provider='official',event_id='1',url='https://www.federalreserve.gov/newsevents/pressreleases/example.htm',title='Policy announcement',published_at=NOW.isoformat())
    return Event(**(values|kw))

def test_duplicate_and_revision(tmp_path):
    p=init_db(tmp_path/'r.db')
    with get_conn(p) as c:
        first,new=ingest(c,event(),now=NOW);assert new
        assert ingest(c,event(),now=NOW)==(first,False)
        second,new=ingest(c,event(title='Corrected announcement'),now=NOW);assert new
        assert c.execute('SELECT revision FROM evidence WHERE id=?',(second,)).fetchone()[0]==2
        assert len({r[0] for r in c.execute('SELECT story_key FROM evidence')})==1

def test_backfill_and_replay_suppression(tmp_path):
    p=init_db(tmp_path/'r.db')
    with get_conn(p) as c:
        ingest(c,event(),now=NOW,initial=True)
        ingest(c,event(event_id='2'),now=NOW,replay=True)
        ingest(c,event(event_id='3',published_at=(NOW-timedelta(days=1)).isoformat()),now=NOW)
        assert all(r[0] for r in c.execute('SELECT backfill FROM evidence'))

def test_exclusive_lease_and_recovery(tmp_path):
    p=init_db(tmp_path/'r.db')
    with get_conn(p) as c: seed(c,['feed'])
    with get_conn(p) as c: assert claim(c,'one',now=100)
    with get_conn(p) as c: assert claim(c,'two',now=101) is None
    with get_conn(p) as c: assert claim(c,'two',now=221)
    with get_conn(p) as c:
        with pytest.raises(RuntimeError): finish(c,'feed','one',now=222)
        finish(c,'feed','two',error='HTTP 503',now=222)
    with get_conn(p) as c:
        assert c.execute('SELECT status FROM jobs').fetchone()[0]=='degraded'
        assert claim(c,'three',now=223) is None

def test_feed_parser_and_unsafe_xml():
    rss=b'<rss><channel><item><title>Rates</title><link>https://www.federalreserve.gov/rates.htm</link><guid>123</guid><pubDate>Tue, 06 Oct 2026 14:00:00 -0400</pubDate></item></channel></rss>'
    e=parse_rss(rss,'fed_press')[0]
    assert e.published_at=='2026-10-06T18:00:00+00:00'
    with pytest.raises(Exception): parse_rss(b'<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss>&x;</rss>','fed_press')

def test_connection_failures_visible_and_restart(tmp_path,monkeypatch):
    p=tmp_path/'r.db';w=Worker(p,Settings())
    def fail(job): raise ProviderError('feed unavailable')
    monkeypatch.setattr(w,'collect',fail)
    assert w.tick()
    with get_conn(p) as c:
        assert any(j['last_error']=='feed unavailable' for j in snapshot(c)['jobs'])
    again=Worker(p,Settings())
    assert again.owner!=w.owner
    with get_conn(p) as c: assert c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==10

def test_sec_requires_identification_and_valid_cik():
    with pytest.raises(ProviderError): SEC('Earnings Radar')
    with pytest.raises(ProviderError): SEC('Radar contact@example.org').collect('AAPL','../escape')

def test_request_disallows_retrieved_destinations():
    with pytest.raises(ProviderError): HTTP().request('GET','https://evil.example/api')
    with pytest.raises(ProviderError): HTTP().request('GET','http://data.sec.gov/submissions/x')

def test_sec_fundamentals_preserve_periods_and_precision():
    from earnings_radar.providers.sec_fundamentals import SECFundamentals
    class FixtureHTTP:
        def get_json(self,url):
            return {'units':{'USD':[{'start':'2025-07-01','end':'2025-09-30','filed':'2025-10-30','accn':'old','fy':2025,'fp':'Q3','form':'10-Q','val':100},{'start':'2025-07-01','end':'2025-09-30','filed':'2025-11-10','accn':'amended','fy':2025,'fp':'Q3','form':'10-Q/A','val':110}]}}
    events=SECFundamentals('Radar contact@example.org',FixtureHTTP()).collect('AAPL','0000320193')
    assert len(events)==3
    assert all(e.metadata['value']==110 for e in events)
    assert all(e.metadata['publication_precision']=='filing_date_end_of_day_bound' for e in events)
    assert all(e.published_at.endswith('23:59:59+00:00') for e in events)


def test_news_and_market_fixture_interfaces(monkeypatch):
    from earnings_radar.providers.news import AlpacaNews
    from earnings_radar.providers.market_data import AlpacaMarketData
    monkeypatch.setenv('ALPACA_API_KEY','fixture');monkeypatch.setenv('ALPACA_API_SECRET','fixture')
    class FixtureHTTP:
        def get_json(self,url,**kwargs):
            if '/news' in url:
                assert kwargs['params']['include_content']=='false'
                return {'news':[{'id':1,'url':'https://www.wsj.com/example','headline':'Reported event','created_at':NOW.isoformat(),'updated_at':NOW.isoformat(),'symbols':['AAPL'],'source':'WSJ'}],'next_page_token':'page2'}
            return {'quotes':{'AAPL':{'bp':100,'ap':101,'t':NOW.isoformat(),'bs':1,'as':1}}}
    events,checkpoint=AlpacaNews(FixtureHTTP()).collect(['AAPL'])
    assert events[0].provenance=='secondary' and json.loads(checkpoint)['page_token']=='page2'
    rows=AlpacaMarketData(FixtureHTTP()).collect(['AAPL'])
    assert rows[0]['feed_type']=='indicative' and rows[0]['ask']==101
