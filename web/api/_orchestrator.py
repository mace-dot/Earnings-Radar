"""Persistent company research orchestration and honest decision snapshots."""
import json,re,time,uuid
from datetime import datetime,timezone
from urllib.parse import quote
try:
 from ._collector import Fetch,collect_company,collect_feed,CollectionError
 from ._research import enrich,financial_context,sector_context
 from ._board import company_board
 from ._directory import refresh_directory,discover
except ImportError:
 from _collector import Fetch,collect_company,collect_feed,CollectionError
 from _research import enrich,financial_context,sector_context
 from _board import company_board
 from _directory import refresh_directory,discover

try:
 from ._market import history,refresh as refresh_market
 from ._sources import readable
 from ._news import collect_news,refresh_company
 from ._strategy import assess
except ImportError:
 from _market import history,refresh as refresh_market
 from _sources import readable
 from _news import collect_news,refresh_company
 from _strategy import assess

ENGINE='autonomous-evidence-workflow-1'

def valid_symbol(s):return isinstance(s,str) and bool(re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,14}',s))

def company(store,symbol):
 if not valid_symbol(symbol):raise ValueError('Invalid company ticker')
 directory=store.request('radar_universe',query='select=*&symbol=eq.'+symbol+'&limit=1')
 if not directory:raise ValueError('Company not found in the official directory')
 rows=store.request('radar_events',query='select=*&tickers=cs.'+quote(json.dumps([symbol]))+'&order=published_at.desc&limit=600')
 now=datetime.now(timezone.utc)
 try:
  from ._workflow import available_events
 except ImportError:
  from _workflow import available_events
 rows=available_events(rows,now)
 events=[readable(e) for e in enrich(rows)];contexts={symbol:financial_context(events,symbol)}
 status=store.request('radar_status',query='select=*&id=eq.collector&limit=1');state=status[0]['payload'] if status else {}
 prices=history(store,symbol);state=dict(state);state['quantitative']={**state.get('quantitative',{}),symbol:prices.get('statistics',{})}
 boards=company_board(events,contexts,state)
 for b in boards:b['name']=directory[0]['name']
 queue=store.request('radar_research_queue',query='select=symbol,status,reason,last_success,last_error,next_attempt,attempts&symbol=eq.'+symbol+'&limit=1')
 result={'company':directory[0],'events':events,'financial_context':contexts,'move_board':boards,'status':status,'queue':queue[0] if queue else None,
         'automatic_option_evaluation':{'action':'wait','reason':'Authorized options prices, confirmed catalyst timing, and documented expectations are not connected.'},
         'price_history':prices,'assistant_engine':'statistical and fundamental evidence assistant'}
 result['sector_context']=sector_context(events)
 result['strategies']={d:assess(result,d) for d in ('up','down')}
 try:
  from ._workflow import build,changes
 except ImportError:
  from _workflow import build,changes
 result['research_decision']=build(result)
 prior=store.request('radar_research_snapshots',query='select=payload&symbol=eq.'+symbol+'&order=created_at.desc&limit=1')
 previous=prior[0]['payload'] if prior else None
 result['changes']=changes(previous,result['research_decision'])
 if previous and previous.get('input_hash')==result['research_decision']['input_hash']:
  result['research_decision']['as_of']=previous['as_of']
  result['changes']=previous.get('changes',result['changes'])
 return result

def snapshot_row(symbol,result):
 decision=result['research_decision']
 payload={**decision,'action':'wait','summary':result['move_board'][0] if result['move_board'] else {},
          'strategies':result.get('strategies',{}),'changes':result.get('changes',{}),'horizon_kind':'underlying_monitor_not_trade'}
 return {'id':decision['decision_id'],'symbol':symbol,'engine_version':ENGINE,'payload':payload,
                 'target':'research_monitor','horizon_sessions':5,'evaluation_status':'pending_underlying_monitor'}

def snapshot(store,symbol,result):
 store.request('radar_research_snapshots',rows=[snapshot_row(symbol,result)],ignore=True)

def process_one(store,symbol=None):
 owner=str(uuid.uuid4());job=store.rpc('radar_claim_research',{'p_owner':owner,'p_symbol':symbol})
 if not job:return {'status':'queued_or_busy','records':0}
 symbol=job['symbol']
 try:
  directory=store.request('radar_universe',query='select=*&symbol=eq.'+symbol+'&limit=1')
  if not directory:raise CollectionError('Official identifier missing')
  rows=collect_company(Fetch(time.monotonic()+100),symbol,directory[0]['cik'])
  if not rows:raise CollectionError('No supported SEC disclosures found')
  for i in range(0,len(rows),25):store.request('radar_events',rows=rows[i:i+25])
  aliases=list(directory[0].get('aliases',[]))
  for r in rows:aliases.extend(r['evidence_meta'].get('former_names',[]))
  store.request('radar_universe',query='symbol=eq.'+symbol,rows={'aliases':list(dict.fromkeys(aliases))[-20:]},method='PATCH')
  refresh_market(store,symbol)
  news_jobs=refresh_company(store,symbol)
  if news_jobs:
   status=store.request('radar_status',query='select=*&id=eq.collector&limit=1');state=status[0]['payload'] if status else {}
   jobs={j['name']:j for j in state.get('jobs',[])}
   for j in news_jobs:jobs[j['name']]=j
   state['jobs']=list(jobs.values());store.request('radar_status',rows=[{'id':'collector','updated_at':datetime.now(timezone.utc).isoformat(),'payload':state}])
  result=company(store,symbol)
  if not store.rpc('radar_commit_research',{'p_owner':owner,'p_symbol':symbol,'p_snapshot':snapshot_row(symbol,result)}):raise CollectionError('Research lease expired; result requires recheck')
  return {'status':'complete','records':len(rows),'symbol':symbol}
 except Exception as exc:
  error=str(exc) if isinstance(exc,CollectionError) else type(exc).__name__
  store.rpc('radar_finish_research',{'p_owner':owner,'p_symbol':symbol,'p_error':error})
  return {'status':'retry','symbol':symbol,'records':0,'error':error}

def request_research(store,symbol):
 if not valid_symbol(symbol):raise ValueError('Invalid company ticker')
 directory=store.request('radar_universe',query='select=active&symbol=eq.'+symbol+'&limit=1')
 if not directory or not directory[0]['active']:raise ValueError('Company is not active in the official SEC directory')
 job=store.rpc('radar_enqueue',{'p_symbol':symbol,'p_reason':'search','p_priority':100})
 if job.get('status')=='daily_capacity':return {'status':'daily_capacity','symbol':symbol,'message':'The free research allowance is full; cached research remains available.'}
 if job.get('status')=='complete':
  refresh_market(store,symbol)
  refresh_company(store,symbol)
  result=company(store,symbol);snapshot(store,symbol,result)
  return {'status':'cached','symbol':symbol}
 if job.get('status') in ('queued','retry'):return process_one(store,symbol)
 return {'status':job.get('status','queued'),'symbol':symbol}

def background(store):
 deadline=time.monotonic()+240
 # Cached directory weekly; independently discover recent disclosures on every daily run.
 latest=store.request('radar_universe',query='select=retrieved_at&order=retrieved_at.desc&limit=1')
 now=datetime.now(timezone.utc)
 if not latest or (now-datetime.fromisoformat(latest[0]['retrieved_at'].replace('Z','+00:00'))).days>=7:refresh_directory(store)
 try:discovery=discover(store)
 except Exception as exc:discovery={'error':str(exc) if isinstance(exc,CollectionError) else type(exc).__name__,'candidates':[]}
 watch=store.request('radar_watchlists',query='select=symbol&limit=400')
 for row in list({r['symbol']:r for r in watch}.values())[:10]:
  try:store.rpc('radar_enqueue',{'p_symbol':row['symbol'],'p_reason':'watchlist','p_priority':70})
  except Exception:pass
 results=[]
 for _ in range(3):
  if time.monotonic()>deadline-125:break
  result=process_one(store);results.append(result)
  if result['status']=='queued_or_busy':break
 feeds=[]
 for name,url in [('fed_press','https://www.federalreserve.gov/feeds/press_all.xml'),('fed_speeches','https://www.federalreserve.gov/feeds/speeches.xml')]:
  if time.monotonic()>deadline-25:break
  try:
   rows=collect_feed(Fetch(min(deadline,time.monotonic()+25)),name,url)
   for i in range(0,len(rows),25):store.request('radar_events',rows=rows[i:i+25])
   feeds.append({'name':name,'status':'complete','last_success':datetime.now(timezone.utc).isoformat(),'records':len(rows),'last_error':None})
  except Exception as exc:feeds.append({'name':name,'status':'retry','last_error':type(exc).__name__})
 feeds.extend(collect_news(store,deadline=deadline))
 evaluation={}
 if time.monotonic()<deadline-20:
  try:
   from ._evaluation import run as evaluate
  except ImportError:
   from _evaluation import run as evaluate
  try:evaluation=evaluate(store)
  except Exception:evaluation={'status':'unavailable'}
 previous=store.request('radar_status',query='select=*&id=eq.collector&limit=1');state=previous[0]['payload'] if previous else {}
 jobs={j['name']:j for j in state.get('jobs',[])}
 for feed in feeds:jobs[feed['name']]={**jobs.get(feed['name'],{}),**feed}
 for result in results:
  if result.get('symbol'):
   name='sec:'+result['symbol'];old=jobs.get(name,{})
   jobs[name]={'name':name,'status':result['status'],'last_success':now.isoformat() if result['status']=='complete' else old.get('last_success'),
               'last_error':result.get('error'),'last_attempt':now.isoformat(),'records':result.get('records',0)}
 state.update({'discovery':discovery,'jobs':list(jobs.values()),'cadence':'daily_scheduled','collection_note':'Daily broad filing discovery with bounded deep research; on-demand search research is automatic.',
               'research_engine':ENGINE,'assistant_engine':'deterministic evidence assistant','market_feed':'authorized adapter; per-company cache reports actual availability','options_feed':'not_configured'})
 store.request('radar_status',rows=[{'id':'collector','updated_at':datetime.now(timezone.utc).isoformat(),'payload':state}])
 return {'status':'complete','discovery_matches':discovery.get('matched_companies',0),'research':results,'evaluation':evaluation,'records':sum(r.get('records',0) for r in results)}
