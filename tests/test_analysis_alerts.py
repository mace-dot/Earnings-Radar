from datetime import datetime,timezone,timedelta
import json
import pytest
from earnings_radar.db import init_db,get_conn
from earnings_radar.ingestion import ingest
from earnings_radar.providers.base import Event
from earnings_radar.analysis import factual_analysis,process_pending
from earnings_radar.analysis_schema import validate_analysis
from earnings_radar.alerts import upsert_alert,process_delivery
from earnings_radar.settings import Settings
from earnings_radar.model import reserve
from earnings_radar.systemic import assess

NOW=datetime(2026,10,6,18,tzinfo=timezone.utc)
def setup(tmp_path,backfill=False):
    path=init_db(tmp_path/'r.db')
    with get_conn(path) as c:
        eid,_=ingest(c,Event('fed_press','1','https://www.federalreserve.gov/a.htm','FOMC monetary policy announcement',NOW.isoformat()),now=NOW,initial=backfill)
        evidence=dict(c.execute('SELECT * FROM evidence WHERE id=?',(eid,)).fetchone())
    return path,evidence

def test_facts_resolve_and_no_invented_companies(tmp_path):
    _,e=setup(tmp_path);p=factual_analysis(e).model_dump()
    p['confirmed_facts'][0]['excerpt']='Fabricated earnings beat'
    with pytest.raises(ValueError):validate_analysis(p,e)
    p=factual_analysis(e).model_dump();p['affected_tickers']=['FAKE']
    with pytest.raises(ValueError):validate_analysis(p,e)

def test_secondary_statement_not_enacted(tmp_path):
    _,e=setup(tmp_path);e.update(title='Trump says tariffs may rise',provenance='secondary')
    a=factual_analysis(e)
    assert a.policy_status=='statement' and a.category=='political'
    assert a.hypotheses==[]

def test_budget_and_model_failure_fallback(tmp_path,monkeypatch):
    p,e=setup(tmp_path);monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-only')
    settings=Settings(model_enabled=True,model_daily_budget=.1)
    class Broken:
        def analyze(self,*args):raise TimeoutError()
    assert process_pending(p,settings,model=Broken())==1
    with get_conn(p) as c:
        assert c.execute('SELECT model_version FROM analyses').fetchone()[0]=='deterministic-v2'
        assert 'failed:TimeoutError' in c.execute('SELECT config FROM analyses').fetchone()[0]
        assert not reserve(c,.1)
        assert c.execute('SELECT COUNT(*) FROM alerts').fetchone()[0]==1

def test_disabled_and_replay_do_not_notify(tmp_path,monkeypatch):
    p,e=setup(tmp_path,True)
    settings=Settings(telegram_enabled=True,telegram_verified=True)
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN','fixture');monkeypatch.setenv('TELEGRAM_CHAT_ID','fixture')
    process_pending(p,settings)
    with get_conn(p) as c:assert c.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]==0
    assert process_delivery(p,Settings(), 'one',now=NOW)==0

def test_delivery_retry_and_quiet_hours(tmp_path,monkeypatch):
    p,e=setup(tmp_path);settings=Settings(telegram_enabled=True,telegram_verified=True)
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN','fixture');monkeypatch.setenv('TELEGRAM_CHAT_ID','fixture')
    process_pending(p,settings)
    with get_conn(p) as c:c.execute('UPDATE outbox SET next_attempt=0')
    class Fails:
        def send(self,payload):raise ConnectionError()
    assert process_delivery(p,settings,'one',sender=Fails(),now=NOW)==1
    with get_conn(p) as c:assert c.execute('SELECT status FROM outbox').fetchone()[0]=='retry'
    assert process_delivery(p,settings,'two',sender=Fails(),now=NOW+timedelta(seconds=1))==0
    night=NOW.replace(hour=3)
    with get_conn(p) as c:c.execute('UPDATE outbox SET next_attempt=0')
    assert process_delivery(p,settings,'one',sender=Fails(),now=night)==0
    class Works:
        def send(self,payload):pass
    with get_conn(p) as c:c.execute('UPDATE outbox SET next_attempt=0')
    assert process_delivery(p,settings,'one',sender=Works(),now=NOW+timedelta(minutes=10))==1

def test_correction_updates_original_alert(tmp_path):
    p,e=setup(tmp_path);s=Settings();process_pending(p,s)
    with get_conn(p) as c:ingest(c,Event('fed_press','1',e['url'],'Correction: policy announcement',NOW.isoformat()),now=NOW)
    process_pending(p,s)
    with get_conn(p) as c:
        assert c.execute('SELECT COUNT(*) FROM alerts').fetchone()[0]==1
        assert c.execute('SELECT revision FROM alerts').fetchone()[0]==2

def test_missing_systemic_data_is_unknown():
    result=assess({},NOW)
    assert all(v['status']=='unknown' for v in result['dimensions'].values())
    assert result['probability'] is None
