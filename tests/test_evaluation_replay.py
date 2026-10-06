from datetime import datetime,timezone,timedelta
import json
import pytest
from earnings_radar.evaluation import evaluate,record
from earnings_radar.replay import run
from earnings_radar.db import init_db,get_conn
from earnings_radar.ingestion import ingest
from earnings_radar.providers.base import Event
from test_integrity import EVENT,quote,NOW


def test_fresh_candidate_math_and_fees():
    q=quote();result=evaluate(EVENT,[q],now=NOW,fees=2,slippage=.05)
    assert result['eligible'] and result['maximum_loss']==1012
    assert result['expiration_breakevens']==pytest.approx([89.88,110.12])
    assert result['expiration_scenarios'][2]['expiration_pnl']==-1012
    assert len(result['legs'])==2

@pytest.mark.parametrize('changes',[{'feed_type':'sample'},{'feed_type':'delayed'},{'adjusted':1},{'multiplier':10},{'underlying_timestamp':(NOW-timedelta(minutes=2)).isoformat()}])
def test_no_stale_or_nonstandard_candidate(changes):
    q=quote();q.update(changes)
    assert not evaluate(EVENT,[q],now=NOW)['eligible']

def test_risk_limits_require_user_value():
    result=evaluate(EVENT,[quote()],now=NOW,risk_limit=100)
    assert not result['eligible'] and result['reasons']==['exceeds_configured_risk_limit']

def test_replay_uses_known_revisions_and_cannot_notify(tmp_path):
    p=init_db(tmp_path/'r.db')
    with get_conn(p) as c:
        event=Event('fixture','1','https://www.sec.gov/a','First report',NOW.isoformat())
        ingest(c,event,now=NOW,replay=True)
        ingest(c,Event('fixture','1',event.url,'Revised report',NOW.isoformat()),now=NOW+timedelta(days=1),replay=True)
        report=run(c,NOW+timedelta(hours=1))
        assert report['evidence_count']==1
        assert report['analyses'][0]['confirmed_facts'][0]['excerpt']=='First report'
        assert c.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM alerts').fetchone()[0]==0

def test_snapshot_linked_paper_journal(tmp_path):
    from earnings_radar.evaluation import journal_candidate
    p=init_db(tmp_path/'r.db');now=datetime.now(timezone.utc)
    q=quote();q.update(quote_timestamp=now.isoformat(),underlying_timestamp=now.isoformat(),call_timestamp=now.isoformat(),put_timestamp=now.isoformat(),expiration=(now+timedelta(days=30)).date().isoformat())
    stamp=(now+timedelta(days=30)).strftime('%y%m%d')
    q.update(call_contract_id='AAA'+stamp+'C00100000',put_contract_id='AAA'+stamp+'P00100000')
    event={**EVENT,'earnings_date':(now+timedelta(days=7)).date().isoformat()}
    result=evaluate(event,[q],now=now)
    with get_conn(p) as c:
        evaluation_id=record(c,result)
        trade_id=journal_candidate(c,evaluation_id)
        assert c.execute('SELECT evaluation_id FROM paper_trades WHERE id=?',(trade_id,)).fetchone()[0]==evaluation_id
        assert c.execute('SELECT COUNT(*) FROM paper_legs WHERE trade_id=?',(trade_id,)).fetchone()[0]==2
