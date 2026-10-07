"""Automatic evidence-weighted cases and descriptive price scenarios, not trade execution."""
import math
from datetime import datetime,timezone

def assess(result,direction):
 if direction not in ('up','down'):raise ValueError('Choose up or down')
 events=result['events'];symbol=result['company']['symbol'];signals=[];seen=set()
 tags={'RevenueFromContractWithCustomerExcludingAssessedTax':'Revenue','Revenues':'Revenue','SalesRevenueNet':'Revenue','OperatingIncomeLoss':'Operating profit','NetIncomeLoss':'Net profit','NetCashProvidedByUsedInOperatingActivities':'Operating cash flow'}
 for e in sorted(events,key=lambda e:(e.get('evidence_meta',{}).get('end',''),e['published_at']),reverse=True):
  m=e.get('evidence_meta',{});label=tags.get(m.get('tag'))
  if not label or label in seen:continue
  seen.add(label)
  change=next((c for c in e['research'].get('calculations',[]) if c['label']=='Year-over-year change'),None)
  if not change:continue
  value=change['value'];support=(value>0 if direction=='up' else value<0)
  signals.append({'kind':'fundamental','supports':support,'text':f"{label} {'increased' if value>=0 else 'decreased'} {abs(value):.1f}% versus the matched prior-year period ending {m.get('end')}.",
   'evidence_ids':change['evidence_ids'],'period_end':m.get('end')})
 history=result.get('price_history',{});q=history.get('statistics',{});scenarios=None
 fresh=history.get('status')=='available' and q.get('status')=='available'
 if fresh:
  mom=q['momentum_20'];signals.append({'kind':'price','supports':mom>0 if direction=='up' else mom<0,'text':f"The stock {'rose' if mom>=0 else 'fell'} {abs(mom)*100:.1f}% over 20 sessions. Trend persistence is a hypothesis, not a guarantee.",'evidence_ids':[]})
  sigma=q['realized_volatility_20'];close=q['latest_close'];scenarios=[]
  for n in (5,20):
   move=sigma*math.sqrt(n/252)
   scenarios.append({'sessions':n,'reference_price':close,'lower':close*math.exp(-move),'upper':close*math.exp(move),
    'method':'Symmetric ±recent daily standard deviation × √sessions in log-price space; zero assumed drift. A sensitivity scenario, not a confidence interval or prediction.',
    'as_of_session':q['as_of_session']})
 ratios=result.get('financial_context',{}).get(symbol,[])
 latest={}
 for r in sorted(ratios,key=lambda r:r['period_end'],reverse=True):latest.setdefault(r['label'],r)
 risks=[]
 for label,test,meaning in [('Current ratio',lambda x:x<1,'Reported short-term assets were smaller than short-term obligations.'),('Interest coverage',lambda x:x<1,'Operating profit did not cover reported interest expense.'),('Cash conversion',lambda x:x<0,'Reported profit was accompanied by negative operating cash flow.'),('Liabilities / assets',lambda x:x>100,'Recorded liabilities exceeded recorded assets.')]:
  r=latest.get(label)
  if r and test(r['value']):risks.append({'text':meaning+' Period ended '+r['period_end']+'.','evidence_ids':r['evidence_ids']})
 support=[s for s in signals if s['supports']];against=[s for s in signals if not s['supports']]
 # Do not translate a tally of correlated business metrics into a probability or position size.
 support_state='mixed' if support and against else 'supported historical case' if support else 'opposing evidence' if against else 'insufficient evidence'
 case=f"{symbol}'s {'upward' if direction=='up' else 'downward'} case has {support_state}."
 explanation='Improving demand, profits and cash generation could strengthen the business, if sustained and not already reflected in its price.' if direction=='up' else 'Weakening demand, profit or cash generation could pressure the business, if sustained and not already reflected in its price.'
 missing=[]
 if not fresh:missing.append('Fresh completed-session price history and sufficient observations')
 missing.extend(['Confirmed upcoming catalyst/date','Current options chain, executable bid/ask and implied volatility','Documented market expectations and valuation context'])
 reported=[]
 for e in sorted(events,key=lambda x:x['published_at'],reverse=True):
  if e.get('evidence_meta',{}).get('source_kind')!='publisher RSS headline':continue
  age=(datetime.now(timezone.utc)-datetime.fromisoformat(e['published_at'].replace('Z','+00:00'))).days
  if 0<=age<=7:reported.append({'title':e['title'],'url':e.get('readable_url',e['url']),'published_at':e['published_at'],'evidence_id':e['id'],'status':'reported; corroboration required'})
  if len(reported)>=4:break
 citations=[]
 ids={eid for s in signals+risks for eid in s.get('evidence_ids',[])}
 for e in events:
  if e['id'] in ids:citations.append({'evidence_id':e['id'],'title':e.get('display_title',e['title']),'url':e.get('readable_url',e['url'])})
 return {'symbol':symbol,'direction':direction,'decision':'WATCH' if support else 'WAIT','contract_decision':'WAIT','summary':case,'mechanism':explanation,
  'supporting':support,'counterevidence':against,'reported_developments':reported,'funding_risks':risks,'scenarios':scenarios,'citations':citations[:12],
  'horizon':'5–20 trading sessions for price sensitivity; business evidence refers to reported fiscal periods.',
  'catalyst':'Next company update; upcoming date not confirmed.',
  'invalidation':['A new disclosure reverses the observed financial pattern.','The selected price trend reverses or is explained by a corporate action.','Option pricing implies more movement than the evidence-based scenario justifies.'],
  'missing':missing,'next_step':'Monitor the automatically collected company evidence; specific contracts remain unavailable until quotes and event timing are connected.',
  'methods':'Matched-period year-over-year changes; cash conversion and coverage ratios; completed-session momentum and volatility sensitivity. No investor success claim or forecast probability.',
  'limitations':['Historical fundamentals can lag current conditions. Indicators may be correlated; their count is not a probability.','No independent source contradicting a claim does not prove the claim true.'],
  'as_of':datetime.now(timezone.utc).isoformat(),'evidence_support':support_state}
