"""Persistent company research orchestration and honest decision snapshots."""
import json,re,time,uuid
from datetime import datetime,timezone
from urllib.parse import quote
try:
 from ._collector import Fetch,collect_company,collect_feed,CollectionError
 from ._research import enrich,financial_context
 from ._board import company_board
 from ._directory import refresh_directory,discover
except ImportError:
 from _collector import Fetch,collect_company,collect_feed,CollectionError
 from _research import enrich,financial_context
 from _board import company_board
 from _directory import refresh_directory,discover

ENGINE='evidence-research-v3'

def valid_symbol(s):return isinstance(s,str) and bool(re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,14}',s))

def company(store,symbol):
 if not valid_symbol(symbol):raise ValueError('Invalid company ticker')
 directory=store.request('radar_universe',query='select=*&symbol=eq.'+symbol+'&limit=1')
 if not directory:raise ValueError('Company not found in the official directory')
 rows=store.request('radar_events',query='select=*&tickers=cs.'+quote(json.dumps([symbol]))+'&order=published_at.desc&limit=600')
 now=datetime.now(timezone.utc)
 rows=[r for r in rows if datetime.fromisoformat(r['published_at'].replace('Z','+00:00'))<=now]
 events=enrich(rows);contexts={symbol:financial_context(events,symbol)}
 status=store.request('radar_status',query='select=*&id=eq.collector&limit=1');state=status[0]['payload'] if status else {}
 boards=company_board(events,contexts,state)
 for b in boards:b['name']=directory[0]['name']
 queue=store.request('radar_research_queue',query='select=symbol,status,reason,last_success,last_error,next_attempt,attempts&symbol=eq.'+symbol+'&limit=1')
 return {'company':directory[0],'events':events,'financial_context':contexts,'move_board':boards,'status':status,'queue':queue[0] if queue else None,
         'automatic_option_evaluation':{'action':'wait','reason':'Authorized options prices, confirmed catalyst timing, and documented expectations are not connected.'},
         'assistant_engine':'deterministic evidence assistant; AI model not configured'}

def snapshot(store,symbol,result):
 now=datetime.now(timezone.utc);events=result['events']
 available=[e for e in events if all(datetime.fromisoformat(e[k].replace('Z','+00:00'))<=now for k in ('retrieved_at','published_at'))]
 payload={'action':'wait','direction':'unverified','volatility_forecast':'unavailable','funding_crisis_probability':'unavailable',
          'source_ids':[e['id'] for e in available[:80]],'as_of':now.isoformat(),
          'summary':result['move_board'][0] if result['move_board'] else {},
          'limitations':['No executable options quotes','No consensus expectations','No out-of-sample validated forecasting model'],
          'forecast_issued':False,'model_enabled':False}
 store.request('radar_research_snapshots',rows=[{'id':str(uuid.uuid4()),'symbol':symbol,'engine_version':ENGINE,'payload':payload,
                 'target':'research_monitor','horizon_sessions':5,'evaluation_status':'market_data_unavailable'}],ignore=True)

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
  result=company(store,symbol);snapshot(store,symbol,result)
  if not store.rpc('radar_finish_research',{'p_owner':owner,'p_symbol':symbol,'p_error':None}):raise CollectionError('Research lease expired; result requires recheck')
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
 if job.get('status')=='complete':return {'status':'cached','symbol':symbol}
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
  if time.monotonic()>deadline-90:break
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
 previous=store.request('radar_status',query='select=*&id=eq.collector&limit=1');state=previous[0]['payload'] if previous else {}
 jobs={j['name']:j for j in state.get('jobs',[])}
 for feed in feeds:jobs[feed['name']]={**jobs.get(feed['name'],{}),**feed}
 for result in results:
  if result.get('symbol'):
   name='sec:'+result['symbol'];old=jobs.get(name,{})
   jobs[name]={'name':name,'status':result['status'],'last_success':now.isoformat() if result['status']=='complete' else old.get('last_success'),
               'last_error':result.get('error'),'last_attempt':now.isoformat(),'records':result.get('records',0)}
 state.update({'discovery':discovery,'jobs':list(jobs.values()),'cadence':'daily_scheduled','collection_note':'Daily broad filing discovery with bounded deep research; on-demand search research is automatic.',
               'research_engine':ENGINE,'assistant_engine':'deterministic evidence assistant','market_feed':'not_configured','options_feed':'not_configured'})
 store.request('radar_status',rows=[{'id':'collector','updated_at':datetime.now(timezone.utc).isoformat(),'payload':state}])
 return {'status':'complete','discovery_matches':discovery.get('matched_companies',0),'research':results,'records':sum(r.get('records',0) for r in results)}
