"""Immutable underlying monitoring outcomes; no simulated option fills or win rates."""
import hashlib
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

VERSION='underlying-monitor-1'


def evaluate(snapshot,bars):
    payload=snapshot['payload'];context=payload.get('price_context',{})
    q=context.get('statistics') or {};reference=q.get('latest_close');session=q.get('as_of_session')
    if context.get('status')!='available' or not reference or not session:
        return {'status':'data_blocked','reason':'Decision had no eligible recorded price reference','forecast_evaluated':False}
    cutoff=datetime.fromisoformat(payload['as_of'].replace('Z','+00:00'))
    if cutoff.tzinfo is None:raise ValueError('Decision cutoff needs timezone')
    if session>cutoff.astimezone(ZoneInfo('America/New_York')).date().isoformat():raise ValueError('Reference occurred after the decision')
    rows=sorted(bars,key=lambda b:b['session'])
    if len({b['session'] for b in rows})!=len(rows):raise ValueError('Duplicate sessions')
    # Start after the decision date, not after an arbitrarily old reference session.
    day=cutoff.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    future=[b for b in rows if b['session']>day]
    horizon=snapshot.get('horizon_sessions',5)
    if not isinstance(horizon,int) or not 1<=horizon<=60:raise ValueError('Unsupported evaluation horizon')
    if len(future)<horizon:return {'status':'pending','available_future_sessions':len(future),'required_sessions':horizon,'forecast_evaluated':False}
    exit_bar=future[horizon-1]
    # Do not compare histories with inconsistent adjustment versions/feeds.
    reference_bar=next((b for b in rows if b['session']==session),None)
    if not reference_bar or abs(reference_bar['c']/reference-1)>.00001:
        return {'status':'data_blocked','reason':'Reference changed or disappeared; corporate-action reconciliation required','forecast_evaluated':False}
    return {'status':'observed','reference_session':session,'reference_price':reference,'outcome_session':exit_bar['session'],
        'outcome_price':exit_bar['c'],'underlying_return':exit_bar['c']/reference-1,'horizon_sessions':horizon,
        'method':VERSION,'forecast_evaluated':False,'trade_return':None,'option_outcome':None,
        'reference_not_trade_entry':True,
        'meaning':'Change from a retained historical close to a later monitored close; not an executable post-decision return, option result, win rate or validated prediction.'}


def run(store):
    try:
        from ._market import history
    except ImportError:
        from _market import history
    snapshots=store.request('radar_research_snapshots',query='select=*&order=created_at.desc&limit=50')
    counts={'observed':0,'pending':0,'data_blocked':0}
    for s in snapshots:
        h=history(store,s['symbol'])
        out=evaluate(s,h.get('bars',[]))
        counts[out['status']]+=1
        if out['status']=='observed':
            identity=hashlib.sha256((s['id']+VERSION).encode()).hexdigest()
            store.request('radar_evaluations',rows=[{'id':identity,'snapshot_id':s['id'],'payload':out}],ignore=True)
    return counts
