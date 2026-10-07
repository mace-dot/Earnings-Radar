"""Explainable research interpretation; calculations never become forecasts."""
from datetime import datetime, timezone
import math

LABELS = {'RevenueFromContractWithCustomerExcludingAssessedTax':'Revenue','Revenues':'Revenue','SalesRevenueNet':'Revenue',
 'GrossProfit':'Gross profit','NetIncomeLoss':'Net income','OperatingIncomeLoss':'Operating income',
 'NetCashProvidedByUsedInOperatingActivities':'Operating cash flow','PaymentsToAcquirePropertyPlantAndEquipment':'Capital expenditure',
 'Assets':'Assets','Liabilities':'Liabilities','StockholdersEquity':'Shareholders’ equity','InterestExpense':'Interest expense'}

def stamp(s):
    try:
        d=datetime.fromisoformat(s.replace('Z','+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError,TypeError,AttributeError): return None

def duration(m):
    start,end=stamp(m.get('start')),stamp(m.get('end'))
    return (end-start).days if start and end else None

def comparables(event,events):
    m=event.get('evidence_meta',{}); end=stamp(m.get('end')); days=duration(m)
    if not end or days is None: return None
    matches=[]
    for other in events:
        o=other.get('evidence_meta',{}); oe=stamp(o.get('end')); od=duration(o)
        if other.get('tickers')!=event.get('tickers') or o.get('tag')!=m.get('tag') or not oe or od is None:continue
        if 300 <= (end-oe).days <=400 and abs(days-od)<=10 and o.get('units')==m.get('units'):
            matches.append(other)
    return max(matches,key=lambda x:x.get('published_at',''),default=None)

def interpretation(e,events,now=None):
    now=now or datetime.now(timezone.utc); m=e.get('evidence_meta',{}); a=e.get('analysis',{})
    tag=m.get('tag'); value=m.get('value'); label=LABELS.get(tag,tag or 'Reported result')
    facts=[{'text':f.get('excerpt',''),'evidence_id':e['id'],'url':e['url']} for f in a.get('confirmed_facts',[]) if f.get('excerpt')]
    excerpt=m.get('excerpts',[])
    facts += [{'text':s['text'],'evidence_id':e['id'],'url':e['url']} for s in excerpt[:3] if s.get('text')]
    result={'takeaway':e['title'],'mechanism':a.get('economic_mechanism','Read the primary source before drawing conclusions.'),
      'facts':facts,'calculations':[],'bull':a.get('bullish_implications',[]),'bear':a.get('bearish_implications',[]),
      'counterevidence':a.get('counterevidence',[]) or ['No independent counterevidence has been collected; absence is not confirmation.'],
      'expectations':'Not established: no dated consensus or market-expectation series is connected.',
      'contrarian_status':'unverified','action':'Investigate','next_step':'Compare the primary document with prior results, guidance, and price reaction.',
      'catalyst':'Next verified company announcement; its date is not confirmed.',
      'horizon':a.get('time_horizon','Unspecified'),
      'invalidation':a.get('invalidation_conditions',[]) or ['A source correction or conflicting primary evidence.'],
      'missing':list(dict.fromkeys(a.get('missing_information',[])+['Documented consensus expectations','Verified valuation and executable market data'])),
      'category':a.get('category','general'),'confidence':'Primary-source support; investment implications remain hypotheses.'}
    if tag and isinstance(value,(float,int)) and math.isfinite(value):
        result['takeaway']=f"{label} was ${value:,.0f} for the reported period ending {m.get('end','unknown')}."
        prior=comparables(e,events)
        if prior and prior['evidence_meta'].get('value'):
            pv=prior['evidence_meta']['value']; pct=(value-pv)/abs(pv)*100
            result['calculations'].append({'label':'Year-over-year change','value':pct,'unit':'%', 'evidence_ids':[e['id'],prior['id']],
                                          'explanation':'Comparable reported periods; changes from losses use the absolute prior value.'})
            result['takeaway']+=f" That is {'up' if pct>=0 else 'down'} {abs(pct):.1f}% versus a comparable prior-year period."
        if 'Revenue' in (tag or '') or tag=='Revenues':
            result['mechanism']='Revenue measures business demand and scale. Growth creates value only if margins, cash conversion, and the price paid support it.'
            result['bull']=['If comparable revenue growth converts into cash without margin deterioration, operating value could improve.']
            result['bear']=['Growth may require expensive investment or be below expectations; rising revenue alone does not establish an attractive valuation.']
            result['next_step']='Compare revenue growth with margins, operating cash flow, and management’s dated outlook.'
        elif tag in ('GrossProfit','OperatingIncomeLoss','NetIncomeLoss'):
            result['mechanism']='Profit changes can reflect demand, pricing, costs, or one-off accounting effects. Compare matched-period revenue and cash flow before interpreting durability.'
            result['bull']=['If profit improvement is recurring and cash-backed, the business may have more operating flexibility.']
            result['bear']=['One-off gains, weak cash conversion, or already-high expectations can undermine the apparent improvement.']
            result['next_step']='Check recurring versus one-off drivers and matched-period margins and cash conversion.'
        elif tag=='NetCashProvidedByUsedInOperatingActivities':
            result['mechanism']='Operating cash funds investment, debt service, and shareholder returns. Working-capital timing can distort a single period.'
            result['bull']=['Sustained cash generation could reduce external financing needs.']
            result['bear']=['Temporary working-capital benefits can reverse; capital spending and debt obligations may absorb cash.']
            result['next_step']='Compare cash generation with capital expenditure, net income, and working-capital changes.'
        else:
            result['mechanism']='This reported balance or cash-flow item needs matched-period context; its isolated size does not establish financial strength.'
            result['bull']=['If matched-period ratios improve and cash obligations remain manageable, financial resilience could improve.']
            result['bear']=['A balance alone can obscure maturity, quality, or financing risks.']
        result['horizon']='Historical reported financial period; not a forward earnings forecast.'
        result['invalidation']=['Restated results or incompatible fiscal periods.', 'Full filing details showing the change is nonrecurring or materially offset.']
    elif e.get('provider','').startswith('fed_'):
        title=e['title'].lower()
        if any(w in title for w in ('rate','monetary','fomc')):
            result['takeaway']='A Federal Reserve update may change the financing and discount-rate backdrop. The actual policy details matter more than the headline.'
            result['mechanism']='Interest rates influence borrowing costs and the present value of future cash flows. Effects vary with leverage, duration, and what was already expected.'
        else:
            result['takeaway']='An official Federal Reserve development is worth checking for changes to funding, regulation, or financial conditions.'
            result['mechanism']='Changes to funding or regulation can alter financing costs and financial-sector constraints. Company exposure needs separate evidence.'
        if e.get('claim_type')=='opinion':result['takeaway']='A Federal Reserve speaker expressed a view; this is not an enacted policy change.'
        result['bull']=['Easier-than-expected financing conditions could help rate-sensitive businesses, if documented.']
        result['bear']=['Tighter-than-expected conditions could pressure funding and valuations; the expectation gap is currently unverified.']
        result['next_step']='Read the official wording, distinguish speech from enacted policy, and compare with dated expectations.'
        result['catalyst']='Next official policy communication; no directional prediction.'
        result['category']='systemic'
    elif e.get('provider') in ('sec','sec_document'):
        form=m.get('form') or ('8-K' if '8-K' in e['title'] else '10-Q' if '10-Q' in e['title'] else '10-K' if '10-K' in e['title'] else 'filing')
        result['takeaway']=f"A new {form} disclosure is available. {'Relevant passages have been retrieved below.' if excerpt else 'The filing type alone does not establish a positive or negative surprise.'}"
        result['mechanism']='Company disclosures can change estimates of cash flows, obligations, and risk. Establish the specific change and compare it with prior disclosures before assigning direction.'
        result['bull']=['A documented improvement in recurring earnings, liquidity, or outlook could strengthen the business case.']
        result['bear']=['New obligations, weaker outlook, or deteriorating cash conversion could weaken it; a filing itself is not bullish.']
        result['next_step']='Read the extracted passages and compare the financial drivers with the prior filing.'
    if m.get('source_kind')=='publisher RSS headline':
        result['takeaway']=e['title']
        result['mechanism']='This is a timestamped publisher headline or official economic release. Read the source and corroborate the specific company exposure; the headline alone does not establish direction or causation.'
        result['next_step']='Compare this report with company disclosures and observed market history. Full restricted article text has not been collected.'
        result['confidence']='Publisher reporting, not an independently verified company fact.' if e.get('provenance')=='secondary' else 'Official release headline; details require reading the source.'
        result['bull']=['If corroborated details improve cash-flow prospects or financing conditions, the business case may strengthen.']
        result['bear']=['If corroborated details weaken cash flows or increase financing pressure, the business case may weaken.']
    published=stamp(e.get('published_at')); age=(now-published).total_seconds()/86400 if published else float('inf')
    parts={'source_support':20 if e.get('provenance','primary')=='primary' else 8,
           'freshness':20 if 0<=age<=2 else 12 if 0<=age<=7 else 4 if 0<=age<=30 else 0,
           'specific_evidence':20 if tag or excerpt else 5,
           'financial_comparison':15 if result['calculations'] else 0,
           'context_completeness':5,'missing_expectations':-10,'missing_market_context':-5}
    result['ranking']={'score':max(0,sum(parts.values())),'components':parts,'meaning':'Research priority, not probability of profit.',
                       'eligible_weekly':0<=age<=7 and sum(parts.values())>=40 and bool(tag or excerpt)}
    result['published_age_days']=round(age,1) if math.isfinite(age) else None
    return result

def enrich(events,now=None):
    for e in events:e['research']=interpretation(e,events,now)
    return sorted(events,key=lambda e:(e['research']['ranking']['score'],e.get('published_at','')),reverse=True)

def financial_context(events,symbol):
    facts=[e for e in events if symbol in e.get('tickers',[]) and e.get('evidence_meta',{}).get('tag')]
    groups={}
    for e in facts:
        m=e['evidence_meta'];key=(m.get('start'),m.get('end'),m.get('units'));g=groups.setdefault(key,{})
        tag=m['tag']
        if tag not in g or e['published_at']>g[tag]['published_at']:g[tag]=e
    output=[]
    for period,g in sorted(groups.items(),key=lambda x:x[0][1] or '',reverse=True):
        revenue=next((g[t] for t in ('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet') if t in g),None)
        def ratio(label,a,b,scale=1):
            if a and b and b['evidence_meta']['value']>0:
                output.append({'label':label,'value':a['evidence_meta']['value']/b['evidence_meta']['value']*scale,'period_end':period[1],
                               'evidence_ids':[a['id'],b['id']],'unit':'%' if scale==100 else 'x'})
        for tag,label in [('GrossProfit','Gross margin'),('OperatingIncomeLoss','Operating margin'),('NetIncomeLoss','Net margin')]:ratio(label,g.get(tag),revenue,100)
        ratio('Cash conversion',g.get('NetCashProvidedByUsedInOperatingActivities'),g.get('NetIncomeLoss'))
        if g.get('NetCashProvidedByUsedInOperatingActivities') and g.get('PaymentsToAcquirePropertyPlantAndEquipment'):
            a=g['NetCashProvidedByUsedInOperatingActivities'];b=g['PaymentsToAcquirePropertyPlantAndEquipment']
            output.append({'label':'Free cash flow proxy','value':a['evidence_meta']['value']-b['evidence_meta']['value'],'period_end':period[1],
                           'evidence_ids':[a['id'],b['id']],'unit':'USD','limitation':'Operating cash flow less reported property/plant/equipment purchases; not all forms of investment.'})
        ratio('Interest coverage',g.get('OperatingIncomeLoss'),g.get('InterestExpense'))
        ratio('Current ratio',g.get('AssetsCurrent'),g.get('LiabilitiesCurrent'))
        ratio('Liabilities / assets',g.get('Liabilities'),g.get('Assets'),100)
    return output[:30]
