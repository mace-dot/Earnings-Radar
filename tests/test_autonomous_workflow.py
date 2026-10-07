from datetime import datetime,timezone,timedelta
import pytest
from web.api._live import quote_payload,live_quote
from web.api._workflow import build,changes
from web.api._options_research import payoff,inspect_contract,research
from web.api._evaluation import evaluate
from web.api._research import financial_context,sector_context
from web.api._assistant import validate_model
from web.api._market import history

NOW=datetime(2026,10,7,16,tzinfo=timezone.utc)

def evidence(**patch):
    return {'id':'source1','title':'Reported revenue improved','url':'https://www.sec.gov/filing',
        'published_at':'2026-10-06T14:00:00Z','retrieved_at':'2026-10-07T15:00:00Z',
        'evidence_meta':{'tag':'Revenues'},'provenance':'primary',**patch}

def result(events=None):
    return {'events':events if events is not None else [evidence()], 'price_history':{},
        'strategies':{'up':{'evidence_support':'mixed','supporting':[{'text':'Revenue improved','evidence_ids':['source1']}],
            'counterevidence':[{'text':'Cash weakened'}],'invalidation':['New primary evidence reverses the pattern.']}},'sector_context':{}}

def test_workflow_is_idempotent_and_filters_future_and_unobserved_evidence():
    r=result([evidence(),evidence(id='future',published_at='2026-10-08T00:00:00Z'),evidence(id='unobserved',retrieved_at='2026-10-08T00:00:00Z')])
    a=build(r,NOW);b=build(r,NOW+timedelta(minutes=1))
    assert a['source_ids']==['source1'] and a['decision_id']==b['decision_id']
    assert len(a['roles'])==10 and not a['forecast_issued'] and not a['execution_enabled']
    assert a['cases']['up']['contract']=='WAIT' and a['cases']['up']['counterevidence']
    assert changes(a,b)['status']=='unchanged'

def test_workflow_new_evidence_changes_identity_and_does_not_make_profit_odds():
    a=build(result(),NOW);b=build(result([evidence(),evidence(id='new')]),NOW)
    assert a['decision_id']!=b['decision_id']
    assert changes(a,b)['added_source_ids']==['new']
    assert all(p['state']!='RESEARCH_CANDIDATE' for p in b['playbooks'])

def test_syndicated_headlines_are_grouped():
    a=evidence(evidence_meta={'source_kind':'publisher RSS headline'},claim_type='reporting')
    b={**a,'id':'second','url':'https://finance.yahoo.com/story'}
    assert len(build(result([a,b]),NOW)['claims'])==1

def test_quote_validation_and_venue_scope():
    raw={'quotes':{'AAPL':{'t':NOW.isoformat(),'bp':100,'ap':100.02,'bs':2,'as':3}}}
    q=quote_payload('AAPL',raw,NOW)
    assert q['status']=='fresh_quote' and not q['entry_eligible'] and q['feed']=='IEX'
    assert quote_payload('AAPL',raw,NOW+timedelta(seconds=20))['status']=='stale'
    raw['quotes']['AAPL']['bp']=110
    with pytest.raises(ValueError):quote_payload('AAPL',raw,NOW)

def test_rights_gate_precedes_provider_and_database_mutation(monkeypatch):
    monkeypatch.delenv('RADAR_MARKET_DISPLAY_AUTHORIZED',raising=False)
    monkeypatch.delenv('RADAR_OPTIONS_DISPLAY_AUTHORIZED',raising=False)
    class Store:
        def rpc(self,*a,**kw):raise AssertionError('No unentitled retrieval')
        def request(self,*a,**kw):raise AssertionError('No unentitled retrieval')
    assert live_quote(Store(),'AAPL')['status']=='authorization_required'
    assert research(Store(),'AAPL')['contracts']==[]

def test_unconfirmed_public_rights_do_not_leak_existing_bars(monkeypatch):
    monkeypatch.delenv('RADAR_MARKET_DISPLAY_AUTHORIZED',raising=False)
    class Store:
        def request(self,*a,**kw):return [{'payload':{'bars':[{'session':'2026-10-06','c':100}]}}]
    assert history(Store(),'AAPL')['bars']==[]

def test_long_option_can_lose_with_correct_direction():
    call=payoff('call',100,5,103);put=payoff('put',100,4,98)
    assert call['expiry_profit_loss']==-200 and call['premium_at_risk']==500
    assert put['expiry_profit_loss']==-200 and put['expiry_break_even']==96
    assert payoff('call',100,5,90,multiplier=10)['premium_at_risk']==50
    with pytest.raises(ValueError):payoff('call',100,float('nan'),100)
    with pytest.raises(ValueError):payoff('call',100,5,100,multiplier=True)

def option_raw():
    return {'latestQuote':{'t':NOW.isoformat(),'bp':2,'ap':2.4,'bs':10,'as':10},'greeks':{'delta':.5}}

def test_indicative_options_and_unknown_metadata_are_not_executable():
    c=inspect_contract('AAPL261106C00100000',option_raw(),'AAPL',NOW)
    assert c['decision']=='WAIT' and c['multiplier'] is None
    assert any('Indicative' in x for x in c['reasons']) and any('Spread' in x for x in c['reasons'])
    assert c['scenario_probabilities'] is None and c['personal_quantity'] is None
    with pytest.raises(ValueError):inspect_contract('MSFT261106C00100000',option_raw(),'AAPL',NOW)

def test_stale_option_and_expiry_rejected():
    raw=option_raw();raw['latestQuote']['t']=(NOW-timedelta(minutes=1)).isoformat()
    c=inspect_contract('AAPL261007P00100000',raw,'AAPL',NOW,feed='opra')
    assert any('stale' in x for x in c['reasons']) and any('Expiry' in x for x in c['reasons'])


def test_sector_ratios_are_suppressed_for_banks():
    def fact(tag,val):return {'id':tag,'tickers':['BANK'],'published_at':'2026-10-01T00:00:00Z','evidence_meta':{'tag':tag,'value':val,'units':'USD','end':'2026-06-30','sic':'6021'}}
    events=[fact('AssetsCurrent',10),fact('LiabilitiesCurrent',100),fact('Assets',100),fact('Liabilities',120)]
    assert sector_context(events)['kind']=='bank'
    assert financial_context(events,'BANK')==[]


def snapshot():
    return {'horizon_sessions':2,'payload':{'as_of':'2026-10-07T16:00:00Z','price_context':{'status':'available','statistics':{'latest_close':100,'as_of_session':'2026-10-06'}}}}

def test_outcome_does_not_use_same_day_unavailable_close_or_invent_option_returns():
    bars=[{'session':d,'c':c} for d,c in [('2026-10-06',100),('2026-10-07',999),('2026-10-08',102),('2026-10-09',103)]]
    e=evaluate(snapshot(),bars)
    assert e['outcome_session']=='2026-10-09' and e['underlying_return']==pytest.approx(.03)
    assert e['option_outcome'] is None and not e['forecast_evaluated']
    assert evaluate(snapshot(),bars[:-1])['status']=='pending'
    bars[0]['c']=50
    assert evaluate(snapshot(),bars)['status']=='data_blocked'


def test_future_reference_and_duplicate_bars_rejected():
    s=snapshot();s['payload']['price_context']['statistics']['as_of_session']='2026-10-08'
    with pytest.raises(ValueError):evaluate(s,[])
    with pytest.raises(ValueError):evaluate(snapshot(),[{'session':'2026-10-06','c':100}]*2)


def test_llm_numeric_claims_need_supplied_evidence():
    payload={'answer':'Revenue rose 99.9%.','citations':[{'evidence_id':'source1','quote':'Reported revenue improved'}],'invalidation':[]}
    with pytest.raises(ValueError):validate_model(payload,[evidence()])

def test_user_policy_audit_fields_are_present():
    from web.api._policy import CONTRACT
    decision=build(result(),NOW)
    assert all(k in decision for k in CONTRACT['audit_required_fields'])
    assert CONTRACT['status']=='PROPOSED_NOT_ACTIVE'

def test_hidden_xbrl_and_scripts_do_not_become_evidence_passages():
    from web.api._collector import excerpts
    rows=excerpts(b'<html><ix:hidden><p>Revenue secret code and hidden funding context should never appear here.</p></ix:hidden><div style="display: none">Debt hidden content should never become an excerpt.</div><p>Revenue increased during this period, while cash flow declined materially.</p></html>')
    assert len(rows)==1 and 'Revenue increased' in rows[0]['text']
    assert not any('hidden' in r['text'] for r in rows)

def test_walk_forward_purges_unavailable_outcomes_and_never_promotes():
    from web.api._validation import walk_forward
    rows=[]
    base=datetime(2026,1,1,tzinfo=timezone.utc)
    for i in range(16):
        issued=base+timedelta(days=i*2)
        rows.append({'id':str(i),'issued_at':issued.isoformat(),'outcome_at':(issued+timedelta(days=3)).isoformat(),
            'feature_cutoff':issued.isoformat(),'probability':.6,'outcome':i%2,'universe':'US common','target':'up','horizon_sessions':2})
    r=walk_forward(rows,min_train=4,test_size=4)
    assert r['folds'] and not r['model_promoted'] and not r['live_forecasts_enabled']
    assert r['folds'][0]['training_count']==7
    assert r['folds'][0]['count']==4 and 'baseline_brier' in r['folds'][0]
    rows[0]['feature_cutoff']=(base+timedelta(days=1)).isoformat()
    with pytest.raises(ValueError):walk_forward(rows,min_train=4,test_size=4)

def test_deep_collection_finds_quarterly_report_beyond_insider_filings():
    import json
    from web.api._collector import collect_company
    forms=['4']*35+['8-K','10-Q']
    recent={'form':forms,'accessionNumber':[f'0000320193-26-{i:06d}' for i in range(len(forms))],
        'primaryDocument':['other.htm']*35+['current.htm','quarter.htm'],
        'acceptanceDateTime':['2026-10-06T12:00:00Z']*len(forms),'reportDate':['2026-06-30']*len(forms)}
    class Fetch:
        urls=[]
        def json(self,url):
            if '/submissions/' in url:return {'name':'Apple','sic':'3571','filings':{'recent':recent}}
            return {}
        def get(self,url,limit=None):
            self.urls.append(url)
            if 'companyfacts' in url:return json.dumps({'facts':{'us-gaap':{}}}).encode()
            return b'<p>Revenue improved during the quarter, while cash flow and debt obligations require further review.</p>'
    f=Fetch();rows=collect_company(f,'AAPL','0000320193')
    assert any(u.endswith('/quarter.htm') for u in f.urls)
    assert any(e['evidence_meta'].get('form')=='10-Q' and e['evidence_meta'].get('excerpts') for e in rows)

def test_share_counts_are_not_displayed_as_dollars():
    from web.api._sources import readable
    r=readable({'id':'a','provider':'sec_fundamentals','title':'Shares','tickers':['TEST'],'url':'https://data.sec.gov/a','evidence_meta':{'tag':'CommonStockSharesOutstanding','value':120,'units':'shares'}})
    assert r['display_value']=='120 shares' and 'Common shares outstanding' in r['display_title']
