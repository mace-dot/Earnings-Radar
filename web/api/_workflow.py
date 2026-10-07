"""Bounded, reproducible analyst roles. No LLM votes, forecasts or trade execution."""
import hashlib, json, uuid
from datetime import datetime, timezone
try:
    from ._policy import POLICY_VERSION,CONTRACT
except ImportError:
    from _policy import POLICY_VERSION,CONTRACT

VERSION = 'autonomous-evidence-workflow-1'


def available_events(events, cutoff):
    result=[]
    for e in events:
        try:
            stamps=[datetime.fromisoformat(e[k].replace('Z','+00:00')) for k in ('published_at','retrieved_at')]
            if all(t.tzinfo and t<=cutoff for t in stamps): result.append(e)
        except (KeyError,TypeError,ValueError): continue
    return result


def build(result, now=None):
    now=now or datetime.now(timezone.utc)
    events=available_events(result.get('events',[]),now)[:600]
    ids={e['id'] for e in events}
    strategies=result.get('strategies',{})
    claims=[];groups=set()
    for e in sorted(events,key=lambda e:e['published_at'],reverse=True):
        group=e.get('story_key') or e.get('content_hash') or e['id']
        # Repeated syndication cannot count as independent corroboration.
        title=' '.join(e.get('title','').lower().split())
        if e.get('claim_type')=='reporting':group=hashlib.sha256(title.encode()).hexdigest()
        if group in groups:continue
        groups.add(group)
        m=e.get('evidence_meta',{})
        for x in m.get('excerpts',[])[:3]:
            if x.get('text'):claims.append({'text':x['text'][:1200],'evidence_id':e['id'],'source_group':group,
                'kind':'primary_passage' if e.get('provenance')=='primary' else 'publisher_claim',
                'url':e.get('readable_url',e['url']),'published_at':e['published_at']})
        if m.get('source_kind')=='publisher RSS headline':claims.append({'text':e['title'],'evidence_id':e['id'],
            'source_group':group,'kind':'reported_headline','url':e.get('readable_url',e['url']),'published_at':e['published_at']})
        if len(claims)>=24:break
    prices=result.get('price_history',{})
    price_ready=prices.get('status')=='available' and prices.get('statistics',{}).get('status')=='available'
    financial=any(e.get('evidence_meta',{}).get('tag') for e in events)
    sector=result.get('sector_context',{})
    latest=max((e['published_at'] for e in events),default=None)
    statistics=prices.get('statistics',{}) if price_ready else {}
    market_finding=f"20-session change {statistics['momentum_20']*100:.2f}%; venue-scoped volume, institutional flow unverified." if isinstance(statistics.get('momentum_20'),(int,float)) else 'Venue-scoped historical behavior unavailable; institutional flows unverified.'
    vol_finding=f"Annualized 20-session realized movement {statistics['realized_volatility_20']*100:.2f}%; backward-looking, not option-implied volatility." if isinstance(statistics.get('realized_volatility_20'),(int,float)) else 'Realized movement is unavailable; option value requires a suitable feed.'
    business_signals=(strategies.get('up',{}).get('supporting',[])+strategies.get('up',{}).get('counterevidence',[]))
    fundamental_texts=[x['text'] for x in business_signals if x.get('kind')=='fundamental']
    fundamental_finding=' '.join(fundamental_texts)[:900] or 'No matched-period business comparison is available yet.'
    roles=[
        {'role':'discovery','status':'complete' if events else 'data_blocked','finding':f'{len(events)} available evidence records; repeated stories are grouped.','evidence_ids':sorted(ids)[:20]},
        {'role':'fundamentals','status':'complete' if financial else 'data_blocked','finding':fundamental_finding,'evidence_ids':[e['id'] for e in events if e.get('evidence_meta',{}).get('tag')][:20]},
        {'role':'market_structure','status':'complete' if price_ready else 'data_blocked','finding':market_finding,'missing':[] if price_ready else ['Eligible completed-session price history']},
        {'role':'volatility','status':'complete' if price_ready else 'data_blocked','finding':vol_finding},
        {'role':'catalyst','status':'data_blocked','finding':'Recent disclosures are observed events; no confirmed future earnings date is connected.'},
        {'role':'expectations','status':'data_blocked','finding':'A contrarian edge needs a dated expectation benchmark; narrative disagreement is insufficient.'},
        {'role':'strategy','status':'complete' if strategies else 'data_blocked','finding':'Business, timing and contract verdicts are assessed separately.'},
        {'role':'skeptic','status':'complete','finding':'Check recurring versus temporary gains, price-in expectations, correlated metrics and timing mismatch.'},
        {'role':'risk','status':'complete','finding':'Specific contracts remain blocked without eligible quotes and horizon checks; personalized sizing is unassessed.'},
        {'role':'evaluation','status':'model_unvalidated','finding':'No calibrated success odds or proven forecasting model is active.'}]
    cases={}
    for direction,s in strategies.items():
        valid_support=[x for x in s.get('supporting',[]) if all(i in ids for i in x.get('evidence_ids',[]))]
        cases[direction]={'business':s.get('evidence_support','insufficient evidence'),
            'timing':'watch' if price_ready else 'data_blocked','contract':'WAIT',
            'supporting':valid_support,'counterevidence':s.get('counterevidence',[]),
            'invalidation':s.get('invalidation',[])}
    playbooks=[{'name':'Fundamental catalyst','state':'WATCH' if financial else 'DATA_BLOCKED','reason':'Business evidence exists; dated future catalyst remains unverified.'},
        {'name':'Trend continuation','state':'WATCH' if price_ready else 'DATA_BLOCKED','reason':'Descriptive trend requires registered triggers and prospective validation.'},
        {'name':'Volatility expansion','state':'WATCH' if price_ready else 'DATA_BLOCKED','reason':'Historical range change alone does not establish cheap options or direction.'},
        {'name':'Funding pressure','state':'WATCH' if financial else 'DATA_BLOCKED','reason':sector.get('note','Obligation timing and funding alternatives require deeper primary evidence.')},
        {'name':'Expectations divergence','state':'DATA_BLOCKED','reason':'Dated market expectations are missing.'}]
    feature_context={k:prices.get(k) for k in ('status','feed','retrieved_at','statistics')}
    identity=hashlib.sha256(json.dumps({'version':VERSION,'policy':POLICY_VERSION,'ids':sorted(ids),'instrument':result.get('company',{}),
        'price':feature_context,'sector':sector},sort_keys=True,allow_nan=False).encode()).hexdigest()
    instrument=result.get('company',{})
    observations=sorted(ids)
    supporting=list(dict.fromkeys(i for s in strategies.values() for x in s.get('supporting',[]) for i in x.get('evidence_ids',[]) if i in ids))
    opposing=list(dict.fromkeys(i for s in strategies.values() for x in s.get('counterevidence',[]) for i in x.get('evidence_ids',[]) if i in ids))
    missing=list(dict.fromkeys(x for s in strategies.values() for x in s.get('missing',[])))
    return {'instrument_id':{'symbol':instrument.get('symbol'),'cik':instrument.get('cik'),'exchange':instrument.get('exchange'),'identity_scope':'SEC issuer mapping; tradable common-equity identity needs market-provider verification'},
        'strategy_version':VERSION,'observation_ids':observations,'feature_versions':{'financial':'matched-period-2','market':'daily-descriptive-1'},
        'supporting_claim_ids':supporting,'counterevidence_ids':opposing,'missing_reasons':missing,
        'eligibility_results':{'price_history':price_ready,'contract':False,'forecast':False,'personal_sizing':False},
        'invalidation_rules':list(dict.fromkeys(x for s in strategies.values() for x in s.get('invalidation',[]))),
        'next_review_trigger':'New primary disclosure, verified market observation, source correction or scheduled periodic research',
        'decision_dimensions':CONTRACT['decision_dimensions'],'decision_id':str(uuid.uuid5(uuid.NAMESPACE_URL,identity)),'input_hash':identity,
        'engine_version':VERSION,'policy_version':POLICY_VERSION,'as_of':now.isoformat(),
        'state':'WATCH' if events else 'RESEARCHING','capability_flags':['MODEL_UNVALIDATED','PERSONAL_SIZING_UNASSESSED']+([] if price_ready else ['DATA_BLOCKED']),
        'summary':((' '.join(fundamental_texts[:2]) or fundamental_finding)+' Timing and option value require separate confirmation.') if events else 'Collecting verified evidence before forming a case.',
        'latest_evidence_at':latest,'source_count':len(ids),'source_ids':sorted(ids),'claims':claims[:24],
        'roles':roles,'cases':cases,'playbooks':playbooks,'price_context':feature_context,
        'next_checks':['Confirm the next company event from an official calendar or release.','Check fresh contract quotes, spreads and premium sensitivity.','Compare the business change with a dated expectation benchmark.'],
        'forecast_issued':False,'model_enabled':False,'execution_enabled':False,
        'limitations':['Logical analyst roles share evidence; agreement is not independent confirmation.','No calibrated probabilities, executable strategy or personalized quantity is inferred.']}


def changes(previous,current):
    if not previous:return {'status':'first_snapshot','summary':'First retained research decision; no earlier comparison exists.','added_source_ids':current['source_ids'][:20]}
    old=set(previous.get('source_ids',[]));new=set(current.get('source_ids',[]))
    return {'status':'changed' if previous.get('input_hash')!=current.get('input_hash') else 'unchanged',
        'summary':f'{len(new-old)} new evidence records; {len(old-new)} records outside the current bounded view.',
        'added_source_ids':sorted(new-old)[:20],'removed_source_ids':sorted(old-new)[:20],
        'previous_as_of':previous.get('as_of'),'current_as_of':current.get('as_of')}
