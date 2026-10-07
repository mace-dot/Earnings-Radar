"""Plain-language option research context; no trade eligibility inferred from filings."""
from datetime import datetime,timezone
import math
try:
 from ._research import stamp
except ImportError:
 from _research import stamp

NAMES={'AAPL':'Apple','MSFT':'Microsoft','NVDA':'NVIDIA','TSLA':'Tesla','AMZN':'Amazon','META':'Meta Platforms','GOOG':'Alphabet','GOOGL':'Alphabet','JPM':'JPMorgan Chase','AMD':'AMD','NFLX':'Netflix','WMT':'Walmart','DIS':'Disney','BAC':'Bank of America','XOM':'Exxon Mobil'}

def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def company_board(events,contexts,state,now=None):
 now=now or datetime.now(timezone.utc);output=[]
 for symbol in sorted({s for e in events for s in e.get('tickers',[])}):
  rows=[e for e in events if symbol in e.get('tickers',[])];specific=[e for e in rows if e.get('evidence_meta',{}).get('tag')]
  # Prefer latest reported financial period, then its latest source revision.
  specific.sort(key=lambda e:(e['evidence_meta'].get('end',''),e['published_at'],e['retrieved_at']),reverse=True)
  latest_tags={}
  for e in specific:latest_tags.setdefault(e['evidence_meta']['tag'],e)
  meaningful=next((latest_tags[t] for t in ('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','NetIncomeLoss','OperatingIncomeLoss','NetCashProvidedByUsedInOperatingActivities') if t in latest_tags),None)
  if meaningful:
   growth=next((c['value'] for c in meaningful.get('research',{}).get('calculations',[]) if c['label']=='Year-over-year change'),None)
   business=meaningful.get('research',{}).get('takeaway',meaningful['title'])
   signal='Business growing' if finite(growth) and growth>0 else 'Business slowing' if finite(growth) and growth<0 else 'Comparison needed'
  else:
   meaningful=max(rows,key=lambda e:e['published_at']);business='Company disclosures are available, but the financial change needs verification.';signal='Read the disclosure'
  q=state.get('quantitative',{}).get(symbol,{})
  if q.get('status')=='available':
   day=stamp(q.get('as_of_session'));stale=not day or (now-day).days>5
   ratio=q.get('volatility_ratio');z=q.get('latest_return_zscore')
   movement='Old price data' if stale else 'Unusual daily move' if finite(z) and abs(z)>=2 else 'Movement picking up' if finite(ratio) and ratio>=1.3 else 'Quiet stretch' if finite(ratio) and ratio<.7 else 'Usual recent movement'
   movement_note='Historical price behavior does not tell us the next direction or whether an option is cheap.'
  else:
   movement='Price data needed';movement_note='We cannot judge recent price swings until historical prices are connected.'
  ratios=contexts.get(symbol,[]);latest_ratio={}
  for r in sorted(ratios,key=lambda r:r['period_end'],reverse=True):latest_ratio.setdefault(r['label'],r)
  flags=[]
  for label,test,text in [('Interest coverage',lambda v:v<1,'Reported operating profit did not cover the reported interest bill.'),('Cash conversion',lambda v:v<0,'The company reported profit but money left its day-to-day operations.'),('Liabilities / assets',lambda v:v>100,'Reported obligations were greater than recorded assets.'),('Current ratio',lambda v:v<1,'Short-term assets were smaller than obligations due within a year.')]:
   r=latest_ratio.get(label)
   if r and finite(r['value']) and test(r['value']):flags.append({'text':text,'period_end':r['period_end'],'evidence_ids':r['evidence_ids']})
  output.append({'symbol':symbol,'name':NAMES.get(symbol,symbol),'evidence_id':meaningful['id'],'business':business,'business_signal':signal,
    'movement':movement,'movement_note':movement_note,'quantitative':q,'stress_flags':flags,
    'stress_status':'Funding questions to investigate' if flags else 'Crisis risk not established',
    'direction':'Not confirmed','trade_readiness':'Research only — option prices and upcoming catalysts are not verified',
    'priority':meaningful.get('research',{}).get('ranking',{}).get('score',0),
    'last_source_at':max(e['retrieved_at'] for e in rows),'period_end':meaningful.get('evidence_meta',{}).get('end'),
    'hidden_edge':'Unverified: no documented market-expectation comparison is connected.',
    'catalyst':'Next earnings or company update; date not verified.',
    'next_step':'Check the next catalyst, the direction thesis, and what the option already costs.'})
 return sorted(output,key=lambda x:(len(x['stress_flags']),x['priority']),reverse=True)
