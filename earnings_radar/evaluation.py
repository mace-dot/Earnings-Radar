"""Conservative paper candidates. No eligible quote means no trade suggestion."""
from datetime import datetime,timezone
import json
from earnings_radar.paper import cost,expiration_pnl,validate_legs,SUPPORTED
from earnings_radar.quote_selection import select_quote,rejection_reasons
from earnings_radar.validation import number
from earnings_radar.db import utc_now

def evaluate(event,quotes,*,strategy='long_straddle',quantity=1,fees=2.0,slippage=.05,now=None,capital=None,risk_limit=None):
    now=now or datetime.now(timezone.utc)
    if strategy not in SUPPORTED:raise ValueError('unsupported strategy')
    quantity=number(quantity,integer=True,positive=True)
    fees=number(fees);slippage=number(slippage)
    if quantity is None or fees is None or slippage is None:raise ValueError('quantity, fees and slippage required')
    q=select_quote(event,quotes,now=now,live=True)
    base={'evaluated_at':now.isoformat(),'event_snapshot':dict(event),'strategy':strategy,'simulation':True,'fill_assumption':'Ask plus configured per-share slippage; fills and quote sizes are not guaranteed','fees':fees,'slippage_per_share':slippage,'model_version':'deterministic-evaluator-v1'}
    if q is None:
        reasons=sorted({r for quote in quotes if quote.get('ticker')==event.get('ticker') for r in rejection_reasons(quote,event,now=now,live=True)})
        return {**base,'eligible':False,'action':'wait','reasons':reasons or ['no_option_quote'],'legs':[]}
    legs=[dict(side='buy',quantity=quantity,strike=q['strike'],expiration=q['expiration'],option_type=kind,multiplier=q['multiplier'],contract_id=q[kind+'_contract_id'],premium=q[kind+'_ask']+slippage) for kind in SUPPORTED[strategy]]
    max_loss=cost(legs,fees)
    if capital is not None and max_loss>number(capital):return {**base,'eligible':False,'action':'wait','reasons':['exceeds_configured_capital'],'legs':[]}
    if risk_limit is not None and max_loss>number(risk_limit):return {**base,'eligible':False,'action':'wait','reasons':['exceeds_configured_risk_limit'],'legs':[]}
    debit=max_loss/(quantity*q['multiplier'])
    breakevens=[q['strike']+debit] if strategy=='long_call' else ([q['strike']-debit] if strategy=='long_put' else [q['strike']-debit,q['strike']+debit])
    scenarios=[{'spot':round(q['stock_price']*(1+change),2),'expiration_pnl':expiration_pnl(legs,q['stock_price']*(1+change),fees),'label':f'{change:+.0%} spot at expiration; illustrative, not forecast'} for change in (-.2,-.1,0,.1,.2)]
    return {**base,'eligible':True,'action':'evaluate defined-risk strategy','reasons':[],'legs':legs,'quote_snapshot':dict(q),'maximum_loss':max_loss,'cost':max_loss,'expiration_breakevens':breakevens,'expiration_scenarios':scenarios,'quote_age_seconds':(now-datetime.fromisoformat(q['quote_timestamp'])).total_seconds(),'feed_type':q['feed_type'],'limitations':['No intraday valuation without validated volatility and time inputs','No consensus/expected-move estimate','Quote sizes and real fills unverified','No brokerage execution']}

def record(conn,payload,*,alert_id=None,evidence_id=None):
    # quote identity is in an immutable snapshot; application and research DB IDs differ.
    return int(conn.execute('INSERT INTO evaluations(alert_id,evidence_id,created_at,config,payload) VALUES (?,?,?,?,?)',(alert_id,evidence_id,utc_now(),json.dumps({'schema':'v1','simulation':True}),json.dumps(payload))).lastrowid)

def journal_candidate(conn,evaluation_id,*,thesis='',invalidation=''):
    from earnings_radar.db import add_paper_trade
    from earnings_radar.sources import research_path
    row=conn.execute('SELECT * FROM evaluations WHERE id=?',(evaluation_id,)).fetchone()
    if not row:raise ValueError('evaluation missing')
    p=json.loads(row['payload'])
    if not p['eligible']:raise ValueError('cannot journal rejected candidate')
    q=p['quote_snapshot'];legs=p['legs']
    # Caller must refresh evaluation before journaling; no stale cached trading pick.
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(p['evaluated_at'])).total_seconds()
    if age>60 or age<0:raise ValueError('evaluation expired; refresh quotes')
    return add_paper_trade(conn,{'ticker':q['ticker'],'strategy':p['strategy'],'strike':q['strike'],'expiration':q['expiration'],'contracts':legs[0]['quantity'],'entry_date':datetime.now(timezone.utc).date().isoformat(),'entry_call_ask':next((l['premium'] for l in legs if l['option_type']=='call'),None),'entry_put_ask':next((l['premium'] for l in legs if l['option_type']=='put'),None),'entry_debit':sum(l['premium'] for l in legs),'fees':p['fees'],'thesis':thesis,'invalidation':invalidation,'evaluation_id':evaluation_id,'origin':'conservative_simulation','call_contract_id':q.get('call_contract_id'),'put_contract_id':q.get('put_contract_id'),'multiplier':q['multiplier']})

def evaluate_research_event(evidence,events,quotes,*,now=None):
    now=now or datetime.now(timezone.utc)
    tickers=json.loads(evidence['tickers'])
    upcoming=[e for e in events if e['ticker'] in tickers and e['earnings_date']>=now.date().isoformat() and e.get('superseded_by') is None]
    if not upcoming:
        result={'eligible':False,'action':'wait','reasons':['no_verified_upcoming_earnings_schedule','no_synchronized_executable_option_data'],'legs':[],'simulation':True,'evaluated_at':now.isoformat(),'model_version':'deterministic-evaluator-v1'}
    else:result=evaluate(min(upcoming,key=lambda e:e['earnings_date']),quotes,now=now)
    result['evidence_snapshot']={k:evidence[k] for k in ('id','provider','provider_event_id','revision','url','title','published_at','content_hash')}
    return result
