from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import pandas as pd
import pytest
from earnings_radar.db import SCHEMA_SQL, init_db, get_conn, insert_earnings_event, insert_option_quote
from earnings_radar.imports import validate_earnings_df, validate_options_df, load_sample_data
from earnings_radar.quote_selection import select_quote, rejection_reasons, cutoff
from earnings_radar.paper import expiration_pnl, cost

NOW = datetime(2026,10,6,18,tzinfo=timezone.utc)
EVENT = dict(ticker='AAA',earnings_date='2026-10-15',earnings_time='AMC',confirmation_status='Confirmed',source='IR')
def quote(**updates):
    return dict(ticker='AAA',stock_price=100,strike=100,expiration='2026-10-23',call_bid=4,call_ask=5,put_bid=4,put_ask=5,quote_timestamp=NOW.isoformat(),underlying_timestamp=NOW.isoformat(),call_timestamp=NOW.isoformat(),put_timestamp=NOW.isoformat(),feed_type='live',call_contract_id='CALL',put_contract_id='PUT',**updates)

def test_legacy_migration_preserves_and_backs_up(tmp_path):
    path=tmp_path/'old.db'
    with sqlite3.connect(path) as c:
        c.executescript(SCHEMA_SQL)
        c.execute("INSERT INTO research_notes(ticker,category,source_url,notes,created_at,updated_at) VALUES ('AAA','other','','keep','t','t')")
        c.execute("INSERT INTO paper_trades(ticker,strategy,entry_date,created_at,updated_at) VALUES ('AAA','long_strangle','2026-01-01','t','t')")
    init_db(path); init_db(path)
    with get_conn(path) as c:
        assert c.execute('SELECT notes FROM research_notes').fetchone()[0]=='keep'
        assert c.execute('SELECT strategy FROM paper_trades').fetchone()[0]=='long_strangle'
        assert c.execute('SELECT MAX(version) FROM schema_version').fetchone()[0]==4
        assert c.execute('SELECT COUNT(*) FROM paper_legs').fetchone()[0]==0
    assert len(list((tmp_path/'backups').glob('*.bak')))==1

def test_samples_cannot_erase_real_data(tmp_path,monkeypatch):
    import earnings_radar.db as db
    real=tmp_path/'real.db'; monkeypatch.setattr(db,'DB_PATH',real);init_db(real)
    with get_conn(real) as c: insert_earnings_event(c,EVENT)
    load_sample_data(db_path=tmp_path/'demo.db')
    with get_conn(real) as c: assert c.execute('SELECT ticker FROM earnings_events').fetchone()[0]=='AAA'
    with pytest.raises(ValueError): load_sample_data(db_path=real)

@pytest.mark.parametrize('value',['2026-02-30','2026-01-01trailing','01/01/2026',pd.NA])
def test_invalid_date(value):
    _,errors=validate_earnings_df(pd.DataFrame([{**EVENT,'earnings_date':value}]))
    assert errors

@pytest.mark.parametrize('changes',[{'call_ask':float('inf')},{'put_bid':-1},{'call_bid':6},{'strike':0},{'call_volume':1.2},{'quote_timestamp':'2099-01-01T00:00:00Z'}])
def test_reject_invalid_quotes(changes):
    q=quote();q.update(changes)
    _,errors=validate_options_df(pd.DataFrame([q]));assert errors

def test_missing_and_zero_are_distinct():
    q=quote();q.update(call_bid=0,call_volume=0,stock_price=pd.NA)
    cleaned,errors=validate_options_df(pd.DataFrame([q]));assert not errors
    assert cleaned.iloc[0]['call_bid']==0 and cleaned.iloc[0]['stock_price'] is None

def test_fresh_selection_and_amc():
    old=quote();old.update(quote_timestamp=(NOW-timedelta(days=3)).isoformat())
    fresh=quote();fresh.update(strike=105)
    assert select_quote(EVENT,[old,fresh],now=NOW)['strike']==105
    same=quote();same.update(expiration='2026-10-15')
    assert select_quote(EVENT,[same],now=NOW) is None
    assert select_quote({**EVENT,'earnings_time':'BMO'},[same],now=NOW)
    assert select_quote({**EVENT,'earnings_time':'Unknown'},[fresh],now=NOW,live=True) is None

def test_latest_invalid_snapshot_does_not_fall_back():
    valid=quote(); bad=quote();bad.update(call_timestamp=(NOW-timedelta(seconds=10)).isoformat(),id=2)
    assert select_quote(EVENT,[valid,bad],now=NOW,live=True) is None

def test_calendar_holiday_and_early_close():
    assert cutoff('2026-11-27').hour==18  # 13:00 New York
    assert cutoff('2026-12-25').date().isoformat()=='2026-12-24'

def test_schedule_revision_identity(tmp_path):
    p=tmp_path/'r.db';init_db(p)
    with get_conn(p) as c:
        first=insert_earnings_event(c,{**EVENT,'provider':'IR','provider_event_id':'Q3'})
        second=insert_earnings_event(c,{**EVENT,'provider':'IR','provider_event_id':'Q3','earnings_date':'2026-10-16'})
        assert first!=second
        assert c.execute('SELECT COUNT(*) FROM earnings_events WHERE superseded_by IS NULL').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM earnings_revisions').fetchone()[0]==1

def test_leg_payoff_and_multiplier():
    legs=[dict(side='buy',quantity=2,strike=100,expiration='2026-10-23',option_type='call',multiplier=10,premium=5)]
    assert cost(legs,2)==102
    assert expiration_pnl(legs,110,2)==98
    assert expiration_pnl(legs,90,2)==-102
