"""Permitted snapshot adapter and deterministic long-option economics gates."""
import math, os, re
from datetime import datetime,timezone
try:
    from ._live import provider_get
    from ._policy import POLICY
except ImportError:
    from _live import provider_get
    from _policy import POLICY


def payoff(kind,strike,premium,target,multiplier=100):
    values=(strike,premium,target,multiplier)
    if kind not in ('call','put') or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in values) or strike<=0 or premium<=0 or target<0 or multiplier<=0:
        raise ValueError('Invalid long-option inputs')
    intrinsic=max(target-strike if kind=='call' else strike-target,0)
    return {'premium_at_risk':premium*multiplier,'expiry_break_even':strike+premium if kind=='call' else strike-premium,
        'expiry_profit_loss':(intrinsic-premium)*multiplier,'fees_included':False,'valuation':'expiry only; not an early-exit value'}


def inspect_contract(symbol,raw,underlying,now=None,metadata=None,feed='indicative'):
    now=now or datetime.now(timezone.utc);metadata=metadata or {}
    m=re.fullmatch(r'([A-Z]{1,6})(\d{6})([CP])(\d{8})',symbol)
    if not m:raise ValueError('Unsupported OCC identifier')
    if m[1]!=underlying:raise ValueError('Contract underlying mismatch')
    expiry=datetime.strptime(m[2],'%y%m%d').date();dte=(expiry-now.date()).days
    strike=int(m[4])/1000
    if strike<=0:raise ValueError('Invalid strike')
    kind='call' if m[3]=='C' else 'put'
    q=raw.get('latestQuote') or {};reasons=[]
    if feed!='opra':reasons.append('Indicative prices are not executable OPRA quotes')
    try:
        t=datetime.fromisoformat(q['t'].replace('Z','+00:00'));age=(now-t).total_seconds()
        bid,ask=float(q['bp']),float(q['ap']);sizes=[float(q[k]) for k in ('bs','as')]
        if not t.tzinfo or age< -2 or age>POLICY['option_quote_max_age_seconds']:reasons.append('Quote is stale or has invalid timing')
        if not all(math.isfinite(v) and v>0 for v in [bid,ask]+sizes) or bid>=ask:raise ValueError('Invalid option quote')
    except (KeyError,TypeError,ValueError):
        bid=ask=None;age=None;reasons.append('Executable bid/ask and sizes are missing or invalid')
    mid=(bid+ask)/2 if bid is not None else None
    spread=ask-bid if bid is not None else None
    if mid and (spread/mid>POLICY['spread_fraction_review'] or spread>POLICY['spread_dollars_review']):reasons.append('Spread exceeds proposed research screen')
    delta=(raw.get('greeks') or {}).get('delta')
    if isinstance(delta,bool) or not isinstance(delta,(int,float)) or not math.isfinite(delta):delta=None;reasons.append('Actual/model-labeled delta unavailable')
    elif not POLICY['delta_range'][0]<=abs(delta)<=POLICY['delta_range'][1]:reasons.append('Delta outside proposed comparison range')
    if not POLICY['expiry_days_range'][0]<=dte<=POLICY['expiry_days_range'][1]:reasons.append('Expiry outside proposed comparison range')
    multiplier=metadata.get('multiplier')
    if isinstance(multiplier,bool) or not isinstance(multiplier,(int,float)) or not math.isfinite(multiplier) or multiplier<=0:
        multiplier=None;reasons.append('Contract multiplier and adjustment metadata need verification')
    if metadata.get('adjusted') is not False:reasons.append('Standard unadjusted contract status unverified')
    reasons+=['Confirmed future catalyst and event-expiry alignment unavailable','Exchange session status unverified','No validated contract-return forecasting model']
    scenarios=[]
    # Educational expiry sensitivity can be calculated only with verified metadata.
    if ask and multiplier and metadata.get('adjusted') is False:
        for move in (-.10,0,.10):
            scenarios.append({'underlying_move':move,**payoff(kind,strike,ask,metadata['reference_price']*(1+move),multiplier)}) if metadata.get('reference_price') else None
    return {'contract_id':symbol,'kind':kind,'expiry':expiry.isoformat(),'strike':strike,'days_to_expiry':dte,
        'bid':bid,'ask':ask,'spread_fraction':spread/mid if mid else None,'quote_age_seconds':age,
        'delta':delta,'multiplier':multiplier,'feed':feed,'decision':'WAIT','reasons':list(dict.fromkeys(reasons)),
        'scenarios':scenarios,'scenario_probabilities':None,'personal_quantity':None,'policy_version':POLICY['version']}


def research(store,symbol):
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,14}',symbol):raise ValueError('Invalid ticker')
    if os.getenv('RADAR_OPTIONS_DISPLAY_AUTHORIZED','false').lower()!='true':
        return {'status':'authorization_required','contracts':[],'reason':'Options data use and quote-feed entitlement are not confirmed. No manual strategy input is required.'}
    directory=store.request('radar_universe',query='select=active&symbol=eq.'+symbol+'&limit=1')
    if not directory or not directory[0]['active']:raise ValueError('Unsupported company')
    feed=os.getenv('RADAR_OPTIONS_FEED','indicative')
    if feed not in ('indicative','opra'):raise ValueError('Unsupported options feed')
    key='options:'+symbol
    if store.rpc('radar_claim_data',{'p_key':key,'p_seconds':60}):
        try:
            raw=provider_get('/v1beta1/options/snapshots/'+symbol,{'feed':feed,'limit':100})
            contracts=[]
            for cid,value in list(raw.get('snapshots',{}).items())[:100]:
                try:contracts.append(inspect_contract(cid,value,symbol,feed=feed))
                except (ValueError,TypeError):continue
            result={'status':'research_only','feed':feed,'contracts':contracts[:20],
                'coverage':'bounded first page; not a complete chain' if raw.get('next_page_token') else 'provider snapshot response',
                'retrieved_at':datetime.now(timezone.utc).isoformat(),'reason':'Contract metadata, catalysts and validation remain independent gates.'}
            store.request('radar_data_cache',query='id=eq.'+key,rows={'payload':result,'last_error':None},method='PATCH')
        except Exception:
            store.request('radar_data_cache',query='id=eq.'+key,rows={'last_error':'Options source unavailable'},method='PATCH')
    rows=store.request('radar_data_cache',query='select=payload,last_error&id=eq.'+key+'&limit=1')
    row=rows[0] if rows else {};result=dict(row.get('payload') or {})
    if not result:return {'status':'unavailable','contracts':[],'reason':row.get('last_error') or 'No eligible observations'}
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(result['retrieved_at'])).total_seconds()
    if age>30:
        result['status']='stale'
        result['contracts']=[{**c,'decision':'WAIT','reasons':list(dict.fromkeys(c['reasons']+['Cached quote exceeds freshness limit']))} for c in result.get('contracts',[])]
    return {**result,'last_error':row.get('last_error')}
